# Sổ vấn đề kỹ thuật

Thư mục này ghi lại các vấn đề phát hiện trong quá trình phát triển, kiểm thử và vận hành demo. **Mỗi vấn đề viết thành một tệp `.md` riêng.** Mục đích là để thành viên nhóm hiểu nhanh vấn đề, cách giải quyết và có tư liệu trả lời khi bảo vệ.

## Đặt tên tệp

`YYYY-MM-DD_<ten-ngan-tieng-anh>.md`, ví dụ `2026-11-28_bedrock-rate-limit.md`. Ngày là ngày phát hiện, tên viết thường, nối bằng dấu gạch ngang.

## Nội dung bắt buộc

Mỗi tệp phải mô tả rõ **vấn đề** và **hướng giải quyết**, theo mẫu dưới đây. Mục nào chưa có thông tin thì ghi "Chưa xác định", không bỏ trống và không ghi suy đoán như kết quả đã kiểm chứng.

```markdown
# <Tên vấn đề>

- **Ngày phát hiện:** YYYY-MM-DD
- **Trạng thái:** Mới phát hiện | Đang xử lý | Đã giải quyết | Tạm chấp nhận
- **Thành phần liên quan:** ví dụ backend/app/sentiment.py, Bedrock, EC2

## Vấn đề
Hiện tượng quan sát được, khi nào xảy ra, ảnh hưởng đến người dùng hoặc demo.

## Bằng chứng
Log, lệnh kiểm tra, số liệu, ảnh chụp hoặc liên kết. Ghi rõ nguồn và thời điểm.

## Nguyên nhân
Nguyên nhân gốc. Phân biệt nguyên nhân đã xác minh với suy luận.

## Hướng giải quyết
Các phương án đã cân nhắc kèm ưu, nhược điểm; phương án được chọn và lý do.

## Kết quả và kiểm chứng
Đã sửa gì (commit, tệp, cấu hình), đã kiểm thử thế nào, kết quả ra sao. Ghi việc còn lại nếu chưa xong.
```

## Quy ước

- Viết bằng tiếng Việt, ngắn gọn, đủ để người không tham gia sửa vẫn hiểu.
- Cập nhật **trạng thái** và mục **Kết quả và kiểm chứng** khi vấn đề tiến triển; không tạo tệp mới cho cùng một vấn đề.
- Không ghi khóa API, mật khẩu, token hay dữ liệu cá nhân vào tệp.
- Chi tiết theo giai đoạn vẫn ghi ở [docs/development-process/](../docs/development-process/); tệp ở đây có thể liên kết sang đó thay vì chép lại.

## Danh sách vấn đề

| Ngày | Vấn đề | Trạng thái |
|---|---|---|
| 2026-11-28 | [Giới hạn tốc độ Bedrock Nova Lite](2026-11-28_bedrock-rate-limit.md) | Đã giải quyết |
