# Kiểm thử trình duyệt browser-smoke hỏng vì ô email cảnh báo

- **Ngày phát hiện:** 2026-11-29
- **Trạng thái:** Mới phát hiện
- **Thành phần liên quan:** `frontend/tests/browser-smoke.cjs`, tab Cảnh báo (`frontend/src/workspace/AlertsTab.tsx`)

## Vấn đề

`node tests/browser-smoke.cjs` dừng ở dòng 92 với lỗi Playwright `strict mode violation: locator('textarea') resolved to 2 elements`. Kiểm thử chọn ô từ khóa bằng `page.locator('textarea')`, nhưng tab Cảnh báo nay có thêm ô nhập email nhận cảnh báo (placeholder `ten@congty.vn`), nên bộ chọn khớp hai ô. Các bước phía sau (lưu cấu hình, thu thập, xem bình luận) không được kiểm.

## Bằng chứng

Chạy cục bộ ngày 29/11/2026 trên PostgreSQL 18 tạm, API `tests.e2e_server`, Vite và Chrome; lỗi xuất hiện trước mọi bước liên quan đến thay đổi của nhánh `TL-backend-sua-logic`.

## Nguyên nhân

Ô email theo nhãn hàng được thêm ngày 27/11 (migration `0021`), còn kiểm thử chưa cập nhật bộ chọn. Đây là suy luận từ thông báo lỗi và mã hiện tại; chưa đối chiếu commit cụ thể.

## Hướng giải quyết

Đổi bộ chọn thành theo nhãn, ví dụ `page.getByRole('textbox', { name: 'Từ khóa (mỗi dòng một từ)' })` hoặc `textarea[required]`, rồi chạy lại toàn bộ kịch bản. Thuộc phần giao diện/kiểm thử, nằm ngoài phạm vi phiên sửa logic tìm kiếm; cần người phụ trách nhận issue.

## Kết quả và kiểm chứng

Chưa sửa. Tính năng khung thời gian thu thập được kiểm bằng kịch bản Chrome riêng trong phiên (lưu/đọc lại `lookbackDays`, thông báo thiếu bài trong tab Phiên tracking: đạt), xem [S5](../docs/development-process/s5_tracking.md).
