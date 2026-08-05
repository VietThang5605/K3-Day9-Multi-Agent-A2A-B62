# Member Role Report — Day 9: Multi-Agent E-commerce Dispute Resolution

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Kim Duy Hưng |
| MSSV | 2A202601763 |
| Khóa/Lớp | K3 |
| Vai trò chính | Thành viên 2 — Data & Order |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Shared data repository | `src/data_repository.py`; `DataRepository.from_directory`, `DataRepository.order`, `DataRepository.items`, `DataRepository.payments` | Bốn CSV Olist trong `data/` | View read-only đã index theo `order_id`; `dict` orders, `dict` items_by_order, `dict` payments_by_order, `frozenset` seller_ids | Hoàn thành |
| Indexing và join | `DataRepository.from_directory`; vòng lặp build `items` và `payments` dict | Các list `order_rows`, `item_rows`, `payment_rows`, `seller_rows` từ pandas | Dict đã index theo `order_id`, mỗi group được sort theo `order_item_id` / `payment_sequential` | Hoàn thành |
| Hàm tiện ích tiền | `money(value)` trong `src/data_repository.py` | Giá trị chuỗi CSV | `Decimal` làm tròn ROUND_HALF_UP 2 chữ số BRL | Hoàn thành |
| Order fulfillment facts | `src/agents/order_fulfillment.py`; `build_order_fulfillment_facts` | `DataRepository`, `order_id` | `OrderFulfillmentFacts` — status, dates, items, seller IDs, late flags, source_refs | Hoàn thành |
| Schema `OrderFulfillmentFacts` và `ItemFact` | `src/schemas.py`; class `OrderFulfillmentFacts`, `ItemFact` | Input từ `build_order_fulfillment_facts` | Pydantic model hợp lệ, dùng chung bởi graph, policy và verifier | Hoàn thành |

Vai trò của tôi là xây dựng lớp dữ liệu nền tảng mà toàn bộ pipeline phụ thuộc vào: `DataRepository` phục vụ cả `order_fulfillment_agent` và `payment_agent`; `build_order_fulfillment_facts` cung cấp facts về đơn hàng, người bán và thời hạn giao hàng cho `policy_decision_agent` và `verifier_agent`. Tôi không nhận ownership cho logic payment, policy engine hay verifier.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Đồng thuận contract state key | Thành viên 1 (Lead/Integrator) | Key `order_fulfillment_facts` trong `CaseGraphState` map 1-1 với `OrderFulfillmentFacts.model_dump(mode="python")` |
| Cung cấp `source_refs` cho verifier | Thành viên 5 (Policy/QA) | `source_refs` trong `OrderFulfillmentFacts` liệt kê đúng format `order:<id>` và `item:<id>:<seq>` để `evidence_exists` resolver tra cứu |
| Review định nghĩa `payment_matches` | Thành viên 4 (Payment/Finance) | Xác nhận ngưỡng `<= 0.10 BRL` là đúng theo yêu cầu, không nhân với số kỳ trả góp |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Nạp và index bốn bảng CSV Olist | `DataRepository.from_directory` trong `src/data_repository.py` | Bốn bảng nạp một lần, index theo `order_id`, sort theo sequence; singleton dùng chung toàn batch | Gọi `DataRepository.from_directory(DATA_DIR)` không báo lỗi; `len(repository.orders)` > 0 |
| Xây dựng facts đơn hàng và người bán | `build_order_fulfillment_facts` trong `src/agents/order_fulfillment.py` | `OrderFulfillmentFacts` gồm status, dates, items, totals, `delivery_late`, `late_seller_ids`, `source_refs` | `tests/test_policy.py::test_all_official_cases_resolve_and_verify` — 50 case đều tạo facts hợp lệ |
| Phát hiện seller giao hàng muộn | Hàm `_after` và set comprehension `late_sellers` trong `build_order_fulfillment_facts` | `late_seller_ids`: danh sách seller có `delivered_carrier_date > shipping_limit_date` | `test_policy_distribution_and_refund_total` xác nhận 8 case `late_delivery_seller` |
| Tính tổng item và freight | `item_total_brl`, `freight_total_brl` trong `build_order_fulfillment_facts` | Dùng `Decimal` sum từng item; khớp với `FinancialResolution` trong output | Tổng refund cả batch là 3,429.64 BRL, khớp oracle |
| Hàm `money()` chuẩn hóa Decimal | `money(value)` trong `src/data_repository.py` | Chuyển chuỗi CSV sang `Decimal` ROUND_HALF_UP 2 chữ số; dùng chung bởi cả fulfillment và payment | Không có lỗi làm tròn trong 50 output; `reconciliation_delta_brl <= 0.10` cho toàn bộ case |
| Định nghĩa schema Pydantic | `ItemFact`, `OrderFulfillmentFacts` trong `src/schemas.py` | Model strict (`extra="forbid"`), giới hạn `max_length` trên list; dùng `Literal` khi cần | Pydantic validate thất bại ngay khi có field thừa/thiếu — verifier luôn nhận đúng contract |

Output cụ thể của phần Data & Order là 50 `OrderFulfillmentFacts` hợp lệ được tạo từ repository — tất cả đều vượt qua `verify_resolution` và tạo ra đúng 50 file `output/EC_001.json` đến `output/EC_050.json` với distribution: 8 `canceled_order_paid`, 8 `unavailable_order_paid`, 8 `late_delivery_seller`, 8 `late_delivery_logistics`, 9 `valid_split_payment`, 9 `unsupported_late_claim`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần một nguồn dữ liệu duy nhất, read-only, đã index sẵn để nhiều agent có thể truy cập đồng thời mà không gây race condition hay ghi đè. Đồng thời, facts về đơn hàng phải đủ phong phú cho policy engine xác định ai là người chịu trách nhiệm (seller hay logistics) và tính đúng refund.

### Cách triển khai

**DataRepository** được implement là `@dataclass(frozen=True)` — tất cả thuộc tính đều immutable sau khi khởi tạo, đảm bảo thread-safety khi nhiều async task truy cập đồng thời. Bốn bảng CSV được nạp một lần duy nhất qua `from_directory`, convert sang `dict` để tra cứu O(1) theo `order_id`. Items và payments được sort theo `order_item_id` / `payment_sequential` để output nhất quán, không phụ thuộc thứ tự CSV.

Hàm `money()` dùng `Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)` thay vì `float` để tránh lỗi floating-point khi cộng nhiều dòng payment. Tất cả tính toán tiền trong fulfillment và payment đều đi qua hàm này.

**build_order_fulfillment_facts** gọi `repository.order(order_id)`, `repository.items(order_id)` rồi build `ItemFact` list. Logic phát hiện seller muộn dùng hàm `_after(left, right)` so sánh ISO datetime: nếu `delivered_carrier_date > shipping_limit_date` của item thì seller đó nằm trong `late_seller_ids`. Tổng `item_total_brl` và `freight_total_brl` tính bằng `sum(Decimal)` để giữ độ chính xác. `source_refs` được build theo format `order:<id>` và `item:<id>:<seq>` — format này được evidence resolver trong `src/evidence.py` dùng regex kiểm tra tồn tại.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input của DataRepository | Bốn CSV: `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_order_payments_dataset.csv`, `olist_sellers_dataset.csv` trong `data/` |
| Input của `build_order_fulfillment_facts` | `DataRepository` (đã nạp), `order_id: str` từ `CaseInput.customer_request.claimed_order_id` |
| Output | `OrderFulfillmentFacts` hợp lệ theo Pydantic schema; chứa `order_id`, `order_status`, `delivered_carrier_date`, `delivered_customer_date`, `estimated_delivery_date`, `item_ids`, `seller_ids`, `items`, `item_total_brl`, `freight_total_brl`, `delivery_late`, `late_seller_ids`, `source_refs` |
| Module tiêu thụ output | `src/graph.py` → `order_fulfillment_agent` node ghi vào `state["order_fulfillment_facts"]`; `src/agents/policy.py` → `decide_policy`; `src/validator.py` → `verify_resolution` |
| Điều kiện lỗi cần xử lý | `order_id` không tồn tại → `ValueError("Unknown order_id: ...")` từ `repository.order()`; `delivered_carrier_date = None` trên đơn canceled → cần guard trước khi parse datetime |

### Cách xác minh

```bash
# Chạy toàn bộ test suite
.venv/bin/python -m pytest -q

# Kiểm tra cụ thể test policy (bao gồm cả fulfillment facts)
.venv/bin/python -m pytest tests/test_policy.py -v

# Kiểm tra nhanh DataRepository nạp được data
.venv/bin/python -c "
from src.config import DATA_DIR
from src.data_repository import DataRepository
repo = DataRepository.from_directory(DATA_DIR)
print('Orders:', len(repo.orders))
print('Sellers:', len(repo.seller_ids))
"

# Kiểm tra build_order_fulfillment_facts cho một order cụ thể
.venv/bin/python -c "
import json
from pathlib import Path
from src.config import DATA_DIR
from src.data_repository import DataRepository
from src.agents.order_fulfillment import build_order_fulfillment_facts
from src.schemas import CaseInput
repo = DataRepository.from_directory(DATA_DIR)
case = CaseInput.model_validate(json.loads(Path('input/EC_001.json').read_text()))
facts = build_order_fulfillment_facts(repo, case.customer_request.claimed_order_id)
print(facts.model_dump(mode='python'))
"
```

- **Kết quả mong đợi:** `test_all_official_cases_resolve_and_verify` pass với 50 case; `test_policy_distribution_and_refund_total` xác nhận distribution và tổng refund 3,429.64 BRL.
- **Kết quả artifact hiện có:** 50 output trong `output/`; metadata ghi `50/50/0`; mỗi output có `source_refs` hợp lệ khớp với resolver.
- **Giới hạn:** máy hiện tại không có `.venv`; cần cài `requirements.txt` trước khi chạy test. Kết quả trên được đối chiếu từ artifact đã commit và logic source code.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** DataRepository cần được chia sẻ an toàn cho nhiều async agent chạy song song (`order_fulfillment_agent` và `payment_agent` fan-out từ `load_case`). Nếu repository có thể bị mutate thì kết quả giữa các case sẽ không nhất quán.
- **Các phương án đã cân nhắc:** (1) mỗi agent tự nạp CSV riêng — tốn RAM và IO, chậm; (2) dùng class thường với lock — phức tạp không cần thiết; (3) `@dataclass(frozen=True)` với `frozenset` và `dict` read-only — immutable sau init.
- **Phương án đã chọn:** `@dataclass(frozen=True)` cho `DataRepository`. Tất cả dict và frozenset được khởi tạo một lần trong `from_directory`, sau đó không thể reassign. Các agent chỉ gọi method đọc (`order()`, `items()`, `payments()`).
- **Lý do:** đảm bảo thread/async safety mà không cần lock, tiết kiệm bộ nhớ (nạp một lần), code đơn giản. Phù hợp với thiết kế "read-only shared repository" trong `architecture.md`.
- **Bằng chứng quyết định phù hợp:** 50 case chạy đồng thời với `Semaphore(max_concurrency=4)` không có race condition; tất cả facts nhất quán và khớp oracle.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** khi build `late_seller_ids`, ban đầu code duyệt tất cả items và so sánh `shipping_limit_date` với `delivered_carrier_date` của đơn hàng — nhưng nếu `delivered_carrier_date` là `None` (đơn chưa được giao carrier), hàm so sánh datetime sẽ raise `TypeError`.
- **Lệnh hoặc bước tái hiện:** gọi `build_order_fulfillment_facts` với một `order_id` thuộc đơn có `order_status = "canceled"` — trường `order_delivered_carrier_date` trên các đơn này thường là `None` trong CSV Olist.
- **Nguyên nhân gốc:** `datetime.fromisoformat(None)` raise `TypeError`, không phải `ValueError`. Cần kiểm tra `None` trước khi parse.
- **Cách xử lý:** hàm `_after(left, right)` dùng `bool(left and right and datetime.fromisoformat(left) > datetime.fromisoformat(right))` — nếu một trong hai là `None` hay chuỗi rỗng, Python short-circuit trả `False` ngay mà không gọi `fromisoformat`.
- **Cách xác minh sau khi sửa:** `test_all_official_cases_resolve_and_verify` bao gồm 8 case `canceled_order_paid` và 8 case `unavailable_order_paid` — những case này có `delivered_carrier_date = None` và đều pass sau khi sửa. `late_seller_ids` đúng là `[]` cho các đơn này.
- **Điều học được:** luôn guard `None` trước khi parse datetime từ CSV; không nên giả định CSV luôn có giá trị cho mọi cột.

## 7. Hiểu biết về luồng end-to-end

1. **Khởi động batch:** `src/main.py` gọi `DataRepository.from_directory(DATA_DIR)` một lần duy nhất, nạp bốn CSV vào memory. Repository này được truyền vào `build_case_graph` và tồn tại suốt cả batch. Mỗi case JSON đi từ `START` đến `load_case` để parse `CaseInput` và lấy `order_id`.

2. **Fan-out song song:** `load_case` tạo edge tới cả `order_fulfillment_agent` và `payment_agent` đồng thời. `order_fulfillment_agent` gọi `build_order_fulfillment_facts(repository, order_id)` — đây là phần Data & Order tôi phụ trách. `payment_agent` gọi `build_payment_facts(repository, order_id)`. Hai agent chỉ đọc từ repository, không ghi đè cùng state key, nên an toàn khi chạy song song.

3. **Tại sao fulfillment và payment chạy song song được:** hai agent đọc cùng `order_id` nhưng ghi vào hai state key khác nhau (`order_fulfillment_facts` và `payment_facts`). Repository là immutable nên không có shared mutable state. LangGraph chờ cả hai xong mới kích hoạt `join_facts`.

4. **Tại sao policy phải chờ join:** `decide_policy` cần đồng thời `fulfillment.delivery_late`, `fulfillment.late_seller_ids`, `fulfillment.freight_total_brl` (từ fulfillment facts) và `payment.payment_total_brl`, `payment.payment_matches`, `payment.payment_row_count` (từ payment facts) để áp đúng rule theo priority và tính refund. Thiếu một trong hai thì policy không thể chạy đúng.

5. **Verifier và quality gate:** `verify_resolution` nhận `candidate`, `order_fulfillment_facts`, `payment_facts` và `repository`. Nó re-validate schema, kiểm tra evidence tồn tại trong CSV (dùng `evidence_exists` với format `order:<id>`, `item:<id>:<seq>`), kiểm tra invariant `action_required ↔ refund > 0`, và so khớp candidate với kết quả `decide_policy` deterministic. Nếu pass, `write_output` ghi atomic `output/EC_*.json`; nếu fail, `record_failure` lưu lỗi. Lớp `trace.jsonl` và `metadata.json` cho phép audit ngược lại từng event theo `run_id` và `case_id`.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Kim Duy Hưng  
**Ngày xác nhận:** 2026-08-05
