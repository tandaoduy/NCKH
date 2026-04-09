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


@bp.route('/next-id', methods=['GET'])
def get_next_student_id():
    """Lấy mã sinh viên kế tiếp theo format SV0001"""
    try:
        service = current_app.student_data_service
        next_id = service.get_next_student_id(force_reload=True)
        return jsonify({
            'success': True,
            'data': {
                'student_id': next_id,
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@bp.route('', methods=['POST'])
def create_student():
    """Tạo mới sinh viên và lưu vào JSON"""
    try:
        payload = request.get_json() or {}
        if not payload:
            return jsonify({
                'success': False,
                'error': 'Không nhận được dữ liệu sinh viên',
            }), 400

        engine = current_app.recommendation_engine
        if engine is None:
            return jsonify({
                'success': False,
                'error': 'Recommendation engine chưa sẵn sàng để tải dữ liệu',
            }), 500

        course_catalog = _get_course_catalog(engine)
        specialization_options = _get_specializations(engine)
        student = current_app.student_data_service.create_student(
            payload,
            course_catalog,
            specialization_options,
        )

        return jsonify({
            'success': True,
            'message': f'Đã thêm sinh viên {student.student_id}',
            'data': student.to_dict(),
        }), 201
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@bp.route('/courses', methods=['GET'])
def list_courses():
    """Lấy danh mục môn học từ ontology"""
    try:
        engine = current_app.recommendation_engine
        if engine is None:
            return jsonify({
                'success': False,
                'error': 'Recommendation engine không khởi tạo được',
            }), 500

        catalog = sorted(
            _get_course_catalog(engine).values(),
            key=lambda item: (item['code'], item['name'])
        )

        return jsonify({
            'success': True,
            'data': catalog,
            'total': len(catalog),
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@bp.route('/specializations', methods=['GET'])
def list_specializations():
    """Lấy danh sách chuyên ngành từ ontology"""
    try:
        engine = current_app.recommendation_engine
        if engine is None:
            return jsonify({
                'success': False,
                'error': 'Recommendation engine không khởi tạo được',
            }), 500

        options = _get_specializations(engine)
        return jsonify({
            'success': True,
            'data': options,
            'total': len(options),
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


def _get_course_catalog(engine) -> dict:
    catalog = {}
    for code, info in engine.course_data.items():
        catalog[code] = {
            'code': code,
            'name': info.get('name', code),
            'credits': info.get('credit', 0),
        }
    return catalog


def _get_specializations(engine) -> list:
    options = sorted({name.strip() for name in engine.specializations_map.values() if isinstance(name, str) and name.strip()})
    return options
