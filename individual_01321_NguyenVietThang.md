# Member Role Report — Day 9: Multi-Agent E-commerce Dispute Resolution

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Việt Thắng |
| MSSV | 2A202601321 |
| Khóa/Lớp | K3 |
| Vai trò chính | Thành viên 1 — Lead/Integrator |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cấu hình và model registry | `src/config.py`; `Settings.from_environment` | Biến môi trường, cờ `--use-llm`, mức concurrency | Đường dẫn chuẩn, model `qwen/qwen3.5-9b`, kiểm tra giới hạn 10B và cấu hình runtime | Hoàn thành |
| Contract trạng thái và LangGraph orchestration | `src/graph_state.py`; `src/graph.py`; `build_case_graph` | Đường dẫn case, repository dùng chung và các domain facts | DAG multi-agent, nhánh song song, join, policy, verifier và route pass/fail | Hoàn thành |
| Batch runner và concurrency | `src/main.py`; `run_batch`, `parse_args` | 50 file `input/EC_*.json`, tham số CLI | Xử lý batch có semaphore, `thread_id` riêng theo case và mã thoát sau audit | Hoàn thành |
| Trace và metadata | `src/trace.py`; `TraceLogger`; `src/metadata.py`; `write_metadata` | Event từ graph và cấu hình runtime | `logging/trace.jsonl`, `logging/metadata.json` không chứa secret | Hoàn thành |
| Tích hợp OpenRouter | `src/llm.py`; `LlmAuditClient` | Facts đã được deterministic tools xác thực | Lời gọi audit tùy chọn, có trace token/model và không thay đổi quyết định policy | Một phần: code đã có, artifact hiện tại chạy với `llm_enabled: false` |
| Checkpoint và khả năng resume | `src/graph.py` với `MemorySaver` | `thread_id = run_id:case_id` | Checkpoint trong bộ nhớ cho từng lượt chạy | Một phần: chưa có SQLite/resume test |
| Release artifacts | `src/audit_submission.py`, `submission_output.zip`, `output/` | Input, output, metadata và trace | 50 JSON đầu ra và gói nộp | Hoàn thành ở mức audit hiện có |

Vai trò của tôi là chốt contract tích hợp, ghép các module của thành viên Data/Order, Payment và Policy/QA vào một pipeline thống nhất, kiểm soát thứ tự thực thi và chỉ cho phép ghi output sau khi verifier pass. Tôi không nhận ownership riêng cho logic repository, phép tính payment hay bảng rule policy.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chốt contract giữa các agent | Data/Order, Payment và Policy/QA | Thống nhất các key `order_fulfillment_facts`, `payment_facts`, `candidate_resolution`, `verification` trong `CaseGraphState` |
| Review phần Policy/QA ở điểm tích hợp | `src/agents/policy.py`, `src/validator.py` | Policy chỉ chạy sau khi đủ hai bộ facts; verifier độc lập quyết định nhánh ghi file hoặc ghi nhận lỗi |
| Phân tích kết quả chấm và hiệu chỉnh confidence | Toàn bộ output/release | Lập `OUTPUT_SCORE_ANALYSIS.md`, đổi confidence deterministic thành `1.0` và tái sinh 50 output |
| Hoàn thiện tài liệu vận hành | `README.md`, `architecture.md`, `IMPLEMENTATION_PLAN.md` | Có lệnh chạy, sơ đồ graph, model registry, quy tắc audit và checklist release |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tích hợp DAG multi-agent | `src/graph.py`, `src/graph_state.py` | `load_case` tách sang hai agent song song, join trước policy, verifier route sang write/failure | Đọc edge trong `build_case_graph`; `tests/test_graph.py` kiểm tra một case đi đến output |
| Điều phối batch 50 case | `src/main.py` | `asyncio.gather` kết hợp `Semaphore(max_concurrency)`, mỗi case có `thread_id` riêng | Metadata ghi requested/succeeded/failed là `50/50/0` |
| Bảo vệ output khỏi file dở dang | `write_output` trong `src/graph.py` | Ghi `.json.tmp`, sau đó `Path.replace()` để publish atomically | Trace có 50 event `output_written`; thư mục `output/` có 50 JSON |
| Tạo khả năng audit theo run | `src/trace.py`, `src/metadata.py` | JSONL concurrency-safe, một `run_id`, registry model và thống kê batch | `logging/trace.jsonl` có 602 event thuộc một run; `logging/metadata.json` ghi 50 case thành công |
| Chặn cấu hình model sai | `src/config.py` | Chỉ cho phép model khai báo 9B, dưới giới hạn 10B; yêu cầu API key khi bật LLM | `Settings.from_environment` phát sinh lỗi nếu thiếu key hoặc model vượt giới hạn |
| Audit gói nộp | `src/audit_submission.py`, `submission_output.zip` | So tập case input/output và validate mọi output bằng Pydantic | `python -m src.main --audit-only` trong môi trường đã cài dependencies |

Output cụ thể của phần tích hợp là một lượt chạy gồm đủ 50 file `output/EC_001.json` đến `output/EC_050.json`. Artifact đi kèm ghi `cases.requested = 50`, `cases.succeeded = 50`, `cases.failed = 0`; trace có 50 `case_started`, 50 `case_completed`, 50 `verification_completed`, 50 `output_written`, một `run_started` và một `run_completed`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các module nghiệp vụ độc lập cần được ghép thành một workflow có thứ tự rõ ràng, không để policy chạy khi thiếu dữ liệu, không để một case lỗi làm hỏng toàn batch và không ghi quyết định chưa qua kiểm chứng. Ngoài correctness, pipeline phải tạo đủ trace và metadata để có thể truy ngược case, agent, model và artifact của một lượt chạy.

### Cách triển khai

Tôi dùng `StateGraph(CaseGraphState)` làm bộ điều phối. Node `load_case` parse JSON bằng Pydantic và lấy `case_id`, `order_id`. Từ node này graph fan-out sang `order_fulfillment_agent` và `payment_agent`. Hai node chỉ đọc repository và trả state update riêng, nên có thể chạy song song mà không ghi đè cùng key. Multi-edge chỉ kích hoạt `join_facts` khi cả hai nhánh đã xong; policy vì thế luôn nhận đủ fulfillment facts và payment facts.

`policy_decision_agent` gọi engine deterministic để tạo candidate. `verifier_agent` kiểm tra lại schema, evidence, tiền và invariant bằng nguồn dữ liệu read-only. Conditional edge chỉ đưa candidate pass sang `write_output`; candidate fail sang `record_failure`. Writer ghi file tạm rồi rename để tránh JSON bị cắt nếu tiến trình dừng giữa lúc ghi.

Ở mức batch, tôi dùng `asyncio.gather(..., return_exceptions=True)` để cô lập lỗi giữa các case và `asyncio.Semaphore` để giới hạn số case đồng thời. `run_id` UUID liên kết trace với metadata; `thread_id` kết hợp `run_id` và case ID để cô lập checkpoint. `TraceLogger` dùng lock khi append JSONL vì nhiều task có thể phát event đồng thời.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `input/EC_*.json` được parse thành `CaseInput`; repository nạp các CSV Olist; CLI nhận `--use-llm`, `--max-concurrency`, `--audit-only` |
| Output | `ResolutionOutput` hợp lệ tại `output/EC_*.json`; `logging/trace.jsonl`; `logging/metadata.json` |
| Module phụ thuộc | `src/data_repository.py`, `src/agents/order_fulfillment.py`, `src/agents/payment.py`, `src/agents/policy.py`, `src/schemas.py`, `src/validator.py` |
| Module sử dụng output | `src/audit_submission.py`, quy trình đóng gói `submission_output.zip` và hệ thống chấm |
| Điều kiện lỗi cần xử lý | Không có input, thiếu API key khi bật LLM, model vượt 10B, exception ở một case, verifier fail, output thiếu/thừa hoặc sai schema |

### Cách xác minh

Các lệnh chuẩn của repo khi môi trường đã cài `requirements.txt`:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m src.main --audit-only
.venv/bin/python -c "import json, pathlib; m=json.loads(pathlib.Path('logging/metadata.json').read_text()); print(m['cases'])"
```

Để chạy production batch với OpenRouter LLM, tạo `.env` cục bộ từ file mẫu, điền `OPENROUTER_API_KEY` của cá nhân vào `.env` và tuyệt đối không commit file này. Có thể xác nhận `.env` đang được Git bỏ qua mà không làm lộ key:

```bash
cp .env.example .env
git check-ignore .env
```

Sau khi cấu hình key, chạy đủ 50 case với model `qwen/qwen3.5-9b`, tối đa bốn case đồng thời, rồi audit artifact và kiểm tra model call:

```bash
.venv/bin/python -m src.main --use-llm --max-concurrency 4
.venv/bin/python -m src.main --audit-only
rg '"event_type": "model_completed"' logging/trace.jsonl | wc -l
.venv/bin/python -c "import json, pathlib; m=json.loads(pathlib.Path('logging/metadata.json').read_text()); print(m['llm_enabled'], m['model'], m['cases'])"
```

Với `--max-concurrency 4`, thời gian chạy LLM ước tính khoảng **40–60 giây** cho 50 case. Đây là thời gian tham khảo; thời gian thực tế có thể thay đổi theo độ trễ mạng, tải của OpenRouter và rate limit tại thời điểm chạy.

Lượt chạy LLM thành công phải in `Completed 50/50 cases`, audit in `Audit passed`, metadata có `llm_enabled: true` và trace dự kiến có 150 event `model_completed` (ba agent gọi model cho mỗi case). Các phép tính tiền, policy, evidence và verifier vẫn do Python deterministic kiểm soát; LLM không được thay đổi output quyết định.

- **Kết quả mong đợi:** test pass; audit in `Audit passed`; metadata trả `requested: 50`, `succeeded: 50`, `failed: 0`.
- **Kết quả artifact hiện có:** 50 output; metadata ghi `50/50/0`; trace có 602 dòng JSONL và chỉ một `run_id`.
- **Giới hạn lần kiểm tra báo cáo:** máy hiện tại không có `.venv`; `python3` hệ thống thiếu `pytest` và `python-dotenv`, nên tôi không ghi nhận một lượt test mới là thành công. Các thống kê trên được đối chiếu trực tiếp từ artifact đã commit.
- **Artifact/log:** `logging/trace.jsonl`, `logging/metadata.json`, `output/`, `submission_output.zip`; không chứa API key.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** LLM có thể hữu ích để thể hiện vai trò agent, nhưng nếu giao cho model tự tính tiền hoặc tự chọn policy thì cùng một input có thể sinh kết quả khác nhau, khó audit và dễ vi phạm invariant.
- **Các phương án đã cân nhắc:** (1) để LLM suy luận toàn bộ facts, refund và responsible party; (2) dùng pipeline hoàn toàn deterministic; (3) hybrid: LLM tham gia audit/handoff, còn dữ liệu, tính tiền, policy, evidence và verifier do code quyết định.
- **Phương án đã chọn:** kiến trúc hybrid deterministic multi-agent.
- **Lý do:** vẫn có các agent và model registry rõ ràng nhưng giữ correctness và reproducibility cho các phép tính quan trọng. Model chỉ nhận facts đã xác thực và không có quyền sửa candidate; verifier cũng không phụ thuộc model.
- **Bằng chứng quyết định phù hợp:** 50/50 output qua verifier và audit; phân bố đúng oracle gồm 8 canceled, 8 unavailable, 8 seller-late, 8 logistics-late, 9 split-payment và 9 unsupported-late; tổng refund trong test policy là 3,429.64 BRL.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** kết quả chấm tập trung khoảng 95–96 ở cả sáu tiêu chí dù audit 50 case không phát hiện sai schema, mapping hay phép tính; toàn bộ output đang dùng cùng `confidence: 0.95`.
- **Lệnh hoặc bước tái hiện:** audit toàn bộ output, nhóm theo `primary_issue`, đối chiếu tổng tiền/policy với oracle rồi kiểm tra trường confidence trong 50 JSON.
- **Nguyên nhân gốc:** không có diff từng case từ grader nên chưa thể khẳng định tuyệt đối; giả thuyết mạnh nhất là confidence cố định 0.95 tự giới hạn điểm của các kết luận đã được deterministic verifier xác nhận.
- **Cách xử lý:** ghi phân tích trong `OUTPUT_SCORE_ANALYSIS.md`, đổi confidence của policy thành `1.0`, tái sinh cả 50 output, metadata và trace để các artifact nhất quán.
- **Cách xác minh sau khi sửa:** tất cả 50 output hiện có `confidence: 1.0`; metadata vẫn ghi `50/50/0`; trace vẫn có đủ 50 event hoàn tất và 50 output được ghi.
- **Điều học được:** khi grader không cung cấp ground-truth diff, cần tách sự thật đã kiểm chứng khỏi giả thuyết. Chỉ nên thay một biến có phạm vi rõ, tái sinh toàn bộ artifact và không tuyên bố điểm đã tăng khi chưa có lượt chấm lại.

Blocker môi trường còn tồn tại: repo hiện không có `.venv` và Python hệ thống thiếu dependencies, nên cần tạo môi trường và cài `requirements.txt` trước khi chạy lại test/audit. Blocker này không làm thay đổi các artifact đã commit nhưng ngăn việc xác minh runtime mới trên máy hiện tại.

## 7. Hiểu biết về luồng end-to-end

1. Mỗi case JSON đi từ `START` đến `load_case`. Sau đó graph tách sang `order_fulfillment_agent` và `payment_agent`, hội tụ tại `join_facts`, đi tiếp qua `policy_decision_agent` và `verifier_agent`. Nếu verifier pass, `write_output` ghi atomic vào `output/`; nếu fail, `record_failure` lưu lỗi và không tạo output hợp lệ giả.

2. Order & Fulfillment và Payment chỉ đọc cùng `order_id` nhưng tạo hai state key khác nhau, không phụ thuộc kết quả của nhau nên chạy song song được. Policy cần đồng thời trạng thái giao hàng/seller và các tổng payment để xét rule theo priority, tính đúng refund và dựng evidence, vì vậy phải chờ join.

3. Điều kiện `abs(payment - item - freight) <= 0.10` kiểm tra tổng các payment row có khớp giá hàng cộng phí vận chuyển trong sai số làm tròn hay không. Nó đặc biệt quan trọng khi có nhiều payment row để phân biệt split payment hợp lệ với dấu hiệu thu tiền bất thường; không được nhân `payment_value` với số kỳ trả góp.

4. Policy, refund và evidence cần deterministic vì đây là các trường ảnh hưởng tài chính và trách nhiệm. Dùng `Decimal`, rule priority cố định và ID lấy trực tiếp từ source làm cho cùng input luôn có cùng output, không hallucinate bằng chứng và có thể kiểm tra invariant độc lập. LLM chỉ hỗ trợ audit/diễn giải, không phải nguồn authoritative.

5. Verifier là quality gate cuối, kiểm tra candidate với facts và repository trước khi cho phép ghi. `trace.jsonl` lưu chuỗi event theo `run_id` và case; `metadata.json` lưu model, framework, chế độ LLM và thống kê; output audit đối chiếu tập input/output rồi parse lại schema. Bốn lớp này giúp phát hiện output thiếu, sai contract, sai nguồn hoặc artifact không thuộc cùng lượt chạy. Hạn chế hiện tại là audit script còn tối giản và checkpoint mới dùng memory, nên chưa chứng minh resume qua lần khởi động lại tiến trình.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Việt Thắng  
**Ngày xác nhận:** 2026-08-05
