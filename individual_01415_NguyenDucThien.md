# Báo cáo cá nhân - Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | [Điền họ và tên] |
| MSSV | [Điền MSSV] |
| Khóa/Lớp | K3 |
| Vai trò chính | Role 3 - Fulfillment/Delivery |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Fulfillment facts builder | `src/agents/order_fulfillment.py::build_order_fulfillment_facts` | `DataRepository`, `order_id` từ case | `OrderFulfillmentFacts` gồm trạng thái đơn, item, seller, mốc giao hàng, tổng item/freight và late flags | Hoàn thành |
| Logic so sánh timestamp giao hàng | `src/agents/order_fulfillment.py::_after` | Các timestamp ISO từ `olist_orders_dataset.csv` và `olist_order_items_dataset.csv` | Boolean để xác định giao trễ hoặc seller bàn giao trễ | Hoàn thành |
| Seller/logistics attribution | `src/agents/order_fulfillment.py`, tích hợp với `src/agents/policy.py` | `delivered_customer_date`, `estimated_delivery_date`, `delivered_carrier_date`, `shipping_limit_date` | `delivery_late`, `late_seller_ids`; policy dùng để phân biệt `late_delivery_seller` và `late_delivery_logistics` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chuẩn hóa contract dữ liệu fulfillment | `src/schemas.py`, `src/graph.py`, `src/validator.py` | Output fulfillment validate được bằng Pydantic và được truyền qua LangGraph tới policy/verifier |
| Kiểm tra hồi quy trên bộ case chính thức | `tests/test_policy.py`, `tests/test_graph.py` | 50 case đầu vào được resolve và verify; distribution policy và tổng refund có assert cụ thể |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Lấy dữ liệu order và item từ repository theo `order_id` | `src/agents/order_fulfillment.py::build_order_fulfillment_facts` | Tạo danh sách `ItemFact`, `item_ids`, `seller_ids`, `source_refs` cho từng đơn hàng | `pytest -q` |
| Tính tổng tiền hàng và phí vận chuyển bằng `Decimal` | `src/agents/order_fulfillment.py`, `src/data_repository.py::money` | `item_total_brl` và `freight_total_brl` đúng precision 2 chữ số BRL | `tests/test_policy.py` kiểm tra output qua verifier |
| Xác định đơn giao trễ so với ngày dự kiến | `delivery_late = delivered_customer_date > estimated_delivery_date` | Policy có tín hiệu để xử lý late claim | `tests/test_policy.py::test_policy_distribution_and_refund_total` |
| Xác định seller bàn giao trễ | `late_seller_ids`, `_after(carrier_date, shipping_limit_date)` | Nếu carrier nhận hàng sau deadline của item thì seller tương ứng bị quy trách nhiệm | Output có issue `late_delivery_seller` và evidence `seller:<seller_id>` |
| Bàn giao fact bundle vào pipeline A2A | `src/graph.py::order_agent` | `order_fulfillment_facts` được join với `payment_facts`, sau đó policy/verifier sử dụng | `tests/test_graph.py::test_graph_writes_one_valid_output` |

Artifact cụ thể của phần việc là `OrderFulfillmentFacts` cho mỗi case. Fact bundle này là đầu vào bắt buộc để policy quyết định hoàn tiền phí vận chuyển, quy trách nhiệm seller/logistics và sinh evidence liên quan đến order/item/seller.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong khiếu nại giao hàng, chỉ đọc nội dung khách hàng là không đủ để kết luận ai chịu trách nhiệm. Phần Role 3 giải quyết bài toán biến dữ liệu thô từ Olist thành các fulfillment facts có cấu trúc: trạng thái đơn, các item trong đơn, seller liên quan, deadline bàn giao, ngày carrier nhận hàng, ngày khách nhận hàng và ngày giao dự kiến.

### Cách triển khai

Hàm `build_order_fulfillment_facts` nhận `order_id`, đọc order row và các item row từ `DataRepository`. Mỗi item được chuyển thành `ItemFact` gồm `order_item_id`, `seller_id`, `shipping_limit_date`, `price_brl`, `freight_brl`. Tiền được chuyển qua hàm `money()` để dùng `Decimal` thay vì float.

Logic thời gian được gom trong `_after(left, right)`: chỉ trả `True` khi cả hai timestamp tồn tại và `left > right`. Nhờ vậy các trường ngày bị thiếu không làm pipeline crash vì so sánh `None`. Từ đó:

- `delivery_late` cho biết khách nhận hàng sau `order_estimated_delivery_date`.
- `late_seller_ids` gồm các seller có `order_delivered_carrier_date > shipping_limit_date` của item.
- Nếu `delivery_late` đúng và có `late_seller_ids`, policy phân loại `late_delivery_seller`.
- Nếu `delivery_late` đúng nhưng không có seller bàn giao trễ, policy phân loại `late_delivery_logistics`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `repository: DataRepository`, `order_id: str` lấy từ `case.customer_request.claimed_order_id` |
| Output | `OrderFulfillmentFacts` trong `src/schemas.py` |
| Module phụ thuộc | `src/data_repository.py`, `src/schemas.py` |
| Module sử dụng output | `src/graph.py`, `src/agents/policy.py`, `src/validator.py` |
| Điều kiện lỗi cần xử lý | `order_id` không tồn tại sẽ raise `ValueError`; timestamp thiếu được xử lý bằng `_after` trả `False`; order không có item thì danh sách item/seller rỗng và tổng tiền bằng `0.00` |

### Cách xác minh

```bash
python -m pytest -q
```

- **Kết quả mong đợi:** Toàn bộ test pass, 50 case chính thức được resolve và verify; policy distribution đúng 6 nhóm issue; tổng refund bằng `3429.64`.
- **Kết quả thực tế trên máy hiện tại:** Chưa chạy được vì môi trường Python chưa cài `pytest` (`No module named pytest`). Bộ test dùng để xác minh nằm trong `tests/test_policy.py` và `tests/test_graph.py`.
- **Artifact/log:** `output/EC_*.json`, `logging/trace.jsonl`, `logging/metadata.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần phân biệt giao trễ do seller bàn giao muộn với giao trễ do logistics.
- **Các phương án đã cân nhắc:** Chỉ dựa vào `order_status` và `estimated_delivery_date`; hoặc so sánh thêm `order_delivered_carrier_date` với từng `shipping_limit_date` của item.
- **Phương án đã chọn:** So sánh `order_delivered_carrier_date > shipping_limit_date` theo từng item, sau đó gom seller vi phạm vào `late_seller_ids`.
- **Lý do:** Cách này bám đúng dữ liệu nguồn, hỗ trợ đơn nhiều item/nhiều seller và tạo được evidence rõ ràng cho policy. Nếu chỉ nhìn ngày khách nhận hàng thì không biết trách nhiệm thuộc seller hay logistics.
- **Bằng chứng quyết định phù hợp:** `tests/test_policy.py` assert phân phối có 8 case `late_delivery_seller` và 8 case `late_delivery_logistics`; verifier kiểm tra candidate output khớp deterministic policy.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** Khi so sánh timestamp có khả năng gặp trường ngày rỗng hoặc `None`, phép `datetime.fromisoformat()` trực tiếp có thể gây lỗi hoặc tạo kết luận sai. Ngoài ra, khi xác minh lại trên máy hiện tại, lệnh `python -m pytest -q` báo thiếu package `pytest`.
- **Bước tái hiện:** Xử lý các order có ngày giao/carrier/date estimate không đầy đủ trong CSV rồi gọi logic phân loại late.
- **Nguyên nhân gốc:** Dữ liệu Olist có các trạng thái như canceled/unavailable hoặc incomplete delivery, nên không phải order nào cũng có đủ timestamp.
- **Cách xử lý:** Tách helper `_after(left, right)` để chỉ parse và so sánh khi cả hai giá trị tồn tại; nếu thiếu dữ liệu thì trả `False`.
- **Cách xác minh sau khi sửa:** Cài dependency theo `requirements.txt`, sau đó chạy `python -m pytest -q`; 50 case cần đi qua policy và verifier mà không lỗi schema hoặc lỗi so sánh timestamp.
- **Điều học được:** Với dữ liệu vận hành thực tế, timestamp là input cần được guard rõ ràng trước khi dùng để quyết định trách nhiệm.

## 7. Hiểu biết về luồng end-to-end

Luồng hệ thống bắt đầu từ `input/EC_*.json`. `Case Loader` đọc case, validate schema bằng `CaseInput`, lấy `claimed_order_id`, rồi kích hoạt song song `order_fulfillment_agent` và `payment_agent`.

`order_fulfillment_agent` là phần Role 3: đọc dữ liệu order/item/seller từ repository read-only, tạo `OrderFulfillmentFacts` và ghi trace `agent_started`/`agent_completed`. Song song đó, `payment_agent` tạo `PaymentFacts`. Hai fact bundle được join lại trước khi chuyển sang `policy_decision_agent`.

`policy_decision_agent` không để LLM tự quyết định tiền hoặc trách nhiệm. Agent này áp dụng rule `EC_POLICY_V1` theo thứ tự: canceled, unavailable, seller late, logistics late, split payment, unsupported late claim. Với phần delivery, nếu `delivery_late` và có `late_seller_ids` thì trách nhiệm thuộc seller; nếu `delivery_late` nhưng không có seller late thì trách nhiệm thuộc logistics provider.

Sau khi policy sinh `ResolutionOutput`, `verifier_agent` kiểm tra lại schema, evidence, tiền hoàn, `case_status` và so khớp output với deterministic policy. Chỉ khi verifier pass thì writer mới ghi `output/EC_*.json`; nếu fail thì ghi lỗi vào trace.

Việc dùng cùng 50 case chính thức cho regression giúp so sánh ổn định giữa các lần sửa code. Các artifact dùng để đánh giá gồm output JSON, `logging/trace.jsonl`, `logging/metadata.json`, kết quả `pytest`, policy distribution và tổng refund.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Điền họ và tên]  
**Ngày xác nhận:** 2026-08-05
