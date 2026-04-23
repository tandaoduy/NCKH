"""
Các route của luồng gợi ý kế hoạch học tập.
"""

from datetime import datetime
import time

from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("recommendations", __name__, url_prefix="/api")


@bp.route("/recommendations", methods=["POST"])
@bp.route("/recommend", methods=["POST"])
def get_recommendation():
    """Sinh gợi ý kế hoạch học tập cho một sinh viên."""
    started_at = time.perf_counter()
    student_id = None

    try:
        if current_app.recommendation_engine is None:
            return jsonify({
                "success": False,
                "error": "Bộ máy gợi ý chưa sẵn sàng. Vui lòng kiểm tra đường dẫn ontology.",
            }), 500

        data = request.get_json(silent=True) or {}
        student_id = str(data.get("student_id", "")).strip()

        if not student_id:
            return jsonify({
                "success": False,
                "error": "student_id không được để trống",
            }), 400

        current_app.logger.info(
            "Đã nhận yêu cầu gợi ý: student_id=%s endpoint=%s",
            student_id,
            request.path,
        )

        student_service = current_app.student_data_service
        student = student_service.get_student(student_id)

        if not student:
            return jsonify({
                "success": False,
                "error": f"Không tìm thấy sinh viên {student_id}",
            }), 404

        errors = student.validate()
        if errors:
            return jsonify({
                "success": False,
                "error": "Dữ liệu sinh viên không hợp lệ",
                "details": errors,
            }), 400

        engine = current_app.recommendation_engine
        result = engine.get_recommendation(student)

        result.generated_at = datetime.now().isoformat()
        result.processing_time_ms = round((time.perf_counter() - started_at) * 1000, 2)

        explanation_generator = getattr(current_app, "explanation_generator", None)
        explanation_text = ""
        if explanation_generator is not None:
            max_credits = current_app.config.get("REGISTER_MAX_CREDITS", 27)
            explanation_text = explanation_generator.generate_recommendation_summary(
                result,
                max_credits=max_credits,
            )

        current_app.logger.info(
            "Đã hoàn tất gợi ý: student_id=%s eligible=%s recommended=%s credits=%s duration_ms=%s",
            student_id,
            result.total_eligible_count,
            result.total_recommended_count,
            result.total_recommended_credits,
            result.processing_time_ms,
        )

        payload = result.to_dict()
        payload["explanation"] = explanation_text

        return jsonify({
            "success": True,
            "data": payload,
        })

    except Exception as exc:
        current_app.logger.exception("Không thể xử lý gợi ý cho student_id=%s", student_id)
        return jsonify({
            "success": False,
            "error": f"Lỗi xử lý: {str(exc)}",
        }), 500
