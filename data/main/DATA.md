# Bản thiết kế bộ dữ liệu: Vận hành thương mại điện tử ngành thời trang

## 1. Tổng quan bộ dữ liệu

* **Bối cảnh kinh doanh:** Mô phỏng hoạt động của một doanh nghiệp thương mại điện tử ngành thời trang tại Việt Nam.
* **Khoảng thời gian:** * Huấn luyện: 04/07/2012 đến 31/12/2022
    * Kiểm thử: 01/01/2023 đến 01/07/2024
* **Phân chia dữ liệu:** `sales_train.csv` so với `sales_test.csv`
* **Nhóm dữ liệu:**
    * **Master:** `products.csv`, `customers.csv`, `promotions.csv`, `geography.csv`
    * **Giao dịch:** `orders.csv`, `order_items.csv`, `payments.csv`, `shipments.csv`, `returns.csv`, `reviews.csv`
    * **Phân tích:** `sales.csv`, `sample_submission.csv`
    * **Vận hành:** `inventory.csv`, `web_traffic.csv`

---

## 2. Lược đồ bảng

### `products.csv`
* **Mô tả:** Danh mục sản phẩm.
* **Độ chi tiết:** 1 dòng = 1 sản phẩm.
* **Khóa chính:** `product_id`
* **Khóa ngoại:** Không có.

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `product_id` | int | Khóa chính |
| `product_name` | str | Tên sản phẩm |
| `category` | str | Danh mục sản phẩm |
| `segment` | str | Phân khúc thị trường |
| `size` | str | Kích cỡ sản phẩm |
| `color` | str | Nhãn màu sản phẩm |
| `price` | float | Giá bán lẻ |
| `cogs` | float | Giá vốn hàng bán. Ràng buộc: `cogs < price` |

### `customers.csv`
* **Mô tả:** Thông tin khách hàng.
* **Độ chi tiết:** 1 dòng = 1 khách hàng.
* **Khóa chính:** `customer_id`
* **Khóa ngoại:** `zip` -> `geography.csv`

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `customer_id` | int | Khóa chính |
| `zip` | int | Mã bưu chính (FK) |
| `city` | str | Thành phố của khách hàng |
| `signup_date` | date | Ngày đăng ký tài khoản |
| `gender` | str | Giới tính (có thể null) |
| `age_group` | str | Nhóm tuổi (có thể null) |
| `acquisition_channel` | str | Kênh marketing (có thể null) |

### `promotions.csv`
* **Mô tả:** Các chiến dịch khuyến mãi.
* **Độ chi tiết:** 1 dòng = 1 chiến dịch.
* **Khóa chính:** `promo_id`
* **Khóa ngoại:** Không có.

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `promo_id` | str | Khóa chính |
| `promo_name` | str | Tên chiến dịch kèm năm |
| `promo_type` | str | Loại giảm giá (theo phần trăm hoặc số tiền cố định) |
| `discount_value` | float | Giá trị giảm giá |
| `start_date` | date | Ngày bắt đầu chiến dịch |
| `end_date` | date | Ngày kết thúc chiến dịch |
| `applicable_category` | str | Danh mục áp dụng (null nếu áp dụng cho tất cả) |
| `promo_channel` | str | Kênh phân phối áp dụng (có thể null) |
| `stackable_flag` | int | Cờ cho phép áp dụng đồng thời nhiều khuyến mãi |
| `min_order_value` | float | Giá trị đơn hàng tối thiểu (có thể null) |

### `geography.csv`
* **Mô tả:** Mã bưu chính theo khu vực.
* **Độ chi tiết:** 1 dòng = 1 mã bưu chính.
* **Khóa chính:** `zip`
* **Khóa ngoại:** Không có.

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `zip` | int | Khóa chính |
| `city` | str | Tên thành phố |
| `region` | str | Vùng địa lý |
| `district` | str | Tên quận/huyện |

### `orders.csv`
* **Mô tả:** Thông tin đơn hàng.
* **Độ chi tiết:** 1 dòng = 1 đơn hàng.
* **Khóa chính:** `order_id`
* **Khóa ngoại:** `customer_id` -> `customers.csv`, `zip` -> `geography.csv`

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `order_id` | int | Khóa chính |
| `order_date` | date | Ngày đặt hàng |
| `customer_id` | int | FK tới `customers.csv` |
| `zip` | int | Mã bưu chính giao hàng (FK tới `geography.csv`) |
| `order_status` | str | Trạng thái xử lý đơn hàng |
| `payment_method` | str | Phương thức thanh toán đã dùng |
| `device_type` | str | Thiết bị khách hàng sử dụng |
| `order_source` | str | Kênh marketing dẫn đến đơn hàng |

### `order_items.csv`
* **Mô tả:** Chi tiết sản phẩm trong từng đơn hàng.
* **Độ chi tiết:** 1 dòng = 1 dòng hàng sản phẩm trong một đơn hàng.
* **Khóa chính:** Không được định nghĩa rõ ràng (ngầm định là khóa ghép `order_id` + `product_id`).
* **Khóa ngoại:** `order_id` -> `orders.csv`, `product_id` -> `products.csv`, `promo_id` / `promo_id_2` -> `promotions.csv`

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `order_id` | int | FK tới `orders.csv` |
| `product_id` | int | FK tới `products.csv` |
| `quantity` | int | Số lượng đặt mua |
| `unit_price` | float | Đơn giá |
| `discount_amount` | float | Tổng số tiền giảm giá cho dòng này |
| `promo_id` | str | FK tới `promotions.csv` (có thể null) |
| `promo_id_2` | str | FK tới `promotions.csv` (khuyến mãi thứ hai) (có thể null) |

### `payments.csv`
* **Mô tả:** Thông tin thanh toán.
* **Độ chi tiết:** 1 dòng = 1 khoản thanh toán.
* **Khóa chính:** Không được định nghĩa rõ ràng (ngầm định là `order_id`).
* **Khóa ngoại:** `order_id` -> `orders.csv`

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `order_id` | int | FK tới `orders.csv` (quan hệ 1:1) |
| `payment_method` | str | Phương thức thanh toán |
| `payment_value` | float | Tổng giá trị thanh toán của đơn hàng |
| `installments` | int | Số kỳ trả góp |

### `shipments.csv`
* **Mô tả:** Thông tin vận chuyển.
* **Độ chi tiết:** 1 dòng = 1 lần giao hàng.
* **Khóa chính:** Không được định nghĩa rõ ràng (ngầm định là `order_id`).
* **Khóa ngoại:** `order_id` -> `orders.csv`

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `order_id` | int | FK tới `orders.csv` |
| `ship_date` | date | Ngày gửi hàng |
| `delivery_date` | date | Ngày giao cho khách hàng |
| `shipping_fee` | float | Phí vận chuyển. Ràng buộc: bằng 0 nếu được miễn phí vận chuyển |

### `returns.csv`
* **Mô tả:** Sản phẩm được trả lại.
* **Độ chi tiết:** 1 dòng = 1 trường hợp trả lại của một mặt hàng.
* **Khóa chính:** `return_id`
* **Khóa ngoại:** `order_id` -> `orders.csv`, `product_id` -> `products.csv`

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `return_id` | str | Khóa chính |
| `order_id` | int | FK tới `orders.csv` |
| `product_id` | int | FK tới `products.csv` |
| `return_date` | date | Ngày trả hàng |
| `return_reason` | str | Lý do trả hàng |
| `return_quantity` | int | Số lượng trả |
| `refund_amount` | float | Số tiền hoàn trả |

### `reviews.csv`
* **Mô tả:** Đánh giá sản phẩm sau khi giao hàng.
* **Độ chi tiết:** 1 dòng = 1 đánh giá.
* **Khóa chính:** `review_id`
* **Khóa ngoại:** `order_id` -> `orders.csv`, `product_id` -> `products.csv`, `customer_id` -> `customers.csv`

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `review_id` | str | Khóa chính |
| `order_id` | int | FK tới `orders.csv` |
| `product_id` | int | FK tới `products.csv` |
| `customer_id` | int | FK tới `customers.csv` |
| `review_date` | date | Ngày gửi đánh giá |
| `rating` | int | Điểm đánh giá từ 1 đến 5 |
| `review_title` | str | Tiêu đề đánh giá |

### `sales.csv` (và `sample_submission.csv`)
* **Mô tả:** Dữ liệu doanh thu / định dạng đầu ra.
* **Độ chi tiết:** 1 dòng = 1 ngày.
* **Khóa chính:** `Date` (ngầm định).
* **Khóa ngoại:** Không có.

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `Date` | date | Ngày đặt hàng |
| `Revenue` | float | Doanh thu thuần |
| `COGS` | float | Tổng giá vốn hàng bán |

### `inventory.csv`
* **Mô tả:** Ảnh chụp tồn kho vào cuối tháng.
* **Độ chi tiết:** 1 dòng = 1 sản phẩm theo từng tháng.
* **Khóa chính:** Không được định nghĩa rõ ràng (ngầm định là khóa ghép `snapshot_date` + `product_id`).
* **Khóa ngoại:** `product_id` -> `products.csv`

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `snapshot_date` | date | Ngày chụp dữ liệu (cuối tháng) |
| `product_id` | int | FK tới `products.csv` |
| `stock_on_hand` | int | Tồn kho cuối tháng |
| `units_received` | int | Số lượng nhập trong tháng |
| `units_sold` | int | Số lượng bán ra trong tháng |
| `stockout_days` | int | Số ngày hết hàng trong tháng |
| `days_of_supply` | float | Số ngày cung ứng hiện có |
| `fill_rate` | float | Tỷ lệ đáp ứng đơn hàng từ tồn kho |
| `stockout_flag` | int | Cờ hết hàng |
| `overstock_flag` | int | Cờ tồn kho dư |
| `reorder_flag` | int | Cờ đặt hàng lại sớm |
| `sell_through_rate` | float | Tỷ lệ bán được trên lượng hàng sẵn có |
| `product_name` | str | Tên sản phẩm |
| `category` | str | Danh mục sản phẩm |
| `segment` | str | Phân khúc sản phẩm |
| `year` | int | Năm trích xuất từ `snapshot_date` |
| `month` | int | Tháng trích xuất từ `snapshot_date` |

### `web_traffic.csv`
* **Mô tả:** Lưu lượng truy cập website hằng ngày.
* **Độ chi tiết:** 1 dòng = 1 ngày.
* **Khóa chính:** Không được định nghĩa rõ ràng (ngầm định là `date`).
* **Khóa ngoại:** Không có.

| Cột | Kiểu | Mô tả & Ràng buộc |
| :--- | :--- | :--- |
| `date` | date | Ngày ghi nhận lưu lượng |
| `sessions` | int | Tổng số phiên trong ngày |
| `unique_visitors` | int | Số khách truy cập duy nhất |
| `page_views` | int | Tổng số lượt xem trang |
| `bounce_rate` | float | Tỷ lệ thoát của phiên chỉ xem một trang |
| `avg_session_duration_sec` | float | Thời lượng phiên trung bình tính bằng giây |
| `traffic_source` | str | Nguồn chính tạo ra lưu lượng trong ngày |

---

## 3. Mối quan hệ

* **`orders` <-> `payments`**: 1 : 1 (bắt buộc).
* **`orders` <-> `shipments`**: 1 : 0 hoặc 1 (tùy chọn; chỉ tồn tại nếu trạng thái là shipped, delivered, hoặc returned).
* **`orders` <-> `returns`**: 1 : 0 hoặc nhiều (tùy chọn; chỉ tồn tại nếu trạng thái là returned).
* **`orders` <-> `reviews`**: 1 : 0 hoặc nhiều (tùy chọn; chỉ tồn tại nếu trạng thái là delivered, khoảng 20% thời gian).
* **`order_items` <-> `promotions`**: nhiều : 0 hoặc 1 (tùy chọn; `promo_id` có thể là null).
* **`products` <-> `inventory`**: 1 : nhiều (1 dòng cho mỗi sản phẩm mỗi tháng).

---

## 4. Logic kinh doanh & quy tắc

* **Ràng buộc giá:** `cogs` phải luôn nhỏ hơn nghiêm ngặt `price` đối với tất cả sản phẩm.
* **Công thức khuyến mãi:**
    * **Theo phần trăm:** `discount_amount = quantity * unit_price * (discount_value / 100)`
    * **Số tiền cố định:** `discount_amount = quantity * discount_value`
* **Ràng buộc vận hành:**
    * `applicable_category` trong `promotions.csv` là `NULL` nếu khuyến mãi áp dụng cho tất cả danh mục.
    * `shipping_fee` trong `shipments.csv` bằng `0` nếu đơn hàng đủ điều kiện miễn phí vận chuyển.

---

## 5. Chỉ số suy diễn

* **Biên lợi nhuận gộp:** `(price - cogs) / price` (cần `products.csv`) .
* **Tỷ lệ trả hàng:** Số bản ghi trong `returns.csv` chia cho số dòng trong `order_items.csv` (cần nối `returns.csv` với `products.csv` theo `product_id` để lọc theo thuộc tính sản phẩm như size, và so sánh với `order_items.csv`) .
* **Khoảng cách giữa các đơn hàng:** Số ngày trung vị giữa hai lần mua liên tiếp của cùng một khách hàng (cần `orders.csv`) .
* **Số đơn hàng trung bình mỗi khách hàng:** Tổng số đơn hàng / Số khách hàng trong một nhóm cụ thể, chẳng hạn một nhóm tuổi (cần `orders.csv`, `customers.csv`) .
* **Tỷ lệ áp dụng khuyến mãi:** Tỷ lệ phần trăm các dòng trong `order_items.csv` có áp dụng khuyến mãi (tức là `promo_id` không null) .
* **Tính số tiền giảm giá** (cần `promotions.csv`, `order_items.csv`):
  * *Khuyến mãi theo phần trăm:* `discount_amount = quantity × unit_price × (discount_value/100)`
  * *Khuyến mãi số tiền cố định:* `discount_amount = quantity × discount_value`

---

## 6. Rủi ro chất lượng dữ liệu

* **Các cột có thể null:**
    * `customers.csv`: `gender`, `age_group`, `acquisition_channel`.
    * `promotions.csv`: `applicable_category`, `promo_channel`, `min_order_value`.
    * `order_items.csv`: `promo_id`, `promo_id_2`.
* **Thiếu quan hệ:** Không có liên kết trực tiếp giữa `web_traffic.csv` và dữ liệu giao dịch. Hai nguồn này phải được nối theo ngày hoặc bằng cách ánh xạ `traffic_source` sang `order_source`.

---

## 7. Cơ hội phân tích

Các phân tích được hỗ trợ ánh xạ trực tiếp với tiêu chí đánh giá cho EDA (Mô tả -> Đề xuất):

* **Hành vi khách hàng:** Khoảng cách giữa các đơn hàng, số đơn trung bình theo nhóm tuổi.
* **Hiệu suất sản phẩm:** Biên lợi nhuận gộp theo phân khúc, tỷ lệ trả hàng theo size sản phẩm, lý do trả hàng.
* **Marketing:** Tỷ lệ thoát website theo nguồn lưu lượng, đánh giá tỷ lệ áp dụng khuyến mãi.
* **Vận hành:** Tương quan giữa số kỳ trả góp và giá trị đơn hàng, ánh xạ các đơn bị hủy theo phương thức thanh toán, theo dõi doanh thu theo khu vực địa lý.

---

## 8. Định nghĩa tác vụ học máy

* **Biến mục tiêu:** Revenue (dự đoán các bộ ba `Date`, `Revenue`, `COGS` duy nhất theo ngày cho giai đoạn kiểm thử).
* **Đặc trưng đầu vào:** Phải được thiết kế nghiêm ngặt từ các tệp được cung cấp. Việc sử dụng `Revenue` hoặc `COGS` từ giai đoạn kiểm thử làm đặc trưng là bị cấm tuyệt đối và sẽ dẫn đến bị loại.
* **Phụ thuộc thời gian:** Dự báo Revenue theo ngày cho giai đoạn 01/01/2023 đến 01/07/2024. Thứ tự thời gian chính xác trong tệp nộp bài phải được giữ nguyên tuyệt đối, không được xáo trộn.
* **Thước đo đánh giá:** MAE, RMSE và $R^2$ (Hệ số xác định).

---

## 9. Giới hạn

* **Điều cấm:** Nghiêm cấm sử dụng bất kỳ bộ dữ liệu bên ngoài nào.
* **Khía cạnh dữ liệu bị thiếu:** Các giá trị mục tiêu của tập kiểm thử (`sales_test.csv`) được cố ý giữ lại.
* **Giới hạn suy luận:** Khóa chính cho các bảng nghiệp vụ/giao dịch chi tiết (`order_items`, `payments`, `shipments`, `inventory`, `web_traffic`) không được định nghĩa rõ ràng trong tài liệu nguồn và cần chiến lược khóa ghép.

---

## 10. Kiểm tra và xác minh sự thật nghiêm ngặt

* **Nguồn trích dẫn rõ ràng:** Mọi tên cột, kiểu dữ liệu, quan hệ khóa ngoại và công thức liệt kê ở trên đều được hỗ trợ trực tiếp bởi Bảng 1 và 2, cùng với Mục 1 của các trích đoạn tài liệu được cung cấp. 
* **Giới hạn nhiệm vụ:** Các ràng buộc ML, biến mục tiêu và tiêu chí đánh giá đều được trích trực tiếp từ Mục 2.
* **Tránh suy đoán:** Không tự suy diễn khóa chính cho các bảng không có định nghĩa rõ ràng (ví dụ: `order_items`, `payments`, `shipments`, `web_traffic`). Các trường nullable được ghi nhận đúng như mô tả trong phần tổng quan bộ dữ liệu nguồn.