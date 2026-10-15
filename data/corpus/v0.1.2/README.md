# Kho tài liệu v0.1.2 — đầu ra 1, tuần 04

Bản đóng gói gọn ngày 15/10/2026, kế thừa snapshot v0.1. Không thay đổi nguồn
luật hoặc nâng trạng thái phê duyệt. Phiên bản chính xác và parent release ID
được lưu trong manifest.json.

## Chỉ ba file dữ liệu

- `manifest.json`: danh mục nguồn, hash/phiên bản, thống kê, metadata kế thừa,
  cảnh báo và trạng thái review. Không cần CSV hoặc JSON riêng cho từng bảng.
- `pages.jsonl`: toàn bộ chữ trích xuất. Mỗi dòng có `kind`, `source_id`,
  `source_version_id`, `source_sha256`, `text`, `text_sha256` cùng locator.
- `README.md`: hướng dẫn này.

PDF/DOCX gốc vẫn được lưu riêng theo `artifact_path` trong manifest, không bị
chỉnh sửa. Các đường dẫn tính từ thư mục bàn giao `KhoTaiLieu/`.

## Phạm vi và cách đọc

37 PDF pháp lý, 3,424 trang PDF;
2 tài liệu thiết kế nghiệp vụ nội bộ từ
tuần 02, không phải hướng dẫn thuế chính thức hoặc hồ sơ doanh nghiệp thực.
6 PDF nghiên cứu kỹ thuật được liệt kê riêng, không đưa vào căn cứ pháp lý.

Metadata pháp lý nằm trong `sources`; tài liệu nội bộ trong `business_sources`;
thống kê trong `summary`. Cảnh báo và việc cần duyệt nằm ngay trong từng source:
`quality_issues`, `review_note`, `review`. Kiểm kê cần cho tái lập đã nhúng trong
`inventory_snapshot`, không cần phát sinh thêm file audit trong gói nộp.

`kind=legal_pdf_page` có `pdf_page` bắt đầu từ 1. `text` giữ nguyên chữ do
pdftotext -layout trích xuất, bao gồm xuống dòng/khoảng trắng. Chưa phải bản chữ
được người duyệt; không bảo đảm công cụ trích xuất đúng mọi ký tự/bảng biểu.
`kind=internal_business_paragraph` có `paragraph` bắt đầu từ 1 và `urls` lấy từ
DOCX gốc. Chỉ dùng kind pháp lý khi xây legal index; không trộn tài liệu nội bộ
thành căn cứ luật chỉ vì nằm cùng một file vật lý.

Tên văn bản/URL kế thừa Phụ lục A tuần 01, có hash/locator tham chiếu nhưng chưa
được đối chiếu lại website. Metadata khai báo cũ giữ trong `reported_metadata_text`.
Ngày tải/hiệu lực chưa xác minh để null, không suy đoán từ tên tệp/ngày ban hành.
`source_id` là ID nội bộ, không thay số hiệu văn bản. Source version dùng SHA-256
đầy đủ; một PDF Công báo có thể chứa nhiều văn bản.

## Giới hạn giữ nguyên

- 03, 07, 13 cần OCR; 34 nguồn có chữ không
  đồng nghĩa đã được duyệt đầy đủ hoặc đúng hiệu lực.
- 20, 29, 30, 31, 33, 36, 37 có chỉ dẫn phần tiếp; tệp 33 thiếu phần phụ lục tiếp.
- 14, 19, 33 chứa nhiều văn bản, cần rà ranh giới; tệp 32 chỉ có TT 21/2026 sửa
  TT 80/2021 chứ chưa có toàn văn TT 80/2021.
- 24–27 là quản trị AI/dữ liệu, không phải căn cứ trả lời nghiệp vụ VAT.
- Tất cả nguồn còn pending semantic/temporal review, `online_eligible=false`.
  Không có cảnh báo ưu tiên không có nghĩa là nguồn đầy đủ hoặc còn hiệu lực.
- Chưa có hồ sơ doanh nghiệp thực; chưa xác định tổng quy tắc độc lập.

## Chạy và kiểm tra

Từ project root hoặc thư mục bàn giao `KhoTaiLieu/` (Python 3.10+):

```bash
python3 scripts/build_corpus_release.py --verify-only
python3 -m unittest discover -s tests -p 'test_corpus_release.py' -v
```

Tái trích xuất cần thêm Poppler/pdftotext; không cần mạng, API key hay PostgreSQL:

```bash
python3 scripts/build_corpus_release.py
```

Cùng dữ liệu chạy lại không đổi release. Kết quả khác bản đóng băng thì dừng,
không ghi đè; cần review và tạo version mới. Hash kiểm tra tính toàn vẹn, không
chứng minh tính xác thực pháp lý hoặc phê duyệt nội dung. Gói có thể tái lập mà
không phụ thuộc `.firecrawl` hoặc file kiểm kê bên ngoài thư mục bàn giao.

Bàn giao trực tiếp bằng các thư mục, không tạo file nén:

```bash
python3 scripts/build_corpus_release.py --verify-only --export-dir Nop_Bao_Cao_Tung_Tuan/Tuan_04/KhoTaiLieu
```

Thư mục bàn giao có `resources/` (PDF gốc), `data/` (ba file corpus),
`scripts/` và `tests/` (mã nguồn/kiểm thử). Các DOCX tham chiếu được giữ dưới
đường dẫn gốc `Nop_Bao_Cao_Tung_Tuan/` để hash và liên kết trong manifest vẫn đúng.

## Trạng thái tuần 04

Đã có đầu ra 1 ở mức snapshot v0.1 có giới hạn, được đóng gói gọn thành v0.1.2.
Đầu ra 2 mới có nạp/trích xuất/quản lý phiên bản mức file; chưa có chunking
Điều–Khoản–Điểm, chỉ mục từ khóa/ngữ nghĩa hoặc PostgreSQL/pgvector.
Đầu ra 3 (ca đánh giá và hướng dẫn gắn nhãn) chưa tạo. Chưa chạy benchmark A/B/C,
chưa tự cập nhật bảng tiến độ thành đã nộp hoặc phê duyệt Lean packet.
