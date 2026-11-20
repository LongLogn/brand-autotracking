# Giao diện Brand Auto-Tracking

Ứng dụng web React + TypeScript (Vite) theo [kiến trúc AWS](../docs/architecture_aws.md): build ra file tĩnh để đặt trên S3 và phân phối qua CloudFront. Thiết kế và token xem [DESIGN.md](DESIGN.md).

> Giao diện mặc định kết nối backend và Cognito khi được cấu hình. Chế độ minh họa dùng **dữ liệu mẫu**, chỉ bật bằng `VITE_DEMO_MODE=true`.

`src/lib/api.ts` là client cho backend, nhận access token từ hàm do ứng dụng cung cấp. Store và các màn hình minh họa vẫn dùng dữ liệu mẫu.

`src/lib/brand-workflow.ts` và `src/lib/tracking-view.ts` xử lý tạo nhãn hàng/cấu hình và tải dữ liệu phiên theo trang. Backend hỗ trợ khóa chống tạo trùng và giao diện giữ khóa khi thử lại trong cùng trang; nếu mất phản hồi cần kiểm tra danh sách trước khi tiếp tục. Khóa chỉ ở bộ nhớ và mất khi tải lại trang, vì vậy không bảo đảm chống trùng qua lần tải lại. Backend cần migration `0007_brand_create_key` trước khi dùng frontend này.

### Giao diện thử backend

Có một giao diện thử nghiệm riêng, không dùng dữ liệu mẫu. Trong PowerShell tại `frontend/`:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
npm run dev
```

Backend cần chạy, cấu hình CORS cho origin frontend và xác thực Cognito. Có thể nhập Cognito **access token** thủ công; token chỉ giữ trong bộ nhớ trang, không lưu vào localStorage. Không nhập token vào ứng dụng hoặc origin không tin cậy. Giao diện hỗ trợ danh sách, tạo và sửa tên/cấu hình nhãn hàng, tạo phiên chờ, xem phiên, bài và bình luận theo trang; tổng quan đọc số bản ghi đã lưu và phần nội dung tổng hợp đọc bài/bình luận theo nhãn hàng. Bộ lọc thời gian của nội dung tổng hợp áp dụng cho cả bài và bình luận được mở sau đó; bản ghi thiếu thời gian đăng bị loại khi lọc. Client cũng hỗ trợ lọc bình luận theo phiên, nhưng màn hình chi tiết phiên chưa có điều khiển riêng. Worker và bộ lập lịch cần được bật trên máy chủ; cấu hình đơn thuần không bảo đảm dịch vụ đang chạy. Cảnh báo, AI và xóa nhãn hàng chưa kết nối. Để mở giao diện mẫu, đặt `VITE_DEMO_MODE=true` và khởi động lại Vite.

Để bật nút đăng nhập Cognito, đặt `VITE_COGNITO_DOMAIN` và `VITE_COGNITO_CLIENT_ID` theo output CloudFormation trước khi khởi chạy Vite; origin phải khớp callback và logout URL đã đăng ký. Đã có nút tạo tài khoản mở trang đăng ký Cognito; mới kiểm tra trang mở, chưa kiểm thử xác minh email thật. Luồng authorization code + PKCE, refresh, cách ly hai tài khoản và đăng xuất managed login đã thử với Cognito, Lambda/API Gateway và RDS thật trong stack tạm. Access/refresh token chỉ giữ trong bộ nhớ; tải lại trang cần đăng nhập lại. Đăng xuất managed login xóa phiên trình duyệt nhưng không tự thu hồi access token đã cấp. Các màn hình minh họa chưa dùng đăng nhập thật.

Kiểm thử trình duyệt cục bộ trong `tests/browser-smoke.cjs` cần Playwright cài ngoài dự án, Chrome và frontend/backend thử nghiệm với PostgreSQL riêng, xác thực giả. Đặt `PLAYWRIGHT_MODULE` là đường dẫn module Playwright, `TEST_BROWSER` là đường dẫn Chrome và `TEST_UI_BASE` là URL frontend, rồi chạy `node tests/browser-smoke.cjs`. Kiểm thử tạo dữ liệu trong backend được chỉ định; chỉ dùng database thử nghiệm riêng.

Để kiểm tra thêm worker giả và hiển thị bài/bình luận, đặt `TEST_FAKE_WORKER_PYTHON` tới Python trong môi trường backend, `TEST_ONLY_AUTH_STUB=1` và `DATABASE_URL`/`TEST_DATABASE_URL` giống nhau, trỏ tới database **`brand_test` trên localhost** đã migration và chỉ dành cho kiểm thử. Backend thử nghiệm phải dùng cùng database. Worker giả xử lý một phiên chờ; không chạy nếu các điều kiện bảo vệ không khớp. Không dùng database chứa dữ liệu thật.

## Chạy

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # kết quả trong dist/
```

## Màn hình

| Đường dẫn | Nội dung | SRS |
|---|---|---|
| `/login` | Đăng nhập, tạo tài khoản (giả lập) | FR-01 |
| `/brands`, `/brands/new` | Danh sách và tạo nhãn hàng | FR-03 |
| `/brands/:id` | Tổng quan: xu hướng tiêu cực theo hai cửa sổ, độ bao phủ theo nền tảng | FR-17, FR-24, NFR-06 |
| `/brands/:id/content` | Nội dung tổng hợp, lọc thời gian/nền tảng/cảm xúc, bình luận nổi bật | FR-19 – FR-21 |
| `/brands/:id/runs`, `/runs/:runId` | Lịch sử phiên, lượt theo cặp nền tảng × từ khóa, lỗi và lượt rỗng | FR-14, FR-16 – FR-18 |
| `/brands/:id/alerts` | Quy tắc và lịch sử cảnh báo | FR-23 – FR-26 |
| `/brands/:id/analysis` | Yêu cầu phân tích AI, phạm vi dữ liệu, nhận định có dẫn chứng | FR-27 – FR-30 |
| `/brands/:id/settings` | Từ khóa, nền tảng, lịch, giới hạn bài, xóa nhãn hàng | FR-04 – FR-09 |

## Nối backend

- Thay các hàm trong `src/lib/store.tsx` bằng lời gọi API Gateway, kèm access token Cognito.
- Giữ quy ước `null` = không khả dụng; giao diện hiển thị khác với 0.
- Router dùng đường dẫn thường (`BrowserRouter`): cấu hình CloudFront trả `index.html` cho lỗi 403/404 để mở trực tiếp đường dẫn con.

Giao diện tự cập nhật danh sách phiên mỗi 5 giây khi có phiên đang chờ/chạy và 30 giây trong các trường hợp khác; phần chi tiết phiên cần mở lại để tải dữ liệu mới.
