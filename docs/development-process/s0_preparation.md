# Giai đoạn 0 — Chuẩn bị làm việc và môi trường

**Cập nhật:** 16/11/2026. **Trạng thái:** Đã có một phần; chưa đủ bằng chứng hoàn thành.

- Firecrawl MCP và API đã được thử thành công; xem [giai đoạn 2](s2_firecrawl.md). Không lưu khóa vào tài liệu.
- Ngày 16/11, AWS CLI profile `profile-name-logn` xác thực STS thành công qua SSO; Region cấu hình là `ap-southeast-1`. Lệnh liệt kê Cognito user pool thành công và trả 0 pool tại Region này; chưa kiểm tra các Region khác. `FIRECRAWL_API_KEY` có trong biến môi trường User Windows nhưng tiến trình Codex cũ chưa tự nhận; cần nạp vào tiến trình worker. Chưa kiểm tra tính hợp lệ của khóa trong lượt này.
- Người dùng cho phép chi tối đa 30 USD trong số dư AWS khoảng 60 USD, chỉ bật tài nguyên khi làm; chưa chốt thời gian thử. Người dùng báo Firecrawl 1.000 credit miễn phí, đã dùng 11; chưa đối chiếu Usage. Cần kiểm tra quyền Bedrock, phân công và triển khai đầy đủ.
- Đã tạo AWS Budget `brand-tracking-dev-monthly-30usd`, loại COST tổng tài khoản theo tháng, ngưỡng ACTUAL lớn hơn 50%, 80%, 100%, gửi tới email người dùng chỉ định; đã đọc lại ngân sách và các ngưỡng. Budget không tự dừng tài nguyên, không tách chi phí dự án và không bảo đảm giới hạn tổng 30 USD xuyên tháng; cần theo dõi chi phí và tắt/dọn tài nguyên thử. Budget `My Zero-Spend Budget` có sẵn được giữ nguyên.
- Ngày 16/11 CloudFormation xác thực và tạo stack Cognito phát triển `brand-tracking-dev-auth`; một lượt đăng nhập Cognito thật với backend cục bộ đã được kiểm chứng. Chi tiết và việc còn lại ở [S8](s8_aws_delivery.md).
- Tiếp theo: đối chiếu từng mục giai đoạn 0 trong [lộ trình](../development_roadmap.md), ghi bằng chứng, người phụ trách và việc còn lại; không coi cấu hình đề xuất là đã triển khai.
