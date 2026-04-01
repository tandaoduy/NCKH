# Kiến Trúc Flask App - Hệ Thống Gợi Ý Kế Hoạch Học Tập

## TỔNG QUAN GIẢI PHÁP

### 1. Bối cảnh Nghiên Cứu Khoa Học
**Đề tài**: Hệ thống hỗ trợ xây dựng kế hoạch học tập cá nhân hóa dựa trên Ontology chương trình đào tạo và hồ sơ sinh viên

**Đặc điểm nổi bật**:
- ✓ Kết hợp **tri thức cuộc (Ontology RDF)** với **dữ liệu sinh viên**
- ✓ Sử dụng **logic lập luận (inference)**: kiểm tra tiên quyết, song hành, kỳ mở
- ✓ Sử dụng **heuristic scoring** để ưu tiên môn dựa trên nợ, kết nối, trễ kỳ
- ✓ Sử dụng **Beam Search** để tối ưu tổ hợp môn trong ràng buộc
- ✓ **Giải thích quyết định**: mỗi môn có lý do tại sao được chọn

### 2. Luồng Xử Lý Tổng Thể

```
┌─────────────────────────────────────────────────────────────┐
│             FLASK WEB APPLICATION                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Frontend]                    [Backend]                   │
│  • Form nhập hồ sơ      →      1. Xác thực dữ liệu       │
│  • Select SV từ DB      →      2. Chuẩn hóa             │
│  • Hiển thị kết quả     →      3. Gọi Engine            │
│  • In báo cáo          ←      4. Trả về kết quả         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  RECOMMENDATION ENGINE (Module Hiện Tại)             │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │ 1. Nạp Ontology RDF                             │ │  │
│  │  │    → Trích xuất môn học, tiên quyết, v.v.     │ │  │
│  │  │                                                 │ │  │
│  │  │ 2. Chuẩn hóa hồ sơ SV                          │ │  │
│  │  │    → passed_courses, failed_courses            │ │  │
│  │  │                                                 │ │  │
│  │  │ 3. Lọc môn hợp lệ (8 điều kiện kinh doanh)    │ │  │
│  │  │    → Tiên quyết ✓, Kỳ mở ✓, v.v.             │ │  │
│  │  │                                                 │ │  │
│  │  │ 4. Chấm điểm heuristic                          │ │  │
│  │  │    H = debt×1000 + doPhu×20 + doTre×50         │ │  │
│  │  │    H_total = H + openNow×50 + rec×10 + goal    │ │  │
│  │  │                                                 │ │  │
│  │  │ 5. Phân nhóm Elective (4 nhóm quota)           │ │  │
│  │  │    → general, physical, foundation, special    │ │  │
│  │  │                                                 │ │  │
│  │  │ 6. Beam Search tối ưu (width=8)               │ │  │
│  │  │    → Chọn best_state (quota + score + credit) │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                  ↓                                    │  │
│  │  OUTPUT: Danh sách môn với giải thích               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## PHẦN I: KIẾN TRÚC THƯ MỤC (Folder Structure)

```
NCKH/
├── README.md
├── FLASK_APP_ARCHITECTURE.md (tài liệu này)
├── REQUIREMENTS.txt
│
├── owl/                           # Data layer
│   └── ontology_v18.rdf          # (giữ nguyên)
│
├── StudentDataStandardization/   # (giữ nguyên)
│   ├── DanhSachSinhVien.json
│   ├── DanhSachSinhVien.csv
│   ├── recommend_courses.py      # (sẽ refactor thành module)
│   └── ...
│
└── flask_app/                     # NEW: Web application
    ├── app.py                     # Điểm vào Flask
    ├── config.py                  # Cấu hình
    │
    ├── models/                    # Data models
    │   ├── __init__.py
    │   ├── student.py             # StudentProfile
    │   ├── course.py              # CourseInfo
    │   └── recommendation.py      # RecommendationResult
    │
    ├── services/                  # Business logic
    │   ├── __init__.py
    │   ├── ontology_loader.py     # Tải RDF ontology
    │   ├── student_data_service.py # Đọc/quản lý DP SV
    │   ├── recommendation_engine.py # Chuyển recommend_courses.py
    │   └── explanation_generator.py # Tạo giải thích
    │
    ├── routes/                    # Web endpoints
    │   ├── __init__.py
    │   ├── student_routes.py      # GET/POST sinh viên
    │   ├── recommendation_routes.py # POST gợi ý, GET kết quả
    │   └── report_routes.py       # Export/download báo cáo
    │
    ├── templates/                 # HTML Jinja2
    │   ├── base.html
    │   ├── student_form.html
    │   ├── student_list.html
    │   └── recommendation_result.html
    │
    ├── static/                    # CSS, JS
    │   ├── style.css
    │   └── main.js
    │
    └── utils/                     # Helper functions
        ├── __init__.py
        ├── constants.py           # WEIGHT_DEBT, MAX_CREDITS, v.v.
        └── validators.py          # Validate input
```

---

## PHẦN II: TUẦN TỰ XÂY DỰNG (Step-by-Step)

### BƯỚC 1: Refactor Recommendation Engine thành Module

**Mục tiêu**: Tách logic từ `recommend_courses.py` thành class reusable

**File**: `flask_app/services/recommendation_engine.py`

```python
# Pseudo-code cấu trúc
class RecommendationEngine:
    def __init__(self, ontology_path: str, ontology_type: str = 'rdf'):
        self.ontology_path = ontology_path
        self.graph = None
        self.course_data = {}
        self.dependency_count = {}
        self._load_ontology()
    
    def _load_ontology(self):
        """Nạp RDF ontology, trích xuất course_data"""
        # [Các code từ recommend_courses.py, dòng 244-337]
        pass
    
    def get_recommendation(self, target_student: Dict[str, Any]) -> RecommendationResult:
        """
        Nhận hồ sơ SV → trả về tổ hợp môn đề xuất
        
        Bao gồm các bước:
        1. Chuẩn hóa hồ sơ (passed_courses, failed_courses)
        2. Lọc môn hợp lệ (8 điều kiện)
        3. Chấm điểm heuristic
        4. Phân nhóm elective
        5. Beam Search
        
        Output: RecommendationResult(
            eligible_courses=[],      # Danh sách môn hợp lệ (đầu vào Beam)
            recommended_courses=[],   # Tơ hợp cuối cùng (đầu ra Beam)
            total_credit=0,
            explanations={},          # Giải thích tại sao chọn
            warnings=[]
        )
        """
        pass
```

**Các hàm chính (từ recommend_courses.py)**:
- `_load_ontology()`: dòng 244-337
- `_normalize_student_data()`: dòng 424-463
- `_get_valid_courses()`: dòng 471-549
- `_calculate_heuristic_scores()`: dòng 550-608
- `_categorize_electives()`: dòng 609-675
- `_beam_search()`: dòng 720-875

---

### BƯỚC 2: Xây Dựng Data Models

**File**: `flask_app/models/student.py`

```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class StudentProfile:
    """Hồ sơ sinh viên (từ DanhSachSinhVien.json)"""
    student_id: str
    name: str
    year_admitted: int
    major: str
    specialization: str
    study_goal: str  # 'đúng hạn', 'giảm tải', 'học vượt'
    current_semester: int
    total_credits_accumulated: int
    passed_courses: List[str]
    failed_courses: List[str]
    course_grades: Dict[str, float]
    
    def validate(self) -> List[str]:
        """Trả về danh sách lỗi nếu có"""
        errors = []
        if not self.student_id:
            errors.append("Mã sinh viên không được trống")
        if self.current_semester < 1:
            errors.append("Học kỳ hiện tại phải >= 1")
        return errors
```

**File**: `flask_app/models/recommendation.py`

```python
@dataclass
class RecommendedCourse:
    """Một môn trong tổ hợp đề xuất"""
    code: str
    name: str
    credits: int
    is_retake: bool
    heuristic_score: float
    total_priority_score: float
    reasons: List[str]  # Giải thích
    corequisites: List[str]
    
@dataclass
class RecommendationResult:
    """Kết quả đề xuất toàn bộ"""
    student: StudentProfile
    eligible_courses: List[RecommendedCourse]  # Đầu vào Beam
    recommended_courses: List[RecommendedCourse]  # Tơ hợp cuối
    total_recommended_credits: int
    elective_quotas: Dict[str, int]  # general, physical, foundation, specialization
    elective_quota_remaining: Dict[str, int]
    warnings: List[str]
    beam_search_details: str  # Giải thích chi tiết thuật toán
```

---

### BƯỚC 3: Xây Dựng Flask Routes

**File**: `flask_app/routes/recommendation_routes.py`

```python
@app.route('/api/students', methods=['GET'])
def list_students():
    """Lấy danh sách sinh viên từ DanhSachSinhVien.json"""
    students = student_data_service.get_all_students()
    return jsonify([s.to_dict() for s in students])

@app.route('/api/recommend', methods=['POST'])
def get_recommendation():
    """
    POST: {
        "student_id": "SV0016",
        "custom_data": {...}  # Optional: nếu cần override
    }
    
    RESPONSE: {
        "success": true,
        "result": RecommendationResult,
        "timestamp": "2026-03-29T10:30:00"
    }
    """
    data = request.json
    student_id = data.get('student_id')
    
    # Tải hồ sơ SV từ JSON/CSV
    student_profile = student_data_service.get_student(student_id)
    
    if not student_profile:
        return jsonify({
            "success": False,
            "error": f"Không tìm thấy SV {student_id}"
        }), 404
    
    # Gọi engine để tính toán
    result = recommendation_engine.get_recommendation(student_profile)
    
    return jsonify({
        "success": True,
        "result": result.to_dict(),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/ui/recommendation', methods=['GET'])
def recommendation_ui():
    """Giao diện web hiển thị kết quả"""
    # GET tham số ?student_id=SV0016 từ session hoặc DB
    result = get_recommendation_from_cache or database query
    return render_template('recommendation_result.html', result=result)
```

---

### BƯỚC 4: HTML Templates

**File**: `flask_app/templates/student_form.html`

```html
<form id="recommendation-form" method="POST" action="/api/recommend">
    <div class="form-group">
        <label for="student_id">Chọn/Nhập Mã Sinh Viên:</label>
        <datalist id="studentList">
            <!-- Tự động fill từ API /api/students -->
        </datalist>
        <input type="text" id="student_id" name="student_id" list="studentList" required>
    </div>
    
    <!-- Optional: Cho phép override dữ liệu nếu muốn nhập thủ công -->
    <div class="form-group">
        <label for="current_semester">Học Kỳ Hiện Tại:</label>
        <input type="number" id="current_semester" name="current_semester" min="1" max="8">
    </div>
    
    <button type="submit" class="btn-primary">Tạo Kế Hoạch Học Tập</button>
</form>
```

**File**: `flask_app/templates/recommendation_result.html`

**Hiển thị 4 phần chính:**

1. **Danh sách môn hợp lệ** (Eligible Courses)
   ```html
   <table class="eligible-courses">
       <thead>
           <tr>
               <th>Mã</th><th>Tên</th><th>TC</th><th>H</th><th>H_total</th><th>Lý Do</th>
           </tr>
       </thead>
       <tbody>
           {% for course in eligible_courses %}
           <tr>
               <td>{{ course.code }}</td>
               <td>{{ course.name }}</td>
               <td>{{ course.credits }}</td>
               <td>{{ "%.0f"|format(course.heuristic_score) }}</td>
               <td>{{ "%.0f"|format(course.total_priority_score) }}</td>
               <td>{{ course.reasons | join(', ') }}</td>
           </tr>
           {% endfor %}
       </tbody>
   </table>
   ```

2. **Tơ hợp đề xuất** (Recommended Courses - kết quả Beam Search)
   ```html
   <table class="recommended-courses" style="background-color: #e8f5e9;">
       <!-- Tương tự, nhưng highlight -->
   </table>
   <p style="font-weight: bold;">
       Tổng tín chỉ: <span id="total-credits">{{ total_recommended_credits }}</span>
   </p>
   ```

3. **Quota tự chọn**
   ```html
   <div class="quota-summary">
       <h4>Tiến độ Quota Tự Chọn:</h4>
       <ul>
           <li>Đại cương: {{ completed.general }}/{{ target.general }} boxes checked</li>
           <li>Thể chất: {{ completed.physical }}/{{ target.physical }}</li>
           <li>Cơ sở ngành: {{ completed.foundation }}/{{ target.foundation }}</li>
           <li>Chuyên ngành: {{ completed.specialization }}/{{ target.specialization }}</li>
       </ul>
   </div>
   ```

4. **Giải thích thuật toán**
   ```html
   <div class="algorithm-explanation">
       <h4>Giải Thích Beam Search (Nghiên Cứu Khoa Học)</h4>
       <pre>{{ beam_search_details }}</pre>
       
       <h5>Công Thức Heuristic:</h5>
       <pre>
           H = debt × 1000 + doPhu × 20 + doTre × 50
           H_total = H + openNow × 50 + recProximity × 10 + goalScore
       </pre>
   </div>
   ```

---

## PHẦN III: GIẢI THÍCH NGHIÊN CỨU (Research Explanation)

### 1. Công Thức Heuristic Scoring

```
┌─────────────────────────────────────────────────────┐
│ Điểm Ưu Tiên (Priority Score) để Xếp Hạng Môn      │
└─────────────────────────────────────────────────────┘

H = debt × 1000 + doPhu × 20 + doTre × 50

  debt = 1 nếu môn bị trượt (cần học lại), = 0 nếu không
         ⟹ Ưu tiên môn học lại, tránh để nợ

  doPhu = số môn khác phụ thuộc vào môn này (đếm qua toàn bộ tiên quyết)
         ⟹ Ưu tiên môn có nhiều tiên quyết cho môn khác
         ⟹ Giúp mở khóa nhiều môn tiếp theo

  doTre = max(0, current_semester - recommended_semester)
         ⟹ Nếu môn khuyến nghị ở kỳ 3 mà SV ở kỳ 5 → doTre = 2
         ⟹ Ưu tiên môn bị trễ so với lộ trình

H_total = H + openNow × 50 + recProximity × 10 + goalScore

  openNow = 1 nếu môn mở đúng kỳ đăng ký này, = 0
           ⟹ Ưu tiên môn có sẵn kỳ này

  recProximity = max(0, 10 - |next_semester - recommended_semester|)
                ⟹ Càng gần kỳ khuyến nghị, càng cao
                ⟹ Nếu khuyến nghị kỳ 3, đăng ký kỳ 4 → score = 9
                ⟹ Nếu khuyến nghị kỳ 3, đăng ký kỳ 8 → score = 0

  goalScore = 30 nếu mục tiêu 'đúng hạn'
            = 20 nếu mục tiêu 'giảm tải'
            = 10 nếu mục tiêu 'học vượt'
           ⟹ Ưu tiên môn phù hợp mục tiêu riêng của SV
```

**Ý nghĩa khoa học**:
- Các hệ số (1000, 20, 50, 50, 10) được thiết kế để nợ > trễ > kết nối > proximity
- Phản ánh chiến lược: học lại nợ trước → trễ kỳ → kết nối → gần khuyến nghị
- Có thể điều chỉnh hệ số dựa trên phân tích định lượng logic chương trình

---

### 2. Beam Search Algorithm

```
Khởi tạo:
  - Beam width = 8 (giữ 8 trạng thái tốt nhất mỗi vòng)
  - State = {selected_codes, credit, score, elective_counts}
  - best_state = trạng thái rỗng

Vòng lặp (until no improvement):
  Với mỗi State hiện tại:
    - Lất tất cả môn chưa chọn
    - Thử thêm từng môn (hoặc bundle corequisite)
      - Kiểm tra: credit không vượt max?
      - Kiểm tra: quota tự chọn không vượt?
      - Kiểm tra: môn và tiên quyết đủ điều kiện?
      ↓ Nếu thỏa, tạo State mới
        next_state = state + course_bundle
        
  Giữ lại 8 State tốt nhất theo:
    1. Đáp ứng quota tự chọn (cao nhất)
    2. Điểm ưu tiên (nếu hòa)
    3. Tín chỉ (nhiều hơn nếu hòa)
    
  Nếu không có State mới → kết thúc

Chọn kết quả:
  best_state = State có (quota_fill_score, total_score, credit) tốt nhất
```

**Tại sao Beam Search?**
- NP-hard problem: số lượng tổ hợp môn là exponential
- Beam Search: tìm nghiệm gần tối ưu trong thời gian polynomial
- Tham số `beam_width=8`: cân bằng giữa chất lượng và tốc độ

---

### 3. Các Ràng Buộc Kinh Doanh

```
Lọc Môn Hợp Lệ (Boolean Rules):

  1. Chưa đậu: code ∉ passed_courses
     └─ Không gợi ý môn đã đạt
  
  2. Tiên quyết đủ: ∀ prerequisite ∈ passed_courses
     └─ Kiểm tra logic chương trình đào tạo
  
  3. Kỳ mở: openSemesterType ∈ {next_sem_type, 3, 12}
     └─ 1 = Lẻ, 2 = Chẵn, 3 = Cả 2
  
  4. Kỳ khuyến nghị: 
     - Nếu goal = 'học vượt': cho phép bất kỳ
     - Nếu goal ∈ {'đúng hạn', 'giảm tải'}: recommended_sem ≤ next_sem
  
  5. Chuyên ngành khớp:
     - Nếu SV chọn chuyên ngành→ môn phải của chuyên ngành đó
     - Nếu SV chưa chọn → chỉ nhận môn bắt buộc (foundation)
  
  6. Tín chỉ bản thân: credit ≤ 27 (không quá tải)
  
  7. Ràng buộc cứng 1: 
     - Nếu recommended_sem = 8 → chỉ gợi ý ở next_sem = 8
  
  8. Ràng buộc cứng 2:
     - Nếu là "Môn thực tập ngành" → chỉ gợi ý ở next_sem = 7

Constraint Tổ Hợp:
  
  9. Quota Elective: Giữ môn tự chọn theo nhu cầu
     general, physical, foundation, specialization
     └─ Không gợi ý thừa 1 danh mục
  
  10. Bundle Corequisite: Nếu chọn môn A, phải chọn luôn môn song hành B
      └─ Đảm bảo tính nhất quán học lý thuyết + thực hành
  
  11. Max Credit: tổn total_credit ≤ student_max_register
      (mặc định 27, có thể custom)
```

---

## PHẦN IV: TUẦN TỰ TRIỂN KHAI (Deployment Sequence)

### Phase 1: Backend Module (Tuần 1)
- [ ] Refactor `recommendation_engine.py` từ script
- [ ] Viết `StudentDataService` đọc JSON/CSV
- [ ] Viết `OntologyLoader` tách logic Ontology
- [ ] Unit test cho từng module

### Phase 2: Flask API (Tuần 2)
- [ ] Tạo routes `/api/students`, `/api/recommend`
- [ ] Viết request/response validators
- [ ] Caching strategy: không tải ontology mỗi request
- [ ] Integration test: end-to-end flow

### Phase 3: Frontend UI (Tuần 3)
- [ ] Form nhập hồ sơ + datalist SV
- [ ] Hiển thị kết quả 4 phần chính
- [ ] Động CSS highlight, hover, tooltip
- [ ] Export PDF báo cáo

### Phase 4: Nghiên Cứu & Tài Liệu (Tuần 4)
- [ ] Viết bài báo: " Hybrid Approach kết hợp Ontology + Heuristic + Beam Search"
- [ ] So sánh beam_width=8 vs width=4,16,32
- [ ] Phân tích: thời gian, chất lượng giải pháp
- [ ] Ghi chú: cách điều chỉnh hệ số trọng số theo mục tiêu

---

## PHẦN V: CÁC TỆPIN THIẾT (Configuration Files)

### File: `requirements.txt`

```
Flask==3.0.0
rdflib==7.0.0
Werkzeug==3.0.0
python-dotenv==1.0.0
gunicorn==21.0.0
```

### File: `config.py`

```python
import os

class Config:
    # Paths
    ONTOLOGY_PATH = os.path.join(os.path.dirname(__file__), '..', 'owl', 'ontology_v18.rdf')
    STUDENT_DATA_JSON = os.path.join(os.path.dirname(__file__), '..', 'StudentDataStandardization', 'DanhSachSinhVien.json')
    STUDENT_DATA_CSV = os.path.join(os.path.dirname(__file__), '..', 'StudentDataStandardization', 'DanhSachSinhVien.csv')
    
    # Recommendation Engine Parameters
    BEAM_WIDTH = 8
    REGISTER_MAX_CREDITS = 27
    REGISTER_MIN_CREDITS = 10
    
    # Heuristic Weights
    WEIGHT_DEBT = 1000
    WEIGHT_LINK = 20
    WEIGHT_DELAY = 50
    
    # Elective Quotas (default)
    ELECTIVE_QUOTAS = {
        'general': 1,
        'physical': 2,
        'foundation': 1,
        'specialization': 3,
    }
```

---

## PHẦN VI: Ví Dụ API Request/Response

### POST /api/recommend

**Request:**
```json
{
  "student_id": "SV0016"
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "student": {
      "student_id": "SV0016",
      "name": "Nguyễn Văn A",
      "current_semester": 3,
      "study_goal": "đúng hạn"
    },
    "eligible_courses": [
      {
        "code": "SOT301",
        "name": "Nhập môn ngành Công nghệ thông tin",
        "credits": 3,
        "heuristic_score": 1050,
        "total_priority_score": 1135,
        "reasons": ["môn bắt buộc", "mở đúng học kỳ hiện tại", "đúng học kỳ khuyến nghị"]
      },
      ...
    ],
    "recommended_courses": [
      {
        "code": "SOT301",
        "name": "Nhập môn ngành Công nghệ thông tin",
        "credits": 3,
        "is_retake": false,
        "reasons": ["môn bắt buộc", "mở đúng học kỳ hiện tại"]
      },
      ...
    ],
    "total_recommended_credits": 24,
    "elective_quotas": {
      "general": 1,
      "physical": 2,
      "foundation": 1,
      "specialization": 3
    },
    "elective_quota_remaining": {
      "general": 0,
      "physical": 1,
      "foundation": 1,
      "specialization": 2
    },
    "beam_search_details": "Beam width=8, final state selected 5 courses, quota filled 2/7 categories..."
  },
  "timestamp": "2026-03-29T10:30:00.123456"
}
```

---

## PHẦN VII: Giải Thích Tại Sao (Why This Architecture)

| Yếu tố | Giải thích Nghiên Cứu |
|--------|----------------------|
| **Ontology** | Tri thức cuộc (domain knowledge) quy chuẩn hóa, cho phép suy luận logic tiên quyết chính xác |
| **Heuristic Scoring** | Kết hợp multiple objectives (nợ, kết nối, trễ kỳ, mục tiêu) thành 1 điểm tổng hợp |
| **Beam Search** | Giải pháp gần tối ưu cho NP-hard combinatorial problem, đạt ✓ quota, ✓ credit, ✓ điểm tối đa |
| **Explanation** | Độ tin cậy (trust) hệ thống tăng khi người dùng hiểu "vì sao" được gợi ý |
| **Modular Design** | Cho phép: (1) Testing từng phần độc lập, (2) Mở rộng (thêm constraint, heuristic), (3) A/B test beam_width |

---

## PHẦN VIII: Bước Tiếp Theo cho Bạn

1. **Hôm nay**: Tạo thư mục `flask_app/` và các file `.py` tương ứng
2. **Ngày mai**: Refactor `recommend_courses.py` thành `RecommendationEngine` class
3. **Ngày kia**: Viết routes Flask, test API cơ bản
4. **Tuần sau**: Viết HTML/CSS, hoàn biến kết quả

---

**Tôi sẵn sàng hướng dẫn chi tiết từng phần. Muốn bắt đầu phần nào trước?**
- A. Refactor Engine → RecommendationEngine class
- B. Xây dựng folder structure + Django/Flask cơ bản
- C. Viết HTML templates + CSS
- D. Viết unit tests

