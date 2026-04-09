"""
Service for loading and managing student data (JSON/CSV)
"""

import csv
import json
import os
import re
from typing import Any, Dict, List, Optional

from flask_app.models.student import StudentProfile


class StudentDataService:
    """Quan ly du lieu sinh vien tu JSON/CSV."""

    def __init__(self, json_path: str, csv_path: str):
        self.json_path = json_path
        self.csv_path = csv_path
        self._students_cache: Optional[List[StudentProfile]] = None

    def get_all_students(self, force_reload: bool = False) -> List[StudentProfile]:
        """Lay danh sach tat ca sinh vien."""
        if self._students_cache and not force_reload:
            return self._students_cache

        students: List[StudentProfile] = []

        if os.path.exists(self.json_path):
            try:
                students = self._load_from_json()
            except Exception as exc:
                print(f"Error loading JSON: {exc}")

        if not students and os.path.exists(self.csv_path):
            try:
                students = self._load_from_csv()
            except Exception as exc:
                print(f"Error loading CSV: {exc}")

        self._students_cache = students
        return students

    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        """Lay ho so sinh vien theo ma."""
        normalized_id = self._normalize_student_id(student_id)
        for student in self.get_all_students():
            if self._normalize_student_id(student.student_id) == normalized_id:
                return student
        return None

    def get_next_student_id(self, force_reload: bool = True) -> str:
        """
        Lay ma sinh vien tiep theo theo format SV0001.
        Quy tac: lay ma SV co so lon nhat trong du lieu + 1.
        """
        students = self.get_all_students(force_reload=force_reload)
        max_num = 0

        for s in students:
            raw = str(getattr(s, "student_id", "") or "").strip()
            match = re.match(r"^\s*SV\s*(\d+)\s*$", raw, flags=re.IGNORECASE)
            if not match:
                continue
            try:
                num = int(match.group(1))
            except ValueError:
                continue
            if num > max_num:
                max_num = num

        return f"SV{max_num + 1:04d}"

    def create_student(
        self,
        student_data: Dict[str, Any],
        course_catalog: Dict[str, Dict[str, Any]],
        specialization_options: List[str],
    ) -> StudentProfile:
        """Tao moi sinh vien va luu vao JSON nguon."""
        student_id = str(student_data.get("student_id", "")).strip().upper()
        if not student_id:
            raise ValueError("Mã sinh viên không được để trống")

        if self.get_student(student_id):
            raise ValueError(f"Sinh viên {student_id} đã tồn tại")

        normalized_goal = self._normalize_study_goal(student_data.get("study_goal"))
        current_semester = self._safe_int(student_data.get("current_semester"), 1)
        specialization = str(student_data.get("specialization", "Chưa chọn chuyên ngành")).strip() or "Chưa chọn chuyên ngành"

        if current_semester < 4:
            if specialization != "Chưa chọn chuyên ngành":
                raise ValueError("Sinh viên từ học kỳ 1 đến 3 không được chọn chuyên ngành")
            specialization = "Chưa chọn chuyên ngành"
        else:
            if specialization != "Chưa chọn chuyên ngành" and specialization not in specialization_options:
                raise ValueError("Chuyên ngành không hợp lệ")

        course_entries = student_data.get("courses", [])
        passed_courses: List[str] = []
        failed_courses: List[str] = []
        course_grades: Dict[str, float] = {}
        total_credits_accumulated = 0

        for entry in course_entries:
            code = str(entry.get("code", "")).strip().upper()
            if not code:
                continue

            if code in course_grades:
                raise ValueError(f"Môn học {code} đang bị trùng")

            course_info = course_catalog.get(code)
            if not course_info:
                raise ValueError(f"Môn học {code} không tồn tại trong ontology")

            try:
                grade = float(entry.get("grade", 0))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Điểm của môn {code} không hợp lệ") from exc

            if grade < 0 or grade > 10:
                raise ValueError(f"Điểm của môn {code} phải trong khoảng 0-10")

            course_grades[code] = round(grade, 2)
            course_credit = self._safe_int(course_info.get("credits"), 0)

            if grade >= 5:
                passed_courses.append(code)
                total_credits_accumulated += course_credit
            else:
                failed_courses.append(code)

        student = StudentProfile(
            student_id=student_id,
            name=str(student_data.get("name", "")).strip(),
            year_admitted=self._safe_int(student_data.get("year_admitted"), 2023),
            major=str(student_data.get("major", "Công Nghệ Thông Tin")).strip() or "Công Nghệ Thông Tin",
            specialization=specialization,
            study_goal=normalized_goal,
            current_semester=current_semester,
            total_credits_accumulated=total_credits_accumulated,
            max_credits_to_register=27,
            passed_courses=passed_courses,
            failed_courses=failed_courses,
            course_grades=course_grades,
        )

        errors = student.validate()
        if errors:
            raise ValueError("; ".join(errors))

        self._append_student_to_json(student, course_catalog)
        self._students_cache = None
        return self.get_student(student.student_id) or student

    def _load_from_json(self) -> List[StudentProfile]:
        """Tai du lieu sinh vien tu JSON."""
        with open(self.json_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("JSON phải là danh sách")

        students: List[StudentProfile] = []
        for item in data:
            try:
                student = self._parse_student_dict(item)
                if student:
                    students.append(student)
            except Exception as exc:
                print(f"Warning: Cannot parse student {item.get('mã sinh viên', '?')}: {exc}")

        return students

    def _load_from_csv(self) -> List[StudentProfile]:
        """Tai du lieu sinh vien tu CSV."""
        students: List[StudentProfile] = []

        with open(self.csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    student = self._parse_student_dict(row)
                    if student:
                        students.append(student)
                except Exception as exc:
                    print(f"Warning: Cannot parse CSV row: {exc}")

        return students

    def _append_student_to_json(
        self,
        student: StudentProfile,
        course_catalog: Dict[str, Dict[str, Any]]
    ) -> None:
        """Them sinh vien vao file JSON nguon."""
        existing_data: List[Dict[str, Any]] = []

        if os.path.exists(self.json_path):
            with open(self.json_path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
                if isinstance(loaded, list):
                    existing_data = loaded

        existing_data.append(self._build_student_json_record(student, course_catalog))

        with open(self.json_path, "w", encoding="utf-8") as file:
            json.dump(existing_data, file, ensure_ascii=False, indent=4)

    def _build_student_json_record(
        self,
        student: StudentProfile,
        course_catalog: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Chuyen StudentProfile thanh dinh dang JSON goc cua du an."""
        studied_courses: Dict[str, str] = {}
        grade_entries: List[Dict[str, Any]] = []
        failed_entries: List[Dict[str, str]] = []

        for code, grade in sorted(student.course_grades.items()):
            course_info = course_catalog.get(code, {})
            course_name = course_info.get("name") or code
            is_passed = grade >= 5

            studied_courses[code] = course_name
            grade_entries.append({
                "mã môn học": code,
                "Tên môn học": course_name,
                "điểm": grade,
                "Trạng thái": "Đạt" if is_passed else "Chưa đạt",
            })

            if not is_passed:
                failed_entries.append({
                    "mã môn học": code,
                    "Tên môn học": course_name,
                })

        return {
            "mã sinh viên": student.student_id,
            "tên sinh viên": student.name,
            "năm vào học": student.year_admitted,
            "ngành": student.major,
            "chuyên ngành": student.specialization,
            "mục tiêu học tập": self._display_study_goal(student.study_goal),
            "số tín chỉ đã tích lũy": student.total_credits_accumulated,
            "số tín chỉ đăng ký tối đa": 27,
            "học kỳ hiện tại": student.current_semester,
            "học kỳ dự kiến đăng ký tiếp theo": student.current_semester + 1,
            "danh sách môn đã học": studied_courses,
            "điểm từng môn": grade_entries,
            "danh sách môn chưa đạt": failed_entries,
        }

    def _parse_student_dict(self, data: Dict[str, Any]) -> Optional[StudentProfile]:
        """Parse dict thanh StudentProfile."""
        student_id = None
        for key in [
            "mã sinh viên",
            "mã sinh vien",
            "ma sinh vien",
            "student_id",
            "id",
            self._legacy_mojibake("mã sinh viên"),
        ]:
            value = data.get(key)
            if value and str(value).strip():
                student_id = str(value).strip()
                break

        if not student_id:
            return None

        name = (
            str(data.get("tên sinh viên", "")).strip()
            or str(data.get("name", "")).strip()
            or str(data.get(self._legacy_mojibake("tên sinh viên"), "")).strip()
        )
        year_admitted = self._safe_int(
            data.get("năm vào học", data.get(self._legacy_mojibake("năm vào học"), 2023)), 2023
        )
        major = str(data.get("ngành", data.get(self._legacy_mojibake("ngành"), "Công Nghệ Thông Tin"))).strip()
        specialization = str(
            data.get("chuyên ngành", data.get(self._legacy_mojibake("chuyên ngành"), "Chưa chọn chuyên ngành"))
        ).strip()
        study_goal = self._normalize_study_goal(
            data.get("mục tiêu học tập", data.get(self._legacy_mojibake("mục tiêu học tập"), "đúng hạn"))
        )
        current_semester = self._safe_int(
            data.get("học kỳ hiện tại", data.get(self._legacy_mojibake("học kỳ hiện tại"), 1)), 1
        )
        total_credits = self._safe_int(
            data.get("số tín chỉ đã tích lũy", data.get(self._legacy_mojibake("số tín chỉ đã tích lũy"), 0)), 0
        )
        max_credits = self._safe_int(
            data.get("số tín chỉ đăng ký tối đa", data.get(self._legacy_mojibake("số tín chỉ đăng ký tối đa"), 27)),
            27,
        )

        passed_courses = self._parse_course_list(
            data.get("danh sách môn đã học", data.get(self._legacy_mojibake("danh sách môn đã học"), []))
        )
        failed_courses = self._parse_course_list(
            data.get("danh sách môn chưa đạt", data.get(self._legacy_mojibake("danh sách môn chưa đạt"), []))
        )
        grades = self._parse_grades(
            data.get("điểm từng môn", data.get(self._legacy_mojibake("điểm từng môn"), []))
        )
        passed_courses -= failed_courses

        return StudentProfile(
            student_id=student_id,
            name=name,
            year_admitted=year_admitted,
            major=major,
            specialization=specialization,
            study_goal=study_goal,
            current_semester=current_semester,
            total_credits_accumulated=total_credits,
            max_credits_to_register=max_credits,
            passed_courses=list(passed_courses),
            failed_courses=list(failed_courses),
            course_grades=grades,
        )

    def _parse_course_list(self, data: Any) -> set:
        """Parse danh sach mon tu dict hoac list."""
        courses = set()

        if isinstance(data, dict):
            for code in data.keys():
                if code and str(code).strip():
                    courses.add(str(code).strip().upper())
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    code = item.get("mã môn học", item.get(self._legacy_mojibake("mã môn học"), ""))
                elif isinstance(item, str):
                    code = item
                else:
                    continue

                if code and str(code).strip():
                    courses.add(str(code).strip().upper())

        return courses

    def _parse_grades(self, data: Any) -> Dict[str, float]:
        """Parse bang diem."""
        grades: Dict[str, float] = {}
        if not isinstance(data, list):
            return grades

        for item in data:
            if not isinstance(item, dict):
                continue

            code = item.get("mã môn học", item.get(self._legacy_mojibake("mã môn học"), ""))
            grade = item.get("điểm", item.get(self._legacy_mojibake("điểm"), 0))
            if code and str(code).strip():
                try:
                    grades[str(code).strip().upper()] = float(grade)
                except (ValueError, TypeError):
                    pass

        return grades

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        """Chuyen value thanh int an toan."""
        try:
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)

            string_value = str(value).strip()
            if not string_value:
                return default
            if "." in string_value:
                return int(float(string_value))
            return int(string_value)
        except Exception:
            return default

    @staticmethod
    def _normalize_student_id(student_id: str) -> str:
        """Normalize student ID for comparison."""
        return student_id.strip().lower().replace("sv", "")

    @staticmethod
    def _normalize_study_goal(value: Any) -> str:
        """Chuan hoa muc tieu hoc tap."""
        goal = str(value or "").strip().lower()
        normalized = {
            "đúng hạn": "đúng hạn",
            "dung han": "đúng hạn",
            "giảm tải": "giảm tải",
            "giam tai": "giảm tải",
            "học vượt": "học vượt",
            "hoc vuot": "học vượt",
        }
        # Tương thích dữ liệu cũ bị mojibake (dữ liệu UTF-8 bị decode nhầm Latin-1).
        normalized.update({StudentDataService._legacy_mojibake(k): v for k, v in normalized.items()})
        return normalized.get(goal, "đúng hạn")

    @staticmethod
    def _legacy_mojibake(text: str) -> str:
        """
        Sinh key/value "lỗi encoding" để tương thích dữ liệu cũ (UTF-8 bị decode nhầm Latin-1).

        Ví dụ: "mã sinh viên" -> (chuỗi bị lỗi encoding kiểu mojibake)
        """
        try:
            return text.encode("utf-8").decode("latin1")
        except Exception:
            return text

    @staticmethod
    def _display_study_goal(value: str) -> str:
        """Hien thi muc tieu hoc tap theo dinh dang luu JSON."""
        mapping = {
            "đúng hạn": "Đúng hạn",
            "giảm tải": "Giảm tải",
            "học vượt": "Học vượt",
        }
        return mapping.get(value, "Đúng hạn")
