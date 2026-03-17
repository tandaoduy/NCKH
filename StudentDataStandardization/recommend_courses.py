import json
import os
from typing import Dict, Any, List, Set, Optional, cast
from rdflib import Graph, URIRef  # type: ignore
from rdflib.namespace import RDF  # type: ignore

BASE_URI = "http://www.semanticweb.org/henrydao/ontologies/2025/7/TrainingProgramOntology#"

PROP_courseCode = URIRef(BASE_URI + "courseCode")
PROP_courseName = URIRef(BASE_URI + "courseName")
PROP_hasPrerequisiteCourse = URIRef(BASE_URI + "hasPrerequisiteCourse")
PROP_openSemesterType = URIRef(BASE_URI + "openSemesterType")
PROP_recommendedInSemester = URIRef(BASE_URI + "recommendedInSemester")
PROP_specializationName = URIRef(BASE_URI + "specializationName")
PROP_isRequiredForSpecialization = URIRef(BASE_URI + "isRequiredForSpecialization")
PROP_isElectiveForSpecialization = URIRef(BASE_URI + "isElectiveForSpecialization")
PROP_offeredInSpecialization = URIRef(BASE_URI + "offeredInSpecialization")
CLASS_Specialization = URIRef(BASE_URI + "Specialization")

def main() -> None:
    json_path = r"d:\NTU\CNTT\NCKH\Code\StudentDataStandardization\danh_sach_sinh_vien.json"
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
    g = Graph()
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
        recommended_sem_val = 99
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
        for p in [PROP_isRequiredForSpecialization, PROP_isElectiveForSpecialization, PROP_offeredInSpecialization]:
            for spec_uri in g.objects(course, p):
                if isinstance(spec_uri, URIRef):
                    spec_name = specializations_map.get(str(spec_uri))
                    if spec_name:
                        linked_specializations.add(spec_name)
                    
        # Phân loại độ ưu tiên / đại cương (optional)
        course_data[code] = {
            'name': name,
            'prereqs': prereqs,
            'openSemesterType': open_sem_val,
            'recommended_sem': recommended_sem_val,
            'specializations': list(linked_specializations)
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
                else:
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
        
        # Kiểm tra chuyên ngành
        spec_ok = True
        specs: List[str] = info.get('specializations', [])
        if specs:
            if student_spec not in specs:
                spec_ok = False
                
        if prereqs_met and sem_ok and (recommended_ok or is_retake) and spec_ok:
            valid_courses.append({
                "mã môn học": code,
                "tên môn học": info.get('name', ''),
                "là môn học lại": is_retake,
                "học kỳ đề xuất": rec_sem_info,
                "thuộc chuyên ngành": specs
            })
            
    #  Ưu tiên môn học lại, sau đó theo học kỳ đề xuất
    valid_courses.sort(key=lambda x: (not x.get("là môn học lại", False), x.get("học kỳ đề xuất", 99)))
            
    student_result: Dict[str, Any] = {
        "mã sinh viên": target_student_id,
        "tên sinh viên": target_student.get("tên sinh viên", ""),
        "chuyên ngành": student_spec,
        "học kỳ đăng ký": next_sem,
        "tổng số môn có thể đăng ký": len(valid_courses),
        "danh sách môn": valid_courses
    }
    
    # In ra màn hình kết quả
    print(f"KẾT QUẢ GỢI Ý MÔN HỌC")
    print(f"Mã SV: {target_student_id}")
    print(f"Họ tên: {target_student.get('tên sinh viên', '')}")
    print(f"Chuyên ngành: {student_spec}")
    print(f"Tổng số môn hợp lệ có thể đăng ký: {len(valid_courses)}")
    for idx, course in enumerate(valid_courses, 1):
        is_retake_str = course.get('là môn học lại', False)
        rec_sem_str = course.get('học kỳ đề xuất', 99)
        status_str = "[Học Lại]" if is_retake_str else f"[Kỳ {rec_sem_str}]"
        
        spec_list: List[str] = course.get('thuộc chuyên ngành', [])
        spec_str = f"| Chuyên ngành: {', '.join(spec_list)}" if spec_list else "| Đại cương/Cơ sở"
        
        coda = course.get('mã môn học', '')
        name = course.get('tên môn học', '')
        print(f"{idx:2d}. {coda:<8} | {name:<40} | {status_str:<10} {spec_str}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([student_result], f, ensure_ascii=False, indent=4)
        
    print(f"\nĐã lưu chi tiết vào file: {output_path}")

if __name__ == "__main__":
    main()
