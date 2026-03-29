"""
Routes for Student data management
"""

from flask import Blueprint, request, jsonify, current_app

bp = Blueprint('students', __name__, url_prefix='/api/students')


@bp.route('', methods=['GET'])
def list_students():
    """Lấy danh sách tất cả sinh viên"""
    try:
        service = current_app.student_data_service
        students = service.get_all_students()
        
        result = [
            {
                'student_id': s.student_id,
                'name': s.name,
                'major': s.major,
                'specialization': s.specialization,
                'current_semester': s.current_semester,
            }
            for s in students
        ]
        
        return jsonify({
            'success': True,
            'data': result,
            'total': len(result),
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@bp.route('/<student_id>', methods=['GET'])
def get_student(student_id: str):
    """Lấy thông tin chi tiết một sinh viên"""
    try:
        service = current_app.student_data_service
        student = service.get_student(student_id)
        
        if not student:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy sinh viên {student_id}',
            }), 404
        
        return jsonify({
            'success': True,
            'data': student.to_dict(),
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
