"""
Ứng dụng Flask cho hệ thống gợi ý kế hoạch học tập.
"""

from datetime import datetime
import logging
import os
import sys
import time

from flask import Flask, current_app, jsonify, render_template, request

# Thêm thư mục gốc vào `sys.path` để nhập các mô-đun nội bộ.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_app.config import Config
from flask_app.services.explanation_generator import ExplanationGenerator
from flask_app.services.recommendation_engine import RecommendationEngine
from flask_app.services.student_data_service import StudentDataService


def create_app():
    """Nhà máy khởi tạo ứng dụng Flask."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    app.config.from_object(Config)

    # Giữ phản hồi JSON dễ đọc trên demo và không tự sắp xếp khóa.
    try:
        app.json.ensure_ascii = False
        app.json.sort_keys = False
    except Exception:
        pass

    app.logger.setLevel(logging.INFO)

    # Khởi tạo các dịch vụ nền.
    app.student_data_service = StudentDataService(
        json_path=Config.STUDENT_DATA_JSON,
        csv_path=Config.STUDENT_DATA_CSV,
    )

    # Khởi tạo bộ máy gợi ý, nạp ontology theo kiểu lười nếu cần.
    try:
        app.recommendation_engine = RecommendationEngine(
            ontology_path=Config.ONTOLOGY_PATH,
            beam_width=Config.BEAM_WIDTH,
            max_credits=Config.REGISTER_MAX_CREDITS,
            min_credits=Config.REGISTER_MIN_CREDITS,
            heuristic_weights={
                "debt": Config.WEIGHT_DEBT,
                "link": Config.WEIGHT_LINK,
                "delay": Config.WEIGHT_DELAY,
            },
            elective_quotas=Config.ELECTIVE_QUOTAS,
        )
    except Exception as exc:
        print(f"Cảnh báo: lỗi khi khởi tạo RecommendationEngine: {exc}")
        print("Bộ máy sẽ được khởi tạo ở lần yêu cầu đầu tiên.")
        app.recommendation_engine = None

    app.explanation_generator = ExplanationGenerator()

    # Đăng ký các blueprint cho API.
    from flask_app.routes import recommendation_routes, student_routes

    app.register_blueprint(student_routes.bp)
    app.register_blueprint(recommendation_routes.bp)

    # Đăng ký các route giao diện sau khi đã đăng ký blueprint.
    @app.route("/")
    def index():
        """Trang chủ."""
        return render_template("index.html")

    @app.route("/students")
    def students_page():
        """Trang sinh viên với giao diện gợi ý."""
        current_app.logger.info("Đã truy cập route /students")
        return render_template("students.html")

    @app.route("/students/new")
    def create_student_page():
        """Trang thêm sinh viên mới."""
        return render_template("add_student.html")

    @app.route("/students/<student_id>/course-history")
    def student_course_history_page(student_id):
        """Trang chi tiết lịch sử môn học của sinh viên."""
        student = app.student_data_service.get_student(student_id)
        if not student:
            return render_template(
                "student_course_history.html",
                student=None,
                error=f"Không tìm thấy sinh viên {student_id}",
                passed_rows=[],
                failed_rows=[],
            ), 404

        engine = getattr(app, "recommendation_engine", None)
        course_data = getattr(engine, "course_data", {}) if engine is not None else {}

        def build_rows(codes, status_label):
            rows = []
            for idx, code in enumerate(codes, start=1):
                info = course_data.get(code, {}) if isinstance(course_data, dict) else {}
                rows.append({
                    "stt": idx,
                    "code": code,
                    "name": info.get("name") or code,
                    "credits": info.get("credit") if info else None,
                    "grade": student.course_grades.get(code) if student.course_grades else None,
                    "status": status_label,
                })
            return rows

        passed_rows = build_rows(student.passed_courses or [], "Đạt")
        failed_rows = build_rows(student.failed_courses or [], "Chưa đạt")

        all_rows = (passed_rows or []) + (failed_rows or [])
        allowed_page_sizes = (10, 20, 50)
        page_size = request.args.get("per_page", 10, type=int) or 10
        if page_size not in allowed_page_sizes:
            page_size = 10

        page = request.args.get("page", 1, type=int) or 1
        if page < 1:
            page = 1

        total_rows = len(all_rows)
        total_pages = max(1, (total_rows + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paged_rows = all_rows[start_index:end_index]

        display_from = 0 if total_rows == 0 else (start_index + 1)
        display_to = min(start_index + len(paged_rows), total_rows)

        # Tạo danh sách số trang gọn, chèn dấu ba chấm bằng `None`.
        page_numbers = []
        if total_pages <= 7:
            page_numbers = list(range(1, total_pages + 1))
        else:
            candidates = {1, total_pages, page, page - 1, page + 1}
            candidates = sorted([p for p in candidates if 1 <= p <= total_pages])
            last = None
            for p in candidates:
                if last is not None and p - last > 1:
                    page_numbers.append(None)  # dấu ba chấm
                page_numbers.append(p)
                last = p

        return render_template(
            "student_course_history.html",
            student=student,
            error=None,
            passed_rows=passed_rows,
            failed_rows=failed_rows,
            paged_rows=paged_rows,
            page=page,
            page_size=page_size,
            total_rows=total_rows,
            total_pages=total_pages,
            start_index=start_index,
            display_from=display_from,
            display_to=display_to,
            page_numbers=page_numbers,
            base_url=f"/students/{student.student_id}/course-history",
        )

    @app.route("/api/health")
    def health_check():
        """Endpoint kiểm tra nhanh trạng thái hệ thống."""
        engine = getattr(app, "recommendation_engine", None)
        student_service = getattr(app, "student_data_service", None)
        student_count = 0
        if student_service is not None:
            try:
                student_count = len(student_service.get_all_students())
            except Exception as exc:
                app.logger.warning("Không thể nạp danh sách sinh viên khi kiểm tra trạng thái: %s", exc)

        return jsonify({
            "success": True,
            "data": {
                "status": "ok",
                "student_service_ready": student_service is not None,
                "recommendation_engine_ready": engine is not None,
                "ontology_loaded": bool(engine and getattr(engine, "course_data", None)),
                "course_count": len(getattr(engine, "course_data", {}) or {}),
                "specialization_count": len(getattr(engine, "specializations_map", {}) or {}),
                "student_count": student_count,
            }
        })

    @app.route("/api/debug/pipeline/<student_id>")
    def debug_pipeline(student_id):
        """Endpoint gỡ lỗi đầu-cuối để chứng minh luồng chạy thật."""
        started_at = time.perf_counter()
        engine = getattr(app, "recommendation_engine", None)
        student = app.student_data_service.get_student(student_id)

        if student is None:
            return jsonify({
                "success": False,
                "error": f"Không tìm thấy sinh viên {student_id}",
            }), 404

        if engine is None:
            return jsonify({
                "success": False,
                "error": "Bộ máy gợi ý chưa sẵn sàng",
            }), 500

        result = engine.get_recommendation(student)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        result.processing_time_ms = elapsed_ms

        return jsonify({
            "success": True,
            "data": {
                "student": student.to_dict(),
                "course_count": len(getattr(engine, "course_data", {}) or {}),
                "eligible_count": result.total_eligible_count,
                "recommended_count": result.total_recommended_count,
                "total_recommended_credits": result.total_recommended_credits,
                "processing_time_ms": elapsed_ms,
                "result": result.to_dict(),
            }
        })

    return app


# Tạo ứng dụng Flask.
app = create_app()


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"success": False, "error": "Không tìm thấy tài nguyên"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Lỗi máy chủ nội bộ"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
