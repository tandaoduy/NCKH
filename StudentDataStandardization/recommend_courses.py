import json
import os
import sys
import io
from typing import Dict, Any, List, Set, Optional, cast
from rdflib import Graph, URIRef  # type: ignore
from rdflib.namespace import RDF  # type: ignore

# Fix UTF-8 output trên Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

BASE_URI = "http://www.semanticweb.org/henrydao/ontologies/2025/7/TrainingProgramOntology#"

PROP_courseCode: Any = URIRef(BASE_URI + "courseCode")
PROP_courseName: Any = URIRef(BASE_URI + "courseName")
PROP_hasPrerequisiteCourse: Any = URIRef(BASE_URI + "hasPrerequisiteCourse")
PROP_openSemesterType: Any = URIRef(BASE_URI + "openSemesterType")
PROP_recommendedInSemester: Any = URIRef(BASE_URI + "recommendedInSemester")
PROP_specializationName: Any = URIRef(BASE_URI + "specializationName")
PROP_isRequiredForSpecialization: Any = URIRef(BASE_URI + "isRequiredForSpecialization")
PROP_isElectiveForSpecialization: Any = URIRef(BASE_URI + "isElectiveForSpecialization")
PROP_offeredInSpecialization: Any = URIRef(BASE_URI + "offeredInSpecialization")
PROP_isRequiredForMajor: Any = URIRef(BASE_URI + "isRequiredForMajor")
PROP_isElectiveForMajor: Any = URIRef(BASE_URI + "isElectiveForMajor")
PROP_hasCredit: Any = URIRef(BASE_URI + "hasCredit")
PROP_corequisiteWith: Any = URIRef(BASE_URI + "corequisiteWith")
CLASS_Specialization: Any = URIRef(BASE_URI + "Specialization")
CLASS_GeneralEducationCourse: Any = URIRef(BASE_URI + "GeneralEducationCourse")
CLASS_PhysicalEducationCourse: Any = URIRef(BASE_URI + "PhysicalEducationCourse")
CLASS_FoundationCourse: Any = URIRef(BASE_URI + "FoundationCourse")

# Giới hạn số tín chỉ tối đa/tối thiểu cho một học kỳ
REGISTER_MAX_CREDITS = 27
REGISTER_MIN_CREDITS = 10

def main() -> None:
    json_path = r"d:\NTU\CNTT\NCKH\Code\StudentDataStandardization\DanhSachSinhVien.json"
    rdf_path = r"d:\NTU\CNTT\NCKH\Code\owl\ontology_v17.rdf"
    output_path = r"d:\NTU\CNTT\NCKH\Code\StudentDataStandardization\DanhSachMonHoc.json"
    
    # Yêu cầu người dùng nhập mã sinh viên
    target_student_id = input("Nhập mã sinh viên cần tra cứu: ").strip()
    
    if not target_student_id:
        print("Vui lòng nhập mã sinh viên hợp lệ!")
        return

    print(f"\nĐang đọc dữ liệu hồ sơ sinh viên từ {json_path}...")
    if not os.path.exists(json_path):
        print("Không tìm thấy file JSON danh sách sinh viên!")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        students = json.load(f)
        
    # Tìm sinh viên
    target_student_raw = None
    if isinstance(students, list):
        for s in students:
            if isinstance(s, dict) and s.get("mã sinh viên") == target_student_id:
                target_student_raw = s
                break
            
    if target_student_raw is None:
        print(f"Không tìm thấy sinh viên")
        return
        
    target_student = cast(Dict[str, Any], target_student_raw)
    g: Any = Graph()
    g.parse(rdf_path, format="xml")
    
    # 1. Trích xuất thông tin môn học và chuyên ngành
    # Tìm tên các chuyên ngành
    specializations_map: Dict[str, str] = {}
    for spec in g.subjects(RDF.type, CLASS_Specialization):
        if isinstance(spec, URIRef):
            val = g.value(spec, PROP_specializationName)
            if val is not None:
                specializations_map[str(spec)] = str(val)
        
    course_data: Dict[str, Dict[str, Any]] = {}
    for course in g.subjects(PROP_courseCode, None):
        code_val_node = g.value(course, PROP_courseCode)
        if code_val_node is None:
            continue
        code = str(code_val_node)
        
        name_val = g.value(course, PROP_courseName)
        name = str(name_val) if name_val is not None else code
        
        prereqs: List[str] = []
        for p in g.objects(course, PROP_hasPrerequisiteCourse):
            p_code = g.value(p, PROP_courseCode)
            if p_code is not None:
                prereqs.append(str(p_code))
                
        open_sem = g.value(course, PROP_openSemesterType)
        open_sem_val = int(open_sem) if open_sem is not None else 3
        
        # Học kỳ khuyến nghị
        recommended_sem_val = 99999
        sem_uri = g.value(course, PROP_recommendedInSemester)
        if sem_uri is not None:
            sem_str = str(sem_uri).split('#')[-1] 
            if sem_str.startswith("Semester"):
                try:
                    recommended_sem_val = int(sem_str.replace("Semester", ""))
                except ValueError:
                    pass
                    
        # Lấy thông tin môn học thuộc chuyên ngành nào
        linked_specializations: Set[str] = set()
        is_required_for_specialization = False
        is_elective_for_specialization = False
        is_offered_specialization = False
        for spec_uri in g.objects(course, PROP_isRequiredForSpecialization):
            is_required_for_specialization = True
            if isinstance(spec_uri, URIRef):
                spec_name = specializations_map.get(str(spec_uri))
                if spec_name:
                    linked_specializations.add(spec_name)
        for spec_uri in g.objects(course, PROP_isElectiveForSpecialization):
            is_elective_for_specialization = True
            if isinstance(spec_uri, URIRef):
                spec_name = specializations_map.get(str(spec_uri))
                if spec_name:
                    linked_specializations.add(spec_name)
        for spec_uri in g.objects(course, PROP_offeredInSpecialization):
            is_offered_specialization = True
            if isinstance(spec_uri, URIRef):
                spec_name = specializations_map.get(str(spec_uri))
                if spec_name:
                    linked_specializations.add(spec_name)

        # Xét môn song hành nếu ontology đã có corequisiteWith
        coreqs: List[str] = []
        for co in g.objects(course, PROP_corequisiteWith):
            if isinstance(co, URIRef):
                coreq_code = g.value(co, PROP_courseCode)
                if coreq_code is not None:
                    coreqs.append(str(coreq_code))

        # Lấy tín chỉ
        credits_val = g.value(course, PROP_hasCredit)
        try:
            credits = int(credits_val) if credits_val is not None else 0
        except Exception:
            credits = 0

        # Xác định loại môn
        is_general_education = any(str(t).endswith('#GeneralEducationCourse') for t in g.objects(course, RDF.type))
        is_physical_education = any(str(t).endswith('#PhysicalEducationCourse') for t in g.objects(course, RDF.type))
        is_foundation_course = any(str(t).endswith('#FoundationCourse') for t in g.objects(course, RDF.type))

        is_required_for_major = any(True for _ in g.objects(course, PROP_isRequiredForMajor))
        is_elective_for_major = any(True for _ in g.objects(course, PROP_isElectiveForMajor))

        # Phân loại độ ưu tiên / đại cương
        course_data[code] = {
            'name': name,
            'prereqs': prereqs,
            'openSemesterType': open_sem_val,
            'recommended_sem': recommended_sem_val,
            'specializations': list(linked_specializations),
            'is_required_specialization': is_required_for_specialization,
            'is_elective_specialization': is_elective_for_specialization,
            'is_offered_specialization': is_offered_specialization,
            'is_required_major': is_required_for_major,
            'is_elective_major': is_elective_for_major,
            'is_general_education_course': is_general_education,
            'is_physical_education_course': is_physical_education,
            'is_foundation_course': is_foundation_course,
            'corequisites': coreqs,
            'credit': credits,
        }
        
    print(f"Đã tải {len(course_data)} môn học.")
    
    # 2. Xử lý cho sinh viên được chọn
    current_sem = target_student.get("học kỳ hiện tại", 1)
    if not isinstance(current_sem, int):
        current_sem = 1
        
    next_sem = current_sem + 1
    sem_type = 1 if next_sem % 2 != 0 else 2
    
    student_spec = target_student.get("chuyên ngành chọn", "")
    if not isinstance(student_spec, str):
        student_spec = ""
        
    print(f"\nSinh viên {target_student.get('tên sinh viên', '')} đang ở học kỳ {current_sem}, chuẩn bị đăng ký cho học kỳ {next_sem} (Loại học kỳ: {'Lẻ' if sem_type == 1 else 'Chẵn'})")
    print(f"Chuyên ngành đã đăng ký: {student_spec if student_spec else 'Chưa chọn'}")
    
    passed_courses: Set[str] = set()
    failed_courses: Set[str] = set()
    
    diem_tung_mon = target_student.get("điểm từng môn", [])
    if isinstance(diem_tung_mon, list):
        for c in diem_tung_mon:
            if isinstance(c, dict):
                m = c.get("mã môn học")
                if not m or not isinstance(m, str):
                    continue
                if c.get("Trạng thái") == "Đạt":
                    passed_courses.add(m)
                    
    ds_chua_dat = target_student.get("danh sách môn chưa đạt", [])
    if isinstance(ds_chua_dat, list):
        for c in ds_chua_dat:
            if isinstance(c, dict):
                m = c.get("mã môn học")
                if m and isinstance(m, str):
                    failed_courses.add(m)
            
    valid_courses: List[Dict[str, Any]] = []
    
    for code, info in course_data.items():
        # Bỏ qua nếu đã đạt
        if code in passed_courses:
            continue

        # Kiểm tra môn tiên quyết
        prereqs_met = all(p in passed_courses for p in info.get('prereqs', []))

        # Kiểm tra học kỳ mở môn (1: Lẻ, 2: Chẵn, 3: Cả hai, 12: Cả hai)
        open_sem_info = info.get('openSemesterType', 3)
        sem_ok = (open_sem_info in (3, 12) or open_sem_info == sem_type)

        # Kiểm tra môn học có được đề xuất từ học kỳ này trở về trước không (tính cả học lại các kỳ trước)
        rec_sem_info = info.get('recommended_sem', 99)
        recommended_ok = (rec_sem_info <= next_sem)

        # Môn trượt có thể đăng ký học lại nếu được mở
        is_retake = (code in failed_courses)

        # Xử lý trường hợp sinh viên chưa chọn chuyên ngành
        spec_ok = True
        specs: List[str] = info.get('specializations', [])
        if student_spec:
            if specs and student_spec not in specs:
                spec_ok = False
        else:
            # sinh viên chưa chọn chuyên ngành: cho phép đại cương (không chuyên ngành) và cơ sở ngành (bắt buộc chuyên ngành)
            if specs and not info.get('is_required_specialization', False):
                spec_ok = False

        if prereqs_met and sem_ok and (recommended_ok or is_retake) and spec_ok:
            valid_courses.append({
                "mã môn học": code,
                "tên môn học": info.get('name', ''),
                "là môn học lại": is_retake,
                "học kỳ đề xuất": rec_sem_info,
                "thuộc chuyên ngành": specs,
                "tín chỉ": info.get('credit', 0),
                "corequisites": info.get('corequisites', [])
            })

    #  Ưu tiên môn học lại, sau đó theo học kỳ đề xuất
    valid_courses.sort(key=lambda x: (not x.get("là môn học lại", False), x.get("học kỳ đề xuất", 99)))

    # Chia nhóm: bắt buộc / đại cương tự chọn / thể chất tự chọn / còn lại
    required_courses = []
    general_electives = []
    physical_electives = []
    other_courses = []

    for c in valid_courses:
        code_ = c['mã môn học']
        info = course_data.get(code_, {})
        is_required = (
            c.get('là môn học lại', False)
            or info.get('is_required_specialization', False)
            or info.get('is_required_major', False)
            or info.get('is_foundation_course', False)
        )
        if is_required:
            required_courses.append(c)
        elif info.get('is_general_education_course', False):
            general_electives.append(c)
        elif info.get('is_physical_education_course', False):
            physical_electives.append(c)
        else:
            other_courses.append(c)

    def pick_one(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        return min(candidates, key=lambda x: (not x.get('là môn học lại', False), x.get('học kỳ đề xuất', 99)))

    # Chọn 1 môn đại cương tự chọn và 1 môn thể chất tự chọn (nếu có)
    selected_candidates = list(required_courses)
    chosen_gen = pick_one(general_electives)
    if chosen_gen:
        selected_candidates.append(chosen_gen)
    chosen_phys = pick_one(physical_electives)
    if chosen_phys:
        selected_candidates.append(chosen_phys)

    # Bổ sung các môn còn lại (không thuộc nhóm đại cương/tự chọn thể chất) nếu cần
    selected_candidates.extend(other_courses)

    eligible_codes = {c['mã môn học'] for c in selected_candidates}
    course_index = {c['mã môn học']: c for c in selected_candidates}

    def resolve_coreq_bundle(code_: str) -> Optional[Set[str]]:
        bundle = set()
        stack = [code_]
        while stack:
            ccc = stack.pop()
            if ccc in bundle:
                continue
            bundle.add(ccc)
            coreqs = course_data.get(ccc, {}).get('corequisites', [])
            for co in coreqs:
                if co in passed_courses:
                    continue
                if co not in eligible_codes:
                    return None
                if co not in bundle:
                    stack.append(co)
        return bundle

    selected_courses: List[Dict[str, Any]] = []
    selected_codes: Set[str] = set()
    total_credit = 0

    student_max_credit = REGISTER_MAX_CREDITS
    student_request_max = target_student.get('số tín chỉ đăng ký tối đa', REGISTER_MAX_CREDITS)
    if isinstance(student_request_max, int):
        student_max_credit = min(REGISTER_MAX_CREDITS, student_request_max)

    for item in selected_candidates:
        code_ = item['mã môn học']
        if code_ in selected_codes:
            continue

        bundle_codes = resolve_coreq_bundle(code_)
        if bundle_codes is None:
            bundle_codes = {code_}

        bundle_codes = {c for c in bundle_codes if c not in selected_codes}
        bundle_credit = sum(course_data.get(c, {}).get('credit', 0) for c in bundle_codes)

        if total_credit + bundle_credit > student_max_credit:
            continue

        for c in bundle_codes:
            if c not in selected_codes:
                selected_codes.add(c)
                course_obj = course_index.get(c)
                if course_obj:
                    selected_courses.append(course_obj)
        total_credit += bundle_credit

        if total_credit >= student_max_credit:
            break

    if total_credit < REGISTER_MIN_CREDITS:
        for item in valid_courses:
            code_ = item['mã môn học']
            if code_ in selected_codes:
                continue
            credit = item.get('tín chỉ', 0)
            if total_credit + credit <= student_max_credit:
                selected_codes.add(code_)
                selected_courses.append(item)
                total_credit += credit
                if total_credit >= REGISTER_MIN_CREDITS:
                    break

    valid_courses = selected_courses

            
    student_result: Dict[str, Any] = {
        "mã sinh viên": target_student_id,
        "tên sinh viên": target_student.get("tên sinh viên", ""),
        "năm vào học": target_student.get("năm vào học", ""),
        "ngành": target_student.get("ngành", ""),
        "chuyên ngành": student_spec,
        "mục tiêu học tập": target_student.get("mục tiêu học tập", ""),
        "số tín chỉ đã tích lũy": target_student.get("số tín chỉ đã tích lũy", 0),
        "số tín chỉ đăng ký tối đa": target_student.get("số tín chỉ đăng ký tối đa", REGISTER_MAX_CREDITS),
        "học kỳ hiện tại": current_sem,
        "học kỳ đăng ký": next_sem,
        "tổng số môn có thể đăng ký": len(valid_courses),
        "tổng tín chỉ đăng ký": total_credit,
        "danh sách môn": valid_courses
    }
    
    # In ra màn hình kết quả
    print(f"KẾT QUẢ GỢI Ý MÔN HỌC")
    print(f"Mã SV: {target_student_id}")
    print(f"Họ tên: {target_student.get('tên sinh viên', '')}")
    print(f"Năm vào học: {target_student.get('năm vào học', '')}")
    
    student_major = target_student.get("ngành", "Công Nghệ Thông Tin")
    print(f"Ngành: {student_major}")
    
    spec_display = student_spec if student_spec else 'Chưa chọn chuyên ngành'
    print(f"Chuyên ngành: {spec_display}")
    
    print(f"Mục tiêu học tập: {target_student.get('mục tiêu học tập', 'Đúng hạn')}")
    print(f"Số tín chỉ đã tích lũy: {target_student.get('số tín chỉ đã tích lũy', 0)}")
    print(f"Số tín chỉ đăng ký tối đa: {target_student.get('số tín chỉ đăng ký tối đa', 27)}")
    print(f"Học kỳ hiện tại: {current_sem}")
    print(f"Học kỳ dự kiến đăng ký tiếp theo: {next_sem}")
    
    print(f"Tổng số môn hợp lệ có thể đăng ký: {len(valid_courses)}")
    for idx, course in enumerate(valid_courses, 1):
        is_retake_str = course.get('là môn học lại', False)
        rec_sem_str = course.get('học kỳ đề xuất', 99)
        status_str = "Học lại" if is_retake_str else f"Kỳ {rec_sem_str}"

        spec_list: List[str] = course.get('thuộc chuyên ngành', [])
        spec_str = f"Chuyên ngành: {', '.join(spec_list)}" if spec_list else "Đại cương/Cơ sở"

        coda = course.get('mã môn học', '')
        name = course.get('tên môn học', '')
        tinchi = course.get('tín chỉ', 0)

        print(f"{idx}. {coda}  {name}  {tinchi} tín chỉ  {status_str}  {spec_str}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([student_result], f, ensure_ascii=False, indent=4)
        
    print(f"\nĐã lưu chi tiết vào file: {output_path}")

if __name__ == "__main__":
    main()
