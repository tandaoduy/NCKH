"""
Recommendation Result Data Models
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class RecommendedCourse:
    """Một môn học được đề xuất"""
    
    code: str
    name: str
    credits: int
    is_retake: bool = False
    recommended_semester: int = 0
    heuristic_score: float = 0.0
    total_priority_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    corequisites: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return asdict(self)


@dataclass
class RecommendationResult:
    """Kết quả gợi ý kế hoạch học tập toàn bộ"""
    
    student_id: str
    student_name: str
    current_semester: int
    next_semester: int
    study_goal: str
    
    # Danh sách các môn
    eligible_courses: List[RecommendedCourse] = field(default_factory=list)
    recommended_courses: List[RecommendedCourse] = field(default_factory=list)
    
    # Thống kê
    total_eligible_count: int = 0
    total_recommended_count: int = 0
    total_recommended_credits: int = 0
    
    # Quota tự chọn
    elective_target_quotas: Dict[str, int] = field(default_factory=dict)
    elective_completed_counts: Dict[str, int] = field(default_factory=dict)
    elective_quota_remaining: Dict[str, int] = field(default_factory=dict)
    finalized_elective_counts: Dict[str, int] = field(default_factory=dict)
    
    # Cảnh báo & Giải thích
    warnings: List[str] = field(default_factory=list)
    beam_search_details: str = ""
    heuristic_formula: str = ""
    
    # Metadata
    generated_at: str = ""
    processing_time_ms: float = 0.0
    
    def to_dict(self):
        result = asdict(self)
        # Convert nested dataclass lists to dicts
        result['eligible_courses'] = [c.to_dict() for c in self.eligible_courses]
        result['recommended_courses'] = [c.to_dict() for c in self.recommended_courses]
        return result


@dataclass
class BeamSearchState:
    """State trong Beam Search algorithm"""
    
    selected_codes: set = field(default_factory=set)
    selected_courses: List[RecommendedCourse] = field(default_factory=list)
    credit: int = 0
    priority_score: float = 0.0
    
    # Quota tracking
    elective_counts: Dict[str, int] = field(default_factory=lambda: {
        'general': 0,
        'physical': 0,
        'foundation': 0,
        'specialization': 0,
    })
    
    # Tiebreaker
    tie_break_random: float = 0.0
