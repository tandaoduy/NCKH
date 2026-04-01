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
