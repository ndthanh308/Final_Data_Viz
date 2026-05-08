# Use Cases của Ứng dụng Phân tích Dữ liệu AI (Thư mục `app`)

Dựa vào kiến trúc và các tính năng trong thư mục `app` (`app.py`, `main.py`, `graph.py`...), ứng dụng web này là một hệ thống phân tích dữ liệu và vẽ biểu đồ tự động có sự hỗ trợ của AI, được thiết kế theo cơ chế **Human-in-the-loop (HITL)**.

Dưới đây là các Use Cases (tình huống sử dụng) chính của ứng dụng web này:

## 1. Phân Tích Dữ Liệu Tự Động với AI (HITL Analysis Mode)
Đây là tính năng cốt lõi nhất của ứng dụng, cho phép người dùng mô tả yêu cầu bằng ngôn ngữ tự nhiên và hệ thống sẽ tự động viết code phân tích dữ liệu & vẽ biểu đồ.
- **Chọn nguồn dữ liệu (Select Data):** Người dùng có thể quét và chọn các bảng dữ liệu CSV khác nhau từ thư mục `data/main/raw` (ví dụ: `orders.csv`, `inventory.csv`, `shipments.csv`,...). Hệ thống sẽ trích xuất schema, data typé và các dòng sample để gửi cho AI làm ngữ cảnh (context) mà không cần nạp toàn bộ dữ liệu nặng.
- **Tạo mã phân tích (Generate Code):** Người dùng nhập một yêu cầu kinh doanh bằng tiếng Anh (ví dụ: *"Analyze monthly revenue and COGS trend"*, *"Evaluate stockout risk from inventory table"*). AI sẽ sinh ra đoạn code Python (sử dụng Pandas, Matplotlib...) tương ứng.
- **Kiểm duyệt và chỉnh sửa mã (Human-in-the-Loop):** AI chỉ sinh code. Người dùng sẽ xem trước đoạn code này trên UI, có thể tự do chỉnh sửa đoạn code sao cho phù hợp nhất trước khi duyệt.
- **Thực thi và xem kết quả (Execute Code):** Sau khi click "Approve & Execute", hệ thống backend (FastAPI + LangGraph) mới nạp dữ liệu thật và chạy đoạn code một cách cục bộ. Kết quả trả về (bao gồm các số liệu summary, output terminal, bảng dữ liệu, và biểu đồ trực quan base64 code) sẽ được hiển thị ngay lập tức trên màn hình ứng dụng Streamlit.

## 2. Trò Chuyện & Tư Vấn Dữ Liệu (Chat Mode)
Người dùng có thể trò chuyện trực tiếp với AI chuyên gia phân tích dữ liệu mà không cần chạy code.
- **Hỏi đáp về cấu trúc dữ liệu:** Ví dụ: *"Which tables should I join to analyze return behavior by category?"* (Tôi nên join bảng nào để phân tích hành vi trả hàng?).
- **Gợi ý chỉ số (KPIs):** Xin các ý tưởng về dashboard hoặc ý tưởng chỉ số quan trọng cho mô hình E-commerce.
- **Giải mã dữ liệu:** Nhờ AI giải thích chi tiết mối quan hệ giữa các bảng (ví dụ: payments, orders, shipments).

## 3. Hệ Thống Lưu Trữ và Ghi Log Truy Vấn
Dành cho mục đích kiểm soát hệ thống và sao lưu lịch sử.
- **Theo dõi thực thi:** Tất cả các lịch sử yêu cầu (prompt), mã code tương ứng do AI sinh ra, mã đã duyệt và kết quả chạy (báo lỗi hay thành công) đều được ghi nhận vào cơ sở dữ liệu nội bộ SQLite (`logs.db`).
- **Gỡ lỗi (Debug):** Nếu code lỗi (Syntax error, KeyError,...), hệ thống đẩy lỗi (backend_error / logs_error / stdout error) ngược lại giao diện Streamlit để người dùng biết code sai ở đâu để sửa trực tiếp và execute lại.

---
**Tóm lại:** Website này như một **"Nhà phân tích dữ liệu AI nội bộ"** dành cho doanh nghiệp e-commerce/retail. Nó giúp người dùng trích xuất insight và biểu đồ từ file CSV thông qua câu lệnh Chat đơn giản nhưng luôn đảm bảo tính an toàn dữ liệu và quyền kiểm soát code (do người dùng cuối cùng quyết định có chạy script hay không).
