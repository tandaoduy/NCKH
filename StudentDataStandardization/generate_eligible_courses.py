from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

OWL_NS = "http://www.w3.org/2002/07/owl#"
XML_NS = "http://www.w3.org/XML/1998/namespace"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"


@dataclass
class StudentProfile:
    student_id: str
    enrollment_year: int
    specialization_code: str
    specialization_name: str
    studied_courses: list[str]
    grades: dict[str, float]
    statuses: dict[str, str]
    accumulated_credits: int
    current_semester: int
    learning_goal: str

    @property
    def completed_courses(self) -> set[str]:
        return {course for course, status in self.statuses.items() if status == "dat"}

    @property
    def failed_courses(self) -> set[str]:
        return {course for course, status in self.statuses.items() if status == "chua_dat"}


@dataclass
class CourseInfo:
    iri: str
    code: str | None = None
    name: str | None = None
    credits: int | None = None
    open_semester_type: int | None = None
    semester_iri: str | None = None
    semester_number: int | None = None
    prerequisites: set[str] = field(default_factory=set)
    corequisites: set[str] = field(default_factory=set)


@dataclass
class OntologyData:
    courses: dict[str, CourseInfo] = field(default_factory=dict)
    specialization_required: dict[str, set[str]] = field(default_factory=dict)
    specialization_elective: dict[str, set[str]] = field(default_factory=dict)
    major_core: dict[str, set[str]] = field(default_factory=dict)
    major_elective: dict[str, set[str]] = field(default_factory=dict)
    specialization_to_major: dict[str, str] = field(default_factory=dict)
    semester_numbers: dict[str, int] = field(default_factory=dict)


def strip_iri(value: str | None) -> str | None:
    if not value:
        return value
    if "#" in value:
        return value.split("#", 1)[1]
    return value.rsplit("/", 1)[-1]


def safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def normalize_status(value: str) -> str:
    value = (value or "").strip().lower()
    if value in {"dat", "pass", "passed"}:
        return "dat"
    if value in {"chua_dat", "chuadat", "fail", "failed"}:
        return "chua_dat"
    raise ValueError(f"Trang thai mon hoc khong hop le: {value}")


def parse_nested_json(value: str, fallback: Any) -> Any:
    if value is None:
        return fallback
    text = value.strip()
    if not text:
        return fallback
    return json.loads(text)


def load_students(input_path: Path) -> list[StudentProfile]:
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8-sig"))
        records = payload.get("records", [])
    elif suffix == ".csv":
        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            records = []
            for row in reader:
                records.append(
                    {
                        "mssv": row["mssv"],
                        "nam_vao_hoc": safe_int(row["nam_vao_hoc"]),
                        "chuyen_nganh_chon": {
                            "ma": row["chuyen_nganh_chon_ma"],
                            "ten": row["chuyen_nganh_chon_ten"],
                        },
                        "danh_sach_mon_da_hoc": parse_nested_json(row["danh_sach_mon_da_hoc"], []),
                        "diem_tung_mon": parse_nested_json(row["diem_tung_mon"], {}),
                        "trang_thai_dat_chua_dat": parse_nested_json(row["trang_thai_dat_chua_dat"], {}),
                        "so_tin_chi_da_tich_luy": safe_int(row["so_tin_chi_da_tich_luy"]),
                        "hoc_ky_hien_tai": safe_int(row["hoc_ky_hien_tai"]),
                        "muc_tieu_hoc_tap": row["muc_tieu_hoc_tap"],
                    }
                )
    else:
        raise ValueError("Chi ho tro input .json hoac .csv")

    students: list[StudentProfile] = []
    for record in records:
        specialization = record.get("chuyen_nganh_chon") or {}
        grades = {code: float(score) for code, score in (record.get("diem_tung_mon") or {}).items()}
        statuses = {
            code: normalize_status(status)
            for code, status in (record.get("trang_thai_dat_chua_dat") or {}).items()
        }
        student = StudentProfile(
            student_id=record["mssv"],
            enrollment_year=int(record["nam_vao_hoc"]),
            specialization_code=specialization.get("ma", ""),
            specialization_name=specialization.get("ten", ""),
            studied_courses=list(record.get("danh_sach_mon_da_hoc") or []),
            grades=grades,
            statuses=statuses,
            accumulated_credits=int(record["so_tin_chi_da_tich_luy"]),
            current_semester=int(record["hoc_ky_hien_tai"]),
            learning_goal=record["muc_tieu_hoc_tap"],
        )
        students.append(student)
    return students


def parse_ontology(ontology_path: Path) -> OntologyData:
    tree = ET.parse(ontology_path)
    root = tree.getroot()
    data = OntologyData()

    course_types = {
        "Course",
        "CoreCourse",
        "ElectiveCourse",
        "FoundationCourse",
        "ConcurrentCourse",
        "PrerequisiteCourse",
        "Graduate",
        "GeneralEducationCourse",
    }
    entity_types: dict[str, set[str]] = {}
    data_values: dict[str, dict[str, list[str]]] = {}
    object_values: dict[str, dict[str, list[str]]] = {}

    for elem in root:
        tag = elem.tag.split("}", 1)[-1]
        if tag == "ClassAssertion":
            class_elem = elem.find(f"{{{OWL_NS}}}Class")
            named_elem = elem.find(f"{{{OWL_NS}}}NamedIndividual")
            if class_elem is None or named_elem is None:
                continue
            iri = strip_iri(named_elem.attrib.get("IRI"))
            class_iri = strip_iri(class_elem.attrib.get("IRI"))
            entity_types.setdefault(iri, set()).add(class_iri)
        elif tag == "DataPropertyAssertion":
            prop_elem = elem.find(f"{{{OWL_NS}}}DataProperty")
            named_elem = elem.find(f"{{{OWL_NS}}}NamedIndividual")
            literal_elem = elem.find(f"{{{OWL_NS}}}Literal")
            if prop_elem is None or named_elem is None or literal_elem is None:
                continue
            subject = strip_iri(named_elem.attrib.get("IRI"))
            prop = strip_iri(prop_elem.attrib.get("IRI"))
            data_values.setdefault(subject, {}).setdefault(prop, []).append((literal_elem.text or "").strip())
        elif tag == "ObjectPropertyAssertion":
            prop_elem = elem.find(f"{{{OWL_NS}}}ObjectProperty")
            named_elems = elem.findall(f"{{{OWL_NS}}}NamedIndividual")
            if prop_elem is None or len(named_elems) != 2:
                continue
            subject = strip_iri(named_elems[0].attrib.get("IRI"))
            obj = strip_iri(named_elems[1].attrib.get("IRI"))
            prop = strip_iri(prop_elem.attrib.get("IRI"))
            object_values.setdefault(subject, {}).setdefault(prop, []).append(obj)

    for iri, props in data_values.items():
        classes = entity_types.get(iri, set())
        if "Semester" in classes or "hasSemesterNumber" in props:
            number = safe_int(props.get("hasSemesterNumber", [None])[0])
            if number is not None:
                data.semester_numbers[iri] = number

    for iri, props in data_values.items():
        classes = entity_types.get(iri, set())
        if classes.intersection(course_types) or "hasCourseCode" in props:
            course = data.courses.setdefault(iri, CourseInfo(iri=iri))
            course.code = props.get("hasCourseCode", [None])[0] or iri
            course.name = props.get("hasCourseName", [None])[0]
            course.credits = safe_int(props.get("hasCredit", [None])[0])
            course.open_semester_type = safe_int(props.get("hasOpenSemesterType", [None])[0])

    for subject, props in object_values.items():
        if subject in data.courses:
            course = data.courses[subject]
            course.prerequisites.update(props.get("hasPrerequisiteCourse", []))
            course.corequisites.update(props.get("corequisiteWith", []))
            if props.get("isInSemester"):
                course.semester_iri = props["isInSemester"][0]
                course.semester_number = data.semester_numbers.get(course.semester_iri)

        if "Major" in entity_types.get(subject, set()):
            for spec in props.get("hasSpecialization", []):
                if "Specialization" in entity_types.get(spec, set()):
                    data.specialization_to_major[spec] = subject

        if props.get("hasRequiredCourseForSpecialization"):
            data.specialization_required.setdefault(subject, set()).update(props["hasRequiredCourseForSpecialization"])
        if props.get("hasElectiveCourseForSpecialization"):
            data.specialization_elective.setdefault(subject, set()).update(props["hasElectiveCourseForSpecialization"])
        if props.get("hasCoreCourse"):
            data.major_core.setdefault(subject, set()).update(props["hasCoreCourse"])
        if props.get("hasElectiveCourse"):
            data.major_elective.setdefault(subject, set()).update(props["hasElectiveCourse"])

    normalized_courses: dict[str, CourseInfo] = {}
    for iri, course in data.courses.items():
        code = course.code or iri
        normalized_courses[code] = course
        if iri != code:
            normalized_courses[iri] = course
    data.courses = normalized_courses
    return data


def current_term_type(current_semester: int) -> int:
    return 1 if current_semester % 2 == 1 else 2


def is_offered_this_term(course: CourseInfo, term_type: int) -> bool:
    if course.open_semester_type is None:
        return True
    return course.open_semester_type in {12, term_type}


def classify_course(course_code: str, specialization_code: str, major_code: str | None, ontology: OntologyData) -> str:
    if course_code in ontology.specialization_required.get(specialization_code, set()):
        return "specialization_required"
    if course_code in ontology.specialization_elective.get(specialization_code, set()):
        return "specialization_elective"
    if major_code and course_code in ontology.major_core.get(major_code, set()):
        return "major_core"
    if major_code and course_code in ontology.major_elective.get(major_code, set()):
        return "major_elective"
    return "other"


def build_candidate_pool(student: StudentProfile, ontology: OntologyData) -> set[str]:
    major_code = ontology.specialization_to_major.get(student.specialization_code)
    pool: set[str] = set(student.failed_courses)
    pool.update(ontology.specialization_required.get(student.specialization_code, set()))
    pool.update(ontology.specialization_elective.get(student.specialization_code, set()))
    if major_code:
        pool.update(ontology.major_core.get(major_code, set()))
        pool.update(ontology.major_elective.get(major_code, set()))
    return pool


def evaluate_student(student: StudentProfile, ontology: OntologyData) -> dict[str, Any]:
    term_type = current_term_type(student.current_semester)
    major_code = ontology.specialization_to_major.get(student.specialization_code)
    completed = student.completed_courses
    candidate_pool = build_candidate_pool(student, ontology)
    eligible_courses: list[dict[str, Any]] = []
    blocked_courses: list[dict[str, Any]] = []

    for course_code in sorted(candidate_pool):
        course = ontology.courses.get(course_code)
        if course is None:
            blocked_courses.append({
                "course_code": course_code,
                "reason": "Khong tim thay mon hoc trong ontology",
            })
            continue
        if course_code in completed:
            continue

        missing_prerequisites = sorted(pr for pr in course.prerequisites if pr not in completed)
        offered_now = is_offered_this_term(course, term_type)
        coreq_completed = sorted(co for co in course.corequisites if co in completed)
        coreq_open = sorted(co for co in course.corequisites if co not in completed and is_offered_this_term(ontology.courses.get(co, CourseInfo(co)), term_type))
        missing_coreq = sorted(co for co in course.corequisites if co not in completed and co not in coreq_open)
        category = classify_course(course_code, student.specialization_code, major_code, ontology)

        result = {
            "course_code": course.code or course_code,
            "course_name": course.name,
            "credits": course.credits,
            "recommended_semester": course.semester_number,
            "open_semester_type": course.open_semester_type,
            "category": category,
            "retake": course_code in student.failed_courses,
            "corequisites": sorted(course.corequisites),
            "missing_prerequisites": missing_prerequisites,
        }

        if missing_prerequisites:
            result["reason"] = "Chua dat hoc phan tien quyet"
            blocked_courses.append(result)
            continue
        if not offered_now:
            result["reason"] = "Mon khong mo trong dot hoc hien tai"
            blocked_courses.append(result)
            continue
        if missing_coreq:
            result["reason"] = "Thieu hoc phan song hanh"
            result["missing_corequisites"] = missing_coreq
            blocked_courses.append(result)
            continue

        if course.corequisites and coreq_open:
            result["eligibility"] = "eligible_if_coregistered"
            result["required_coregistration"] = coreq_open
        else:
            result["eligibility"] = "eligible"
        eligible_courses.append(result)

    eligible_courses.sort(key=lambda item: (item["recommended_semester"] or 999, item["course_code"]))
    blocked_courses.sort(key=lambda item: (item.get("recommended_semester") or 999, item["course_code"]))

    return {
        "student_id": student.student_id,
        "specialization_code": student.specialization_code,
        "specialization_name": student.specialization_name,
        "major_code": major_code,
        "current_semester": student.current_semester,
        "term_type": term_type,
        "learning_goal": student.learning_goal,
        "completed_courses": sorted(completed),
        "failed_courses": sorted(student.failed_courses),
        "eligible_courses": eligible_courses,
        "blocked_courses": blocked_courses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sinh danh sach mon hop le co the dang ky tu ho so sinh vien va ontology.")
    parser.add_argument(
        "--input",
        default=r"D:\NTU\CNTT\NCKH\Code\StudentDataStandardization\student_input_standard.json",
        help="Duong dan toi file input .json hoac .csv",
    )
    parser.add_argument(
        "--ontology",
        default=r"D:\NTU\CNTT\NCKH\Code\owl\TrainingProgramOntology_v10.owl",
        help="Duong dan toi ontology OWL/XML",
    )
    parser.add_argument("--student-id", help="Loc theo ma sinh vien cu the")
    parser.add_argument(
        "--output",
        default=r"D:\NTU\CNTT\NCKH\Code\StudentDataStandardization\eligible_courses_output.json",
        help="File JSON ket qua",
    )
    parser.add_argument(
        "--include-blocked",
        action="store_true",
        help="Giu ca danh sach mon bi chan va ly do trong output",
    )
    args = parser.parse_args()

    students = load_students(Path(args.input))
    if args.student_id:
        students = [student for student in students if student.student_id == args.student_id]
    if not students:
        raise SystemExit("Khong tim thay sinh vien phu hop voi dau vao.")

    ontology = parse_ontology(Path(args.ontology))
    results = []
    for student in students:
        evaluated = evaluate_student(student, ontology)
        if not args.include_blocked:
            evaluated.pop("blocked_courses", None)
        results.append(evaluated)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Da xu ly {len(results)} sinh vien. Ket qua luu tai: {output_path}")


if __name__ == "__main__":
    main()

