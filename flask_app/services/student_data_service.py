"""
Service for loading and managing student data (JSON/CSV)
"""

import json
import csv
import os
from typing import List, Optional, Dict, Any
from flask_app.models.student import StudentProfile


class StudentDataService:
    """Quản lý dữ liệu sinh viên từ JSON/CSV"""
    
    def __init__(self, json_path: str, csv_path: str):
        self.json_path = json_path
        self.csv_path = csv_path
        self._students_cache: Optional[List[StudentProfile]] = None
    
    def get_all_students(self, force_reload: bool = False) -> List[StudentProfile]:
        """Lấy danh sách tất cả sinh viên"""
        if self._students_cache and not force_reload:
            return self._students_cache
        
        students = []
        
        # Try loading from JSON first
        if os.path.exists(self.json_path):
            try:
                students = self._load_from_json()
            except Exception as e:
                print(f"Error loading JSON: {e}")
        
        # Fallback to CSV
        if not students and os.path.exists(self.csv_path):
            try:
                students = self._load_from_csv()
            except Exception as e:
                print(f"Error loading CSV: {e}")
        
        self._students_cache = students
        return students
    
    def get_student(self, student_id: str) -> Optional[StudentProfile]:
        """Lấy hồ sơ sinh viên theo mã"""
        students = self.get_all_students()
        
        # Normalize student_id for comparison
        normalized_id = self._normalize_student_id(student_id)
        
        for student in students:
            if self._normalize_student_id(student.student_id) == normalized_id:
                return student
        
        return None
    
    def _load_from_json(self) -> List[StudentProfile]:
        """Tải dữ liệu sinh viên từ JSON"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError("JSON phải là danh sách")
        
        students = []
        for item in data:
            try:
                student = self._parse_student_dict(item)
                if student:
                    students.append(student)
            except Exception as e:
                print(f"Warning: Cannot parse student {item.get('mã sinh viên', '?')}: {e}")
        
        return students
    
    def _load_from_csv(self) -> List[StudentProfile]:
        """Tải dữ liệu sinh viên từ CSV"""
        students = []
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    student = self._parse_student_dict(row)
                    if student:
                        students.append(student)
                except Exception as e:
                    print(f"Warning: Cannot parse CSV row: {e}")
        
        return students
    
    def _parse_student_dict(self, data: Dict[str, Any]) -> Optional[StudentProfile]:
        """Parse dict thành StudentProfile"""
        
        # Find student ID
        student_id = None
        for key in ['mã sinh viên', 'mã sinh vien', 'ma sinh vien', 'student_id', 'id']:
            val = data.get(key)
            if val and str(val).strip():
                student_id = str(val).strip()
                break
        
        if not student_id:
            return None
        
        # Parse other fields
        name = str(data.get('tên sinh viên', '')).strip() or str(data.get('name', '')).strip()
        year_admitted = self._safe_int(data.get('năm vào học', 2023), 2023)
        major = str(data.get('ngành', 'Công Nghệ Thông Tin')).strip()
        specialization = str(data.get('chuyên ngành', 'Chưa chọn chuyên ngành')).strip()
        study_goal = str(data.get('mục tiêu học tập', 'đúng hạn')).strip().lower()
        current_semester = self._safe_int(data.get('học kỳ hiện tại', 1), 1)
        total_credits = self._safe_int(data.get('số tín chỉ đã tích lũy', 0), 0)
        max_credits = self._safe_int(data.get('số tín chỉ đăng ký tối đa', 27), 27)
        
        # Parse course lists
        passed_courses = self._parse_course_list(data.get('danh sách môn đã học', []))
        failed_courses = self._parse_course_list(data.get('danh sách môn chưa đạt', []))
        
        # Parse grades
        grades = self._parse_grades(data.get('điểm từng môn', []))
        
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
        """Parse danh sách môn (có thể là dict hoặc list)"""
        courses = set()
        
        if isinstance(data, dict):
            for code in data.keys():
                if code and str(code).strip():
                    courses.add(str(code).strip().upper())
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    code = item.get('mã môn học', '')
                elif isinstance(item, str):
                    code = item
                else:
                    continue
                if code and str(code).strip():
                    courses.add(str(code).strip().upper())
        
        return courses
    
    def _parse_grades(self, data: Any) -> Dict[str, float]:
        """Parse bảng điểm"""
        grades = {}
        
        if not isinstance(data, list):
            return grades
        
        for item in data:
            if not isinstance(item, dict):
                continue
            code = item.get('mã môn học', '')
            grade = item.get('điểm', 0)
            if code and str(code).strip():
                try:
                    grades[str(code).strip().upper()] = float(grade)
                except (ValueError, TypeError):
                    pass
        
        return grades
    
    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        """Chuyển value thành int an toàn"""
        try:
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            s = str(value).strip()
            if not s:
                return default
            if '.' in s:
                return int(float(s))
            return int(s)
        except Exception:
            return default
    
    @staticmethod
    def _normalize_student_id(student_id: str) -> str:
        """Normalize student ID for comparison"""
        return student_id.strip().lower().replace('sv', '')
