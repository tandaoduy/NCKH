# Student Input Standard

Bo du lieu dau vao nay duoc thiet ke de phu hop voi hai ontology:

- `owl/owl_v8.rdf`
- `owl/TrainingProgramOntology_v8.owl`

## Cac truong toi thieu

- `mssv`: anh xa voi `StudentID`
- `nam_vao_hoc`: anh xa voi `enrollmentYear`
- `chuyen_nganh_chon`: anh xa voi `hasChosenSpecialization`
- `danh_sach_mon_da_hoc`: danh sach ma mon sinh vien da hoc
- `diem_tung_mon`: map `ma_mon -> diem`
- `trang_thai_dat_chua_dat`: map `ma_mon -> dat/chua_dat`
- `so_tin_chi_da_tich_luy`: tong tin chi cac mon dat
- `hoc_ky_hien_tai`: anh xa voi `currentSemester`
- `muc_tieu_hoc_tap`: `dung_han`, `hoc_vuot`, `giam_tai`

## Gia tri chuan hoa de dung

- Chuyen nganh:
  - `CNPM`: Cong nghe phan mem
  - `HTTT`: He thong thong tin
  - `TTMMT`: Truyen thong va Mang may tinh
- Trang thai mon hoc:
  - `dat`
  - `chua_dat`
- Muc tieu hoc tap:
  - `dung_han`
  - `hoc_vuot`
  - `giam_tai`

## Dinh dang file

- `data.csv`: mau du lieu dang bang, phu hop khi nhap lieu hoac xu ly bang pandas/Excel
- `student_input_standard.json`: mau du lieu co schema va ban ghi minh hoa, phu hop khi map sang ontology

## Luu y chuan hoa

- `hoc_ky_hien_tai` nen dung so nguyen tu `1` den `8`.
- Ma mon trong `diem_tung_mon` va `trang_thai_dat_chua_dat` phai xuat hien trong `danh_sach_mon_da_hoc`.
- Neu mon co trang thai `dat` thi co the map sang `hasCompletedCourse`.
- Neu mon co trang thai `chua_dat` thi co the map sang `hasFailedCourse`.
