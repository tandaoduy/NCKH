"""
Simple startup script for Flask app
This handles environment setup and provides helpful output
"""

import sys
import os
from pathlib import Path

def setup_environment():
    """Setup Python environment for Flask app"""
    # Ensure UTF-8 encoding on Windows
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Add parent directory to path if needed
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def main():
    """Start Flask app"""
    setup_environment()
    
    print("\n" + "=" * 70)
    print("Hệ Thống Gợi Ý Kế Hoạch Học Tập")
    print("=" * 70)
    print("\nDựa trên Ontology & Beam Search Algorithm")
    print("Mục tiêu: Hỗ trợ sinh viên lập kế hoạch học tập cá nhân hóa\n")
    
    # Verify setup before starting
    print("Verifying setup...");
    
    try:
        from flask_app.config import Config
        print(f"  Configuration loaded")
        print(f"     - Ontology: {Config.ONTOLOGY_PATH}")
        print(f"     - Student data: {Config.STUDENT_DATA_JSON}")
        
        from flask_app.services.student_data_service import StudentDataService
        service = StudentDataService(Config.STUDENT_DATA_JSON, Config.STUDENT_DATA_CSV)
        students = service.get_all_students()
        print(f"  Student data loaded: {len(students)} students\n")
        
    except Exception as e:
        print(f"  Setup verification failed: {e}\n")
        print("Please run:")
        print("  python test_setup.py")
        print("\nto diagnose the issue.")
        sys.exit(1)
    
    # Start Flask app
    print("🌐 Starting Flask app...")
    print("=" * 70)
    print("\nApplication URL: http://localhost:5000")
    print("API Base: http://localhost:5000/api")
    print("\nAPIs:")
    print("   - GET /api/students - Danh sách sinh viên")
    print("   - GET /api/students/<id> - Thông tin chi tiết")
    print("   - POST /api/recommendations - Tạo gợi ý\n")
    print("Press Ctrl+C to stop the server")
    print("=" * 70 + "\n")
    
    try:
        from flask_app.app import app
        app.run(debug=True, port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nServer stopped")
    except Exception as e:
        print(f"\nError starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
