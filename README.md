# Đề tài gợi ý kế hoạch học tập dựa trên Ontology

## 1) Mục tiêu đề tài

Xây dựng hệ thống hỗ trợ sinh viên đăng ký môn học theo học kỳ bằng cách kết hợp:

- Dữ liệu hồ sơ học tập sinh viên
- Ontology chương trình đào tạo
- Tập luật học vụ
- Heuristic scoring và Beam Search để tối ưu tổ hợp môn

Hệ thống trả về:

- Tập môn hợp lệ có thể đăng ký
- Tổ hợp môn đề xuất cuối cùng
- Giải thích lý do chọn môn để người đọc hiểu rõ quyết định của thuật toán

---

## 2) Cấu trúc thư mục tổng thể (root)

```text
Code/
├─ owl/
│  ├─ ontology_v18.rdf
│  ├─ ontology_v18.properties
│  ├─ TrainingProgramOntology_v18.owl
│  ├─ ... (các version ontology cũ hơn)
│
├─ StudentDataStandardization/
│  ├─ recommend_courses.py
│  ├─ TestSPARQL.py
│  ├─ DanhSachSinhVien.json
│  ├─ DanhSachSinhVien.csv
│  ├─ BANG_MO_TA_QUY_TAC_CHON_MON.md
│  ├─ Output_TestSPARQL.txt
│  ├─ recommend_courses_report_*.txt
│  └─ ...
│
└─ README.md  (tài liệu này)
```

Các thành phần quan trọng:

- Ontology chính đang dùng: [owl/ontology_v18.rdf](owl/ontology_v18.rdf)
- Script gợi ý môn học: [StudentDataStandardization/recommend_courses.py](StudentDataStandardization/recommend_courses.py)
- Script kiểm tra SPARQL: [StudentDataStandardization/TestSPARQL.py](StudentDataStandardization/TestSPARQL.py)
- Dữ liệu sinh viên JSON: [StudentDataStandardization/DanhSachSinhVien.json](StudentDataStandardization/DanhSachSinhVien.json)
- Dữ liệu sinh viên CSV (fallback): [StudentDataStandardization/DanhSachSinhVien.csv](StudentDataStandardization/DanhSachSinhVien.csv)
- Mô tả quy tắc chi tiết hiện hành: [StudentDataStandardization/BANG_MO_TA_QUY_TAC_CHON_MON.md](StudentDataStandardization/BANG_MO_TA_QUY_TAC_CHON_MON.md)

---

## 3) Vai trò của Ontology trong hệ thống

Ontology là nguồn tri thức học vụ chuẩn để thuật toán suy luận điều kiện đăng ký môn.

### 3.1 Dữ liệu ontology cung cấp

Từ ontology, hệ thống trích xuất cho mỗi môn:

- Mã môn học, tên môn học
- Quan hệ tiên quyết
- Quan hệ song hành
- Học kỳ mở môn (lẻ, chẵn, cả hai)
- Học kỳ khuyến nghị
- Thuộc tính bắt buộc/tự chọn theo ngành hoặc chuyên ngành
- Loại môn (đại cương, thể chất, cơ sở ngành)
- Số tín chỉ

### 3.2 Ý nghĩa

Nhờ ontology, hệ thống không chỉ lọc theo dữ liệu điểm mà còn kiểm tra logic chương trình đào tạo theo ngữ nghĩa học vụ.

---

## 4) Luồng xử lý tổng thể (end-to-end)

### Bước 1: Nhận đầu vào

Script [StudentDataStandardization/recommend_courses.py](StudentDataStandardization/recommend_courses.py) nhận:

- Mã sinh viên cần tư vấn
- File JSON hồ sơ sinh viên
- File RDF ontology
- File CSV dự phòng
- Thư mục xuất báo cáo

Nếu không tìm thấy sinh viên trong JSON, hệ thống fallback sang CSV.

### Bước 2: Nạp ontology và dựng dữ liệu môn học

Từ [owl/ontology_v18.rdf](owl/ontology_v18.rdf), hệ thống dựng course_data gồm:

- Prerequisite, corequisite
- Kỳ mở, kỳ khuyến nghị
- Gắn chuyên ngành/nhóm môn
- Tín chỉ và phân loại bắt buộc/tự chọn

### Bước 3: Chuẩn hóa hồ sơ sinh viên

Từ hồ sơ sinh viên, hệ thống tạo:

- passed_courses: môn đã đạt
- failed_courses: môn chưa đạt

Điểm quan trọng:

- Hợp nhất nguồn môn đã học từ điểm từng môn + danh sách môn đã học
- Loại bỏ giao nhau với danh sách môn chưa đạt
- Chuẩn hóa mã môn để tăng tính nhất quán
- Cảnh báo các mã môn không tồn tại trong ontology

### Bước 4: Lọc tập môn hợp lệ

Mỗi môn chỉ được giữ lại nếu thỏa đồng thời:

- Chưa đạt
- Đủ điều kiện tiên quyết
- Mở đúng loại học kỳ
- Phù hợp kỳ khuyến nghị theo mục tiêu học tập
- Phù hợp chuyên ngành đã chọn
- Thỏa ràng buộc cứng (ví dụ môn thực tập ngành, môn khuyến nghị kỳ 8)

### Bước 5: Chấm điểm ưu tiên

Hệ thống chấm mỗi môn theo:

- Debt score: ưu tiên môn học lại
- Link score: ưu tiên môn có nhiều môn phụ thuộc
- Delay score: ưu tiên môn bị trễ so với kế hoạch
- Open semester score
- Recommended semester proximity score
- Goal score theo mục tiêu học tập

Sau đó tính điểm tổng ưu tiên để xếp hạng.

### Bước 6: Quota tự chọn

Phân nhóm tự chọn:

- Đại cương
- Thể chất
- Cơ sở ngành
- Chuyên ngành

Tính số đã hoàn thành và quota còn thiếu để chỉ giữ môn tự chọn còn cần thiết.

### Bước 7: Beam Search tối ưu tổ hợp môn

Sử dụng Beam Search để chọn tổ hợp cuối cùng với ràng buộc:

- Không vượt giới hạn tín chỉ
- Tôn trọng quota tự chọn
- Tôn trọng bundle môn song hành
- Ưu tiên state có độ đáp ứng quota + điểm tổng + tín chỉ tốt hơn

### Bước 8: Xuất kết quả

Hệ thống xuất:

- Kết quả tóm tắt ra terminal
- Báo cáo chi tiết ra file txt trong thư mục dữ liệu

Các file báo cáo mẫu: [StudentDataStandardization](StudentDataStandardization)

---

## 5) Mô tả các module chính

### 5.1 Module gợi ý môn

- File: [StudentDataStandardization/recommend_courses.py](StudentDataStandardization/recommend_courses.py)
- Nhiệm vụ:
  - Nạp dữ liệu sinh viên + ontology
  - Lọc môn hợp lệ
  - Chấm điểm heuristic
  - Chạy beam search
  - Xuất báo cáo

### 5.2 Module kiểm thử SPARQL

- File: [StudentDataStandardization/TestSPARQL.py](StudentDataStandardization/TestSPARQL.py)
- Nhiệm vụ:
  - Chạy các truy vấn SPARQL kiểm tra dữ liệu ontology
  - Kiểm tra môn theo học kỳ, tiên quyết, song hành, nhóm chuyên ngành
  - Hỗ trợ xác minh ontology đúng logic trước khi recommendation

### 5.3 Tài liệu quy tắc nghiệp vụ

- File: [StudentDataStandardization/BANG_MO_TA_QUY_TAC_CHON_MON.md](StudentDataStandardization/BANG_MO_TA_QUY_TAC_CHON_MON.md)
- Nhiệm vụ:
  - Mô tả đầy đủ quy tắc lọc, scoring, quota, beam search
  - Là tài liệu đối chiếu với code

---

## 6) Quy ước dữ liệu đầu vào

### 6.1 Hồ sơ sinh viên

Nguồn chính: [StudentDataStandardization/DanhSachSinhVien.json](StudentDataStandardization/DanhSachSinhVien.json)

Các trường thường dùng:

- mã sinh viên
- tên sinh viên
- học kỳ hiện tại
- chuyên ngành chọn
- mục tiêu học tập
- điểm từng môn
- danh sách môn đã học
- danh sách môn chưa đạt
- số tín chỉ đăng ký tối đa

### 6.2 Chuẩn hóa đầu vào

Hệ thống có xử lý chuẩn hóa để chống sai khác dữ liệu:

- Mã sinh viên: so khớp linh hoạt
- Mã môn: chuẩn hóa kiểu chữ
- Mục tiêu học tập: map về nhóm chuẩn
- Số học kỳ và tín chỉ: ép kiểu an toàn

---

## 7) Cách chạy hệ thống

Chạy từ root workspace:

```bash
python StudentDataStandardization/recommend_courses.py --student-id SV0016
```

Có thể truyền đầy đủ tham số:

```bash
python StudentDataStandardization/recommend_courses.py \
  --student-id SV0016 \
  --json StudentDataStandardization/DanhSachSinhVien.json \
  --csv StudentDataStandardization/DanhSachSinhVien.csv \
  --rdf owl/ontology_v18.rdf \
  --output-dir StudentDataStandardization
```

Chạy kiểm tra SPARQL:

```bash
python StudentDataStandardization/TestSPARQL.py --ontology owl/ontology_v18.rdf
```

---

## 8) Đầu ra và cách đọc kết quả

### 8.1 Terminal

Hiển thị:

- Thông tin sinh viên
- Số môn hợp lệ
- Danh sách môn đề xuất cuối cùng
- Lý do chọn từng môn

### 8.2 Báo cáo txt

Mỗi lần chạy sinh một file report có timestamp tại thư mục [StudentDataStandardization](StudentDataStandardization), gồm:

- Tập môn hợp lệ đầu vào
- Tổ hợp môn cuối cùng
- Mô tả logic beam search đã áp dụng

---

## 9) Nguyên tắc thiết kế hiện tại

- Chặt chẽ nghiệp vụ: ưu tiên ràng buộc học vụ trước tối ưu điểm
- Giải thích được: mọi môn có lý do đi kèm
- Dễ tái lập: random có kiểm soát để tránh dao động vô nghĩa
- Tách nguồn tri thức: ontology tách khỏi code thuật toán


## 10) Định hướng mở rộng

- Đưa quota/ràng buộc thành file cấu hình riêng để thay đổi không cần sửa code
- Bổ sung test tự động cho các case biên (học lại, chuyên ngành, corequisite, quota)
- Xây API hoặc giao diện web để nhập mã sinh viên và xem gợi ý trực quan
- Thêm giải thích sâu ở mức rule-by-rule cho từng môn bị loại

---

## 11) Tài liệu liên quan trong repo

- [README.md](README.md)
- [owl](owl)
- [StudentDataStandardization/recommend_courses.py](StudentDataStandardization/recommend_courses.py)
- [StudentDataStandardization/TestSPARQL.py](StudentDataStandardization/TestSPARQL.py)
- [StudentDataStandardization/BANG_MO_TA_QUY_TAC_CHON_MON.md](StudentDataStandardization/BANG_MO_TA_QUY_TAC_CHON_MON.md)
- [StudentDataStandardization/Output_TestSPARQL.txt](StudentDataStandardization/Output_TestSPARQL.txt)
