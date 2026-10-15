# Packet mẫu — khoản 2 Điều 14

Rule ID: `VAT_ART14_C2_EXPORT_DOCS`. Phiên bản: `0.1.0-demo`.

Packet minh họa đường đi từ văn bản nguồn qua Legal IR và mapping tới Lean 4. Lean source dùng trực tiếp Lean 4; chưa import thư viện LegalLean. Các JSON là định dạng demo có kiểm tra nhất quán bằng script, chưa phải JSON Schema hay compiler Legal IR tổng quát.

## Nội dung

| File | Vai trò |
| --- | --- |
| `source.json` | Nguồn PDF, hash, nguyên văn các điểm a/b/c, vị trí trang và ngữ cảnh |
| `legal_ir.json` | Rule candidate, điều kiện, ngoại lệ ngoài scope và boundary |
| `mapping.json` | Chín field bindings và sáu synthetic regression cases |
| `manifest.json` | Rule/symbol/toolchain và hashes cố định của các artifact |
| `verification.json` | Bằng chứng kiểm tra kỹ thuật tại thời điểm chạy |
| `../../../Article14Clause2.lean` | Lean source được manifest khóa bằng hash |

Đường dẫn trong manifest tính từ thư mục gốc `project_da2`. Manifest tham chiếu file Lean hiện có để tránh tạo hai bản code dễ lệch nhau. Khi code hoặc nội dung packet thay đổi sau khi đóng gói, tạo packet version mới; không tái sử dụng kết quả kiểm tra cũ.

## Phạm vi và trạng thái

Predicate kiểm tra trạng thái chứng từ đã chuẩn hóa cho nhánh hàng xuất khẩu thông thường được mô hình hóa. Điểm a được gộp thành một evidence slot cho các lựa chọn hóa đơn/chứng từ; loại chứng từ cụ thể vẫn cần kiểm tra bên ngoài.

Các ngoại lệ do Chính phủ quy định tại điểm b, các trường hợp xuất khẩu đặc thù tại điểm c, dịch vụ xuất khẩu, khoản 1/khoản 3 Điều 14 và quy định chi tiết nằm ngoài mô hình này. Không dùng kết quả predicate làm kết luận toàn bộ quyền khấu trừ.

Mapping “nếu có” sang bảo hiểm `present OR notApplicable` là ứng viên cần semantic review. Lean chỉ thấy trạng thái, không kiểm tra lý do miễn áp dụng. Tính xác thực, tính hợp lệ của chứng từ, mâu thuẫn giữa tài liệu và hiệu lực áp dụng của rule chưa được chứng minh. Các ngày hiệu lực để trống và ghi `temporal_review: pending`.

Packet giữ `candidate`, `semantic_review: pending`, `approval: not_approved`, `online_eligible: false` dù mọi kiểm tra kỹ thuật thành công. Đây là packet runnable cho báo cáo, chưa phải approved registry entry hoặc một case doanh nghiệp thật.

## Chạy kiểm tra

Yêu cầu Python 3.9+, `pdftotext`, `elan` và toolchain `leanprover/lean4:v4.33.1` đã cài.

Chạy từ thư mục gốc dự án:

```bash
python3 scripts/verify_article14_packet.py
```

Script chỉ đọc file và in JSON ra stdout, không sửa packet hoặc tự phê duyệt. Kiểm tra hashes; nguyên văn theo trang PDF; identity và trạng thái demo; metadata IR–mapping; Lean structure; token scan; compile; type của sáu theorem và axiom dependencies. Token scan là kiểm tra bổ trợ của demo, không phải parser Lean hoàn chỉnh. `#print axioms` kiểm tra dependencies của các theorem; allowlist của packet chỉ gồm `propext`, không cho phép `sorryAx` hoặc axiom pháp lý.

Lệnh compile trực tiếp:

```bash
elan run leanprover/lean4:v4.33.1 lean formalization/Article14Clause2.lean
```

## Bộ test

| ID | Case | Predicate kỳ vọng |
| --- | --- | --- |
| T01 | Các chứng từ bắt buộc present; bảo hiểm notApplicable | True |
| T02 | Tờ khai unknown | False |
| T03 | Tờ khai absent | False |
| T04 | Bảo hiểm unknown | False |
| T05 | Tờ khai notApplicable | False |
| T06 | Bảo hiểm present; các trường khác đủ | True |

`False` là không đạt predicate trạng thái chứng từ trong mô hình. Đặc biệt, T02/T04 yêu cầu bổ sung dữ kiện ở tầng nghiệp vụ; không chứng minh giao dịch thực tế không đủ điều kiện pháp lý. T01/T06 cũng chưa xác minh toàn bộ quyền khấu trừ hay chứng từ thực tế.

Script còn chạy ba mutation smoke tests trong stdin: bỏ điều kiện tờ khai; cho unknown bảo hiểm đạt; cho unknown ở chứng từ bắt buộc đạt. Mỗi predicate biến đổi phải typecheck trước, sau đó regression suite phải phát hiện bằng goal chưa giải được. File nguồn không bị thay đổi. Đây là kiểm tra độ nhạy của mẫu, chưa phải benchmark formalization hoặc held-out evaluation.

## Cách đọc verification record

`technical_checks_passed` xác nhận các checks được liệt kê đã thành công cho hashes/toolchain ghi trong record. Record giữ thời gian, command/exit code, stdout/stderr, theorem dependencies, checker hash và manifest hash. Chạy lại tạo một JSON record mới trên stdout; kết quả cũ không bị ghi đè tự động.

Nguồn được đối chiếu ở PDF pages 15–16, tương ứng trang in Công báo 122–123. Các đoạn trích chỉ chuẩn hóa khoảng trắng do xuống dòng, không thêm ngữ cảnh vào nguyên văn citation.
