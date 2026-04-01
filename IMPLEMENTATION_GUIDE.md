# HƯỚNG DẪN TRIỂN KHAI CHUYÊN BIỆT

## GIAI ĐOẠN 1: XÂY DỰNG RECOMMENDATION ENGINE CLASS

### Bước 1.1: Refactor `recommend_courses.py` → `RecommendationEngine` class

**Tại sao phải refactor?**
- Script hiện tại: Đầu vào từ CLI, đầu ra là file + console
- Flask app cần: Đầu vào từ API, đầu ra là Python object (JSON serializable)
- Refactor: Tách logic thành class reusable + methods tĩnh

**Bước này:**
1. Tạo file `flask_app/services/recommendation_engine.py`
2. Sao chép các function từ `recommend_courses.py`
3. Ggroup lại thành class - xem ví dụ pseudo-code dưới

```python
# Pseudo-code: flask_app/services/recommendation_engine.py

class RecommendationEngine:
    
    def __init__(self, ontology_path, beam_width=8):
        self.ontology_path = ontology_path
        self.beam_width = beam_width
        self.graph = None          # RDF graph
        self.course_data = {}      # code -> {name, prereqs, ...}
        self.dependency_count = {} # code -> độ phục thuộc
        self._load_ontology()
    
    def _load_ontology(self):
        """
        Sao chép dòng 244-337 recommend_courses.py
        Trích xuất: course_data dict, specializations_map
        """
        self.graph = Graph()
        self.graph.parse(self.ontology_path, format="xml")
        # ... extract course_data, dependency_count ...
    
    def get_recommendation(self, student_profile: StudentProfile) -> RecommendationResult:
        """
        Main entry point
        Input: StudentProfile object
        Output: RecommendationResult object
        """
        # Bước 1: Chuẩn hóa (dòng 424-463)
        passed_courses, failed_courses = self._normalize_student_data(student_profile)
        
        # Bước 2: Lọc môn (dòng 471-549)
        valid_courses = self._get_valid_courses(
            student_profile, passed_courses, failed_courses
        )
        
        # Bước 3: Chấm điểm (dòng 550-608)
        self._score_courses(student_profile, valid_courses)
        
        # Bước 4: Phân nhóm tự chọn (dòng 609-675)
        self._categorize_electives(valid_courses)
        
        # Bước 5: Beam Search (dòng 720-875)
        result = self._beam_search_optimize(student_profile, valid_courses)
        
        return result
    
    def _normalize_student_data(self, student):
        """Parse passed/failed courses từ StudentProfile"""
        # Implement từ dòng 424-463
        pass
    
    def _get_valid_courses(self, student, passed, failed):
        """Lọc 8 điều kiện"""
        # Implement từ dòng 471-549
        pass
    
    def _score_courses(self, student, courses):
        """Tính H, H_total"""
        # Implement từ dòng 550-608
        pass
    
    def _categorize_electives(self, courses):
        """Phân loại general/physical/foundation/specialization"""
        # Implement từ dòng 609-675
        pass
    
    def _beam_search_optimize(self, student, courses):
        """Beam Search main loop"""
        # Implement từ dòng 720-875
        pass
```

---

## GIAI ĐOẠN 2: XÂY DỰNG DATA MODELS

**Đã tạo sẵn:**
- `flask_app/models/student.py` → `StudentProfile`
- `flask_app/models/recommendation.py` → `RecommendationResult`, `RecommendedCourse`

**Như thế nào để sử dụng:**

```python
# Trong API route
@app.route('/api/recommendations', methods=['POST'])
def create_recommendation():
    data = request.json
    student_id = data['student_id']
    
    # Lấy hồ sơ
    student = student_service.get_student(student_id)
    # → Returns: StudentProfile(id, name, passed_courses, ...)
    
    # Gọi engine
    result = recommendation_engine.get_recommendation(student)
    # → Returns: RecommendationResult(eligible_courses, recommended_courses, ...)
    
    # Serialize JSON
    return jsonify(result.to_dict())
```

---

## GIAI ĐOẠN 3: VIẾT HTML/CSS TEMPLATES

**Hiển thị kết quả gồm 4 phần:**

### 1. Thông tin sinh viên (header)
```html
<div class="student-info">
    <h2>{{ student_name }} ({{ student_id }})</h2>
    <p>Ngành: {{ major }}, Chuyên ngành: {{ specialization }}</p>
    <p>Kỳ hiện tại: {{ current_semester }} → Đăng ký kỳ {{ next_semester }}</p>
    <p>Mục tiêu: {{ study_goal }}</p>
</div>
```

### 2. Danh sách môn hợp lệ (table)
```html
<div class="eligible-section">
    <h3>Danh Sách Môn Hợp Lệ ({{ eligible_count }} môn)</h3>
    <table class="courses-table">
        <thead>
            <tr>
                <th>Mã</th><th>Tên</th><th>TC</th>
                <th>Là Nợ?</th><th>H (Heuristic)</th><th>H_total</th><th>Lý Do</th>
            </tr>
        </thead>
        <tbody>
            {% for course in eligible_courses %}
            <tr>
                <td>{{ course.code }}</td>
                <td>{{ course.name }}</td>
                <td>{{ course.credits }}</td>
                <td>{% if course.is_retake %}✓{% endif %}</td>
                <td>{{ "%.1f"|format(course.heuristic_score) }}</td>
                <td class="score-high">{{ "%.1f"|format(course.total_priority_score) }}</td>
                <td>{{ course.reasons|join(', ') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

### 3. Tơ hợp đề xuất (highlight)
```html
<div class="recommended-section" style="background-color: #e8f5e9; padding: 20px;">
    <h3>Kế Hoạch Học Tập Đề Xuất ({{ recommended_count }} môn)</h3>
    <div class="highlight">
        <strong>Tổng Tín Chỉ: {{ total_recommended_credits }}/27</strong>
    </div>
    <table class="courses-table">
        <!-- Tương tự, highlight với background -->
    </table>
</div>
```

### 4. Giải thích Beam Search
```html
<div class="explanation-section">
    <h3>Giải Thích Thuật Toán & Công Thức</h3>
    <details>
        <summary>📊 Công Thức Heuristic Scoring</summary>
        <pre>{{ heuristic_formula }}</pre>
    </details>
    <details>
        <summary>🔍 Beam Search Algorithm</summary>
        <pre>{{ beam_search_details }}</pre>
    </details>
</div>
```

---

## GIAI ĐOẠN 4: TEST & DEBUG

### Unit Test Example

```python
# tests/test_recommendation_engine.py

def test_load_ontology():
    engine = RecommendationEngine('path/ontology_v18.rdf')
    assert len(engine.course_data) > 0
    assert 'INS326' in engine.course_data

def test_normalize_student():
    student = StudentProfile(
        student_id='SV0016',
        passed_courses=['INS326', 'SOT320'],
        failed_courses=['INS330'],
    )
    engine = RecommendationEngine('...')
    passed, failed = engine._normalize_student_data(student)
    
    assert 'INS326' in passed
    assert 'INS330' in failed

def test_scoring():
    # Kiểm tra công thức H = debt*1000 + ...
    # Kiểm tra H_total = H + openNow*50 + ...
    pass

def test_beam_search():
    # Kiểm tra kết quả tối ưu
    # Kiểm tra không vượt credit max
    # Kiểm tra quota hợp lệ
    pass
```

---

## GIAI ĐOẠN 5: TRIỂN KHAI & OPTIMIZATION

### A. Caching Ontology

```python
# app.py
class OntologyCache:
    def __init__(self):
        self.graph = None
        self.course_data = None
    
    def load(self, path):
        # Load once, reuse for all requests
        if self.graph is None:
            self.graph = Graph()
            self.graph.parse(path, format='xml')
            # Extract course_data
    
    def get_course_data(self):
        return self.course_data

# Initialize once
ontology_cache = OntologyCache()
app.ontology_cache = ontology_cache

# In RecommendationEngine
def __init__(self, ontology_path):
    self.course_data = app.ontology_cache.get_course_data()
```

### B. Performance Profiling

```python
import time

@app.route('/api/recommendations', methods=['POST'])
def get_recommendation():
    start_time = time.time()
    
    # ... processing ...
    
    elapsed = time.time() - start_time
    response = {
        'data': result.to_dict(),
        'processing_time_ms': elapsed * 1000,
    }
    return jsonify(response)
```

---

## GIAI ĐOẠN 6: VIẾT PAPER NGHIÊN CỨU

### Cấu trúc bài báo:

1. **Abstract**: Kết hợp Ontology + Heuristic + Beam Search
2. **Introduction**: Vấn đề đề xuất môn học, lý do làm khó
3. **Related Work**: So sánh với phương pháp khác
   - Brute force (exponential)
   - Greedy algorithm (fast but suboptimal)
   - Beam Search (polynomial near-optimal)
4. **Proposed Approach**:
   - Ontology modeling
   - Heuristic scoring formula
   - Beam Search algorithm
5. **Evaluation**:
   - Dataset: DanhSachSinhVien.json (26 students)
   - Metrics: Execution time, quota fill rate, solution quality
   - Comparison: beam_width=4,8,16,32
6. **Results & Discussion**
7. **Conclusion & Future Work**

---

## CHECKLIST TRIỂN KHAI

- [ ] Tạo folder `flask_app/` + subfolder models, services, routes, templates, static
- [ ] Refactor `recommend_courses.py` → `RecommendationEngine` class
- [ ] Implement `StudentDataService` (load JSON/CSV)
- [ ] Implement Flask routes (`/api/students`, `/api/recommendations`)
- [ ] Viết HTML templates (form, result page, explanation)
- [ ] Viết CSS (styling, responsive design)
- [ ] Test API endpoints (Postman/curl)
- [ ] Unit tests (pytest)
- [ ] Caching strategy (Ontology load once)
- [ ] Error handling & validation
- [ ] Documentation (README)
- [ ] Deploy (gunicorn + nginx hoặc Heroku)

