# Member Role Report — Day 9: Multi-Agent E-commerce Dispute Resolution

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Vũ Minh Đức |
| MSSV | 2A202602006 |
| Khóa/Lớp | K3 |
| Vai trò chính | Thành viên 4 — Payment/Finance |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Chuẩn hóa số tiền BRL | Logic finance tại `src/data_repository.py`; `money` | Giá trị tiền dạng chuỗi từ CSV Olist | `Decimal` được lượng tử hóa về 2 chữ số bằng `ROUND_HALF_UP` | Hoàn thành |
| Payment facts builder | `src/agents/payment.py`; `build_payment_facts` | `DataRepository`, `order_id` | `PaymentFacts` gồm payment IDs, số dòng, tổng tiền, reconciliation delta, kết quả khớp và source refs | Hoàn thành |
| Decimal totals | `build_payment_facts`; `payment_total`, `expected_total` | Các dòng payment và item của cùng order | Tổng payment và tổng kỳ vọng `item + freight`, không dùng `float` | Hoàn thành |
| Reconciliation | `build_payment_facts`; `delta`, `payment_matches` | `payment_total`, `expected_total` | Sai lệch tuyệt đối và cờ khớp với ngưỡng `<= 0.10 BRL` | Hoàn thành |
| Payment Agent handoff | `src/graph.py`; node `payment_agent` | `case_id`, `order_id`, repository read-only | Ghi `payment_facts` vào `CaseGraphState`, tạo trace và bàn giao cho policy/verifier | Hoàn thành |
| Contract PaymentFacts | `src/schemas.py`; `PaymentFacts` | Facts do payment builder tạo | Pydantic model strict, giới hạn độ dài danh sách và từ chối field ngoài contract | Hoàn thành |

Vai trò của tôi là sở hữu logic tài chính và đối soát thanh toán: chuẩn hóa mọi giá trị tiền bằng `Decimal`, cộng đúng các payment row, tính tổng kỳ vọng từ giá hàng cộng phí vận chuyển, rồi bàn giao một `PaymentFacts` có thể kiểm chứng cho các agent phía sau. Tôi không sở hữu logic trạng thái giao hàng, xác định seller giao muộn, bảng policy cuối cùng hay independent verifier.

> **Lưu ý về tên file:** trong phiên bản repository hiện tại và toàn bộ lịch sử Git đang có không tồn tại file `finance.py` độc lập. Logic finance dùng chung thực tế nằm ở `src/data_repository.py::money`; logic Payment Agent nằm ở `src/agents/payment.py`. Báo cáo dùng đúng đường dẫn hiện hữu để bảo đảm có thể truy vết.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thống nhất cách hiểu `payment_value` | Data/Order và Policy/QA | Xác nhận đây là giá trị của từng payment row, không nhân với `payment_installments` |
| Chốt ngưỡng reconciliation | Policy/QA | Dùng `abs(payment_total - item_total - freight_total) <= Decimal("0.10")` |
| Đồng bộ state contract | Lead/Integrator | Payment Agent chỉ ghi `payment_facts`, không ghi đè `order_fulfillment_facts` |
| Chuẩn hóa payment evidence | Policy/QA và Evidence resolver | Thống nhất `payment:<order_id>:<payment_sequential>` và entity ID `<order_id>:<payment_sequential>` |
| Review financial resolution | Policy/QA | `payment_total_brl` là nguồn cho full refund ở các order canceled/unavailable đã thanh toán |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Đọc toàn bộ payment rows theo order | `DataRepository.payments`; `build_payment_facts` | Không bỏ sót split payment; báo lỗi rõ khi order không có payment row | Kiểm tra `payment_row_count` và `payment_ids` trong `PaymentFacts` |
| Tính tổng payment chính xác | `payment_total = sum(..., Decimal("0.00"))` | Tổng tiền được cộng bằng `Decimal`, giữ precision tiền tệ | Đối chiếu `payment_total_brl` với các `payment_value` gốc |
| Tính tổng kỳ vọng | `expected_total = sum(price + freight)` | Tổng kỳ vọng bằng toàn bộ item price cộng freight của cùng order | Đối chiếu với `item_total_brl + freight_total_brl` từ fulfillment facts |
| Đối soát thanh toán | `delta`; `payment_matches` | Trả sai lệch tuyệt đối và boolean theo ngưỡng 0.10 BRL | Kiểm tra `reconciliation_delta_brl` và invariant `payment_matches == (delta <= 0.10)` |
| Nhận diện split payment hợp lệ | `payment_row_count`; `src/agents/policy.py` | Cho phép policy phân biệt order có từ 2 payment row và đã reconciliation | `tests/test_policy.py::test_policy_distribution_and_refund_total` kỳ vọng 9 case `valid_split_payment` |
| Bàn giao evidence có nguồn gốc | `source_refs` trong `PaymentFacts` | Mỗi payment row có một evidence ID deterministic | `src/evidence.py` kiểm tra format và sự tồn tại trong repository |

Output trực tiếp của phần Payment/Finance là một `PaymentFacts` cho mỗi case, trong đó các tổng tiền và kết quả reconciliation được tính deterministic. Các facts này được policy dùng để xác định full refund cho order canceled/unavailable đã thanh toán, nhận diện split payment hợp lệ và bác bỏ late claim không có cơ sở khi payment vẫn khớp.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu Olist cho phép một order có nhiều payment row và nhiều item. Vì vậy không thể chỉ lấy payment row đầu tiên, cũng không thể coi `payment_installments` là hệ số nhân của `payment_value`. Payment Agent phải tổng hợp đúng toàn bộ giao dịch, so sánh với tổng giá hàng cộng phí vận chuyển và giữ độ chính xác tiền tệ trong mọi bước.

### Cách triển khai

`build_payment_facts` nhận `DataRepository` và `order_id`. Hàm gọi `repository.payments(order_id)` để lấy các dòng payment đã được index, đồng thời gọi `repository.items(order_id)` để lấy các item thuộc đúng đơn hàng.

Tổng thanh toán được tính bằng:

```python
payment_total = sum(
    (money(row["payment_value"]) for row in rows),
    Decimal("0.00"),
)
```

Giá trị kỳ vọng được tính độc lập từ dữ liệu item:

```python
expected_total = sum(
    (money(row["price"]) + money(row["freight_value"]) for row in item_rows),
    Decimal("0.00"),
)
```

Sau đó agent tính `delta = abs(payment_total - expected_total)` và gán `payment_matches = delta <= Decimal("0.10")`. So sánh bao gồm đúng dấu bằng, vì sai lệch 0.10 BRL vẫn nằm trong ngưỡng cho phép của đề bài.

Hàm `money()` tại `src/data_repository.py` chuyển giá trị CSV qua `Decimal(str(value))`, rồi `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. Quyết định này tránh sai số nhị phân của `float` và bảo đảm các giá trị tiền luôn ở precision hai chữ số trước khi cộng.

Mỗi payment được định danh bằng `<order_id>:<payment_sequential>`. `source_refs` thêm prefix `payment:` để tạo evidence ID có thể được `src/evidence.py` đối chiếu trực tiếp với CSV. Payment Agent không tự đưa ra kết luận refund; agent chỉ cung cấp facts tài chính authoritative cho `policy_decision_agent`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `DataRepository` read-only và `order_id` lấy từ `CaseInput.customer_request.claimed_order_id` |
| Dữ liệu đọc | `olist_order_payments_dataset.csv` và `olist_order_items_dataset.csv` thông qua repository |
| Output | `PaymentFacts`: `order_id`, `payment_ids`, `payment_row_count`, `payment_total_brl`, `reconciliation_delta_brl`, `payment_matches`, `source_refs` |
| State handoff | Node `payment_agent` ghi output vào `state["payment_facts"]` |
| Module tiêu thụ | `src/agents/policy.py::decide_policy` và `src/validator.py::verify_resolution` |
| Điều kiện lỗi | Order không có payment row: `ValueError("Order has no payment rows: ...")`; dữ liệu tiền không hợp lệ: chuyển đổi `Decimal` thất bại |

### Cách xác minh

```bash
# Chạy toàn bộ test suite
.venv/bin/python -m pytest -q

# Kiểm tra policy, split payment và tổng refund
.venv/bin/python -m pytest tests/test_policy.py -v

# Chạy batch và audit artifact
.venv/bin/python -m src.main --max-concurrency 4
.venv/bin/python -m src.main --audit-only
```

- **Kết quả mong đợi:** toàn bộ 50 case qua verifier; phân bố gồm 9 case `valid_split_payment`; tổng refund toàn batch là 3,429.64 BRL.
- **Bằng chứng hiện có:** repository có đủ `output/EC_001.json` đến `output/EC_050.json`; `tests/test_policy.py` chứa oracle cho phân bố 8/8/8/8/9/9 và tổng refund 3,429.64 BRL.
- **Giới hạn kiểm tra tại máy hiện tại:** lệnh test chưa chạy lại được vì môi trường hiện tại không nhận diện executable `python`. Do đó báo cáo không khẳng định một lượt test mới vừa pass; các kỳ vọng trên được đối chiếu từ source code, test oracle và artifact có sẵn.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** các phép tính payment ảnh hưởng trực tiếp đến quyết định hoàn tiền. Dùng `float` có thể tạo sai số như `0.1 + 0.2 != 0.3`, đặc biệt khi cộng nhiều payment row và so sánh sát ngưỡng 0.10 BRL.
- **Các phương án đã cân nhắc:** (1) dùng `float` và `round` ở cuối; (2) chuyển tiền sang số nguyên cent; (3) dùng `Decimal`, chuẩn hóa từng giá trị về 0.01 BRL rồi mới cộng.
- **Phương án đã chọn:** dùng `Decimal` và hàm `money()` với `ROUND_HALF_UP`; khởi tạo `sum` bằng `Decimal("0.00")`.
- **Lý do:** biểu diễn thập phân chính xác, code dễ đọc, tương thích trực tiếp với Pydantic schema và tránh trộn `float` với `Decimal`.
- **Bằng chứng quyết định phù hợp:** `payment_total_brl`, `reconciliation_delta_brl` và các giá trị trong `FinancialResolution` đều dùng `Decimal`; policy có thể so sánh ngưỡng bằng `Decimal("0.10")` một cách deterministic.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** split payment có nguy cơ bị tính quá cao nếu lấy `payment_value * payment_installments`, hoặc bị tính thiếu nếu chỉ đọc dòng payment đầu tiên.
- **Bước tái hiện:** chọn một order có từ hai payment row; so sánh tổng `payment_value` của tất cả dòng với kết quả chỉ lấy dòng đầu hoặc nhân thêm số installment.
- **Nguyên nhân gốc:** hiểu sai ý nghĩa cột `payment_installments`. Trong Olist, `payment_value` đã là giá trị của payment row; installments chỉ mô tả số kỳ trả góp, không phải số lượng giao dịch cần nhân.
- **Cách xử lý:** cộng đúng một lần `payment_value` cho mỗi payment row; dùng `payment_row_count = len(rows)` để mô tả split payment; không sử dụng `payment_installments` trong phép tính tổng.
- **Cách xác minh sau khi sửa:** policy nhận diện split payment bằng điều kiện `payment_row_count >= 2` kết hợp `payment_matches`; test oracle kỳ vọng đúng 9 case `valid_split_payment`.
- **Điều học được:** trước khi viết phép tính tài chính cần xác định rõ grain của dữ liệu; tên cột liên quan trả góp không đồng nghĩa với hệ số nhân số tiền.

## 7. Hiểu biết về luồng end-to-end

1. `src/main.py` nạp `DataRepository` một lần rồi đưa repository read-only vào graph. Với mỗi `input/EC_*.json`, node `load_case` validate `CaseInput`, lấy `case_id` và `claimed_order_id`.

2. Graph fan-out từ `load_case` sang `order_fulfillment_agent` và `payment_agent`. Phần tôi phụ trách đọc payment rows và item rows của order, tính Decimal totals, reconciliation delta, payment IDs và source refs, rồi trả state update `payment_facts`.

3. Hai agent domain chạy song song vì cùng chỉ đọc repository và ghi hai key khác nhau. `join_facts` chỉ hoàn tất khi cả `order_fulfillment_facts` và `payment_facts` đã sẵn sàng.

4. `policy_decision_agent` dùng `payment_total_brl` để xác định order canceled/unavailable đã thanh toán và mức full refund; dùng `payment_row_count` cùng `payment_matches` để nhận diện split payment hợp lệ; đồng thời kết hợp facts giao hàng để áp rule đúng thứ tự ưu tiên.

5. `verifier_agent` validate lại `PaymentFacts`, kiểm tra evidence tồn tại, kiểm tra invariant tài chính và so candidate với policy deterministic. Chỉ khi verifier pass thì `write_output` mới ghi JSON atomic; nếu fail, graph route sang `record_failure`.

6. `trace.jsonl` ghi các sự kiện bắt đầu/kết thúc Payment Agent cùng `source_refs`; `metadata.json` ghi thống kê batch. Nhờ vậy có thể truy vết từ kết luận tài chính về đúng payment rows nguồn.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Minh Đức  
**Ngày xác nhận:** 2026-08-05
