# STRICT COMPLIANCE GUIDELINES: AI GUIDE V2 & PROJECT FINAL DV
*(Tài liệu này định nghĩa các ranh giới tuyệt đối KHÔNG ĐƯỢC PHÉP vi phạm khi AI Agent hỗ trợ viết code cho dự án Phân tích & Trực quan hóa Dữ liệu).*

## 1. GIỚI HẠN VỀ DỮ LIỆU & NGỮ CẢNH (DATA & CONTEXT LIMITS)
- **Bắt buộc về ngữ cảnh:** Dữ liệu phải mang ngữ cảnh Việt Nam (trên 50% dữ liệu) [1]. Mô phỏng hoạt động kinh doanh thương mại điện tử thời trang tại Việt Nam [2].
- **Kích thước tối thiểu:** Dữ liệu phải có tối thiểu 7 biến độc lập và 2000 dòng [1].
- **Cấm sử dụng dữ liệu ngoài:** Tuyệt đối KHÔNG được sử dụng bất kỳ nguồn dữ liệu bên ngoài nào khác ngoài các file đã cung cấp [3].
- **Tính nguyên vẹn của dữ liệu:** AI không được phép tự ý thay đổi dữ liệu gốc của hệ thống [4]. Không được tự ý thêm số liệu hay hình ảnh từ bên ngoài vào kết quả phân tích [5].

## 2. NHỮNG ĐIỀU AI KHÔNG ĐƯỢC LÀM (STRICT PROHIBITIONS FOR AI)
- **KHÔNG "Thực thi ngầm":** Tuyệt đối không được âm thầm chạy các thuật toán [4]. AI chỉ có quyền "viết code" và "chờ duyệt" [6, 7].
- **KHÔNG thực thi trên môi trường Online:** Mã phân tích phải được thiết kế để chạy trực tiếp trên môi trường Local của người dùng. Cấm gọi API thực thi code bên thứ 3 hoặc trên server online [4, 7].
- **KHÔNG bỏ qua chú thích:** Mỗi khi sinh code, BẮT BUỘC phải đính kèm comment giải thích bằng ngôn ngữ tự nhiên ngay trong đoạn code (VD: `# Đoạn code này sẽ...`) [4, 7].

## 3. CƠ CHẾ HUMAN-IN-THE-LOOP (BẮT BUỘC PHẢI CÓ)
Mọi luồng xử lý bằng AI phải tuân thủ nghiêm ngặt 3 giai đoạn, không được phép bypass (bỏ qua) bất kỳ bước nào:
1. **Trạng thái chờ:** Code AI sinh ra phải ở trạng thái "Chờ duyệt" [6, 7].
2. **Chỉnh sửa:** UI phải cho phép người dùng xem, can thiệp và gõ sửa các tham số trong đoạn code AI vừa viết [6, 7].
3. **Chấp nhận & Thực thi:** Chỉ khi người dùng chủ động bấm "Phê duyệt" (Approve), code mới được đẩy xuống backend để thực thi và vẽ biểu đồ [6, 7].

## 4. QUY ĐỊNH VỀ TRỰC QUAN HÓA & BIỂU ĐỒ (VISUALIZATION RULES)
- **Đúng mục đích:** Lựa chọn biểu đồ phải tuân thủ chuẩn mực thống kê (VD: So sánh dùng biểu đồ cột, theo dõi xu hướng thời gian dùng biểu đồ đường) [8].
- **Không lạm dụng màu sắc:** Tránh sự quá tải màu, sử dụng màu sắc có ý nghĩa và rõ ràng [9].
- **Mức độ phân tích:** Biểu đồ phải thể hiện được sự thay đổi, xu hướng theo thời gian, hoặc mối quan hệ giữa các biến [10].
- **Độc lập với Dashboard:** Nếu tích hợp AI vào hệ thống đã có Dashboard, luồng sinh biểu đồ của AI có thể thiết kế độc lập, không bắt buộc phải làm thay đổi trực tiếp các biểu đồ cố định trên Dashboard chính [11].

## 5. RÀNG BUỘC KIẾN TRÚC API VÀ LOGGING (ARCHITECTURE & LOGS)
Hệ thống phải được chia tách rõ Frontend và Backend (Decoupled APIs) [7, 12] với 3 API bắt buộc không được thiếu:
- **`API AI`:** Nhận request, trả về code sinh ra và giải thích (Chưa chạy) [13, 14].
- **`API Thực thi`:** Nhận mã đã duyệt, thực thi trên local và trả về biểu đồ/bảng dữ liệu [13-15].
- **`API Logs`:** Lưu trữ toàn bộ yêu cầu, mã nguồn sinh ra, mã nguồn đã duyệt, kết quả phân tích và giải thích. (Cho phép dùng SQLite cục bộ hoặc thư viện bên ngoài như LangSmith) [6, 14-16].

## 6. SỬ DỤNG TOOL CALLING CHO CÁC TÁC VỤ KHÓ
- Đối với những câu hỏi phân tích rất chuyên sâu hoặc phức tạp, LLM được phép (và khuyến khích) định nghĩa các Tools (Function calling) để agent gọi thực thi. Điều này giúp đảm bảo đáp án tính toán phân tích chính xác 100% [17].
