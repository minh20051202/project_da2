# project_da2

Đồ án 2: truy xuất và giải thích quy định thuế GTGT trong hoạt động xuất khẩu,
hướng tới so sánh RAG, Agentic RAG và Agentic RAG + Lean 4 trên cùng bộ ca.

## Nội dung hiện có

- `resources/references/`: PDF nguồn dùng cho corpus và tài liệu tham khảo kỹ thuật.
- `docs/architecture/`: quyết định kiến trúc Legal IR, formalization và proof retrieval.
- `data/corpus/v0.1.2/`: snapshot corpus, provenance và cảnh báo chất lượng.
- `data/retrieval/v0.1/`: index offline BM25, E5 semantic và hybrid RRF.
- `data/evaluation/pilot-v0.1/`: 16 biến thể giả lập, input và nhãn draft tách riêng.
- `formalization/`: Lean seed và packet candidate, chưa được phê duyệt ngữ nghĩa/hiệu lực.
- `scripts/`, `tests/`: mã xử lý và kiểm tra.

Báo cáo, bộ nộp trong `Nop_Bao_Cao_Tung_Tuan/` và các Excel quản lý trong
`resources/docs/Quan_Ly_Do_An/` chỉ giữ local, không theo dõi trong phiên bản Git
hiện tại. Các snapshot dữ liệu/provenance phục vụ code vẫn được giữ nguyên.

File index là prototype offline tái tạo được. PostgreSQL/pgvector vẫn là thiết kế
deployment, chưa phải database đã triển khai. Chưa có benchmark so sánh ba hệ thống,
expert gold hay held-out; kiểm tra kỹ thuật không thay thế thẩm định pháp lý.

## Cài và chạy

Đã kiểm tra với Python 3.12. Tạo môi trường, kích hoạt rồi cài dependencies:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-week4.txt
python scripts/download_embedding_model.py
python -B -m unittest discover -s tests
python -B scripts/legal_retrieval.py verify
```

Model ONNX và tokenizer không lưu trong Git. Script tải model công khai
`intfloat/multilingual-e5-small` theo revision cố định
`614241f622f53c4eeff9890bdc4f31cfecc418b3`; manifest kiểm tra hash khi sử dụng.
Giữ nguyên model card đi kèm. Lần tải model/cài package cần mạng; truy xuất sau đó
chạy local, không cần API key.

Tìm kiếm thử trên snapshot offline:

```bash
python -B scripts/legal_retrieval.py search --offline-snapshot --source-id LEGAL-001 --mode hybrid --query "chứng từ xuất khẩu"
```

## Kiểm tra đầy đủ và tài liệu local

`build_corpus_release.py`, `verify_week4_submission.py` và script đóng bộ nộp
cần thêm 3 DOCX nguồn local theo đúng đường dẫn và hash trong manifest corpus:

- `Nop_Bao_Cao_Tung_Tuan/Tuan_01/DA2_NguyenTuanMinh_Tuan1_TaiLieuThamKhao.docx`.
- `Nop_Bao_Cao_Tung_Tuan/Tuan_02/DA2_NguyenTuanMinh_Tuan2_BaoCaoTongQuanLyThuyet_YeuCauNghiepVu.docx`.
- `Nop_Bao_Cao_Tung_Tuan/Tuan_02/DA2_NguyenTuanMinh_Tuan2_DacTaPhamVi_DoiChung_DanhGia.docx`.

Clone mới không có các DOCX này. Muốn build/verify corpus đầy đủ, khôi phục chúng
từ bộ local; không sửa manifest hay bỏ qua kiểm tra hash để ép pass.

Khi đủ nguồn local, chạy `python -B scripts/verify_week4_submission.py`.
Nếu đã cài Lean 4.33.1 qua elan và Poppler/pdftotext, kiểm tra thêm Lean:

```bash
python -B scripts/verify_week4_submission.py --with-lean
```

Kết quả kiểm tra tuần 4 lưu local tại `Nop_Bao_Cao_Tung_Tuan/Tuan 4/KiemTra/ket_qua.json`:
53 unit tests, 9 smoke searches và 11 Lean fixture đã qua. Đây không phải kết quả
benchmark held-out hoặc semantic approval. Chế độ online vẫn bị chặn đối với nguồn
chưa đủ điều kiện; truy xuất thử cần cờ `--offline-snapshot` rõ ràng.

Cache, virtualenv và backup trong `.firecrawl/` không được đưa vào Git. Các tài
liệu nguồn và báo cáo local được giữ nguyên; repository chưa cấp license chung cho chúng.
