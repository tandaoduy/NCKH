# Flask App - Quick Start Guide

## Cài Đặt & Chạy

### 1. Cài Đặt Dependencies
```bash
pip install -r requirements.txt
```

### 2. Chạy Flask App
```bash
python flask_app/app.py
```

Ứng dụng sẽ chạy trên: `http://localhost:5000`

### 3. Test API

#### A. Lấy danh sách sinh viên
```bash
curl http://localhost:5000/api/students
```

#### B. Lấy thông tin một sinh viên
```bash
curl http://localhost:5000/api/students/SV0016
```

#### C. Tạo gợi ý kế hoạch học tập
```bash
curl -X POST http://localhost:5000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"student_id": "SV0016"}'
```

---

## Cấu Trúc Project

```
flask_app/
├── app.py                           # Điểm vào chính
├── config.py                        # Cấu hình ứng dụng
│
├── models/                          # Data models
│   ├── student.py
│   └── recommendation.py
│
├── services/                        # Business logic
│   ├── student_data_service.py      # Đọc/quản lý dữ liệu SV
│   ├── recommendation_engine.py     # Engine gợi ý (refactor)
│   └── explanation_generator.py     # Tạo giải thích
│
├── routes/                          # API endpoints
│   ├── student_routes.py            # /api/students
│   └── recommendation_routes.py     # /api/recommendations
│
├── templates/                       # HTML (Jinja2)
│   ├── base.html
│   └── index.html
│
└── static/                          # CSS/JS
    ├── style.css
    └── main.js
```

---

## API Endpoints

### GET /api/students
Lấy danh sách tất cả sinh viên từ DanhSachSinhVien.json

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "student_id": "SV0016",
      "name": "Nguyễn Văn A",
      "major": "Công Nghệ Thông Tin",
      "current_semester": 3
    }
  ],
  "total": 26
}
```

---

### GET /api/students/<student_id>
Lấy thông tin chi tiết một sinh viên

**Response:**
```json
{
  "success": true,
  "data": {
    "student_id": "SV0016",
    "name": "Nguyễn Văn A",
    "year_admitted": 2023,
    "major": "Công Nghệ Thông Tin",
    "specialization": "Chưa chọn chuyên ngành",
    "study_goal": "đúng hạn",
    "current_semester": 3,
    "total_credits_accumulated": 21,
    "passed_courses": ["INS326", "SOT320"],
    "failed_courses": ["INS330", "MAT327"]
  }
}
```

---

### POST /api/recommendations
Tạo gợi ý kế hoạch học tập

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
  "data": {
    "student_id": "SV0016",
    "student_name": "Nguyễn Văn A",
    "current_semester": 3,
    "next_semester": 4,
    "study_goal": "đúng hạn",
    "eligible_courses": [
      {
        "code": "INS330",
        "name": "Cơ sở dữ liệu",
        "credits": 3,
        "is_retake": true,
        "heuristic_score": 1090,
        "total_priority_score": 1260,
        "reasons": ["môn học lại", "mở đúng học kỳ hiện tại"]
      }
    ],
    "recommended_courses": [
      {
        "code": "INS330",
        "name": "Cơ sở dữ liệu",
        "credits": 3,
        "is_retake": true,
        "reasons": ["môn học lại", "mở đúng học kỳ hiện tại"]
      }
    ],
    "total_eligible_count": 5,
    "total_recommended_count": 4,
    "total_recommended_credits": 12,
    "elective_quota_remaining": {
      "general": 1,
      "physical": 2,
      "foundation": 1,
      "specialization": 3
    }
  }
}
```

---

## Tính Năng Chính

### 1. Nạp Dữ liệu Sinh Viên
- Tự động đọc từ `DanhSachSinhVien.json`
- Fallback sang CSV nếu cần
- Cache dữ liệu để tăng tốc độ

### 2. Nạp Ontology RDF
- Parse file `ontology_v18.rdf`
- Trích xuất: mã môn, tiên quyết, song hành, kỳ mở, tín chỉ
- Xây dựng dependency graph

### 3. Lọc Môn Hợp Lệ (8 Điều Kiện)
```
✓ Chưa đạt (hoặc học lại)
✓ Tiên quyết đã đạt
✓ Kỳ mở phù hợp
✓ Kỳ khuyến nghị phù hợp goal
✓ Chuyên ngành khớp
✓ Tín chỉ môn ≤ 27
✓ Không vi phạm ràng buộc kỳ 8 (kỳ tối giản)
✓ Không vi phạm ràng buộc kỳ 7 (thực tập)
```

### 4. Chấm Điểm Heuristic
```
H = debt × 1000 + doPhu × 20 + doTre × 50

H_total = H + openNow × 50 
        + recProximity × 10 
        + goalScore (30/20/10)
```

### 5. Beam Search Tối Ưu
- Giữ 8 state (tơ hợp môn) tốt nhất
- Ưu tiên: quota → score → credit
- Tìm tơ hợp gần tối ưu trong thời gian polynomial

---

## Debugging

### Issue 1: "Module not found: flask_app.services.recommendation_engine"
**Giải pháp**: Đảm bảo file đã được tạo:
```bash
ls flask_app/services/recommendation_engine.py
```

### Issue 2: "Ontology file not found"
**Giải pháp**: Kiểm tra đường dẫn trong `flask_app/config.py`:
```python
ONTOLOGY_PATH = os.path.join(PARENT_DIR, 'owl', 'ontology_v18.rdf')
```

### Issue 3: Lỗi UTF-8 trên Windows
**Giải pháp**: Chạy Python với UTF-8:
```bash
set PYTHONIOENCODING=utf-8
python flask_app/app.py
```

---

## Phát Triển Tiếp Theo

### Phase 1: Backend Core (Hoàn thành)
- ✅ Refactor RecommendationEngine
- ✅ Xây dựng data models
- ✅ Viết API routes
- ⏳ Unit tests

### Phase 2: Frontend UI
- ⏳ Viết HTML templates chi tiết
- ⏳ Styling CSS responsive
- ⏳ JavaScript interactivity

### Phase 3: Optimization
- ⏳ Caching strategy
- ⏳ Performance profiling
- ⏳ Error handling nâng cao

### Phase 4: Deployment
- ⏳ Config production
- ⏳ Docker container
- ⏳ Deploy lên server

---

## Tài Liệu Tham Khảo

- [FLASK_APP_ARCHITECTURE.md](../FLASK_APP_ARCHITECTURE.md) - Kiến trúc chi tiết
- [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) - Hướng dẫn triển khai
- [BANG_MO_TA_QUY_TAC_CHON_MON.md](../StudentDataStandardization/BANG_MO_TA_QUY_TAC_CHON_MON.md) - Quy tắc kinh doanh

---

## Support

Nếu gặp vấn đề, hãy kiểm tra:
1. Python version >= 3.8
2. Tất cả dependencies được cài đặt
3. Các tệp dữ liệu tồn tại (JSON, RDF)
4. Đường dẫn được cấu hình đúng

