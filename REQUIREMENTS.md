
### I. YÊU CẦU VỀ ĐỒ ÁN TRỰC QUAN HÓA DỮ LIỆU (PROJECT FINAL DV)

**1. Ràng buộc về Dữ liệu:**
*   Dữ liệu phải là dữ liệu thật và mang ngữ cảnh liên quan đến Việt Nam.
*   Tổng số dữ liệu liên quan đến Việt Nam phải chiếm trên 50%.
*   Bộ dữ liệu phải có tối thiểu 7 biến độc lập và ít nhất 2000 dòng.

**2. Tiêu chí thiết kế và phân tích trên Dashboard:**
*   **Độ tin cậy:** Nguồn dữ liệu phải minh bạch, đáng tin cậy và không có thiếu sót trong quy trình xử lý.
*   **Đúng mục đích:** Lựa chọn biểu đồ phải chuẩn xác (ví dụ: dùng biểu đồ cột để so sánh, biểu đồ đường để theo dõi xu hướng thời gian) và phù hợp với đối tượng mục tiêu.
*   **Rõ ràng và dễ hiểu:** Thông điệp trực quan hóa phải được truyền đạt nhanh chóng, dễ nhận thức.
*   **Tính liên kết:** Nếu Dashboard có nhiều biểu đồ, chúng phải có sự liên kết, tích hợp với nhau và làm rõ được các mối quan hệ.
*   **Tương tác & Điều hướng:** Hệ thống điều hướng phải dễ sử dụng; tính năng tương tác phải hợp lý để người xem thăm dò dữ liệu.
*   **Thẩm mỹ:** Thiết kế hấp dẫn, màu sắc có ý nghĩa và đặc biệt **tránh sự quá tải về màu sắc**.
*   **Chiều sâu phân tích:** Phải thể hiện được sự thay đổi/xu hướng theo thời gian, làm rõ mối quan hệ giữa các biến và rút ra được các kết luận, câu chuyện từ dữ liệu.
*   Thiết kế và vận hành tốt phần Tích hợp AI.

---

### II. YÊU CẦU TÍCH HỢP AI (AI GUIDE V2)

**1. Nguyên tắc cốt lõi về Vai trò và Môi trường:**
*   **Môi trường thực thi:** Code bắt buộc phải được chạy trên **môi trường local** của người dùng, tuyệt đối không được thực thi trên môi trường online.
*   **Vai trò của AI:** Đề xuất ý tưởng, viết code theo yêu cầu, trình bày kết quả dựa trên số liệu/hình ảnh con người cấp. AI **không được tự ý thêm số liệu hay hình ảnh khác** ngoài dữ liệu gốc.
*   **Vai trò con người:** Ra quyết định, định hướng phân tích, yêu cầu AI đưa ra gợi ý nếu chưa có ý tưởng.

**2. Nguyên tắc "Không thực thi ngầm" (Vô cùng quan trọng):**
*   AI không được tự ý thay đổi dữ liệu gốc hoặc âm thầm chạy các thuật toán.
*   **Hiển thị code:** Code do AI sinh ra phải được hiển thị rõ ràng.
*   **Comment giải thích:** Ngay trong đoạn code, AI **bắt buộc** phải đính kèm các dòng comment giải thích bằng ngôn ngữ tự nhiên (VD: "Đoạn code này sẽ xóa 15 dòng...").

**3. Nguyên tắc Phê duyệt (Cơ chế Human-in-the-loop):**
*   **Trạng thái chờ:** Đoạn code do AI sinh ra ban đầu phải nằm ở trạng thái “Chờ duyệt”.
*   **Quyền chỉnh sửa:** Giao diện phải cho phép người dùng trực tiếp can thiệp, gõ sửa các tham số trong đoạn code AI vừa viết.
*   **Chấp nhận & Thực thi:** Chỉ khi con người bấm phê duyệt (chấp thuận) thì đoạn code đó mới được phép thực thi và trả về kết quả/biểu đồ.

**4. Yêu cầu về Kiến trúc Hệ thống (Bắt buộc phân tách Frontend và API):**
*   **Frontend (Giao diện):** Cần đảm bảo các chức năng: Nhận yêu cầu của người dùng, xem & chỉnh sửa mã nguồn, phê duyệt mã nguồn và hiển thị kết quả.
*   **API AI (Bắt buộc):** Tiếp nhận yêu cầu từ Frontend, gửi kèm ngữ cảnh cho mô hình AI (chạy local model), trả về cả code và giải thích.
*   **API Thực thi (Bắt buộc):** Tiếp nhận mã đã được "chỉnh sửa" và "phê duyệt" từ Frontend, chạy code trực tiếp trên dữ liệu tại máy local, sau đó thu thập kết quả (ảnh biểu đồ, bảng dữ liệu, logs) trả về Frontend.
*   **API Logs (Bắt buộc) & Lưu trữ:** Hệ thống phải lưu trữ toàn bộ lịch sử bao gồm: yêu cầu, mã nguồn, kết quả phân tích và giải thích để có thể truy xuất lại được.