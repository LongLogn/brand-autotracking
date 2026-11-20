# Giai đoạn 6 — Cảm xúc và cảnh báo

Ngày 16/11 chuẩn bị [hàm đánh giá ngưỡng độc lập](../../backend/app/alert_rules.py): chỉ đánh giá khi bên gọi xác nhận độ phủ so sánh được và phân loại đầy đủ; phân biệt mốc bằng 0, thiếu dữ liệu, ngưỡng tăng và ngưỡng tuyệt đối. Kiểm thử 10→15, 10→14, 0→15, tối thiểu và dữ liệu thiếu đạt trong bộ 30 kiểm thử backend với PostgreSQL thử. Đây chưa phải tính năng cảnh báo: chưa xác minh độ phủ hoặc phân loại, lưu quy tắc/cảnh báo, chống lặp hay nối UI; cần hoàn thành các phụ thuộc trước khi sử dụng.

**Cập nhật:** 15/11/2026. **Trạng thái:** Chưa có bằng chứng triển khai thực tế.

- Giao diện cảnh báo trong [frontend](../../frontend/README.md) dùng dữ liệu mẫu; chưa chứng minh phân tích cảm xúc hay tạo cảnh báo thật.
- Cần dữ liệu tracking, quyền mô hình phù hợp và quy tắc cảnh báo theo [SRS](../software_requirements_specification.md) và [lộ trình](../development_roadmap.md).
- Tiếp theo: kiểm chứng phân loại và các trường hợp ngưỡng, dữ liệu thiếu, chống lặp; lưu kết quả và giới hạn đánh giá.
