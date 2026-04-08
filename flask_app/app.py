"""
Flask Application for Course Recommendation System
Hệ thống gợi ý kế hoạch học tập dựa trên Ontology
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os
import sys

# Add parent directory to path to import StudentDataStandardization modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_app.config import Config
from flask_app.services.student_data_service import StudentDataService
from flask_app.services.recommendation_engine import RecommendationEngine
from flask_app.services.explanation_generator import ExplanationGenerator


def create_app():
    """Application Factory"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    app.config.from_object(Config)
    
    # Initialize services
    app.student_data_service = StudentDataService(
        json_path=Config.STUDENT_DATA_JSON,
        csv_path=Config.STUDENT_DATA_CSV
    )
    
    # Initialize recommendation engine (lazy load ontology)
    try:
        app.recommendation_engine = RecommendationEngine(
            ontology_path=Config.ONTOLOGY_PATH,
            beam_width=Config.BEAM_WIDTH,
            max_credits=Config.REGISTER_MAX_CREDITS,
            min_credits=Config.REGISTER_MIN_CREDITS,
            heuristic_weights={
                'debt': Config.WEIGHT_DEBT,
                'link': Config.WEIGHT_LINK,
                'delay': Config.WEIGHT_DELAY,
            },
            elective_quotas=Config.ELECTIVE_QUOTAS,
        )
    except Exception as e:
        print(f"Warning: Error initializing RecommendationEngine: {e}")
        print("The engine will be initialized on first request")
        app.recommendation_engine = None
    
    app.explanation_generator = ExplanationGenerator()
    
    # Register blueprints (API routes)
    from flask_app.routes import student_routes, recommendation_routes
    app.register_blueprint(student_routes.bp)
    app.register_blueprint(recommendation_routes.bp)
    
    # Register template routes AFTER blueprints
    @app.route('/')
    def index():
        """Home page"""
        return render_template('index.html')

    @app.route('/students')
    def students_page():
        """Students page with recommendation interface"""
        print("[DEBUG] Route /students accessed")
        return render_template('students.html')

    @app.route('/students/new')
    def create_student_page():
        """Add new student page"""
        return render_template('add_student.html')

    @app.route('/students/<student_id>/course-history')
    def student_course_history_page(student_id):
        """Student passed/failed course history page"""
        student = app.student_data_service.get_student(student_id)
        if not student:
            return render_template(
                'student_course_history.html',
                student=None,
                error=f'Không tìm thấy sinh viên {student_id}',
                passed_rows=[],
                failed_rows=[],
            ), 404

        engine = getattr(app, 'recommendation_engine', None)
        course_data = getattr(engine, 'course_data', {}) if engine is not None else {}

        def build_rows(codes, status_label):
            rows = []
            for idx, code in enumerate(codes, start=1):
                info = course_data.get(code, {}) if isinstance(course_data, dict) else {}
                rows.append({
                    'stt': idx,
                    'code': code,
                    'name': info.get('name') or code,
                    'credits': info.get('credit') if info else None,
                    'grade': student.course_grades.get(code) if student.course_grades else None,
                    'status': status_label,
                })
            return rows

        passed_rows = build_rows(student.passed_courses or [], 'Đạt')
        failed_rows = build_rows(student.failed_courses or [], 'Chưa đạt')

        all_rows = (passed_rows or []) + (failed_rows or [])

        allowed_page_sizes = (10, 20, 50)
        page_size = request.args.get('per_page', 10, type=int) or 10
        if page_size not in allowed_page_sizes:
            page_size = 10

        page = request.args.get('page', 1, type=int) or 1
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

        # Build compact page number list with ellipses (None)
        page_numbers = []
        if total_pages <= 7:
            page_numbers = list(range(1, total_pages + 1))
        else:
            candidates = {1, total_pages, page, page - 1, page + 1}
            candidates = sorted([p for p in candidates if 1 <= p <= total_pages])
            last = None
            for p in candidates:
                if last is not None and p - last > 1:
                    page_numbers.append(None)  # ellipsis
                page_numbers.append(p)
                last = p

        return render_template(
            'student_course_history.html',
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
            base_url=f'/students/{student.student_id}/course-history',
        )
    
    return app


# Create Flask app
app = create_app()


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'success': False, 'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
