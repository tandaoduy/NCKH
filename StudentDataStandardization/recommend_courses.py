import argparse
import ast
import csv
import json
import os
import sys
import io
import random
import unicodedata
from datetime import datetime
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
PROP_credit: Any = URIRef(BASE_URI + "credit")
PROP_corequisiteWith: Any = URIRef(BASE_URI + "corequisiteWith")
CLASS_Specialization: Any = URIRef(BASE_URI + "Specialization")
CLASS_GeneralEducationCourse: Any = URIRef(BASE_URI + "GeneralEducationCourse")
CLASS_PhysicalEducationCourse: Any = URIRef(BASE_URI + "PhysicalEducationCourse")
CLASS_FoundationCourse: Any = URIRef(BASE_URI + "FoundationCourse")

# Giới hạn số tín chỉ tối đa/tối thiểu cho một học kỳ
REGISTER_MAX_CREDITS = 27
REGISTER_MIN_CREDITS = 10

# Trọng số thuật toán ưu tiên khóa học
WEIGHT_DEBT = 1000      # W_debt
WEIGHT_LINK = 20        # W_link (môn có nhiều môn phụ thuộc hơn thì ưu tiên)
WEIGHT_DELAY = 50       # W_delay (môn trễ kỳ đề xuất sẽ ưu tiên)

def main(target_student_id: Optional[str] = None) -> None:
    json_path = r"d:\NTU\CNTT\NCKH\Code\StudentDataStandardization\DanhSachSinhVien.json"
    rdf_path = r"d:\NTU\CNTT\NCKH\Code\owl\ontology_v18.rdf"

    # Yêu cầu người dùng nhập mã sinh viên nếu chưa có
    if target_student_id:
        target_student_id = target_student_id.strip()
    else:
        target_student_id = input("Nhập mã sinh viên cần tra cứu: ").strip()

    if not target_student_id:
        print("Vui lòng nhập mã sinh viên hợp lệ!")
        return

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = rf"d:\NTU\CNTT\NCKH\Code\StudentDataStandardization\DanhSachMonHoc_{target_student_id}_{run_ts}.json"
    report_path = rf"d:\NTU\CNTT\NCKH\Code\StudentDataStandardization\recommend_courses_report_{target_student_id}_{run_ts}.txt"

    print(f"\nĐang đọc dữ liệu hồ sơ sinh viên từ {json_path}...")
    if not os.path.exists(json_path):
        print("Không tìm thấy file JSON danh sách sinh viên!")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        students = json.load(f)
        
    # Tìm sinh viên
    target_student_raw = None
    normalized_target_id = target_student_id.strip().lower()

    if isinstance(students, list):
        for s in students:
            if not isinstance(s, dict):
                continue
            student_code = None
            # hỗ trợ nhiều key trong JSON khác nhau
            for key in ["mã sinh viên", "mã sinh vien", "ma sinh vien", "student_id", "id"]:
                if key in s and s.get(key) is not None:
                    student_code = str(s.get(key)).strip()
                    break
            if not student_code:
                continue

            if student_code.strip().lower() == normalized_target_id or student_code.strip().lower().replace("sv", "") == normalized_target_id.replace("sv", ""):
                target_student_raw = s
                break

    if target_student_raw is None:
        # Fallback: đọc từ CSV nếu JSON không có
        csv_path = r"d:\NTU\CNTT\NCKH\Code\StudentDataStandardization\DanhSachSinhVien.csv"
        if os.path.exists(csv_path):
            with open(csv_path, newline='', encoding='utf-8') as fcsv:
                reader = csv.DictReader(fcsv)
                for row in reader:
                    row_code = None
                    for key in ['mã sinh viên', 'mã sinh vien', 'ma sinh vien', 'student_id', 'id']:
                        if row.get(key):
                            row_code = str(row.get(key)).strip()
                            break
                    if not row_code:
                        continue
                    if row_code.lower() == normalized_target_id or row_code.lower().replace('sv','') == normalized_target_id.replace('sv',''):
                        target_student_raw = dict(row)
                        break
            if target_student_raw is not None:
                print(f"Đã tìm thấy SV {target_student_id} trong CSV (fallback), sẽ tự động thêm vào JSON để lần sau lấy nhanh.")
                # chuyển kiểu dữ liệu trường danh sách từ string sang structure
                for key in ['danh sách môn đã học', 'điểm từng môn', 'danh sách môn chưa đạt']:
                    if key in target_student_raw and isinstance(target_student_raw[key], str) and target_student_raw[key].strip():
                        try:
                            target_student_raw[key] = ast.literal_eval(target_student_raw[key])
                        except Exception:
                            pass
                # thêm vào JSON để đỡ phải nhập lại
                if isinstance(students, list):
                    students.append(target_student_raw)
                    try:
                        with open(json_path, 'w', encoding='utf-8') as fw:
                            json.dump(students, fw, ensure_ascii=False, indent=4)
                        print(f"Đã ghi thêm SV {target_student_id} vào {json_path}")
                    except Exception as e:
                        print("Không thể ghi vào JSON:", e)

        if target_student_raw is None:
            print(f"Không tìm thấy sinh viên với mã '{target_student_id}'. Vui lòng kiểm tra lại mã và dữ liệu JSON/CSV.")
            print("Các mã sinh viên khả dụng (một số):")
            if isinstance(students, list):
                cnt = 0
                for s in students:
                    if not isinstance(s, dict):
                        continue
                    candidate = s.get("mã sinh viên") or s.get("mã sinh vien") or s.get("ma sinh vien") or s.get("student_id") or s.get("id")
                    if candidate:
                        print(" -", candidate)
                        cnt += 1
                        if cnt >= 20:
                            break
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
        if credits_val is None:
            credits_val = g.value(course, PROP_credit)
        credits = 0
        if credits_val is not None:
            try:
                # Có thể là Literal('3.0'), Literal('3') ...
                if isinstance(credits_val, (int, float)):
                    credits = int(credits_val)
                else:
                    credit_str = str(credits_val).strip()
                    if '.' in credit_str:
                        credits = int(float(credit_str))
                    else:
                        credits = int(credit_str)
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
            'elective_category': None  # Sẽ được gán sau
        }
        
    print(f"Đã tải {len(course_data)} môn học.")

    # Tính số môn phụ thuộc (DoPhu), dựa vào danh sách prerequisite của các môn khác
    dependency_count: Dict[str, int] = {code: 0 for code in course_data.keys()}
    for cinfo in course_data.values():
        for pr in cinfo.get('prereqs', []):
            if pr in dependency_count:
                dependency_count[pr] += 1

    # 2. Xử lý cho sinh viên được chọn
    current_sem = target_student.get("học kỳ hiện tại", 1)
    if not isinstance(current_sem, int):
        current_sem = 1
        
    next_sem = current_sem + 1
    sem_type = 1 if next_sem % 2 != 0 else 2
    
    student_spec = target_student.get("chuyên ngành chọn") or target_student.get("chuyên ngành", "")
    if not isinstance(student_spec, str):
        student_spec = ""
    student_spec = student_spec.strip()

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
        prereqs_met = True
        for p in info.get('prereqs', []):
            if p in passed_courses:
                continue
            # Nếu tiên quyết bị rớt thì chưa đủ điều kiện đăng ký môn phụ thuộc
            if p in failed_courses:
                prereqs_met = False
                break
            prereqs_met = False
            break

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
            def _normalize(v: str) -> str:
                return ''.join(ch for ch in unicodedata.normalize('NFKD', v.lower().strip()) if not unicodedata.combining(ch))

            normalized_student_spec = _normalize(student_spec)
            normalized_specs = [_normalize(s) for s in specs if isinstance(s, str)]

            if specs and normalized_student_spec not in normalized_specs:
                spec_ok = False
        else:
            # sinh viên chưa chọn chuyên ngành: cho phép đại cương (không chuyên ngành) và cơ sở ngành (bắt buộc chuyên ngành)
            if specs and not info.get('is_required_specialization', False):
                spec_ok = False

        # Lọc môn quá tải tín chỉ cá nhân (nếu có môn > 27 tín chỉ bị lỗi dữ liệu, bỏ luôn)
        if info.get('credit', 0) > REGISTER_MAX_CREDITS:
            continue

        if prereqs_met and sem_ok and (recommended_ok or is_retake) and spec_ok:
            debt_score = 1 if is_retake else 0
            link_score = dependency_count.get(code, 0)
            delay_score = max(0, current_sem - rec_sem_info)
            heuristic_H = (debt_score * WEIGHT_DEBT) + (link_score * WEIGHT_LINK) + (delay_score * WEIGHT_DELAY)

            open_now_score = 1 if sem_ok else 0
            rec_gap = abs(next_sem - rec_sem_info) if rec_sem_info < 999 else 999
            rec_proximity_score = max(0, 10 - rec_gap)

            study_goal = str(target_student.get('mục tiêu học tập', '')).strip().lower()
            if study_goal == 'đúng hạn':
                goal_score = 30
            elif study_goal == 'giảm tải':
                goal_score = 20
            elif study_goal == 'học vượt':
                goal_score = 10
            else:
                goal_score = 0

            priority_score = heuristic_H + (open_now_score * 50) + (rec_proximity_score * 10) + goal_score

            reasons = []
            if is_retake:
                reasons.append('môn học lại')
            if info.get('is_required_major', False) or info.get('is_required_specialization', False):
                reasons.append('môn bắt buộc')
            elif info.get('is_elective_major', False) or info.get('is_elective_specialization', False):
                reasons.append('môn tự chọn')
            elif info.get('is_foundation_course', False):
                # foundation là dạng cơ sở ngành; nếu chưa gắn loại thì coi là tự chọn
                reasons.append('môn tự chọn cơ sở ngành')
            if open_now_score:
                reasons.append('mở đúng học kỳ hiện tại')
            if rec_gap == 0:
                reasons.append('đúng học kỳ khuyến nghị')
            if student_spec and student_spec in specs:
                reasons.append('phù hợp chuyên ngành')

            valid_courses.append({
                "mã môn học": code,
                "tên môn học": info.get('name', ''),
                "là môn học lại": is_retake,
                "học kỳ đề xuất": rec_sem_info,
                "thuộc chuyên ngành": specs,
                "tín chỉ": info.get('credit', 0),
                "corequisites": info.get('corequisites', []),
                "điểm nợ môn": debt_score,
                "điểm kết nối": link_score,
                "điểm trễ": delay_score,
                "điểm ưu tiên": heuristic_H,
                "mở đúng kỳ": open_now_score,
                "độ gần kỳ đề xuất": rec_proximity_score,
                "điểm mục tiêu": goal_score,
                "điểm tổng ưu tiên": priority_score,
                "lý do": reasons
            })

    # Ưu tiên theo điểm tổng (H + mở kỳ + gần kỳ đề xuất + mục tiêu học tập)
    valid_courses.sort(key=lambda x: (
        -x.get("điểm tổng ưu tiên", 0),
        not x.get("là môn học lại", False),
        -x.get("mở đúng kỳ", 0),
        -x.get("độ gần kỳ đề xuất", 0),
        x.get("học kỳ đề xuất", 99)
    ))

    # Phân loại danh mục tự chọn cho mỗi môn
    def categorize_elective(course_code: str, course_info: Dict[str, Any]) -> Optional[str]:
        """Phân loại môn vào danh mục tự chọn: general, physical, foundation, specialization"""
        is_gen = course_info.get('is_general_education_course', False)
        is_phy = course_info.get('is_physical_education_course', False)
        is_fnd = course_info.get('is_foundation_course', False)
        is_elec = course_info.get('is_elective_major', False) or course_info.get('is_elective_specialization', False)
        
        if not is_elec:
            return None  # Không phải tự chọn
        
        if is_phy:
            return 'physical'
        elif is_fnd:
            return 'foundation'
        elif is_gen:
            return 'general'
        else:
            return 'specialization'
    
    # Ghi nhớ các danh mục trong course_data
    for code, info in course_data.items():
        info['elective_category'] = categorize_elective(code, info)
    
    # Kiểm tra sinh viên đã chọn từ danh mục nào
    elective_selected = {'general': 0, 'physical': 0, 'foundation': 0, 'specialization': 0}
    for code in passed_courses:
        cat = course_data.get(code, {}).get('elective_category')
        if cat:
            elective_selected[cat] += 1
    
    # Chia nhóm: bắt buộc / core cơ sở ngành (tự chọn) / đại cương tự chọn / thể chất tự chọn / còn lại
    required_courses = []
    required_foundation_courses = []
    elective_foundation_courses = []
    general_electives = []
    physical_electives = []
    specialization_electives = []
    other_courses = []

    for c in valid_courses:
        code_ = c['mã môn học']
        info = course_data.get(code_, {})

        # Kiểm tra xem có phải môn bắt buộc không
        is_required = (
            c.get('là môn học lại', False)
            or info.get('is_required_specialization', False)
            or info.get('is_required_major', False)
        )

        # Nếu là một phần của nền tảng bắt buộc
        if info.get('is_foundation_course', False) and is_required:
            required_foundation_courses.append(c)
            continue

        # Nếu là môn bắt buộc, thêm vào required_courses
        if is_required:
            required_courses.append(c)
            continue

        # Xử lý các môn tự chọn
        elec_cat = info.get('elective_category')
        
        if elec_cat == 'foundation':
            elective_foundation_courses.append(c)
        elif elec_cat == 'general':
            general_electives.append(c)
        elif elec_cat == 'physical':
            physical_electives.append(c)
        elif elec_cat == 'specialization':
            specialization_electives.append(c)
        else:
            # Trường hợp cùng không phải tự chọn và không bắt buộc
            other_courses.append(c)

    # Áp dụng ràng buộc danh mục tự chọn
    study_goal = str(target_student.get('mục tiêu học tập', '')).strip().lower()

    # Random hóa thứ tự môn tự chọn để công bằng cho các môn cùng mức ưu tiên
    random.shuffle(elective_foundation_courses)
    random.shuffle(general_electives)
    random.shuffle(physical_electives)
    random.shuffle(specialization_electives)
    
    selected_candidates = list(required_courses) + required_foundation_courses
    
    # Kỳ 1 không có tự chọn, từ kỳ 2 trở đi mỗi kỳ có thể chọn từ 2 danh mục tự chọn khác nhau
    if next_sem > 1:
        # Danh sách các danh mục tự chọn có sẵn với ưu tiên: cơ sở ngành, đại cương, thể chất, chuyên ngành
        available_categories = []
        
        # 1. Tự chọn cơ sở ngành: chỉ chọn 1, không chọn lại các kỳ sau (trừ rớt)
        if elective_selected['foundation'] == 0 and len(elective_foundation_courses) > 0:
            selected_foundation = random.choice(elective_foundation_courses)
            available_categories.append(selected_foundation)
        
        # 2. Tự chọn đại cương: chỉ chọn 1, không chọn lại các kỳ sau (trừ rớt)
        if elective_selected['general'] == 0 and len(general_electives) > 0:
            # Trong general_electives đã shuffle để đảm bảo công bằng, chọn 1 trong top ưu tiên
            general_electives.sort(key=lambda x: x.get('điểm tổng ưu tiên', 0), reverse=True)
            top_general = [g for g in general_electives if g.get('điểm tổng ưu tiên', 0) == general_electives[0].get('điểm tổng ưu tiên', 0)]
            selected_general = random.choice(top_general)
            available_categories.append(selected_general)
        
        # 3. Tự chọn thể chất: chọn 2 (mỗi kỳ 1, trừ nếu "học vượt" có thể 2 cùng kỳ)
        if elective_selected['physical'] < 2 and len(physical_electives) > 0:
            if study_goal == 'học vượt':
                phys_select_count = min(2 - elective_selected['physical'], len(physical_electives))
            else:
                phys_select_count = 1
            available_categories.extend(physical_electives[:phys_select_count])
        
        # 4. Tự chọn chuyên ngành: chọn 3, bắt đầu từ kỳ 5, nếu "học vượt" có thể 2 cùng kỳ
        # Đặc biệt: cho phép chọn từ các kỳ khác nhau (từ kỳ 5+), không chỉ kỳ hiện tại
        if next_sem >= 5 and elective_selected['specialization'] < 3:
            # Tìm thêm các môn chuyên ngành từ tất cả các kỳ >= 5
            all_specialization_options = []
            for code_spec, info_spec in course_data.items():
                if code_spec in passed_courses:
                    continue
                
                is_required_spec = (
                    info_spec.get('is_required_specialization', False) or
                    info_spec.get('is_required_major', False)
                )
                if is_required_spec:
                    continue
                
                # Kiểm tra xem có phải môn tự chọn chuyên ngành không
                is_elec_spec = (
                    info_spec.get('is_elective_specialization', False) or
                    info_spec.get('is_elective_major', False)
                )
                if not is_elec_spec:
                    continue
                
                # Kiểm tra tiên quyết
                prereqs_spec = info_spec.get('prereqs', [])
                prereqs_met_spec = True
                for p in prereqs_spec:
                    if p in passed_courses:
                        continue
                    if p in failed_courses:
                        prereqs_met_spec = False
                        break
                    prereqs_met_spec = False
                    break
                
                if not prereqs_met_spec:
                    continue
                
                # Kiểm tra học kỳ mở
                open_sem_spec = info_spec.get('openSemesterType', 3)
                sem_ok_spec = (open_sem_spec in (3, 12) or open_sem_spec == sem_type)
                if not sem_ok_spec:
                    continue
                
                # Kiểm tra định hướng chuyên ngành
                specs_spec = info_spec.get('specializations', [])
                spec_ok_spec = True
                if student_spec and specs_spec:
                    def _normalize(v: str) -> str:
                        return ''.join(ch for ch in unicodedata.normalize('NFKD', v.lower().strip()) if not unicodedata.combining(ch))
                    normalized_student_spec = _normalize(student_spec)
                    normalized_specs = [_normalize(s) for s in specs_spec if isinstance(s, str)]
                    if specs_spec and normalized_student_spec not in normalized_specs:
                        spec_ok_spec = False
                
                if not spec_ok_spec:
                    continue
                
                rec_sem_spec = info_spec.get('recommended_sem', 99)
                # Chỉ lấy môn từ kỳ 5 trở đi
                if rec_sem_spec < 5:
                    continue
                
                # Tính điểm ưu tiên
                rec_gap_spec = abs(next_sem - rec_sem_spec) if rec_sem_spec < 999 else 999
                rec_proximity_score_spec = max(0, 10 - rec_gap_spec)
                
                if study_goal == 'đúng hạn':
                    goal_score_spec = 30
                elif study_goal == 'giảm tải':
                    goal_score_spec = 20
                elif study_goal == 'học vượt':
                    goal_score_spec = 10
                else:
                    goal_score_spec = 0
                
                delay_score_spec = max(0, current_sem - rec_sem_spec)
                link_score_spec = dependency_count.get(code_spec, 0)
                heuristic_H_spec = delay_score_spec * WEIGHT_DELAY + link_score_spec * WEIGHT_LINK
                
                priority_score_spec = heuristic_H_spec + (rec_proximity_score_spec * 10) + goal_score_spec
                
                all_specialization_options.append({
                    "mã môn học": code_spec,
                    "tên môn học": info_spec.get('name', ''),
                    "là môn học lại": False,
                    "học kỳ đề xuất": rec_sem_spec,
                    "thuộc chuyên ngành": specs_spec,
                    "tín chỉ": info_spec.get('credit', 0),
                    "corequisites": info_spec.get('corequisites', []),
                    "điểm nợ môn": 0,
                    "điểm kết nối": link_score_spec,
                    "điểm trễ": delay_score_spec,
                    "điểm ưu tiên": heuristic_H_spec,
                    "mở đúng kỳ": 1,
                    "độ gần kỳ đề xuất": rec_proximity_score_spec,
                    "điểm mục tiêu": goal_score_spec,
                    "điểm tổng ưu tiên": priority_score_spec,
                    "lý do": ['môn tự chọn, phù hợp chuyên ngành']
                })
            
            # Randomize và sắp xếp để ưu tiên đồng thời công bằng với các điểm bằng nhau
            random.shuffle(all_specialization_options)
            all_specialization_options.sort(key=lambda x: x.get('điểm tổng ưu tiên', 0), reverse=True)
            if study_goal == 'học vượt':
                spec_select_count = min(3 - elective_selected['specialization'], len(all_specialization_options))
            else:
                spec_select_count = min(1, 3 - elective_selected['specialization'], len(all_specialization_options))
            
            available_categories.extend(all_specialization_options[:spec_select_count])
        
        # Chọn tối đa 2 danh mục tự chọn từ danh sách có sẵn
        selected_candidates.extend(available_categories[:2])
    
    # Thêm các môn khác (không là bắt buộc, không là tự chọn)
    selected_candidates.extend(other_courses)

    eligible_codes = {c['mã môn học'] for c in selected_candidates}
    course_index = {c['mã môn học']: c for c in selected_candidates}

    student_max_credit = REGISTER_MAX_CREDITS
    student_request_max = target_student.get('số tín chỉ đăng ký tối đa', REGISTER_MAX_CREDITS)
    if isinstance(student_request_max, int):
        student_max_credit = min(REGISTER_MAX_CREDITS, student_request_max)

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

    # Beam Search để chọn tổ hợp khóa học tốt nhất
    beam_width = 8

    def state_score(state: Dict[str, Any]) -> float:
        return state['score']

    initial_state = {
        'selected_codes': set(),
        'selected_courses': [],
        'credit': 0,
        'score': 0.0
    }

    beam = [initial_state]
    best_state = initial_state

    while True:
        new_beam = []
        improved = False

        for state in beam:
            remaining = [c for c in selected_candidates if c['mã môn học'] not in state['selected_codes']]
            for c in remaining:
                bundle_codes = resolve_coreq_bundle(c['mã môn học'])
                if bundle_codes is None:
                    continue
                bundle_codes = {x for x in bundle_codes if x not in state['selected_codes']}
                bundle_credit = sum(course_data.get(x, {}).get('credit', 0) for x in bundle_codes)

                if state['credit'] + bundle_credit > student_max_credit:
                    continue

                next_credit = state['credit'] + bundle_credit
                next_selected_codes = state['selected_codes'] | bundle_codes
                next_selected_courses = list(state['selected_courses'])
                next_score = state['score']

                for code_ in bundle_codes:
                    course_item = course_index.get(code_)
                    if course_item is not None:
                        next_selected_courses.append(course_item)
                        next_score += course_item.get('điểm tổng ưu tiên', 0)

                next_state = {
                    'selected_codes': next_selected_codes,
                    'selected_courses': next_selected_courses,
                    'credit': next_credit,
                    'score': next_score
                }

                new_beam.append(next_state)
                improved = True

        if not improved:
            break

        # Thêm cả các state cũ để Beam không bị mất tùy chọn không thêm
        new_beam.extend(beam)

        # Giữ beam_width phương án tốt nhất theo điểm + credit (ưu tiên nhiều credit khi bằng điểm)
        beam = sorted(new_beam, key=lambda x: (x['score'], x['credit']), reverse=True)[:beam_width]

        # Cập nhật best_state: luôn chọn phương án có điểm cao nhất
        top_state = max(beam, key=lambda x: (x['score'], x['credit']))
        if top_state['score'] > best_state['score'] or (
            top_state['score'] == best_state['score'] and top_state['credit'] > best_state['credit']
        ):
            best_state = top_state

    # Chọn danh sách môn hợp lệ ban đầu trước khi Beam chọn tổ hợp
    eligible_courses = list(selected_candidates)

    # Chọn kết quả ban đầu từ beam
    selected_codes = set(best_state['selected_codes'])
    selected_courses = list(best_state['selected_courses'])
    total_credit = best_state['credit']

    # Cứng chắc: bắt buộc tổng tín chỉ tổ hợp không vượt 27
    if total_credit > student_max_credit:
        selected_courses = [c for c in selected_courses if c.get('tín chỉ', 0) <= student_max_credit]
        total_credit = sum(c.get('tín chỉ', 0) for c in selected_courses)
        selected_codes = {c['mã môn học'] for c in selected_courses}

    # Bổ sung các môn hợp lệ tiếp theo nếu vẫn còn dư tín chỉ
    for c in sorted(selected_candidates, key=lambda x: x.get('điểm tổng ưu tiên', 0), reverse=True):
        if c['mã môn học'] in selected_codes:
            continue

        bundle_codes = resolve_coreq_bundle(c['mã môn học'])
        if bundle_codes is None:
            continue

        bundle_codes = [b for b in bundle_codes if b not in selected_codes]
        bundle_credit = sum(course_data.get(b, {}).get('credit', 0) for b in bundle_codes)

        if total_credit + bundle_credit > student_max_credit:
            continue

        for b in bundle_codes:
            selected_codes.add(b)
            sc = course_index.get(b)
            if sc is not None:
                selected_courses.append(sc)

        total_credit += bundle_credit

    # Bước đảm bảo cuối: nếu vì lý do logic có sai sót thì cắt bớt môn cho <= 27 tín chỉ
    if total_credit > student_max_credit:
        selected_courses = sorted(selected_courses, key=lambda c: c.get('điểm tổng ưu tiên', 0), reverse=True)
        adjusted = []
        sum_credit = 0
        for c in selected_courses:
            c_credit = c.get('tín chỉ', 0)
            if sum_credit + c_credit <= student_max_credit:
                adjusted.append(c)
                sum_credit += c_credit
        selected_courses = adjusted
        total_credit = sum_credit

    valid_courses = selected_courses

    # Thu thập và lọc theo yêu cầu: 1 đại cương/cơ sở, 2 thể chất, 3 chuyên ngành
    required_course_codes = set(c['mã môn học'] for c in required_courses)

    def is_general_core(c):
        info = course_data.get(c['mã môn học'], {})
        return info.get('is_general_education_course', False) or info.get('is_foundation_course', False)

    def is_physical(c):
        info = course_data.get(c['mã môn học'], {})
        return info.get('is_physical_education_course', False)

    def is_specialization_elective(c):
        info = course_data.get(c['mã môn học'], {})
        return info.get('is_elective_specialization', False)

    def open_ok(c):
        info = course_data.get(c['mã môn học'], {})
        open_sem_val = info.get('openSemesterType', 3)
        return open_sem_val in (3, 12) or open_sem_val == sem_type

    def rec_ok(c):
        rec_sem = c.get('học kỳ đề xuất', 99)
        if isinstance(rec_sem, int):
            if str(target_student.get('mục tiêu học tập', '')).strip().lower() == 'học vượt':
                return True
            return rec_sem <= next_sem
        return False

    def pick_top(candidates, count, distinct_key=None):
        selected = []
        seen_keys = set()
        for c in sorted(candidates, key=lambda x: x.get('điểm tổng ưu tiên', 0), reverse=True):
            if len(selected) >= count:
                break
            if c['mã môn học'] in [x['mã môn học'] for x in selected]:
                continue
            if not open_ok(c):
                continue
            if not rec_ok(c):
                continue
            if distinct_key:
                key_val = c.get(distinct_key)
                if key_val in seen_keys:
                    continue
                seen_keys.add(key_val)
            selected.append(c)

        return selected

    final_courses = []
    final_credit = 0

    def add_course(c):
        nonlocal final_credit
        if c['mã môn học'] in {x['mã môn học'] for x in final_courses}:
            return False
        c_credit = c.get('tín chỉ', 0)
        if final_credit + c_credit > student_max_credit:
            return False
        final_courses.append(c)
        final_credit += c_credit
        return True

    # luôn giữ môn bắt buộc (đã sắp xếp theo score)
    for c in sorted(required_courses, key=lambda x: x.get('điểm tổng ưu tiên', 0), reverse=True):
        add_course(c)

    # 1 môn đại cương/cơ sở ngành
    general_core_candidates = [c for c in selected_courses if is_general_core(c) and c['mã môn học'] not in {x['mã môn học'] for x in final_courses}]
    if general_core_candidates:
        add_course(general_core_candidates[0])

    # 2 môn thể chất, ưu tiên khác kỳ đề xuất
    physical_pool = [c for c in selected_courses if is_physical(c) and c['mã môn học'] not in {x['mã môn học'] for x in final_courses}]
    physical_picked = pick_top(physical_pool, 2, distinct_key='học kỳ đề xuất')
    if len(physical_picked) < 2:
        for c in physical_pool:
            if len(physical_picked) >= 2:
                break
            if c not in physical_picked:
                physical_picked.append(c)
    for c in physical_picked:
        add_course(c)

    # 3 môn tự chọn chuyên ngành (ưu tiên khuyến nghị và mở kỳ)
    spec_pool = [c for c in selected_courses if is_specialization_elective(c) and c['mã môn học'] not in {x['mã môn học'] for x in final_courses}]
    spec_picked = pick_top(spec_pool, 3)
    for c in spec_picked:
        add_course(c)

    # Bổ sung nếu còn dư tín chỉ và chưa đủ nguồn
    for c in sorted(selected_courses, key=lambda x: x.get('điểm tổng ưu tiên', 0), reverse=True):
        if len(final_courses) >= len(selected_courses):
            break
        add_course(c)

    valid_courses = final_courses
    total_credit = final_credit

    # Chuẩn bị giá trị in báo cáo
    student_major = target_student.get("ngành", "Công Nghệ Thông Tin")
    spec_display = student_spec if student_spec else 'Chưa chọn chuyên ngành'
    total_selected_credits = sum(c.get('tín chỉ', 0) for c in valid_courses)

    # Xuất báo cáo chi tiết ra file text
    with open(report_path, 'w', encoding='utf-8') as report:
        report.write('=== BÁO CÁO GỢI Ý KẾ HOẠCH HỌC TẬP ===\n')
        report.write(f"Mã sinh viên: {target_student_id}\n")
        report.write(f"Tên: {target_student.get('tên sinh viên', '')}\n")
        report.write(f"Ngành: {student_major}\n")
        report.write(f"Chuyên ngành: {spec_display}\n")
        report.write(f"Học kỳ hiện tại: {current_sem}, học kỳ đăng ký: {next_sem}\n")
        report.write(f"Mục tiêu học: {target_student.get('mục tiêu học tập', 'Đúng hạn')}\n")
        report.write('---\n')

        report.write('1. Tập môn hợp lệ (đầu vào)\n')
        report.write('Mỗi môn: [H = debt*1000 + doPhu*20 + doTre*50] + [H_total thêm open/rec/goal] \n')
        for c in eligible_courses:
            h = c.get('điểm ưu tiên', 0)
            total = c.get('điểm tổng ưu tiên', 0)
            reasons = c.get('lý do', [])
            report.write(f"- {c['mã môn học']} {c['tên môn học']} ({c.get('tín chỉ', 0)} TIC) H={h}, H_total={total}, Lý do: {', '.join(reasons)}\n")
        report.write('---\n')

        report.write('2. Tổ hợp môn cuối cùng (beam search chọn)\n')
        report.write(f"Tổng số môn hợp lệ có thể đăng ký: {len(valid_courses)}\n")
        report.write(f"Tổng số tín chỉ của các môn đã liệt kê: {total_selected_credits}\n")
        report.write(f"Tổng tín chỉ: {total_credit}\n")
        for c in valid_courses:
            h = c.get('điểm ưu tiên', 0)
            total = c.get('điểm tổng ưu tiên', 0)
            reasons = c.get('lý do', [])
            report.write(f"* {c['mã môn học']} {c['tên môn học']} ({c.get('tín chỉ', 0)} TIC) H_total={total}, Lý do: {', '.join(reasons)}\n")
        report.write('---\n')

        report.write('3. Giải thích quy trình beam search đã dùng\n')
        report.write('- Beam width = 8\n')
        report.write('- Mỗi state lưu selected_codes, credit, score\n')
        report.write('- Mỗi lần mở rộng thêm 1 môn hoặc bundle corequisite nếu không vượt max credit\n')
        report.write('- Giữ lại top 8 state theo (score, credit)\n')
        report.write('- Kết thúc khi không thể mở rộng thêm\n')
        report.write('- Chọn best_state (score cao nhất, ưu credit cao nếu hòa)\n')

    print(f"\nĐã lưu báo cáo chi tiết vào: {report_path}\n")

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
    total_selected_credits = sum(c.get('tín chỉ', 0) for c in valid_courses)
    print(f"Tổng số tín chỉ của các môn đã liệt kê: {total_selected_credits}")

    for idx, course in enumerate(valid_courses, 1):
        is_retake_str = course.get('là môn học lại', False)
        rec_sem_str = course.get('học kỳ đề xuất', 99)
        status_str = "Học lại" if is_retake_str else f"Kỳ {rec_sem_str}"

        spec_list: List[str] = course.get('thuộc chuyên ngành', [])
        spec_str = f"Chuyên ngành: {', '.join(spec_list)}" if spec_list else "Đại cương/Cơ sở"

        coda = course.get('mã môn học', '')
        name = course.get('tên môn học', '')
        tinchi = course.get('tín chỉ', 0)
        h_score = course.get('điểm ưu tiên', 0)
        total_score = course.get('điểm tổng ưu tiên', 0)
        reasons = course.get('lý do', [])
        reason_str = ', '.join(reasons) if reasons else 'Không rõ'

        print(f"{idx}. {coda}  {name}  {tinchi} tín chỉ  {status_str}  {spec_str}  [H={h_score}] [H_total={total_score}]  Lý do: {reason_str}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([student_result], f, ensure_ascii=False, indent=4)
        
    print(f"\nĐã lưu chi tiết vào file: {output_path}")

if __name__ == "__main__":
    main()  
