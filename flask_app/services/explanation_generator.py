"""
Generate explanation for recommendation decisions
Tạo giải thích chi tiết về quyết định gợi ý môn học
"""

from typing import List, Dict
from flask_app.models.recommendation import RecommendationResult


class ExplanationGenerator:
    """Tạo giải thích lý do tại sao môn được chọn"""
    
    def generate_beam_search_explanation(self, 
                                         beam_width: int,
                                         iterations: int,
                                         final_quota_fill: int) -> str:
        """Giải thích chi tiết thuật toán Beam Search"""
        
        explanation = f"""
=== GIẢI THÍCH THUẬT TOÁN BEAM SEARCH ===

1. TỔNG QUAN:
   - Beam width: {beam_width} (giữ {beam_width} trạng thái tốt nhất mỗi vòng)
   - Mục tiêu: Tìm tổ hợp môn tối ưu trong constraint (credit, quota, score)
   - Kết quả: Đạt {final_quota_fill}/4 quota danh mục tự chọn

2. LUỒNG THUẬT TOÁN:
   Vòng lặp (until convergence):
     - Với mỗi state hiện tại:
       • Lấy tất cả môn chưa chọn
       • Thử thêm từng môn (hoặc bundle corequisite)
       • Kiểm tra: credit ≤ max ✓, quota OK ✓, tiên quyết ✓?
       → Nếu OK, tạo state mới: next_state = state + course
       
     - Giữ lại TOP {beam_width} state theo:
       1. Đáp ứng quota tự chọn cao nhất
       2. Điểm ưu tiên cao nhất (nếu hòa)
       3. Tín chỉ nhiều nhất (nếu hòa)
   
   Kết thúc khi không có state mới hoặc đã lặp đủ lần

3. CHỌN KẾT QUẢ:
   - Best state = state có (quota_score, priority_score, credit) cao nhất
   - Đảm bảo:
     ✓ Tổng tín chỉ ≤ {beam_width * 3} (max credit)
     ✓ Quota tự chọn phù hợp
     ✓ Tất cả tiên quyết được thỏa

4. ĐẶC ĐIỂM:
   - Tư duy: Tìm gần-tối-ưu (near-optimal) thay vì brute force
   - Thời gian: O(beam_width × num_courses) = Polynomial
   - So sánh: Brute force sẽ là O(2^num_courses) = Exponential (không khả thi)
"""
        return explanation
    
    def generate_heuristic_explanation(self) -> str:
        """Giải thích công thức heuristic scoring"""
        
        explanation = """
=== GIẢI THÍCH CÔNG THỨC HEURISTIC ===

Công thức Điểm Ưu Tiên (Priority Score):

H = debt × 1000 + doPhu × 20 + doTre × 50

  ┌─────────────────────────────────────────────────┐
  │ debt (Nợ Môn): 1 nếu bị trượt, 0 nếu chưa học   │
  │ → Weight 1000 (cao nhất!)                       │
  │ → Ưu tiên: PHẢI học lại môn nợ trước           │
  │ → VD: SV0016 trượt INS330 → debt=1 → +1000      │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │ doPhu (Số Môn Phụ Thuộc):                       │
  │ = số môn khác có tiên quyết là môn này          │
  │ → Weight 20                                      │
  │ → Ưu tiên: Học môn có nhiều "con em"          │
  │ → VD: SOT320 có 3 môn phụ thuộc → doPhu=3      │
  │      → +60 điểm                                 │
  │ → Logic: Mở khóa nhiều cơ hội học tiếp         │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │ doTre (Trễ Kỳ):                                 │
  │ = max(0, current_semester - recommended_sem)   │
  │ → Weight 50                                      │
  │ → Ưu tiên: Môn bị trễ so với lộ trình          │
  │ → VD: MAT327 khuyến nghị S3, SV ở S5:          │
  │      doTre = 5-3 = 2 → +100 điểm               │
  │ → Logic: Tránh tình trạng quá trễ lộ trình    │
  └─────────────────────────────────────────────────┘

H_total = H + openNow × 50 + recProximity × 10 + goalScore

  ┌─────────────────────────────────────────────────┐
  │ openNow: 1 nếu mở đúng kỳ đang đăng ký, 0      │
  │ → Weight 50                                      │
  │ → Logic: Môn mở sẵn là tốt, không cần chờ     │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │ recProximity: max(0, 10 - |next_sem - rec_sem|)│
  │ → Nếu next_sem = 4, rec_sem = 3: gap=1         │
  │    → recProximity = 10-1 = 9 → +90 điểm         │
  │ → Nếu next_sem = 8, rec_sem = 3: gap=5         │
  │    → recProximity = 10-5 = 5 → +50 điểm         │
  │ → Logic: Gần khuyến nghị → ưu tiên              │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────┐
  │ goalScore: Phụ thuộc mục tiêu học               │
  │ = 30 nếu "đúng hạn"                             │
  │ = 20 nếu "giảm tải"                             │
  │ = 10 nếu "học vượt"                             │
  │ → Logic: Ưu tiên môn phù hợp chiến lược SV     │
  └─────────────────────────────────────────────────┘

VÍ DỤ THỰC TẾ:
─────────────

Học viên: SV0016, ở kỳ 3, mục tiêu "đúng hạn"

Môn A: INS330 (Database)
  - debt = 1 (trượt ở kỳ 1)
  - doPhu = 2 (SOT341, SOT342 cần INS330)
  - doTre = 3 - 2 = 1 (khuyến nghị kỳ 2, giờ kỳ 3)
  - H = 1×1000 + 2×20 + 1×50 = 1090
  
  - openNow = 1 (mở kỳ lẻ, kỳ 3 lẻ)
  - recProximity = max(0, 10 - |3-2|) = 9
  - goalScore = 30 (mục tiêu đúng hạn)
  - H_total = 1090 + 50 + 90 + 30 = 1260
  
  → SCORE CAO → ƯU TIÊN ĐƯỢC CHỌ TRƯỚC

Môn B: SOT350 (Elective, nước ngoài)
  - debt = 0 (chưa học)
  - doPhu = 0 (không có môn phụ thuộc)
  - doTre = 0 (khuyến nghị kỳ 4, hiện kỳ 3)
  - H = 0 + 0 + 0 = 0
  
  - openNow = 1
  - recProximity = max(0, 10 - |3-4|) = 9
  - goalScore = 30
  - H_total = 0 + 50 + 90 + 30 = 170
  
  → SCORE THẤP → CHỌN SAU CÓ KHẢ NĂNG KHÔNG CHỌN
"""
        return explanation
    
    def generate_recommendation_summary(self, result: RecommendationResult) -> str:
        """Tóm tắt kết quả gợi ý"""
        
        summary = f"""
=== TÓM TẮT KẾ HOẠCH HỌC TẬP ===

Sinh viên: {result.student_name} ({result.student_id})
Học kỳ hiện tại: {result.current_semester} → Đăng ký kỳ: {result.next_semester}
Mục tiêu học: {result.study_goal}

KẾT QUẢ:
─────────

Danh sách môn hợp lệ (đầu vào Beam Search):
  • Tổng số: {result.total_eligible_count} môn
  • Gồm: môn bắt buộc, tự chọn, học lại
  • Những môn này đã thỏa 8 điều kiện kinh doanh:
    ✓ Chưa đạt
    ✓ Tiên quyết OK
    ✓ Kỳ mở phù hợp
    ✓ Kỳ khuyến nghị phù hợp goal
    ✓ Chuyên ngành khớp
    ✓ Tín chỉ không quá tải
    ✓ Không vi phạm ràng buộc cứng kỳ 8 vs kỳ 7
    + Quota tự chọn chưa đầy

Tơ hợp đề xuất (kết quả Beam Search):
  • Tổng số: {result.total_recommended_count} môn
  • Tổng tín chỉ: {result.total_recommended_credits}/27
  • Danh sách:
"""
        
        for i, course in enumerate(result.recommended_courses, 1):
            status = "Học lại" if course.is_retake else f"S{course.recommended_semester}"
            summary += f"\n    {i}. {course.code} - {course.name}\n"
            summary += f"       TC: {course.credits} | {status} | Score: {course.total_priority_score:.0f}\n"
            summary += f"       Lý do: {', '.join(course.reasons)}\n"
        
        summary += f"""

TIẾN ĐỘ QUOTA TỰ CHỌN:
─────────────────────

Danh mục           | Đã Hoàn | Mục Tiêu | Còn Thiếu | Đã Chọn
─────────────────────────────────────────────────────────
"""
        
        for cat in ['general', 'physical', 'foundation', 'specialization']:
            completed = result.elective_completed_counts.get(cat, 0)
            target = result.elective_target_quotas.get(cat, 0)
            remaining = result.elective_quota_remaining.get(cat, 0)
            finalized = result.finalized_elective_counts.get(cat, 0)
            
            cat_name = {
                'general': 'Đại cương',
                'physical': 'Thể chất',
                'foundation': 'Cơ sở ngành',
                'specialization': 'Chuyên ngành',
            }.get(cat, cat)
            
            summary += f"{cat_name:15} | {completed:7} | {target:8} | {remaining:9} | {finalized:8}\n"
        
        if result.warnings:
            summary += f"""

CẢNH BÁO:
─────────
"""
            for warning in result.warnings:
                summary += f"  ⚠ {warning}\n"
        
        return summary
