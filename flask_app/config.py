"""
Configuration for Flask Application
"""

import os

class Config:
    """Base Configuration"""
    
    # Flask config
    DEBUG = True
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Paths - Build dynamically from current file location
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    ONTOLOGY_PATH = os.path.join(BASE_DIR, 'owl', 'ontology_v18.rdf')
    STUDENT_DATA_JSON = os.path.join(BASE_DIR, 'StudentDataStandardization', 'DanhSachSinhVien.json')
    STUDENT_DATA_CSV = os.path.join(BASE_DIR, 'StudentDataStandardization', 'DanhSachSinhVien.csv')
    REPORT_OUTPUT_DIR = os.path.join(BASE_DIR, 'StudentDataStandardization', 'reports')
    
    # Recommendation Engine Parameters
    BEAM_WIDTH = 8
    REGISTER_MAX_CREDITS = 27
    REGISTER_MIN_CREDITS = 10
    
    # Heuristic Weights
    WEIGHT_DEBT = 1000
    WEIGHT_LINK = 20
    WEIGHT_DELAY = 50
    
    # Elective Quotas (default - can be customized by study goal)
    ELECTIVE_QUOTAS = {
        'general': 1,           # Môn đại cương tự chọn
        'physical': 2,          # Môn thể chất tự chọn
        'foundation': 1,        # Môn cơ sở ngành tự chọn
        'specialization': 3,    # Môn chuyên ngành tự chọn
    }
    
    # Study goals
    STUDY_GOALS = ['đúng hạn', 'giảm tải', 'học vượt']
    
    # Majors
    MAJORS = ['Công Nghệ Thông Tin', 'Kỹ Thuật Phần Mềm', 'Khoa Học Dữ Liệu']


class DevelopmentConfig(Config):
    """Development Configuration"""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing Configuration"""
    TESTING = True
    DEBUG = True


class ProductionConfig(Config):
    """Production Configuration"""
    DEBUG = False
    TESTING = False
