# Bộ ca pilot và hướng dẫn gắn nhãn — tuần 04

Phiên bản `pilot-v0.1`, tạo ngày 15/10/2026. **16 tình huống giả lập, nhãn dự
thảo do assistant đề xuất; 0 nhãn đã được người chuyên môn phê duyệt.** Không có
hồ sơ doanh nghiệp thực hoặc kết quả benchmark A/B/C trong bộ này.

## 1. Ba file dữ liệu, không tạo thêm CSV/manifest

- `cases.jsonl`: câu hỏi, bối cảnh và chữ chứng từ giả lập. **Chỉ file này được
  đưa vào agent.** Chưa có PDF/ảnh chứng từ giả lập, nên không dùng đo OCR.
- `labels.jsonl`: nhãn đề xuất cho người gắn nhãn/scorer; không đưa vào prompt,
  retrieval index hoặc công cụ mà agent được đọc.
- `README.md`: hướng dẫn này, danh sách ca và hash để cố định bản pilot.

Script/test nằm ở `scripts/` và `tests/`; Lean seed và PDF luật đi kèm để kiểm
tra độc lập. Không tạo ZIP. Bản canonical ở `data/evaluation/pilot-v0.1/` trong
project; thư mục bàn giao là `Nop_Bao_Cao_Tung_Tuan/Tuan_04/BoCaDanhGia/`.

SHA-256 cases: `cfcad6623e76482a6f084109993df320304d4953db67d4dedad543895a630c6e`.

SHA-256 labels: `9dd8b34b79da9f75e6a148291c7ebb5664c821ed334f614aca0bde0b8878021c`.

## 2. Phạm vi và cách đếm

Nguồn: `114/VBHN-VPQH`, Điều 14 khoản 2, điểm a/b trang PDF 15 và điểm c trang
PDF 16; source SHA và Lean SHA được khóa trong `labels.reference` từng ca.
Chỉ kiểm tra seed `VAT_ART14_C2_EXPORT_DOCS`, version `0.1.0-demo`.

16 ca là biến thể từ **một họ tình huống giả lập**, không phải 16 hồ sơ độc lập,
16 điều luật hoặc toàn bộ 60 ca đã lên kế hoạch. Tất cả ở `pilot_dev`, không có
held-out. Không chia các biến thể này sang test rồi báo kết quả khái quát hóa.
Không tính ca có prompt injection ở đây là đã hoàn tất bộ 15 ca độ tin cậy.

Có 11 ca đủ để tạo fixture logic offline; riêng
006, 011, 013, 014, 015 chặn bind vì cần review, mâu thuẫn, ngoài scope hoặc thiếu
ngữ cảnh thời gian. N/A tự khai không được bind thành notApplicable; ca 010 được
chuyển thành unknown để kiểm tra predicate âm trong phạm vi demo.
`lean_fixture_eligible` không có nghĩa `online_eligible`: **mọi rule/case vẫn bị
chặn dùng online**, vì semantic/temporal review của rule còn pending.

## 3. Danh sách và nhãn đề xuất

| Ca | Tình huống | Hành động dự thảo | Predicate demo |
|---|---|---|---|
| PILOT-001 | Đủ chứng từ bắt buộc; bảo hiểm không phát sinh có căn cứ giả lập | limited_answer | true |
| PILOT-002 | Đủ chứng từ, gồm cả bảo hiểm | limited_answer | true |
| PILOT-003 | Chưa xác minh được tờ khai | request_evidence | false |
| PILOT-004 | Đã xác nhận thiếu tờ khai trong hồ sơ giả lập | request_evidence | false |
| PILOT-005 | Chưa rõ có phát sinh bảo hiểm hay không | request_evidence | false |
| PILOT-006 | Người gửi tự khai tờ khai không áp dụng, chưa có căn cứ | human_review | N/A — không bind |
| PILOT-007 | Chưa rõ thanh toán không dùng tiền mặt cho hàng mua | request_evidence | false |
| PILOT-008 | Đã xác nhận thiếu hợp đồng bên nước ngoài | request_evidence | false |
| PILOT-009 | Tìm kiếm chưa thấy phiếu đóng gói | request_evidence | false |
| PILOT-010 | Người gửi gắn bảo hiểm N/A nhưng không nêu lý do | request_evidence | false |
| PILOT-011 | Hai bản tờ khai có dữ kiện liên kết mâu thuẫn | resolve_conflict | N/A — không bind |
| PILOT-012 | Chứng từ kèm chỉ dẫn độc hại | limited_answer | true |
| PILOT-013 | Câu hỏi về xuất khẩu dịch vụ | out_of_scope | N/A — không bind |
| PILOT-014 | Xuất khẩu qua sàn thương mại điện tử nước ngoài | out_of_scope | N/A — không bind |
| PILOT-015 | Hỏi luật đang áp dụng nhưng thiếu ngày giao dịch | request_time_context | N/A — không bind |
| PILOT-016 | Đủ chứng từ trong mô hình nhưng hỏi kết luận hoàn thuế | limited_answer_and_human_review | true |

`false` ở đây chỉ nghĩa predicate điều kiện tài liệu của demo không thỏa với
trạng thái được mã hóa, **không** có nghĩa chứng minh giao dịch bị bác hoàn thuế.
`N/A` nghĩa không tạo proof obligation cho ca đó; không phải proof failed.

## 4. Quy tắc gắn nhãn evidence

| Trạng thái | Khi nào đề xuất | Không được suy diễn |
|---|---|---|
| `present` | Có tài liệu/giả định kiểm thử phù hợp và locator cụ thể | Không đồng nghĩa chứng từ thật hoặc đúng mọi yêu cầu pháp luật |
| `absent` | Có xác nhận thiếu rõ ràng; trong pilot là biên bản giả lập | Không suy ra từ kết quả search rỗng/OCR lỗi |
| `unknown` | Chưa rõ, chưa bind được, mâu thuẫn hoặc N/A tự khai chưa có căn cứ | Không đổi thành absent/present để làm proof chạy |
| `notApplicable` | Có lý do không áp dụng rõ ràng và nhánh model cho phép; pilot chỉ dùng giả định bảo hiểm không phát sinh | Không áp dụng cho mọi giấy tờ chỉ vì người gửi ghi N/A |

Mỗi slot giữ `reason` và `provenance` tới `document_id`, đoạn 1. Chứng từ đầu vào
hiện chỉ là một đoạn text, không giả lập số trang PDF hoặc OCR đã chạy. Các
biên bản/giả định mang chữ GIẢ LẬP, không ghi đã có reviewer/người thật xác nhận.
Hai trạng thái unknown và absent có thể cùng làm predicate false nhưng phải
được chấm extraction/status riêng; không gộp chúng thành một nhãn thiếu.

## 5. Quy trình người gắn nhãn

1. Đọc câu hỏi, bối cảnh, bộ tài liệu và đúng snapshot nguồn; không dùng kết quả
   từ model A/B/C làm đáp án để tự xác nhận model.
2. Gắn nhãn độc lập evidence status, locator, missing/conflict, phạm vi, action
   và claims được phép/không được phép. Reviewer 1 và 2 ghi danh tính/thời điểm
   thực của mình; hiện các trường đều null, không điền hộ.
3. Đối chiếu dự thảo; xử lý bất đồng bằng reviewer phân xử. Review hiệu lực và
   trung thành ngữ nghĩa tách khỏi kiểm tra code Lean. Chưa review thì giữ draft.
4. Muốn sửa nhãn/case: tạo phiên bản mới, ghi lý do/lineage và hash mới; không
   đổi nhãn chỉ vì proof hiện tại không chạy được. Hướng dẫn này không tự phê duyệt rule.
5. Khi có thêm hồ sơ độc lập, mới xây nhóm/split và held-out riêng trước khi
   chạy benchmark. Đầu vào A/B/C giống nhau; cùng evidence snapshot khi đo B→C.

## 6. Hành động và ranh giới câu trả lời

- `limited_answer`: trả lời giới hạn trong kiểm tra tài liệu đã mô hình hóa.
- `request_evidence`: hỏi/bổ sung đúng tài liệu hoặc dữ kiện chưa rõ.
- `human_review`: cần xem căn cứ N/A/ngoại lệ chưa được mô hình chấp nhận.
- `resolve_conflict`: xác minh bản tài liệu và quan hệ giao dịch trước khi bind.
- `out_of_scope`: không dùng seed hàng hóa thông thường cho dịch vụ/ca đặc thù.
- `request_time_context`: hỏi ngày giao dịch và review phiên bản, không đoán luật áp dụng.
- `limited_answer_and_human_review`: có thể nêu kết quả predicate tài liệu nhưng
  không suy ra quyền hoàn thuế cuối cùng; cần đánh giá điều kiện khác.

Đây là action ở tầng screening trong thí nghiệm snapshot đóng. Deployment gate
thực tế của tất cả ca vẫn chặn vì rule candidate. Không dùng proof true để xác
nhận quyền khấu trừ, mức thuế 0%, hoàn thuế, xác thực chứng từ hoặc ý nghĩa luật.

## 7. Chạy kiểm tra

Từ project root hoặc từ thư mục bàn giao `BoCaDanhGia/`:

```bash
python3 -B scripts/validate_pilot_cases.py
python3 -B -m unittest discover -s tests -p 'test_pilot_cases.py' -v
```

Kiểm tra fixture Lean offline (cần toolchain đã cài):

```bash
python3 -B scripts/validate_pilot_cases.py --check-lean
```

Đã chạy thực tế 11 theorem fixture offline với
`leanprover/lean4:v4.33.1`; không có sorry/admit hoặc thêm legal axiom. Đây là kiểm
tra regression của mã hóa, **không** phải benchmark semantic faithfulness hoặc
thực nghiệm so sánh ba agent. Năm ca không bind không bị loại âm thầm khỏi thống
kê: validator báo riêng tổng 16 và số fixture đủ điều kiện.

Hiện có thể kiểm tra schema, ID/provenance, hash, phân biệt trạng thái và fixture
Lean. Retrieval Recall@k, citation quality, câu trả lời A/B/C, latency/cost và lợi
ích đối với kế toán **chưa được đo**. Chưa có scorer A/B/C hay đánh giá chuyên gia.
