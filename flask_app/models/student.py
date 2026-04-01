"""
Student Profile Data Models
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class StudentProfile:
    """Hồ sơ sinh viên"""
    
    student_id: str
    name: str
    year_admitted: int
    major: str
    specialization: str = "Chưa chọn chuyên ngành"
    study_goal: str = "đúng hạn"  # 'đúng hạn', 'giảm tải', 'học vượt'
    current_semester: int = 1
    total_credits_accumulated: int = 0
    max_credits_to_register: int = 27
    
    passed_courses: List[str] = field(default_factory=list)
    failed_courses: List[str] = field(default_factory=list)
    course_grades: Dict[str, float] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """Kiểm tra tính hợp lệ của hồ sơ"""
        errors = []
        
        if not self.student_id or not self.student_id.strip():
            errors.append("Mã sinh viên không được trống")
        
        if not self.name or not self.name.strip():
            errors.append("Tên sinh viên không được trống")
        
        if self.year_admitted < 2000 or self.year_admitted > 2030:
            errors.append("Năm vào học không hợp lệ (2000-2030)")
        
        if self.current_semester < 1 or self.current_semester > 8:
            errors.append("Học kỳ hiện tại phải từ 1-8")
        
        if self.total_credits_accumulated < 0 or self.total_credits_accumulated > 150:
            errors.append("Tín chỉ tích lũy không hợp lệ (0-150)")
        
        if self.max_credits_to_register < 10 or self.max_credits_to_register > 30:
            errors.append("Tín chỉ tối đa đăng ký phải từ 10-30")
        
        if self.study_goal not in ['đúng hạn', 'giảm tải', 'học vượt']:
            errors.append("Mục tiêu học không hợp lệ")
        
        return errors
    
    def to_dict(self):
        """Chuyển thành dict (để serialize JSON)"""
        return asdict(self)
    
    def next_semester(self) -> int:
        """Học kỳ sắp tới"""
        return self.current_semester + 1
    
    def next_semester_type(self) -> int:
        """Loại học kỳ sắp tới: 1=Lẻ, 2=Chẵn"""
        next_sem = self.next_semester()
        return 1 if next_sem % 2 != 0 else 2


@dataclass
class CourseRecord:
    """Ghi nhận kết quả học một môn"""
    
    code: str
    name: str
    credits: int
    grade: float
    status: str  # "Đạt" hoặc "Chưa đạt"
    semester_taken: int
    
    def is_passed(self) -> bool:
        return self.status == "Đạt"
