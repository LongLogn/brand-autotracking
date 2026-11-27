# Giao diện Brand Auto-Tracking

**Hủy phiên:** Trong tab Phiên tracking, nút Hủy phiên xuất hiện với phiên đang chờ. Phiên đã bắt đầu không thể hủy; nếu trạng thái đổi trong lúc thao tác, hệ thống tải lại danh sách. Chưa triển khai AWS.

**Email cảnh báo:** Tab Cảnh báo cho phép lưu tối đa 10 địa chỉ theo nhãn hàng; bỏ hết địa chỉ để tắt gửi. Chỉ áp dụng cảnh báo demo, cần cấu hình SES và chưa triển khai AWS.

Khi chuẩn bị bản trình diễn, đặt `VITE_DEMO_TOOLS=true` để hiện mã nhãn hàng (kèm nút sao chép) ở đầu trang sau khi chọn nhãn hàng. Bài từ bộ sinh được ghi nguồn “Dữ liệu giả lập”, nội dung có nhãn giả và liên kết `.invalid` không mở được. Tự đăng ký email giả qua Cognito demo riêng dùng [cognito-demo.yaml](../infrastructure/cognito-demo.yaml); đó là xác minh giả lập. Kịch bản và trạng thái kiểm chứng tại [thư mục demo](../demo/architecture.md).

Ứng dụng web React + TypeScript (Vite) theo [kiến trúc AWS](../docs/architecture_aws.md): build ra file tĩnh để đặt trên S3 và phân phối qua CloudFront. Thiết kế và token xem [DESIGN.md](DESIGN.md).

> Giao diện mặc định kết nối backend và Cognito khi được cấu hình. Chế độ minh họa dùng **dữ liệu mẫu**, chỉ bật bằng `VITE_DEMO_MODE=true`.

`src/lib/api.ts` là client cho backend, nhận access token từ hàm do ứng dụng cung cấp. Store và các màn hình minh họa vẫn dùng dữ liệu mẫu.

`src/lib/brand-workflow.ts` và `src/lib/tracking-view.ts` xử lý tạo nhãn hàng/cấu hình và tải dữ liệu phiên theo trang. Backend hỗ trợ khóa chống tạo trùng và giao diện giữ khóa khi thử lại trong cùng trang; nếu mất phản hồi cần kiểm tra danh sách trước khi tiếp tục. Khóa chỉ ở bộ nhớ và mất khi tải lại trang, vì vậy không bảo đảm chống trùng qua lần tải lại. Backend cần migration `0007_brand_create_key` trước khi dùng frontend này.

Giao diện kết nối có nút xóa nhãn hàng với hộp thoại xác nhận. Backend xóa dữ liệu liên quan trong database và trả 409 nếu tracking đang chờ/chạy hoặc phân loại/phân tích đang chạy; bản sao lưu có thể còn dữ liệu sau thao tác, thời hạn lưu chưa được thống nhất. Nút này cần backend hỗ trợ `DELETE /brands/{id}` và CORS cho `DELETE`; không áp dụng cho store minh họa.

### Bố cục giao diện kết nối (27/11)

`ApiApp.tsx` giữ phần đăng nhập, trạng thái và các lời gọi API; các tab nằm trong `src/workspace/` (`OverviewTab`, `AlertsTab`, `AnalysisTab`, `ContentTab`, `shared`, `workspace.css`). Thanh trái liệt kê nhãn hàng và nút Thêm nhãn hàng; sau khi chọn nhãn hàng có 6 tab: Tổng quan, Cảnh báo, Phân tích AI, Nội dung, Phiên tracking, Cấu hình. Tab chỉ tải dữ liệu khi mở lần đầu và giữ trạng thái khi chuyển qua lại. Giải thích dài nằm trong biểu tượng ⓘ. Kiểm thử trình duyệt mở tab bằng `openTab` trước khi thao tác.

Trước khi đăng nhập, `Landing.tsx` hiển thị trang chào: thanh trên có nút **Đăng nhập** và **Tạo tài khoản**, phần chính có hình sản phẩm dựng bằng HTML (số liệu minh họa) và ba bước sử dụng. Ô access token cho kiểm thử nằm ở chân trang. Đăng nhập vẫn qua trang Cognito, đã đổi màu và logo theo [hướng dẫn hạ tầng](../infrastructure/README.md).

### Giao diện thử backend

Có một giao diện thử nghiệm riêng, không dùng dữ liệu mẫu. Trong PowerShell tại `frontend/`:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
npm run dev
```

Backend cần chạy, cấu hình CORS cho origin frontend và xác thực Cognito. Có thể nhập Cognito **access token** thủ công; token chỉ giữ trong bộ nhớ trang, không lưu vào localStorage. Không nhập token vào ứng dụng hoặc origin không tin cậy. Giao diện hỗ trợ danh sách, tạo và sửa tên/cấu hình nhãn hàng, tạo phiên chờ, xem phiên, bài và bình luận theo trang; tổng quan đọc số bản ghi đã lưu và phần nội dung tổng hợp đọc bài/bình luận theo nhãn hàng. Bộ lọc thời gian của nội dung tổng hợp áp dụng cho cả bài và bình luận được mở sau đó; chi tiết phiên có bộ lọc thời gian riêng cho bình luận. Thời gian theo múi giờ thiết bị, gồm đầu và không gồm cuối; bản ghi thiếu thời gian đăng bị loại khi lọc. Worker và bộ lập lịch cần được bật trên máy chủ; cấu hình đơn thuần không bảo đảm dịch vụ đang chạy. Xóa nhãn hàng đã kết nối như mô tả ở trên. Để mở giao diện mẫu, đặt `VITE_DEMO_MODE=true` và khởi động lại Vite.

Phân tích AI theo khoảng thu thập và lịch sử đã kết nối API thử nghiệm sau migration `0016`; dịch vụ mặc định tắt. Bedrock thật đã được thử qua AWS với dữ liệu giả, chưa đánh giá độc lập chất lượng trên dữ liệu thật; xem [S7](../docs/development-process/s7_ai_analysis.md). Kết quả dùng mẫu giới hạn, chỉ để tham khảo; kiểm tra ID dẫn chứng không bảo đảm nhận định đúng. Khi mất phản hồi, giao diện giữ khóa trong trang để kiểm tra lại, nhưng khóa mất khi tải lại trang; xem lịch sử trước khi yêu cầu mới.

Phần cảnh báo lưu cấu hình, đánh giá thủ công cửa sổ đã hoàn tất và xem lịch sử sau các migration đến `0015`. Nhãn cảm xúc theo phiên bản nội dung hiện tại nếu worker phân loại đã được bật và hoàn tất. Phân loại và đánh giá tự động mặc định tắt; cảnh báo đã thử trên AWS với dữ liệu giả, chưa nghiệm thu chất lượng phân loại hoặc hai cửa sổ dữ liệu thật. Thiếu bằng chứng trả không đủ dữ liệu; xem [S6](../docs/development-process/s6_sentiment_alerts.md).

Để bật nút đăng nhập Cognito, đặt `VITE_COGNITO_DOMAIN` và `VITE_COGNITO_CLIENT_ID` theo output CloudFormation trước khi khởi chạy Vite; origin phải khớp callback và logout URL đã đăng ký. Đã có nút tạo tài khoản mở trang đăng ký Cognito; mới kiểm tra trang mở, chưa kiểm thử xác minh email thật. Luồng authorization code + PKCE, refresh, cách ly hai tài khoản và đăng xuất managed login đã thử với Cognito, Lambda/API Gateway và RDS thật trong stack tạm. Access/refresh token chỉ giữ trong bộ nhớ; tải lại trang cần đăng nhập lại. Đăng xuất managed login xóa phiên trình duyệt nhưng không tự thu hồi access token đã cấp. Các màn hình minh họa chưa dùng đăng nhập thật.

Kiểm thử AWS tùy chọn dùng `tests/cognito-browser.cjs` cùng `backend/tests/cognito_browser_check.py` và Lambda fixture `backend/tests/aws_analysis_fixture.py`: chỉ chạy trên database thử riêng có hostname `brand-ai-check-data-*`, với cờ `TEST_ONLY_AWS_FIXTURE=1`. Khi đặt `TEST_ANALYSIS_FIXTURE_FUNCTION`, kịch bản kiểm tra AI thật với bài giả, cảnh báo 10→15, chống trùng và cách ly lịch sử; tạo/xóa tài khoản Cognito thử và phát sinh tối đa một lượt Bedrock mỗi lần chạy. Phải tự chuẩn bị, giới hạn ngân sách và dọn stack/fixture theo [S8](../docs/development-process/s8_aws_delivery.md).

**Cảnh báo theo lần thu thập (27/11):**
- Tab Cảnh báo có mục "Cảnh báo theo lần thu thập": biểu đồ cột tỷ lệ tiêu cực (mốc màu đậm, lần cảnh báo màu đỏ, phần chưa phân loại là vân gạch) và bảng diễn biến, tự cập nhật mỗi 10 giây. Mỗi dòng gồm lần thu thập, bình luận mới, tiêu cực/tổng lũy kế, tỷ lệ và kết quả (Mốc, Cảnh báo, Không cảnh báo).
- Khi có cảnh báo, mục này hiện thêm một banner và nút "Đánh giá lại lần thu thập gần nhất".
- Liên kết trong email cảnh báo có dạng `/?brand=<id>&alert=<id>`. Ứng dụng lưu liên kết vào `sessionStorage`, chuyển sang đăng nhập Cognito, rồi tự mở đúng nhãn hàng ở tab Cảnh báo và cuộn tới mục cảnh báo.
- Khi API chạy sau CloudFront, đặt `VITE_API_BASE_URL=<FrontendUrl>/api`.
- `tests/demo-minute-browser.cjs` chạy kịch bản qua `app.demo_stream --scenario`. Điều kiện chạy giống `demo-browser.cjs`: database `brand_demo` cục bộ, xác thực giả. Ngoài các biến cũ, cần thêm `TEST_API_BASE`.
- Ngày 27/11 kiểm thử này đã đạt với Chrome, FastAPI xác thực giả và PostgreSQL 18 riêng:
  - mốc 20% → cảnh báo 30%;
  - đánh giá lại không tạo bản sao;
  - đợt tích cực 22% không cảnh báo;
  - link email mở đúng nhãn hàng.
- Build và 18 kiểm thử đơn vị đạt, 1 kiểm thử tích hợp bỏ qua.
- Sau khi chia tab (27/11), chạy lại với Chrome, backend xác thực giả và PostgreSQL 18 tạm: `demo-minute-browser.cjs`, `demo-browser.cjs`, `browser-smoke.cjs` đều đạt; build và 18 kiểm thử đơn vị đạt. Bản mới đã tải lên CloudFront demo ngày 27/11 (trang mở, chuyển Cognito đúng); các script AWS đã sửa để mở tab nhưng chưa chạy lại.
- Ngày 27/11, `tests/aws-demo-minute.cjs` đã đạt trên CloudFront và Cognito demo thật: đăng ký, dòng dữ liệu, cảnh báo, AI, đợt tích cực và link email (link mở bằng URL, không qua email thật).
  - Lượt đầu phát hiện vòng lặp đăng nhập khi mở link; đã sửa.
  - Script cần `TEST_DEMO_SIGNUP=1` và `TEST_DEMO_AUTH_HOST`. Người vận hành chạy `demo_control.py start` khi script in `DEMO_BRAND_ID`, và `release` khi script in `READY_FOR_RELEASE`.

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
