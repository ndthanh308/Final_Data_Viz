# Dataset Blueprint: E-Commerce Fashion Operations

## 1. Dataset Overview

* **Business Context:** Simulates the operations of an e-commerce fashion business in Vietnam.
* **Time Range:** * Training: 04/07/2012 to 31/12/2022
    * Testing: 01/01/2023 to 01/07/2024
* **Data Split:** `sales_train.csv` vs `sales_test.csv`
* **Data Domains:**
    * **Master:** `products.csv`, `customers.csv`, `promotions.csv`, `geography.csv`
    * **Transaction:** `orders.csv`, `order_items.csv`, `payments.csv`, `shipments.csv`, `returns.csv`, `reviews.csv`
    * **Analytical:** `sales.csv`, `sample_submission.csv`
    * **Operational:** `inventory.csv`, `web_traffic.csv`

---

## 2. Table Schema

### `products.csv`
* **Description:** Product catalog.
* **Grain:** 1 row = 1 product.
* **Primary Key:** `product_id`
* **Foreign Keys:** None.

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `product_id` | int | Primary key |
| `product_name` | str | Product name |
| `category` | str | Product category |
| `segment` | str | Market segment |
| `size` | str | Product size |
| `color` | str | Product color label |
| `price` | float | Retail price |
| `cogs` | float | Cost of goods sold. Constraint: `cogs < price` |

### `customers.csv`
* **Description:** Customer information.
* **Grain:** 1 row = 1 customer.
* **Primary Key:** `customer_id`
* **Foreign Keys:** `zip` -> `geography.csv`

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `customer_id` | int | Primary key |
| `zip` | int | Postal code (FK) |
| `city` | str | Customer's city |
| `signup_date` | date | Account registration date |
| `gender` | str | Gender (Nullable) |
| `age_group` | str | Age group (Nullable) |
| `acquisition_channel` | str | Marketing channel (Nullable) |

### `promotions.csv`
* **Description:** Promotional campaigns.
* **Grain:** 1 row = 1 campaign.
* **Primary Key:** `promo_id`
* **Foreign Keys:** None.

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `promo_id` | str | Primary key |
| `promo_name` | str | Campaign name with year |
| `promo_type` | str | Discount type (percentage or fixed amount) |
| `discount_value` | float | Discount value |
| `start_date` | date | Campaign start date |
| `end_date` | date | Campaign end date |
| `applicable_category` | str | Applicable category (Null if applicable to all) |
| `promo_channel` | str | Applicable distribution channel (Nullable) |
| `stackable_flag` | int | Flag for allowing simultaneous promotions |
| `min_order_value` | float | Minimum order value (Nullable) |

### `geography.csv`
* **Description:** Regional postal codes.
* **Grain:** 1 row = 1 postal code.
* **Primary Key:** `zip`
* **Foreign Keys:** None.

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `zip` | int | Primary key |
| `city` | str | City name |
| `region` | str | Geographic region |
| `district` | str | District/County name |

### `orders.csv`
* **Description:** Order information.
* **Grain:** 1 row = 1 order.
* **Primary Key:** `order_id`
* **Foreign Keys:** `customer_id` -> `customers.csv`, `zip` -> `geography.csv`

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `order_id` | int | Primary key |
| `order_date` | date | Order date |
| `customer_id` | int | FK to `customers.csv` |
| `zip` | int | Delivery postal code (FK to `geography.csv`) |
| `order_status` | str | Order processing status |
| `payment_method` | str | Payment method used |
| `device_type` | str | Device used by customer |
| `order_source` | str | Marketing channel leading to order |

### `order_items.csv`
* **Description:** Detail of products in each order.
* **Grain:** 1 row = 1 product line item in an order.
* **Primary Key:** Not explicitly defined (Implicitly composite `order_id` + `product_id`).
* **Foreign Keys:** `order_id` -> `orders.csv`, `product_id` -> `products.csv`, `promo_id` / `promo_id_2` -> `promotions.csv`

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `order_id` | int | FK to `orders.csv` |
| `product_id` | int | FK to `products.csv` |
| `quantity` | int | Quantity ordered |
| `unit_price` | float | Unit price |
| `discount_amount` | float | Total discount amount for this line |
| `promo_id` | str | FK to `promotions.csv` (Nullable) |
| `promo_id_2` | str | FK to `promotions.csv` (second promo) (Nullable) |

### `payments.csv`
* **Description:** Payment information.
* **Grain:** 1 row = 1 payment.
* **Primary Key:** Not explicitly defined (Implicitly `order_id`).
* **Foreign Keys:** `order_id` -> `orders.csv`

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `order_id` | int | FK to `orders.csv` (1:1 relationship) |
| `payment_method` | str | Payment method |
| `payment_value` | float | Total payment value of order |
| `installments` | int | Number of installment periods |

### `shipments.csv`
* **Description:** Shipping information.
* **Grain:** 1 row = 1 shipment.
* **Primary Key:** Not explicitly defined (Implicitly `order_id`).
* **Foreign Keys:** `order_id` -> `orders.csv`

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `order_id` | int | FK to `orders.csv` |
| `ship_date` | date | Shipping date |
| `delivery_date` | date | Date delivered to customer |
| `shipping_fee` | float | Shipping fee. Constraint: 0 if free shipping |

### `returns.csv`
* **Description:** Returned products.
* **Grain:** 1 row = 1 returned item instance.
* **Primary Key:** `return_id`
* **Foreign Keys:** `order_id` -> `orders.csv`, `product_id` -> `products.csv`

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `return_id` | str | Primary key |
| `order_id` | int | FK to `orders.csv` |
| `product_id` | int | FK to `products.csv` |
| `return_date` | date | Return date |
| `return_reason` | str | Reason for return |
| `return_quantity` | int | Quantity returned |
| `refund_amount` | float | Refund amount |

### `reviews.csv`
* **Description:** Product reviews post-delivery.
* **Grain:** 1 row = 1 review.
* **Primary Key:** `review_id`
* **Foreign Keys:** `order_id` -> `orders.csv`, `product_id` -> `products.csv`, `customer_id` -> `customers.csv`

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `review_id` | str | Primary key |
| `order_id` | int | FK to `orders.csv` |
| `product_id` | int | FK to `products.csv` |
| `customer_id` | int | FK to `customers.csv` |
| `review_date` | date | Review submission date |
| `rating` | int | Rating from 1 to 5 |
| `review_title` | str | Review title |

### `sales.csv` (and `sample_submission.csv`)
* **Description:** Revenue data / Target format.
* **Grain:** 1 row = 1 Date.
* **Primary Key:** `Date` (Implicit).
* **Foreign Keys:** None.

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `Date` | date | Order date |
| `Revenue` | float | Net revenue |
| `COGS` | float | Total cost of goods sold |

### `inventory.csv`
* **Description:** End-of-month inventory snapshots.
* **Grain:** 1 row = 1 product per month.
* **Primary Key:** Not explicitly defined (Implicitly composite `snapshot_date` + `product_id`).
* **Foreign Keys:** `product_id` -> `products.csv`

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `snapshot_date` | date | Snapshot date (end of month) |
| `product_id` | int | FK to `products.csv` |
| `stock_on_hand` | int | End of month stock |
| `units_received` | int | Units received in month |
| `units_sold` | int | Units sold in month |
| `stockout_days` | int | Days out of stock in month |
| `days_of_supply` | float | Days of supply available |
| `fill_rate` | float | Order fulfillment rate from stock |
| `stockout_flag` | int | Stockout indicator |
| `overstock_flag` | int | Overstock indicator |
| `reorder_flag` | int | Early reorder indicator |
| `sell_through_rate` | float | Ratio of sold to available stock |
| `product_name` | str | Product name |
| `category` | str | Product category |
| `segment` | str | Product segment |
| `year` | int | Year extracted from `snapshot_date` |
| `month` | int | Month extracted from `snapshot_date` |

### `web_traffic.csv`
* **Description:** Daily website traffic.
* **Grain:** 1 row = 1 day.
* **Primary Key:** Not explicitly defined (Implicitly `date`).
* **Foreign Keys:** None.

| Column | Type | Description & Constraints |
| :--- | :--- | :--- |
| `date` | date | Traffic date |
| `sessions` | int | Total sessions in the day |
| `unique_visitors` | int | Unique visitors |
| `page_views` | int | Total page views |
| `bounce_rate` | float | Single-page session bounce rate |
| `avg_session_duration_sec` | float | Avg session duration in seconds |
| `traffic_source` | str | Main source driving traffic for the day |

---

## 3. Relationships

* **`orders` <-> `payments`**: 1 : 1 (Mandatory).
* **`orders` <-> `shipments`**: 1 : 0 or 1 (Optional; only exists if status is shipped, delivered, or returned).
* **`orders` <-> `returns`**: 1 : 0 or many (Optional; only exists if status is returned).
* **`orders` <-> `reviews`**: 1 : 0 or many (Optional; only exists if status is delivered, ~20% of the time).
* **`order_items` <-> `promotions`**: many : 0 or 1 (Optional; `promo_id` can be null).
* **`products` <-> `inventory`**: 1 : many (1 row per product per month).

---

## 4. Business Logic & Rules

* **Pricing Constraint:** `cogs` must strictly be `< price` for all products.
* **Promotion Formulas:**
    * **Percentage:** `discount_amount = quantity * unit_price * (discount_value / 100)`
    * **Fixed Amount:** `discount_amount = quantity * discount_value`
* **Operational Constraints:**
    * `applicable_category` in `promotions.csv` is `NULL` if a promotion applies to all categories.
    * `shipping_fee` in `shipments.csv` is `0` if the order is eligible for free shipping.

---

## 5. Derived Metrics

* **Gross Profit Margin:** `(price - cogs) / price` (Requires `products.csv`) .
* **Return Rate:** Number of records in `returns.csv` divided by the number of rows in `order_items.csv` (Requires joining `returns.csv` with `products.csv` on `product_id` to filter by product attributes like size, and comparing against `order_items.csv`) .
* **Inter-order Gap:** The median number of days between two consecutive purchases made by the same customer (Requires `orders.csv`) .
* **Average Orders per Customer:** Total orders / Number of customers in a specific group, such as an age group (Requires `orders.csv`, `customers.csv`) .
* **Promotion Application Rate:** Percentage of rows in `order_items.csv` where a promotion is applied (i.e., `promo_id` is not null) .
* **Discount Amount Calculation** (Requires `promotions.csv`, `order_items.csv`):
  * *Percentage Promo:* `discount_amount = quantity × unit_price × (discount_value/100)`
  * *Fixed Promo:* `discount_amount = quantity × discount_value`

---

## 6. Data Quality Risks

* **Nullable Columns:**
    * `customers.csv`: `gender`, `age_group`, `acquisition_channel`.
    * `promotions.csv`: `applicable_category`, `promo_channel`, `min_order_value`.
    * `order_items.csv`: `promo_id`, `promo_id_2`.
* **Missing Relationships:** No direct links exist between `web_traffic.csv` and transactional data. These must be joined by date or by mapping `traffic_source` to `order_source`.

---

## 7. Analytical Opportunities

Supported analyses map directly to evaluation criteria for EDA (Descriptive -> Prescriptive):

* **Customer Behavior:** Inter-order gaps, average orders by age group.
* **Product Performance:** Gross profit margins by segment, return rates by product size, return reasons.
* **Marketing:** Website bounce rates by traffic source, evaluating promo application ratios.
* **Operational:** Correlating payment installments with order values, mapping cancelled orders by payment method, revenue tracking by geographic region.

---

## 8. Machine Learning Task Definition

* **Target Variable:** Revenue (Predicting unique daily `Date`, `Revenue`, `COGS` tuples for the test period).
* **Input Features:** Must be engineered strictly from the provided files. Using `Revenue` or `COGS` from the test period as features is strictly prohibited and will result in disqualification.
* **Time Dependency:** Forecasting Revenue per day for 01/01/2023 to 01/07/2024. The exact chronological order in the submission file must be strictly preserved without shuffling.
* **Evaluation Metrics:** MAE, RMSE, and $R^2$ (Coefficient of Determination).

---

## 9. Limitations

* **Prohibitions:** Use of any external datasets is explicitly forbidden.
* **Missing Data Aspects:** Test target values (`sales_test.csv`) are intentionally withheld.
* **Inference Restrictions:** Primary keys for granular operational/transactional tables (`order_items`, `payments`, `shipments`, `inventory`, `web_traffic`) are not explicitly defined in the source document and require composite key strategies.

---

## 10. Strict Fact Check & Verification

* **Explicit Sourcing:** Every column name, data type, foreign key relationship, and formula listed above is explicitly supported by Tables 1 and 2, and Section 1 of the provided document excerpts. 
* **Task Bounds:** The ML constraints, target variables, and evaluation criteria are strictly sourced from Section 2.
* **Assumption Avoidance:** Primary keys were not hallucinated for tables lacking explicit definitions (e.g., `order_items`, `payments`, `shipments`, `web_traffic`). Nullable fields are documented exactly as detailed in the source dataset overview.