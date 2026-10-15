# ADR-001: Legal IR cho formalization và truy xuất chứng minh Lean

- **Trạng thái:** Chấp nhận
- **Ngày quyết định:** 07/10/2026
- **Phạm vi:** Pipeline formalize pháp luật thuế GTGT Việt Nam và pipeline chứng minh Lean 4

## 1. Bối cảnh

Dự án cần chuyển các điều, khoản pháp luật từ ngôn ngữ tự nhiên sang biểu diễn Lean 4 để kiểm tra các mệnh đề liên quan đến hồ sơ thuế GTGT đối với hoạt động xuất khẩu.

Các vấn đề chính:

- Sinh Lean trực tiếp từ văn bản luật dễ bỏ sót điều kiện, ngoại lệ, thời gian hiệu lực và dẫn chiếu.
- Lean chỉ kiểm tra tính suy diễn của mệnh đề đã mã hóa; Lean không xác nhận rằng bản mã hóa trung thành với văn bản pháp luật.
- Agent cần tìm đúng quy tắc, phiên bản, Lean module, predicate và premise khi chứng minh một mục tiêu.
- Quy tắc do Agent sinh không được tự động đưa vào pipeline xử lý hồ sơ thực tế.
- Hệ thống phải phân biệt chứng cứ `present`, `absent`, `unknown` và `notApplicable`.

## 2. Quyết định tổng thể

Chọn **Pipeline B: văn bản pháp luật → Legal IR → Lean 4** làm pipeline chính.

Pipeline template theo nhóm quy tắc được dùng như đường ưu tiên cho các cấu trúc quen thuộc. Sinh Lean trực tiếp từ văn bản chỉ được giữ làm baseline hoặc fallback tạo ứng viên.

### 2.1. Hình thức triển khai MVP

MVP sử dụng **modular monolith**: một ứng dụng triển khai nhưng được chia thành các mô-đun logic có hợp đồng dữ liệu rõ ràng. Các thành phần như quản lý nguồn/phiên bản, xử lý tài liệu, retrieval, formalization workbench, rule registry, case ingestion, evidence store, agent orchestrator, proof-obligation builder, Lean runtime, explanation, output gate và audit không bắt buộc trở thành các microservice riêng.

Không đưa Kafka, Kubernetes hoặc graph database thành yêu cầu kiến trúc. Chuỗi claim–evidence–document–source được lưu bằng các thực thể và bảng liên kết trong mô hình quan hệ; chỉ xem xét graph database nếu truy vấn đồ thị thực tế chứng minh nhu cầu. Rule registry và case evidence store phải tách biệt; chúng chỉ được liên kết khi tạo proof obligation.

### 2.2. Kiến trúc lưu trữ MVP

MVP sử dụng PostgreSQL cho metadata, quan hệ nghiệp vụ, workflow state và audit metadata; sử dụng `pgvector` trong cùng PostgreSQL cho embedding của legal/evidence chunks; sử dụng filesystem hoặc object storage cho PDF, ảnh, OCR output, Lean source, proof artifact và raw model output.

Artifact gốc là bất biến và được định danh bằng ID cùng SHA-256; thay đổi nội dung tạo artifact/version mới thay vì ghi đè. Database chỉ lưu URI, hash, provenance và identity của file. Không yêu cầu vector database hoặc graph database riêng trong MVP; các implementation này chỉ được cân nhắc sau nếu đo lường thực tế chứng minh PostgreSQL/pgvector không đáp ứng.

MVP dùng một PostgreSQL database `project_da2`. Schema `core` chứa các bảng nghiệp vụ và schema `retrieval` chứa chunk cùng embedding; `pgvector` là extension của cùng database, không phải database thứ hai. Việc tách schema chỉ nhằm tổ chức namespace và quyền truy cập; các bảng vẫn dùng được foreign key, join và transaction chung. Vector store chỉ là chỉ mục tái tạo được, không phải nguồn dữ liệu pháp luật gốc.

### 2.3. Chunking và retrieval index

Văn bản pháp luật được chia theo cấu trúc Điều–Khoản–Điểm thay vì cắt cố định theo số token. Điểm tự đủ nghĩa là đơn vị ưu tiên; khoản không có điểm có thể là một chunk; chỉ chia nhỏ thêm khi nội dung quá dài và mọi phần con vẫn giữ metadata cha. Không trộn hai phiên bản luật trong cùng chunk.

Mỗi chunk giữ `text` nguyên văn để trích dẫn và `embedding_text` có bổ sung tiêu đề/ngữ cảnh để tạo embedding. Citation luôn lấy từ `text`, không lấy từ nội dung đã bổ sung. Retrieval lọc source version theo thời điểm nghiệp vụ trước, sau đó kết hợp keyword/full-text và vector search, mở rộng dẫn chiếu khi cần, rerank và chọn top-k; top-k là tham số đánh giá, không khóa cứng trong kiến trúc.

MVP chỉ vector hóa kho luật trong `retrieval.legal_chunk`. Hồ sơ doanh nghiệp được ưu tiên chuyển thành evidence có cấu trúc và lọc theo case/document/business keys; không trộn dữ liệu hồ sơ nhạy cảm với legal vector index. Chỉ bổ sung `case_chunk` nếu đánh giá thực tế chứng minh nhu cầu tìm kiếm ngữ nghĩa trong tài liệu hồ sơ dài.

### 2.4. Evidence model

`evidence` biểu diễn một evidence slot của case, gồm evidence type, giá trị thô/chuẩn hóa, provenance, confidence, review status, status reason và trạng thái `present`, `absent`, `unknown` hoặc `notApplicable`. `unknown` là mặc định an toàn; không chuyển việc OCR/search không tìm thấy thành `absent`. `absent` và `notApplicable` cần lý do hoặc review phù hợp. Confidence của extraction được tách khỏi evidence status.

Raw extraction được lưu thành artifact; evidence chỉ giữ dữ kiện đã chuẩn hóa và provenance về artifact/trang/vùng. Agent tạo quan hệ ứng viên giữa evidence trong reasoning trace thay vì yêu cầu bảng `EvidenceLink`; chỉ những quan hệ thực sự được dùng trong proof hoặc final result mới được đóng băng cùng artifact tương ứng.

### 2.5. Case snapshot và proof identity

MVP không tạo bảng case snapshot riêng. Mỗi `agent_run` đóng băng đầu vào trong `input_snapshot JSONB` và `case_snapshot_hash`, gồm case/time context cùng evidence IDs, statuses, normalized-value hashes và provenance hashes. Khi evidence thay đổi, phải tạo agent run, proof artifact và final result mới; không sửa hoặc tái sử dụng proof cũ.

Mỗi proof artifact khóa `theorem_statement_hash`, `rule_version_id`, `manifest_hash`, `case_snapshot_hash`, `premise_binding_hash` và toolchain. Premise bindings ánh xạ xác định evidence IDs sang Lean fields/hypotheses. Output gate phải xác nhận toàn bộ identity, trạng thái rule, thời gian hiệu lực, `sorry`/`admit`, axiom allowlist và answer–proof agreement trước khi dùng proof.

### 2.6. Nhật ký truy vết

`agent_run` lưu snapshot và số liệu tổng hợp của một lần chạy; `audit_event` lưu từng bước theo thứ tự và ở chế độ append-only. Event tối thiểu ghi run/sequence/type/component, input/output artifact references, quyết định, metrics và thời điểm. Không update hoặc delete event cũ trong luồng ứng dụng; thay đổi được biểu diễn bằng event mới.

PDF, dữ liệu nhạy cảm, prompt/raw model output lớn và diagnostics đầy đủ được lưu thành artifact; audit chỉ giữ ID/hash cùng metadata cần để tái lập. MVP không yêu cầu blockchain hoặc hash chain. Schema logic bổ sung `core.audit_event`, nâng tổng số bảng logic tối thiểu lên 11.

### 2.7. Module ownership

Mười ba trách nhiệm logic được nhóm thành tám mô-đun nội bộ trong modular monolith: Source & Document, Legal Retrieval, Formalization & Rule Registry, Case & Evidence, Agent Orchestrator, Proof & Lean, Explanation & Output, và Audit & Observability.

Mỗi mô-đun có quyền ghi riêng: Source ghi artifact/source/chunk; Formalization ghi rule/manifest; Case ghi case/document/evidence; Orchestrator ghi agent run; Proof ghi proof artifact; Output ghi final result; Audit ghi append-only audit event. Legal Retrieval chỉ đọc nguồn/chunk trong online flow. Agent Orchestrator điều phối nhưng không sở hữu và không được trực tiếp sửa source, approved rule, reviewed evidence, proof cũ, final result hoặc audit event.

```text
Nguồn luật có phiên bản
        ↓
Tách thành các đơn vị quy tắc
        ↓
Agent sinh Legal IR ứng viên
        ↓
Kiểm tra schema và độ trung thành ngữ nghĩa
        ↓
Template/domain lowering hoặc Agent sinh Lean ứng viên
        ↓
Sinh theorem và test case
        ↓
Lean compile và proof check
        ↓
Cổng phê duyệt
        ↓
Versioned formal-law registry
```

Đầu ra của Agent luôn mang trạng thái `candidate`. Pipeline online chỉ được sử dụng quy tắc có trạng thái `approved`.

## 3. Tách pipeline offline và online

### 3.1. Pipeline offline: formalize pháp luật

```text
Nguồn pháp luật
  → Legal IR candidate
  → semantic review
  → Lean candidate
  → Lean verification
  → approval
  → versioned formal-law registry
```

Pipeline này được phép tạo mới hoặc sửa formalization, nhưng không được tự động kích hoạt một quy tắc chưa được duyệt.

### 3.2. Pipeline online: xử lý hồ sơ

```text
Hồ sơ doanh nghiệp
  → trích xuất chứng cứ
  → Case/Evidence IR
  → chọn approved rule
  → tạo proof obligation
  → tìm premise và proof
  → Lean verification
  → giải thích có trích dẫn
  → deterministic output gate
```

Pipeline online không formalize một điều luật mới trong lúc xử lý hồ sơ rồi dùng ngay formalization đó để kết luận.

## 4. Ba biểu diễn trung gian

### 4.1. Rule Legal IR

Biểu diễn ngữ nghĩa của một đơn vị quy tắc pháp luật.

```json
{
  "rule_id": "VAT_ART14_C2_EXPORT_DOCS",
  "source": {
    "document_id": "114/VBHN-VPQH",
    "article": "14",
    "clause": "2",
    "point": null,
    "source_text": "...",
    "source_hash": "..."
  },
  "effective_from": "...",
  "effective_to": null,
  "subject": "exported_goods_transaction",
  "modality": "must",
  "conditions": [],
  "conclusion": "document_conditions_satisfied",
  "required_evidence": [],
  "exceptions": [],
  "definitions": [],
  "cross_references": [],
  "formalisation_boundary": [],
  "status": "candidate"
}
```

Legal IR phải biểu diễn được tối thiểu:

- Chủ thể và đối tượng áp dụng.
- Nghĩa vụ, quyền, cấm hoặc điều kiện.
- Hội và tuyển của các điều kiện.
- Phủ định và ngoại lệ.
- Ngưỡng số và thời hạn.
- Thời gian hiệu lực.
- Định nghĩa và dẫn chiếu.
- Yêu cầu chứng cứ.
- Phần mơ hồ hoặc cần con người quyết định.
- Nguồn, điều, khoản và phiên bản.

### 4.2. Case/Evidence IR

Biểu diễn dữ kiện và trạng thái chứng cứ của một hồ sơ.

```json
{
  "case_id": "CASE_001",
  "transaction_type": "exported_goods",
  "evidence": {
    "input_vat_invoice": "present",
    "non_cash_payment": "present",
    "customs_declaration": "unknown",
    "packing_list": "present",
    "bill_of_lading": "present",
    "insurance_certificate": "notApplicable"
  }
}
```

Không được tự động chuyển `unknown` thành `absent`, `present` hoặc `notApplicable`.

### 4.3. Proof Goal IR

Biểu diễn mục tiêu cần chứng minh, liên kết với đúng quy tắc và hồ sơ.

```json
{
  "goal_id": "GOAL_CASE001_ART14_C2",
  "goal_kind": "not_verified",
  "rule_id": "VAT_ART14_C2_EXPORT_DOCS",
  "rule_version": "...",
  "case_id": "CASE_001",
  "target_predicate": "SatisfiesDocumentConditions",
  "expected_claim": "not SatisfiesDocumentConditions CASE_001"
}
```

## 5. FormalizationManifest

Không đặt toàn bộ chi tiết triển khai Lean vào Legal IR. Sử dụng một manifest riêng để ánh xạ ngữ nghĩa pháp luật sang code Lean.

Manifest đầy đủ được lưu dưới dạng JSON artifact bất biến, áp dụng pattern metadata/manifest/snapshot tương tự Apache Iceberg ở mức tối giản. `rule_version` giữ `active_manifest_artifact_id`, `manifest_hash` và một `manifest_summary JSONB` cho các trường thường xuyên truy vấn; không cập nhật tại chỗ một manifest đã được duyệt. Khi Lean source, theorem, field mapping, test bundle hoặc toolchain thay đổi, tạo manifest artifact mới và lưu lineage/quan hệ supersede.

```json
{
  "manifest_id": "MANIFEST_VAT_ART14_C2_V1",
  "parent_manifest_id": null,
  "rule_id": "VAT_ART14_C2_EXPORT_DOCS",
  "rule_version": "...",
  "lean_module": "VAT.Article14Clause2",
  "source_file": "formalization/Article14Clause2.lean",
  "predicate_symbol": "SatisfiesDocumentConditions",
  "supporting_symbols": [
    "EvidenceStatus",
    "ExportGoodsEvidence",
    "isPresent",
    "insuranceCondition"
  ],
  "related_theorems": [
    "completeCase_is_verified",
    "unknown_customs_is_not_verified"
  ],
  "required_imports": [],
  "status": "approved",
  "source_hash": "..."
}
```

Các nguyên tắc mượn từ Iceberg gồm indirection, artifact bất biến, pointer tới phiên bản đang hoạt động, hash và lineage. Không đưa manifest list, partition statistics hoặc commit protocol của Iceberg vào MVP.

Phân công trách nhiệm:

- Legal IR trả lời: quy tắc pháp luật nào phù hợp?
- `FormalizationManifest` trả lời: quy tắc đó được triển khai ở đâu trong Lean?
- Lean proof state trả lời: premise hoặc theorem nào cần dùng để hoàn thành chứng minh?

## 6. Pipeline truy xuất code và chứng minh Lean

Legal IR được dùng làm lớp định tuyến ngữ nghĩa, không phải là bộ máy proof search duy nhất.

```text
Câu hỏi hoặc mệnh đề pháp lý
        ↓
Agent tạo Proof Goal IR
        ↓
Đối chiếu Case/Evidence IR
        ↓
Rule retrieval từ Legal IR registry
        ↓
Lọc approved rule đúng phiên bản
        ↓
FormalizationManifest
        ↓
Tạo Lean goal và local hypotheses
        ↓
Premise retrieval theo proof state
        ↓
Deterministic tactics
        ↓ nếu chưa giải được
LeanDojo-v2/Pantograph proof search
        ↓
Lean kernel verification
        ↓
Kiểm tra rule/proof/case identity
        ↓
Giải thích có nguồn và audit trace
```

### 6.1. Ba tầng retrieval

1. **Rule retrieval:** tìm quy tắc theo `rule_id`, chủ thể, kết luận, điều kiện, ngoại lệ, nguồn và phiên bản.
2. **Code retrieval:** tìm module, predicate, definition và import thông qua `FormalizationManifest`.
3. **Premise retrieval:** tìm theorem hoặc lemma theo Lean goal, local hypotheses, type signature và dependency graph.

### 6.2. Chiến lược xếp hạng

Ưu tiên theo thứ tự:

1. Khớp chính xác `rule_id` và phiên bản.
2. Khớp predicate và type signature.
3. Khớp namespace, module và import.
4. Mở rộng theo dependency graph.
5. Tương đồng Legal IR và theorem statement.
6. Lịch sử premise đã giải các goal tương tự.
7. Agent rerank tập ứng viên giới hạn.

Vector embedding chỉ hỗ trợ tìm ứng viên. Nó không được phép vượt qua bộ lọc trạng thái, nguồn hoặc phiên bản.

### 6.3. Bộ công cụ nội bộ cho Agent

Chấp nhận ngày 08/10/2026: đặc tả API/pseudocode tuần 3 bắt đầu bằng sáu hợp đồng hàm nội bộ của modular monolith. Đây là quyết định thiết kế, chưa phải bằng chứng triển khai. Có thể bổ sung HTTP adapter sau mà vẫn giữ các hợp đồng này.

| Công cụ | Trách nhiệm | Đầu ra chính |
| --- | --- | --- |
| `search_legal_sources` | Tìm điều khoản theo câu hỏi và thời điểm nghiệp vụ | Chunk nguyên văn, nguồn, phiên bản, vị trí trích dẫn |
| `find_approved_rules` | Tìm formalization phù hợp với mệnh đề cần kiểm tra | Rule Legal IR, rule version, manifest reference |
| `query_case_evidence` | Lấy dữ kiện theo các trường rule yêu cầu | Evidence status, giá trị và provenance |
| `build_proof_obligation` | Ánh xạ evidence của snapshot sang Lean fields/hypotheses | Proof Goal IR, theorem statement, premise bindings |
| `retrieve_lean_premises` | Tìm definition/theorem/lemma phục vụ goal | Symbol, type, dependency và code reference |
| `check_lean_proof` | Kiểm tra proof ứng viên bằng Lean | Kết quả kỹ thuật, diagnostics; open goals nếu runtime hỗ trợ |

Agent chọn công cụ và đề xuất hành động; module sở hữu dữ liệu kiểm tra yêu cầu. Registry kiểm tra approval/phiên bản; Proof module kiểm tra premise bindings và theorem identity. Phản hồi kỹ thuật từ Lean được Output module kết hợp với phạm vi rule, evidence và trích dẫn để tạo kết luận nghiệp vụ.

Vòng phản hồi gồm bốn hướng: sửa proof ứng viên khi lỗi cú pháp/type/tactic; truy xuất premise khi cần lemma; tìm hoặc yêu cầu thêm chứng từ khi evidence unknown; dừng với trạng thái chưa xác minh và lý do khi hết ngân sách hoặc cần nhận định con người. Repair giữ cố định theorem, rule version và snapshot. Evidence thay đổi phải tạo run/snapshot mới theo mục 2.5; proof artifact cũ không bị ghi đè. Contract chi tiết của từng công cụ được brainstorm riêng trước khi chấp nhận.

### 6.4. Contract `find_approved_rules`

Chấp nhận ngày 08/10/2026: đầu vào gồm `claim` (mệnh đề cần kiểm tra), `case_context` (chủ thể/loại giao dịch/ngữ cảnh đã biết), `legal_time_context` (ngày giao dịch/kỳ thuế hoặc mốc liên quan) và `rule_refs` tùy chọn (điều/khoản hoặc rule ID). Có thể truyền predicate đã nhận diện trong registry để tìm chính xác hơn; không yêu cầu Agent biết Lean symbol từ đầu.

Luồng xử lý: kiểm tra ngữ cảnh; lọc approved và phiên bản phù hợp; tìm theo rule reference/predicate nếu có; tìm ngữ nghĩa trong Legal IR; trả ứng viên cùng phạm vi và phần còn thiếu. Không tự đặt một mốc thời gian để chọn phiên bản khi ngữ cảnh chưa đủ. Trạng thái trả về gồm `found`, `requires_context`, `no_match`.

Mỗi ứng viên trả `rule_version_id`, `manifest_ref`, `legal_ir`, `required_evidence`, `scope`, `formalisation_boundary` và `match_basis` (lý do khớp ngắn, có thể kiểm tra). Tìm được rule chưa xác nhận rule áp dụng cho case: các điều kiện áp dụng phụ thuộc evidence vẫn phải kiểm tra ở bước sau. Nếu rule chỉ bao phủ một phần claim, phải nêu phần được bao phủ và phần còn thiếu. `no_match` chỉ nói về registry trong phạm vi tìm kiếm hiện tại, không khẳng định pháp luật không có quy định. Nội dung hợp đồng này là thiết kế, chưa phải API đã triển khai.

### 6.5. Contract `query_case_evidence`

Chấp nhận ngày 08/10/2026: đầu vào gồm `run_id`, `rule_version_id` và `evidence_keys` tùy chọn. Run xác định case và snapshot; module lấy yêu cầu evidence từ rule/manifest. Bỏ `evidence_keys` thì lấy toàn bộ yêu cầu; nếu có thì lấy phần được chỉ định trong phạm vi rule. Module kiểm tra đúng case/snapshot và không yêu cầu Agent viết lại danh sách chứng từ.

Mỗi slot trong response trả `requirement_key`, `evidence_id` nullable, `status`, `normalized_value`, `provenance`, `review_status` và `status_reason`. Khi snapshot chưa có evidence, trả slot `unknown` với ID/value trống và lý do; slot thiếu trong response không bắt buộc tạo thêm dòng database.

Không tìm thấy dữ kiện không đủ căn cứ để gán `absent`. Khi nhiều evidence mâu thuẫn, trả các ứng viên và đánh dấu xung đột chưa giải quyết; Agent đề xuất lựa chọn có căn cứ, module kiểm tra trước khi mapping sang proof. Evidence mới phải đi qua luồng cập nhật evidence và tạo run/snapshot mới trước khi dùng cho proof. `present` mô tả trạng thái evidence trong hệ thống, không tự xác nhận tính xác thực chứng từ hoặc mọi điều kiện pháp lý; các kiểm tra đó phải được biểu diễn riêng nếu thuộc phạm vi rule. Contract này là thiết kế, chưa phải API đã triển khai.

### 6.6. Contract `build_proof_obligation`

Chấp nhận ngày 08/10/2026: đầu vào gồm `run_id`, `rule_version_id` và `target_ref` (predicate/theorem được manifest công bố). Module kiểm tra rule/manifest/snapshot, lấy evidence theo yêu cầu, ánh xạ qua field mapping đã duyệt, kiểm tra dữ kiện thiếu/xung đột/boundary rồi tạo Proof Goal IR và Lean statement. Agent chọn mục tiêu trong phạm vi formalization đã duyệt; builder dùng manifest để xác định kiểu dữ liệu, field mapping và imports.

Đầu ra gồm `goal_id`, `lean_statement`, `premise_bindings`, `required_imports`, `identity` (rule version, manifest hash, snapshot hash, theorem hash) và `unresolved_items`. Trạng thái gồm `ready`, `needs_evidence`, `requires_human`, `invalid_input`. Nếu positive goal cần một evidence vẫn unknown, trả `needs_evidence` và slot thiếu; không âm thầm bỏ điều kiện hoặc đổi mục tiêu thành phủ định. Những goal đánh giá trạng thái evidence có thể được hỗ trợ riêng khi manifest công bố rõ phạm vi của chúng.

Builder không được đưa chính kết luận cần chứng minh vào làm giả thiết để tạo proof vòng tròn. Giả thiết đầu vào phải đến từ evidence và mapping được phép. Vòng repair giữ cố định statement và identity khi goal ready; thay đổi evidence hoặc mục tiêu phải đi qua builder để tạo obligation mới có truy vết, tuân thủ mục 2.5 khi snapshot thay đổi. Contract này là thiết kế, chưa phải API đã triển khai.

### 6.7. Contract `retrieve_lean_premises`

Chấp nhận ngày 08/10/2026: đầu vào gồm `goal_id`, `proof_state_ref` tùy chọn và `max_results` (tham số điều chỉnh qua đánh giá). Goal xác định statement, imports và phiên bản đã khóa. Khi có phản hồi runtime, truy xuất theo subgoal/local hypotheses nếu runtime cung cấp; khi chưa có, dùng goal ban đầu.

Phạm vi tìm gồm code của rule đã chọn, dependencies được phép và thư viện Lean tương thích với môi trường proof. Thứ tự: lấy symbols/definitions từ manifest; mở rộng dependencies; tìm lemma theo type/kết luận/giả thiết; dùng tìm kiếm ngữ nghĩa để bổ sung hoặc xếp hạng ứng viên. MVP không bắt buộc lập vector index riêng cho toàn bộ code Lean.

Mỗi kết quả gồm `symbol`, `kind`, `type_signature`, `code_ref`, `source_hash`, `dependencies` và `match_basis`. Phân biệt definition dùng để mở nghĩa/simplify với theorem/lemma cung cấp kết quả đã chứng minh. Theorem cho một case cụ thể không tự áp dụng cho case khác dù similarity cao; việc áp dụng phải qua Lean check. Trạng thái trả về gồm `found`, `no_match`, `invalid_context`. Không có premise phù hợp vẫn có thể thử tactic cơ bản; truy xuất thành công chưa khẳng định proof thành công. Contract này là thiết kế, chưa phải API đã triển khai.

### 6.8. Contract `check_lean_proof`

Chấp nhận ngày 08/10/2026: đầu vào gồm `goal_id`, `proof_candidate_ref` và `timeout_ms` (tham số chọn qua đánh giá, bị giới hạn bởi ngân sách còn lại). Module lấy statement, dữ liệu case, imports và toolchain từ obligation; candidate cung cấp phần proof/tactic để ghép vào khung đã khóa. Kiểm tra identity, chạy Lean trong giới hạn thời gian, kiểm tra proof hoàn chỉnh/axiom dependencies rồi lưu kết quả và diagnostics thành artifact.

Trạng thái: `passed` (proof hoàn chỉnh vượt kiểm tra kỹ thuật), `proof_failed` (lỗi cú pháp/type/tactic hoặc goal chưa giải xong), `rejected` (identity không hợp lệ, placeholder hoặc axiom ngoài allowlist), `timeout`, `runtime_error`. Output gồm `status`, `failure_kind`, diagnostics/reference, identity đã kiểm tra, elapsed time và artifact reference. `open_goals` chỉ có khi runtime cung cấp; MVP có thể bắt đầu bằng Lean CLI diagnostics.

`passed` yêu cầu đúng theorem/identity, clean verification trong môi trường đã khóa, không `sorry`/`admit` và không axiom dependency ngoài allowlist; exit code 0 riêng lẻ chưa đủ. Kiểm tra cả dependencies để phát hiện placeholder gián tiếp qua lemma. Orchestrator quản lý tổng retry/time budget, ngoài timeout từng lần gọi. `proof_failed`/`timeout` không phải chứng minh phủ định goal. `passed` xác nhận proof trong phạm vi mã hóa; Output module vẫn kiểm tra phạm vi kết luận, nguồn và citation trước khi phát hành. Contract này là thiết kế, chưa phải API đã triển khai.

### 6.9. Contract `search_legal_sources`

Chấp nhận ngày 08/10/2026: đầu vào gồm `run_id`, `query`, `source_refs` tùy chọn và `max_results` (điều chỉnh qua đánh giá). Lấy thời điểm nghiệp vụ từ run; thiếu ngữ cảnh để chọn phiên bản thì trả `requires_context`. Kết quả có thể gồm cả điều khoản chưa được formalize. Trạng thái gồm `found`, `requires_context`, `no_match`.

Luồng xử lý: xác định phạm vi nguồn/phiên bản; keyword/full-text kết hợp vector; hợp nhất; mở rộng dẫn chiếu/ngữ cảnh cha khi cần; rerank và trả chunks. Mỗi chunk gồm `chunk_id`, `source_version_id`, `text` nguyên văn, `locator`, `source_ref`, `source_hash`, `temporal_metadata`, `cross_references` và `retrieval_basis`. Metadata thời gian giữ căn cứ chọn phiên bản; dẫn chiếu chưa truy xuất được phải được nêu rõ. Citation lấy từ `text`, không lấy phần bổ sung trong `embedding_text`.

Điểm retrieval biểu thị độ liên quan, không xác nhận hiệu lực hoặc việc áp dụng pháp lý. `no_match` nói về corpus trong phạm vi truy xuất hiện tại, không khẳng định pháp luật không có quy định; top-k chưa bảo đảm bao phủ mọi quy định liên quan. Contract này là thiết kế, chưa phải API đã triển khai.

### 6.10. Luồng Orchestrator và vòng Agent–Lean

Chấp nhận ngày 08/10/2026: luồng online có bước bắt buộc; Agent chọn truy vấn, rule ứng viên và chiến lược proof trong từng bước. Thứ tự: tạo run/khóa snapshot; tìm nguồn; tìm approved rules; chọn rule/xác định phạm vi goal; truy vấn evidence; dựng obligation; thử tactic xác định; vòng Agent–Lean nếu cần; tổng hợp; Explanation & Output Gate.

Câu hỏi nhiều mệnh đề được chia thành các claim có kết quả và phạm vi riêng. Proof điều kiện chứng từ chỉ đóng góp vào phần tương ứng, không tự xác minh claim rộng hơn về toàn bộ quyền khấu trừ. Orchestrator kiểm tra trạng thái trả về trước khi chuyển bước: thiếu ngữ cảnh thì yêu cầu bổ sung; có nguồn nhưng thiếu approved formalization thì ghi phần chưa thể kiểm chứng bằng Lean; builder `needs_evidence` thì chuyển luồng bổ sung; `requires_human` thì chuyển người kiểm tra; chỉ `ready` đi vào proof loop.

Pseudocode vòng proof (minh họa thiết kế):

```text
candidate := deterministic_proof(fixed_goal)
while total_budget.can_continue():
    result := budgeted_check_lean_proof(fixed_goal.id, candidate)
    append_audit_event(result)
    if result.status = passed:
        return proof_success(result)
    if result.status in {rejected, runtime_error}:
        return unresolved(result)
    if not total_budget.can_continue():
        break
    premises := budgeted_retrieve_lean_premises(goal.id, result.feedback_ref)
    if not total_budget.can_continue():
        break
    candidate := budgeted_agent_propose_proof(fixed_goal, result, premises)
return unresolved(budget_exhausted)
```

Các lời gọi budgeted là wrapper điều phối quanh contract đã chốt, tính lượt gọi/thời gian/chi phí phù hợp cho cả Agent, retrieval và Lean; không bổ sung công cụ Agent riêng. Diagnostics/proof state được tham chiếu từ `feedback_ref` nếu có. Snapshot/evidence thay đổi thì tạo run mới có lineage đến run trước; toàn yêu cầu có thể giữ ngân sách chung qua các run. Audit lưu hành động, trạng thái, căn cứ ngắn và artifact references, không yêu cầu lưu suy nghĩ nội bộ của mô hình. Mọi kết quả đến người dùng đi qua Output module với phạm vi đã kiểm chứng và phần còn thiếu; đoạn pseudocode chưa phải runtime đã triển khai.

### 6.11. Explanation & Output Gate

Chấp nhận ngày 08/10/2026: kết quả từng claim được chuyển thành bản ghi kết luận có cấu trúc trước khi sinh câu trả lời. Luồng: kết quả kiểm tra claim; structured conclusion; explanation draft; output gate; lưu final result và trả người dùng.

Bản ghi gồm `claim_id`, `target_ref`, `status`, `reason_code`, `scope`, `proof_refs`, `evidence_refs`, `citations`, `unresolved_items`. Phân biệt đã xác minh, chưa xác minh và cần con người, với lý do cụ thể. Proof điều kiện chứng từ không cho phép nâng kết luận thành toàn bộ quyền khấu trừ; phần chưa kiểm tra phải giữ trong kết quả.

Gate kiểm tra xác định được: claim verified có proof passed cho đúng target; rule/manifest/snapshot/proof identity khớp; phiên bản nguồn phù hợp ngữ cảnh; citation trỏ đúng nguồn/đoạn trích; evidence refs khớp premise bindings và unresolved items được giữ. Kiểm tra field/link không tự bảo đảm toàn bộ ý nghĩa văn xuôi do LLM sinh.

MVP dùng template cho kết luận chính, điền scope/status/evidence/rule/unresolved items từ bản ghi; Agent viết giải thích bổ sung từ các bản ghi đó. Đánh giá riêng diễn giải tự do về độ đúng và nguồn hỗ trợ. Nếu gate lỗi, trả lỗi để sửa draft trong budget; hết budget thì trả thông báo chưa xác minh hoặc lỗi xử lý cùng căn cứ đã kiểm tra, không phát hành draft bị lỗi. Contract này là thiết kế, chưa phải output gate đã triển khai.

## 7. Vai trò của LegalLean, LeanDojo-v2 và APOLLO

### LegalLean

LegalLean được dùng làm framework tham khảo cho:

- `LegalRule`.
- `EvidenceFor`.
- `FormalisationBoundary`.
- Modality, negation, exception, temporal constraint, threshold, definition và cross-reference.

Dự án phải bổ sung domain predicates cho VAT Việt Nam, thẩm quyền Việt Nam, typed rule IDs, quản lý phiên bản và lowering riêng. Không sử dụng placeholder làm kết luận pháp lý.

### LeanDojo-v2/Pantograph

LeanDojo-v2 được dùng sau khi đã có Lean statement hoặc proof obligation:

- Trace repository và lập chỉ mục theorem/proof state/tactic/premise.
- Premise retrieval.
- Proof search hoặc sinh tactic.
- Benchmark các phương án proving.

LeanDojo-v2 không xác nhận bản dịch từ tiếng Việt sang Lean có đúng ý nghĩa pháp luật hay không.

### APOLLO

APOLLO không được chọn làm dependency của kiến trúc lõi. Agent loop của dự án đã bao gồm các chức năng chính bị trùng với APOLLO:

- Lean runtime trả proof state, lỗi biên dịch và goal còn mở.
- Agent dùng phản hồi đó để sửa proof.
- Retriever tìm rule, code, premise hoặc evidence liên quan.
- Tactic xác định được thử trước khi gọi mô hình.
- Proof cuối được Lean kiểm tra lại và đi qua cổng `no sorry/admit`, axiom và identity.

Vì vậy APOLLO chỉ được giữ làm:

- Tài liệu tham khảo cho chiến lược compiler-guided proof repair.
- Đối chứng hoặc ablation tùy chọn trên tập proof lỗi.
- Nguồn ý tưởng cho syntax refinement, tách sub-goal và proof assembly nếu loop hiện tại bộc lộ thiếu sót đo được.

Chỉ xem xét tích hợp APOLLO nếu đánh giá cho thấy loop hiện tại thất bại đáng kể do proof hỏng cú pháp, sub-goal chưa được cô lập hoặc chi phí retry quá cao. APOLLO không được đọc hồ sơ thô, thay Legal IR, thay theorem statement, thêm giả thiết, thay rule version hoặc quyết định ý nghĩa pháp lý. Việc APOLLO dùng `sorry` làm trạng thái trung gian không làm thay đổi cổng phát hành: artifact cuối vẫn phải hoàn toàn không có `sorry` hoặc `admit`.

Trong thuật ngữ của kiến trúc này, cần phân biệt:

- **Legal/case evidence** được truy xuất trước khi tạo proof obligation và được mã hóa thành giả thiết có liên kết nguồn.
- **Lean premise/lemma** được truy xuất trong agent proof loop dựa trên goal và proof state.
- Lean runtime kiểm tra việc sử dụng các giả thiết và premise; bản thân Lean không xác minh tính xác thực của chứng từ ngoài đời.

## 8. Bộ seed 10–20 formalization

Bộ seed phục vụ retrieval-guided generation và đánh giá, không được coi là đủ để fine-tune mô hình.

Chọn mẫu theo độ đa dạng:

- Điều kiện đồng thời.
- Điều kiện thay thế.
- Hồ sơ và chứng từ.
- Ngoại lệ và loại trừ.
- Ngưỡng số hoặc thời hạn.
- Dẫn chiếu giữa các điều.
- Hiệu lực và phiên bản.
- Quy tắc cần con người xác định.
- Quy tắc tổng hợp phức tạp.

Mỗi mẫu tạo thành một formalization packet:

```text
Nguồn chính xác
+ Legal IR đã duyệt
+ Lean code
+ test dương
+ test âm
+ test unknown/notApplicable
+ giải thích mapping
+ FormalizationManifest
+ trạng thái phê duyệt
```

`formalization/Article14Clause2.lean` là seed đầu tiên hiện có.

### 8.1. Formalization packet mẫu tuần 3

Chấp nhận ngày 08/10/2026: dùng seed `Article14Clause2.lean` làm mẫu phạm vi điều kiện chứng từ đối với hàng xuất khẩu đã mã hóa; không tuyên bố toàn bộ quyền khấu trừ. Packet gồm source reference (PDF/locator/exact text/hash), Rule Legal IR, source→field/predicate mapping, Lean code/tests, manifest (rule/version/symbols/hashes/toolchain/test refs) và verification record (command/result/checks thực hiện).

Test plan gồm complete case với insurance notApplicable và customs unknown (đã có); bổ sung mandatory-document absent, insurance unknown, mandatory-document notApplicable. Các cases tổng hợp đánh giá predicate trong mô hình; unknown không được diễn giải thành chắc chắn không đủ điều kiện pháp lý. Bổ sung tests/IR/manifest là công việc tạo packet tiếp theo, chưa xác nhận đã thực hiện.

Kiểm tra lại ngày 08/10/2026: `elan run leanprover/lean4:v4.33.1 lean formalization/Article14Clause2.lean` exit 0. Đây là bằng chứng compile của file hiện tại, chưa tự xác nhận semantic review/approval hoặc toàn bộ gate. File dùng Lean 4 thuần, chưa import LegalLean; Legal IR/boundary/lowering là ý tưởng tham khảo cần minh họa qua packet, không được mô tả thành tích hợp thư viện đã chạy. Ghi riêng trạng thái compile, semantic review và approval. Một packet hoàn chỉnh phục vụ mẫu runnable tuần 3; 10–20 packets vẫn là kế hoạch triển khai tiếp theo.

### 8.2. Packet demo đã tạo

Hoàn thành kỹ thuật ngày 08/10/2026 tại `formalization/packets/VAT_ART14_C2_EXPORT_DOCS/v0.1.0/`: `source.json`, `legal_ir.json`, `mapping.json`, `manifest.json`, `verification.json`, `README.md`, tham chiếu canonical Lean source. Đã bổ sung ba tests dự kiến và một test bảo hiểm present, tổng cộng sáu synthetic regression theorems. `scripts/verify_article14_packet.py` là checker chỉ đọc, in JSON, không phê duyệt rule.

Record xác nhận hashes, source excerpts theo PDF pages 15–16 (trang in 122–123), IR/mapping metadata, Lean field structure, compile, expected theorem types và axiom dependencies; sáu theorem chỉ phụ thuộc `propext` trong allowlist. Ba mutation smoke tests với predicates type-correct (bỏ điều kiện tờ khai, cho unknown bảo hiểm đạt, cho unknown chứng từ bắt buộc đạt) đều bị regression suite phát hiện. Đây là kiểm tra mẫu, không phải benchmark held-out.

Trạng thái ngữ nghĩa và hiệu lực vẫn pending, approval not_approved, online_eligible false. Legal IR/mapping JSON là định dạng demo, chưa phải schema hoặc lowering compiler tổng quát. Giữ rõ ngoại lệ điểm b, special export cases điểm c, các lựa chọn chứng từ điểm a và lý do notApplicable cần review ngoài mô hình. Việc tạo packet không xác nhận PostgreSQL/Agent runtime hoặc tích hợp thư viện LegalLean đã triển khai.

## 9. Cổng phê duyệt

### 9.1. Cổng ngữ nghĩa

- Đúng văn bản, điều, khoản và phiên bản.
- Không đảo điều kiện cần và điều kiện đủ.
- Không bỏ sót ngoại lệ, phủ định, thời hạn hoặc dẫn chiếu.
- Đúng phạm vi chủ thể và giao dịch.
- Phần mơ hồ hoặc cần quyền quyết định được đưa vào formalisation boundary.
- Kết quả “không được xác minh” không bị diễn đạt thành “đã chứng minh không đủ điều kiện pháp lý”.

### 9.2. Cổng kỹ thuật

- Clean build.
- Không có `sorry` hoặc `admit`.
- Không có axiom ngoài danh sách cho phép.
- Không có placeholder như kết luận `True`.
- Theorem statement không bị Agent âm thầm thay đổi trong vòng repair.
- Có test dương, âm, `unknown` và `notApplicable` khi phù hợp.
- Proof artifact liên kết đúng `rule_id`, rule version, case ID và proof goal.

### 9.3. Cổng đầu ra

- Nguồn và trích dẫn hợp lệ.
- Rule version đang có hiệu lực.
- Kết luận trong câu trả lời nhất quán với proof result.
- Phân biệt `verified`, `not verified`, `requires human determination` và lỗi hệ thống.
- Có audit trace cho retrieval, mapping, proof và explanation.

## 10. Trạng thái vòng đời

Quy tắc và formalization sử dụng các trạng thái:

```text
draft
  → candidate
  → compiled
  → semantically_reviewed
  → approved
  → superseded hoặc deprecated
```

Chỉ `approved` được dùng trong pipeline online. Khi văn bản thay đổi, không ghi đè phiên bản cũ; tạo phiên bản mới và lưu quan hệ sửa đổi, thay thế hoặc hết hiệu lực.

## 11. Các phương án đã cân nhắc

### Sinh Lean trực tiếp từ văn bản

- Giữ lại làm baseline.
- Nhanh nhưng khó tách lỗi hiểu luật khỏi lỗi viết Lean.
- Không được tự động đưa kết quả vào registry chính thức.

### Template theo nhóm quy tắc

- Chấp nhận làm accelerator cho các cấu trúc phổ biến.
- Nếu quy tắc không khớp template, quay về Legal IR và lowering có kiểm duyệt.
- Không ép một điều luật đặc thù vào template không phù hợp.

### Agent tự formalize và dùng ngay khi trả lời

- Bị từ chối.
- Trộn pipeline offline với online và tạo rủi ro dùng sai bản dịch pháp luật.

### Chỉ dùng vector search trên toàn bộ code Lean

- Bị từ chối.
- Không bảo đảm đúng phiên bản, namespace, type hoặc rule identity.
- Thay bằng hybrid retrieval với bộ lọc xác định và proof-state retrieval.

### Đưa APOLLO vào lõi agent loop

- Chưa chấp nhận vì trùng Lean-feedback repair, retrieval và retry loop hiện có.
- Giữ làm reference implementation và optional ablation.
- Chỉ mở lại quyết định nếu benchmark nội bộ chứng minh cải thiện đủ lớn trên proof VAT với chi phí và toolchain chấp nhận được.

## 12. Kế hoạch triển khai

1. Chốt JSON Schema cho Rule Legal IR, Case/Evidence IR và Proof Goal IR.
2. Chốt schema `FormalizationManifest` và registry trạng thái.
3. Chuyển `Article14Clause2.lean` thành formalization packet hoàn chỉnh.
4. Xây thêm 10–20 seed đại diện.
5. Lập chỉ mục rule, symbol, theorem statement và dependency.
6. Xây rule retriever và code retriever xác định.
7. Tạo proof-obligation builder.
8. Chạy deterministic tactics trước; tích hợp LeanDojo-v2/Pantograph sau.
9. Đánh giá trên tập điều khoản chưa xuất hiện trong seed.

## 13. Thiết kế đánh giá

So sánh tối thiểu:

1. Direct LLM → Lean.
2. RAG examples → Lean.
3. RAG → Legal IR → Lean.
4. RAG → Legal IR → template/domain lowering → Lean.

Chỉ số:

- Tỷ lệ compile lần đầu.
- Tỷ lệ clean proof.
- Độ đúng điều kiện, ngoại lệ và phạm vi áp dụng.
- Độ đúng nguồn và phiên bản.
- Tỷ lệ phát hiện phần cần con người xử lý.
- Recall@k/MRR của rule và premise retrieval.
- Số vòng repair.
- Thời gian review của con người.
- Tỷ lệ mutation test phát hiện lỗi.

### 13.1. Hai bài toán đánh giá

Chấp nhận ngày 08/10/2026: trục đánh giá chính là xử lý hồ sơ với A (RAG theo luồng cố định), B (Agentic RAG) và C (Agentic RAG + approved formalization/obligation/Lean/proof–answer gate), kế thừa đặc tả tuần 2. Dùng chung corpus snapshot, cases, questions và model nền; ghi rõ tool/prompt/budget differences và mức sử dụng thực tế. Cổng citation/từ chối cơ bản áp dụng cho cả A/B/C theo tuần 2. B→C đo hiệu quả của lớp kiểm chứng bổ sung, chưa quy riêng hiệu quả cho Lean kernel nếu không có ablation tương ứng.

C báo cáo cả toàn bộ bộ ca (coverage, yêu cầu bổ sung/chuyển người) và subset nằm trong phạm vi đã formalize (mapping/proof correctness, xác minh sai). Điều kiện vào subset được xác định từ nhãn và registry đã khóa, không chọn lại chỉ các ca C thành công. Cùng đầu ra evidence của B được dùng cho nhánh Lean trong phép so sánh ghép cặp theo đặc tả tuần 2.

Thí nghiệm formalization riêng có phạm vi giới hạn, đơn vị đánh giá là rule unit và so sánh các phương án mục 13. Chấm độ trung thành điều kiện/ngoại lệ/phạm vi/thời gian/dẫn chiếu bên cạnh compile/proof metrics. Held-out formalization gồm điều khoản chưa dùng làm seed/example; held-out online gồm các case riêng. Không chia biến thể gần trùng của cùng hồ sơ qua dev/test. Đây là protocol thiết kế, chưa phải kết quả benchmark.

### 13.2. Bộ ca và nhãn vàng

Chấp nhận ngày 08/10/2026: giữ mục tiêu tuần 2 là 40 ca phát triển, 20 ca held-out, ít nhất 20 ca thuộc phạm vi Lean nằm trong 60 ca trên, và ít nhất 15 tình huống độ tin cậy chạy riêng. Đây là quy mô dự kiến, chưa xác nhận dataset đã có. Tuần 3 chốt thiết kế và xây nhóm mẫu để kiểm tra cách gắn nhãn; nhóm mẫu phát triển không thay thế held-out.

Nhóm mẫu quanh seed chứng từ gồm: đủ evidence; xác nhận thiếu; unknown; notApplicable có căn cứ; mâu thuẫn giữa tài liệu; ngoài phạm vi/cần phiên bản khác. Có thể tạo cặp ca thay đổi một yếu tố, nhưng các biến thể cùng hồ sơ phải ở cùng split. `absent`, `unknown` và `notApplicable` giữ ý nghĩa khác nhau, không suy thiếu dữ kiện thành chắc chắn không đủ điều kiện pháp lý.

Gold record gồm nguồn/phiên bản/điều khoản; evidence values/status/provenance; missing/conflicts; claims được phép và claims phải để ngỏ; expected action; với Lean thêm target/mapping/expected result trong phạm vi formalization. Gold không chỉ là một câu trả lời mẫu. Hai người gắn nhãn độc lập và phân xử bất đồng theo đề xuất tuần 2; thiếu review phù hợp thì ghi nhãn dự thảo, không gọi ground truth pháp lý chỉ vì khớp Lean code. Held-out khóa sau khi hoàn thiện nhãn theo protocol tuần 2, không dùng để chỉnh prompt/rule/ngưỡng.

### 13.3. Phân tầng metrics và yêu cầu đặc tả

Chấp nhận ngày 08/10/2026: bộ bảy nhóm chính cho A/B/C gồm retrieval Recall@k; evidence-status macro-F1 và lỗi nhầm unknown; citation precision/coverage; conclusion rubric 0–2; khẳng định không đủ căn cứ; selective accuracy/coverage và đúng hành động bổ sung/chuyển người; latency/tokens/tool calls/cost. Claims vàng bị bỏ qua vẫn tính trong completeness; claims tự thêm được kiểm tra về căn cứ.

Nhánh C bổ sung mapping correctness và clean-proof success trên obligations được gold xác định có thể chứng minh, với denominator khóa trước chạy; builder lỗi/timeout/budget exhaustion không được loại khỏi denominator. Tách rule coverage khỏi proof readiness, vì ca unknown có thể nằm trong scope rule mà chưa đủ evidence cho positive goal. Tách technical false acceptance (mapping/identity/integrity sai) và khẳng định sai/vượt scope trong final answer; lỗi bị gate chặn báo riêng khỏi lỗi phát hành. Mục tiêu sai xác minh = 0 là mục tiêu, chưa phải kết quả.

Để đủ đánh giá toàn pipeline, bổ sung: value-extraction F1, evidence-link correctness và conflict-detection F1; source/rule temporal-version accuracy; semantic fidelity/first-pass compile/boundary detection/mutation detection của formalization; proof-repair rounds/success within budget/latency by stage; xử lý lỗi phụ thuộc/timeout, gate rejection và false rejection trên test scenarios.

Tổ chức ba tầng: kết quả chính; chẩn đoán module; độ tin cậy. Mỗi metric cần khai báo unit of scoring, numerator/denominator, eligible subset, gold requirement, xử lý unknown/timeout/N/A và phương pháp chấm. Semantic fidelity chấm điều kiện/kết luận, ngoại lệ/phủ định, phạm vi chủ thể/giao dịch, thời gian/dẫn chiếu và human boundary. Mutation test dùng biến thể lỗi có chủ đích để đánh giá khả năng phát hiện. Chưa mặc định compile thành công đồng nghĩa đúng ngữ nghĩa, hay failed proof đồng nghĩa phủ định pháp lý. Chi tiết cách tính tiếp tục được chốt riêng; các metrics trên chưa phải số liệu thực nghiệm.

### 13.4. Metrics formalization theo rule unit

Chấp nhận ngày 08/10/2026: đơn vị là rule unit xác định trước từ điểm/khoản hoặc quy tắc tách từ khoản, có nguồn chính xác, scope yêu cầu và gold reviewed. Không mặc định mỗi điều luật là một đơn vị có độ phức tạp tương đương. Các cấu hình nhận cùng units.

| Metric | Định nghĩa |
| --- | --- |
| Semantic pass rate | Units đúng toàn bộ nội dung trong scope yêu cầu / tổng test units |
| First-pass compile rate | Units compile ngay lần đầu / tổng test units |
| Final clean-build rate | Units có artifact cuối build sạch, đúng identity và vượt technical checks / tổng test units |
| Boundary precision/recall | Đánh giá phát hiện đúng human-boundary items theo gold, gồm bỏ sót/đánh dấu quá mức |
| Mutation detection rate | Mutants lỗi hợp lệ được phát hiện / tổng mutants lỗi hợp lệ |
| Accepted-packet rate | Packets đạt semantic, technical và required tests / tổng test units |
| Effort | Repair rounds, runtime và human-review time mỗi unit |

Semantic pass đánh giá nghiêm trong scope được giao; bỏ ngoại lệ bắt buộc là không đạt dù code compile. Chấm từng chiều để chẩn đoán, không dùng trung bình để che lỗi trọng yếu. Accepted-packet rate là kết quả tổng hợp, báo cùng semantic pass và review cost.

Mutation suite ưu tiên mutants lỗi ngữ nghĩa nhưng hợp lệ syntax/type (bỏ điều kiện, AND→OR, chấp nhận unknown thay present, bỏ nhánh ngoại lệ); việc compiler bắt mutant sai cú pháp không chứng minh khả năng bắt lỗi ngữ nghĩa. Không sinh candidate hoặc budget exhausted giữ trong denominator và không đạt success tương ứng. Gold không có boundary thì chỉ số tương ứng có thể N/A, không ghi mặc định 100%; báo raw counts để diễn giải denominator. Gold chưa review đủ thì chỉ báo draft evaluation, chưa benchmark chính thức. Đây là đặc tả metrics, chưa có kết quả thực nghiệm.

### 13.5. Quy trình chạy và khóa đánh giá

Chấp nhận ngày 08/10/2026: (1) pilot/dev để kiểm tra schema, nhãn, scorer/artifacts và chọn tham số; (2) khóa evaluation manifest trước held-out; (3) chạy A/B/C với đầu vào/thành phần nền chung, nhánh C dùng evidence snapshot của B trong phép so sánh ghép cặp; (4) chấm tự động và review nội dung, ẩn tên cấu hình và phân xử bất đồng; (5) so sánh ghép cặp theo case và nhóm tình huống, báo counts/rates cùng chất lượng–chi phí; (6) phân tích lỗi theo module và lưu kết quả liên kết manifest/run artifacts.

Evaluation manifest là artifact bất biến, chứa refs/hashes của dataset, gold, corpus, rule registry, code, prompts, model/config, retriever, Lean toolchain và budgets. Gold chỉ dành cho scorer/review, không đưa vào Agent inputs. Timeout/builder errors/budget exhaustion giữ trong kết quả. Rerun vì hạ tầng phải theo policy định trước và giữ cả lần lỗi. Không tinh chỉnh bằng held-out rồi tái dùng cùng tập để tuyên bố cải thiện trên test chưa từng thấy.

Khi có variants cùng hồ sơ, phép tổng hợp uncertainty phải tính nhóm hồ sơ; không coi variants là các mẫu hoàn toàn độc lập. Week 3 cung cấp protocol có thể thực thi/kiểm tra, không mặc định benchmark đầy đủ đã chạy; báo riêng pilot/final benchmark và tình trạng gold draft/reviewed.

## 14. Ranh giới bảo đảm

Lean 4 chứng minh rằng kết luận suy ra từ các định nghĩa, giả thiết và rule đã mã hóa. Lean không tự bảo đảm:

- OCR hoặc văn bản nguồn đầy đủ.
- Bản dịch từ tiếng Việt sang Legal IR đúng.
- Lowering từ Legal IR sang Lean trung thành với luật.
- Chứng cứ thực tế xác thực.
- Retrieval không bỏ sót nguồn.
- Văn bản giải thích cuối cùng hoàn toàn đúng.

Các ranh giới này phải được đánh giá và kiểm soát riêng.

## 15. Nguồn tham khảo kiến trúc

- LegalLean: <https://github.com/edu-ap/legal-lean>
- LegalLean typed Legal IR: <https://github.com/edu-ap/legal-lean/blob/main/LegalLean/IR/Legal.lean>
- LegalLean IR lowering: <https://github.com/edu-ap/legal-lean/blob/main/LegalLean/IR/Lower.lean>
- LeanDojo-v2: <https://github.com/lean-dojo/LeanDojo-v2>
- Seed hiện tại: `formalization/Article14Clause2.lean`

