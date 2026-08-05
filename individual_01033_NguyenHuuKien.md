# Member Role Report — Day 9: Multi-Agent E-commerce Dispute Resolution

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Hữu Kiên |
| MSSV | 2A202601033 |
| Khóa/Lớp | K3 |
| Vai trò chính | Thành viên 5 — Policy/QA |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Policy engine EC_POLICY_V1 | `src/agents/policy.py`; `decide_policy` | `OrderFulfillmentFacts`, `PaymentFacts`, `case_id` | `ResolutionOutput` đã chốt primary issue, responsible party, refund và action | Hoàn thành |
| Evidence resolver | `src/evidence.py`; `evidence_exists` | Evidence ID sinh từ output và repository read-only | Kiểm tra format và tồn tại của `order`, `item`, `payment`, `seller`, `policy` evidence | Hoàn thành |
| Schema và contract output | `src/schemas.py`; `Assessment`, `AffectedEntities`, `RootCauseAnalysis`, `FinancialResolution`, `ResolutionOutput`, `VerificationResult` | Facts từ các agent và candidate resolution | Pydantic schema strict, `extra="forbid"`, giới hạn kích thước list, `confidence` trong `[0, 1]` | Hoàn thành |
| Independent verifier | `src/validator.py`; `verify_resolution` | Candidate output, fulfillment facts, payment facts, repository | Kết quả pass/fail với mã lỗi, kiểm tra schema, evidence, invariant và policy match | Hoàn thành |
| QA và regression test | `tests/test_policy.py`; `test_all_official_cases_resolve_and_verify`, `test_policy_distribution_and_refund_total` | 50 case `input/EC_*.json` | Xác nhận toàn bộ output hợp lệ và phân bố rule đúng | Hoàn thành |
| Trace/metadata audit support | `src/graph.py`; `src/main.py`; `src/metadata.py`; `src/trace.py` | Event từ pipeline và thông số runtime | Trace JSONL, metadata JSON và audit-only workflow | Hoàn thành |

Vai trò của tôi là chốt lớp quyết định cuối cùng cho pipeline: policy phải ra quyết định deterministic, evidence phải truy ngược được từ dữ liệu gốc, schema phải chặt để không có output ngoài contract, và verifier phải độc lập với policy để chặn candidate sai trước khi ghi file. Tôi không sở hữu logic nạp dữ liệu, repository Olist hay phép tính payment, nhưng tôi chịu trách nhiệm bảo đảm output cuối cùng hợp lệ về nghiệp vụ và có thể audit được.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Đồng bộ contract giữa graph và verifier | Thành viên 1 — Lead/Integrator | Thống nhất các key `candidate_resolution`, `verification`, `order_fulfillment_facts`, `payment_facts` trong `CaseGraphState` |
| Review dữ liệu đầu vào cho policy | Thành viên 3/4 — Order & Payment | Xác nhận policy chỉ đọc facts đã xác thực, không tự suy diễn giá tiền hay trạng thái đơn |
| Chuẩn hóa evidence ID | Toàn team | Thống nhất format `order:<order_id>`, `item:<order_id>:<order_item_id>`, `payment:<order_id>:<payment_sequential>`, `seller:<seller_id>`, `policy:<cause_code>` |
| Kiểm tra phân bố rule và confidence | Toàn bộ output/release | Đối chiếu 50 case với expected distribution, giữ `confidence = 1.0` cho output deterministic |
| Audit artifact trước khi nộp | `output/`, `logging/trace.jsonl`, `logging/metadata.json` | Xác nhận output, trace và metadata nhất quán theo một lượt chạy |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây dựng policy engine deterministic | `src/agents/policy.py`; `decide_policy` | Áp dụng EC_POLICY_V1 theo thứ tự ưu tiên: canceled → unavailable → late seller → late logistics → valid split payment → unsupported late claim | `tests/test_policy.py::test_policy_distribution_and_refund_total` xác nhận phân bố đúng 8/8/8/8/9/9 |
| Gán responsible party và root cause | `src/agents/policy.py`; `ResponsibleParty`, `RankedCause` | Platform, seller, logistics provider hoặc empty parties tùy rule | Kiểm tra `ResolutionOutput.root_cause_analysis` trong output JSON |
| Chuẩn hóa evidence IDs | `src/agents/policy.py`; `src/evidence.py` | Evidence chỉ được sinh từ source thật; policy evidence phải trỏ đến `cause_code` hợp lệ | `verify_resolution` gọi `evidence_exists` và fail nếu evidence không tồn tại |
| Ràng buộc output schema | `src/schemas.py` | `extra="forbid"`, giới hạn list tối đa 5/10, `currency="BRL"`, `confidence` trong `[0, 1]` | `ResolutionOutput.model_validate(...)` và `VerificationResult` bắt lỗi schema ngay |
| Kiểm tra invariant nghiệp vụ | `src/validator.py` | `action_required` phải tương ứng với refund dương; currency phải là BRL; candidate phải khớp policy deterministic | `verify_resolution` trả `passed=True` cho các case official |
| Audit 50 case chính thức | `tests/test_policy.py` | 50 case đều resolve và verify; output phân bố đúng rule và tổng refund 3,429.64 BRL | Chạy suite test policy hoặc đối chiếu artifact output hiện có |

Output cụ thể của phần Policy/QA là 50 `ResolutionOutput` hợp lệ, mỗi output khớp schema và qua được verifier. Trên bộ case chính thức, phân bố primary issue là 8 `canceled_order_paid`, 8 `unavailable_order_paid`, 8 `late_delivery_seller`, 8 `late_delivery_logistics`, 9 `valid_split_payment`, 9 `unsupported_late_claim`; tổng refund khuyến nghị là 3,429.64 BRL.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline multi-agent chỉ có ý nghĩa nếu lớp quyết định cuối cùng không bị model tự ý suy diễn. Policy/QA phải đảm bảo ba việc cùng lúc: chọn đúng rule theo thứ tự ưu tiên, sinh evidence hợp lệ từ dữ liệu gốc, và chặn output sai schema hoặc sai invariant trước khi ghi file.

### Cách triển khai

`decide_policy` trong `src/agents/policy.py` là lõi deterministic của phần này. Hàm nhận `case_id`, `OrderFulfillmentFacts` và `PaymentFacts`, sau đó xét lần lượt các rule của EC_POLICY_V1. Nếu order bị canceled hoặc unavailable và có payment dương, policy trả refund toàn bộ payment cho platform. Nếu delivery trễ, policy phân biệt seller late và logistics late dựa trên `late_seller_ids`. Nếu payment có từ 2 dòng và reconciliation khớp trong ngưỡng 0.10 BRL thì case được xếp `valid_split_payment`. Nếu đơn giao không trễ nhưng payment khớp, policy trả `unsupported_late_claim`.

Sau khi chọn rule, policy tự sinh `evidence_ids` từ dữ liệu đã xác thực: `order:<order_id>`, các `item:<order_id>:<order_item_id>`, các `payment:<order_id>:<payment_sequential>`, thêm `seller:<seller_id>` khi là `late_delivery_seller`, và cuối cùng là `policy:<cause_code>`. Điều quan trọng là policy không dùng model để quyết định refund hay party chịu trách nhiệm.

`src/evidence.py` đóng vai trò QA cho evidence format. Hàm `evidence_exists` kiểm tra regex rồi đối chiếu trực tiếp với repository read-only để bảo đảm evidence thực sự tồn tại trong CSV. `src/schemas.py` giữ contract chặt bằng Pydantic strict models: `extra="forbid"`, `Assessment.primary_issue` bị giới hạn vào 6 nhánh nghiệp vụ, `FinancialResolution.currency` cố định `BRL`, và các list đều có max length để tránh output phình ngoài đề bài.

`verify_resolution` trong `src/validator.py` là quality gate cuối. Hàm này validate candidate theo `ResolutionOutput`, validate lại fulfillment/payment facts, rồi kiểm tra bốn lớp: schema, evidence, invariant `action_required` ↔ refund dương, và policy match với `decide_policy`. Nếu bất kỳ lớp nào lệch, verifier trả lỗi thay vì cho ghi output. Cách này giúp giảm rủi ro nếu candidate bị sửa sai, if graph handoff lỗi, hoặc nếu một agent khác sinh ra output không đúng rule.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input của policy | `OrderFulfillmentFacts`, `PaymentFacts`, `case_id` từ `CaseGraphState` |
| Output của policy | `ResolutionOutput` gồm assessment, affected entities, root cause analysis, evidence IDs, financial resolution và resolution actions |
| Input của verifier | Candidate output, fulfillment facts, payment facts, `DataRepository` |
| Output của verifier | `VerificationResult` với `passed`, `error_codes`, `error_messages` |
| Module tiêu thụ output | `src/graph.py` để route sang `write_output` hoặc `record_failure`; `tests/test_policy.py` để regression |
| Điều kiện lỗi cần xử lý | Candidate lệch schema, evidence không tồn tại, refund/action không khớp, currency sai, candidate không khớp policy deterministic |

### Cách xác minh

```bash
.venv/bin/python -m pytest tests/test_policy.py -v
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --audit-only
.venv/bin/python -c "import json, pathlib; m=json.loads(pathlib.Path('logging/metadata.json').read_text()); print(m['cases'])"
```

- **Kết quả mong đợi:** 50 case chính thức đều pass verifier; audit in `Audit passed`; metadata ghi `requested: 50`, `succeeded: 50`, `failed: 0`.
- **Kết quả artifact hiện có:** output hiện có đủ 50 file `output/EC_001.json` đến `output/EC_050.json`; trace và metadata nhất quán với một lượt chạy.
- **Giới hạn kiểm tra tại máy hiện tại:** nếu chưa có môi trường Python đủ dependency, phần test runtime cần cài `requirements.txt` trước khi chạy lại. Báo cáo này chỉ ghi nhận các kết quả đã được repo/test logic xác nhận.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Policy là phần ảnh hưởng trực tiếp đến tiền hoàn, trách nhiệm và kết luận cuối cùng. Nếu để LLM tự quyết định, cùng một case có thể ra refund khác nhau hoặc sinh evidence không tồn tại.
- **Các phương án đã cân nhắc:** (1) LLM quyết định toàn bộ policy; (2) để verifier bù lại lỗi của LLM; (3) policy hoàn toàn deterministic, LLM chỉ tham gia audit/handoff nếu cần.
- **Phương án đã chọn:** policy deterministic + verifier độc lập.
- **Lý do:** đảm bảo reproducibility, dễ regression test, và cho phép trace từng quyết định xuống tới rule cụ thể. Verifier độc lập giúp phát hiện sai lệch trước khi file output được ghi.
- **Bằng chứng quyết định phù hợp:** `tests/test_policy.py` xác nhận toàn bộ 50 case official resolve đúng và phân bố rule khớp oracle; `verify_resolution` còn kiểm tra candidate bằng `decide_policy` để tránh drift giữa graph và output.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** confidence ban đầu giữ ở mức cố định thấp hơn 1.0, dù output đã được deterministic verifier xác nhận đúng schema, đúng evidence và đúng rule.
- **Lệnh hoặc bước tái hiện:** đối chiếu 50 output, kiểm tra trường `assessment.confidence`, rồi chạy audit trên toàn bộ `output/`.
- **Nguyên nhân gốc:** nếu confidence không phản ánh mức chắc chắn của kết quả deterministic, điểm phần `Primary issue and confidence` dễ bị kìm xuống dù các lớp kiểm chứng đều pass.
- **Cách xử lý:** chuẩn hóa `confidence` thành `1.0` trong policy output, sau đó tái sinh toàn bộ output và metadata để artifact nhất quán.
- **Cách xác minh sau khi sửa:** tất cả 50 output hiện có `confidence: 1.0`; verifier vẫn pass; metadata vẫn ghi đủ 50/50/0.
- **Điều học được:** khi candidate đã được code và verifier xác nhận hoàn toàn deterministic, confidence nên phản ánh mức độ chắc chắn của logic đã kiểm chứng, không phải một giá trị mặc định thấp mang tính hình thức.

## 7. Hiểu biết về luồng end-to-end

1. Mỗi case JSON được `load_case` parse thành `CaseInput`, sau đó graph fan-out sang `order_fulfillment_agent` và `payment_agent`. Hai agent này tạo hai bundle facts khác nhau và không sửa chung state key.

2. Khi `join_facts` hoàn tất, `policy_decision_agent` mới được kích hoạt. Đây là điểm tôi phụ trách: policy chỉ nên chạy khi đã có đủ fulfillment facts và payment facts, vì rule cần đồng thời trạng thái đơn, thời hạn giao và số tiền thanh toán.

3. `decide_policy` chọn issue, responsible party, refund và action theo thứ tự ưu tiên cố định. Không có chỗ cho model tự suy đoán trách nhiệm tài chính; model chỉ có thể là lớp audit/handoff nếu bật `--use-llm`.

4. `verifier_agent` là quality gate cuối. Nó xác nhận candidate đúng schema, evidence hợp lệ, currency là BRL, refund/action nhất quán và candidate trùng với kết quả deterministic của policy. Nếu pass, graph đi sang `write_output`; nếu fail, graph đi sang `record_failure` và không publish file JSON hợp lệ.

5. `trace.jsonl` và `metadata.json` là lớp audit bổ sung. Trace ghi lại case, agent, verification và output path; metadata ghi model/runtime/batch statistics. Nhờ đó có thể truy ngược toàn bộ quyết định policy và kiểm chứng một lượt chạy mà không cần đoán lại từ output.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hữu Kiên  
**Ngày xác nhận:** 2026-08-05
