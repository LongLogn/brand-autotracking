# Báo cáo Kiểm thử QA Web & Chi tiết Chỉnh sửa Frontend (28/11/2026)

## 1. Thông tin chung

- **Ngày thực hiện:** 28/11/2026
- **Môi trường kiểm thử trực tiếp:** `https://d1ymt5wg42h5sa.cloudfront.net` (CloudFront + S3 + Cognito Managed Login + ALB/EC2 FastAPI + RDS PostgreSQL + EventBridge/SQS/Lambda Worker + Firecrawl + Amazon Bedrock Nova Lite)
- **Công cụ kiểm thử:** Google Chrome (qua Chrome DevTools MCP), Lighthouse Snapshot, bộ kiểm thử đơn vị Node.js (`node --test`) và trình biên dịch TypeScript + Vite (`tsc --noEmit && vite build`).
- **Phạm vi 3 đợt kiểm thử:**
  1. **Đợt 1 — Giao diện trước đăng nhập & Xác thực:** Landing Page (Desktop `1440x900`, Mobile `390x844`), điều hướng nội trang, kiểm tra Console/Network, kiểm tra luồng OAuth 2.0 + PKCE (`S256`) và giao diện Cognito Managed Login.
  2. **Đợt 2 — Nghiệp vụ Workspace Dashboard (0 tốn phí Firecrawl/Bedrock):** Kiểm tra toàn bộ 6 tab (`Tổng quan`, `Cảnh báo`, `Phân tích AI`, `Nội dung`, `Phiên tracking`, `Cấu hình`), tạo nhãn hàng với từ khóa trùng hoa/thường (`422` → thử lại lưu cấu hình), tạm dừng nhãn hàng, chặn thu thập thủ công khi tạm dừng (`409`), **hủy phiên tracking đang chờ (`Hủy phiên` → `200 OK`) trên AWS**, lưu quy tắc cảnh báo, kiểm tra ràng buộc ngày/email và xóa vĩnh viễn nhãn hàng tạm.
  3. **Đợt 3 — Luồng dữ liệu thật End-to-End (`NVIDIA`):** Tạo nhãn hàng `NVIDIA` (`Nvidia`, `Jensen Huang`, TikTok, `postLimit = 3`), chạy **Thu thập ngay** qua Firecrawl (hoàn tất sau `28 giây`, thu được `4` bài viết TikTok duy nhất và `166` bình luận thật), kiểm chứng phân loại cảm xúc tự động bằng Bedrock Nova Lite, biểu đồ cột `Mốc` và chạy **Phân tích AI** thật (`1.30 giây`, sinh `3` chủ đề tiếng Việt kèm câu bình luận dẫn chứng nguyên văn).

---

## 2. Tổng hợp kết quả các luồng đạt trên AWS

| Hạng mục kiểm thử | Kết quả | Minh chứng chính |
|---|---|---|
| Landing Page, Font Tiếng Việt & Minh họa KFCC | **ĐẠT** | Lighthouse Accessibility `100/100`, Best Practices `100/100`, `0` lỗi JS/CORS/4xx/5xx |
| Xác thực Cognito OAuth 2.0 + PKCE (`S256`) & SSO | **ĐẠT** | Đổi mã `POST /oauth2/token [200]`, tải `GET /api/brands [200]` |
| Khôi phục khi tạo nhãn hàng bị lỗi lưu cấu hình (`pendingBrand`) | **ĐẠT** | Không tạo bản ghi nhãn hàng trùng lặp khi bấm *Thử lại lưu cấu hình* |
| Chặn chạy thủ công khi nhãn hàng đang `Tạm dừng` | **ĐẠT** | `POST /api/brands/{id}/runs` trả `409 Conflict` |
| Hủy phiên đang chờ (`Hủy phiên`) trên AWS | **ĐẠT** | `POST /api/brands/{id}/runs/{runId}/cancel` trả `200 OK`, chuyển trạng thái `Đã hủy` |
| Thu thập thật TikTok qua Firecrawl (`NVIDIA`) | **ĐẠT** | Hoàn tất trong `28s`, khử trùng 2 từ khóa còn `4` bài viết, `166` bình luận |
| Phân loại cảm xúc & Biểu đồ tỷ lệ tiêu cực | **ĐẠT** | Nova Lite gán nhãn tự động mỗi phút, dựng cột `Mốc` trên `Tổng quan` & `Cảnh báo` |
| Phân tích AI kèm dẫn chứng nguyên văn (`Bedrock Nova Lite`) | **ĐẠT** | Phản hồi sau `1.30s`, trả `3` chủ đề tiếng Việt + trích dẫn nguyên văn có link TikTok gốc |
| Xóa vĩnh viễn nhãn hàng kiểm thử tạm | **ĐẠT** | `DELETE /api/brands/{id}` trả `200 OK`, làm sạch dữ liệu liên quan |

---

## 3. Danh sách lỗi (Bugs) & Bất cập UX đã phát hiện và khắc phục

| Mã | Mức độ | Đợt phát hiện | Mô tả lỗi / Hiện tượng thực tế | Nguyên nhân gốc | Trạng thái |
|---|---|---|---|---|---|
| **FE-01** | Trung bình | Đợt 1 | Màn hình di động (`<= 560px`) bị mất hoàn toàn nút **Đăng nhập** trên thanh đầu trang, người dùng đã có tài khoản không thấy lối đăng nhập. | Quy tắc `.lp-nav-actions .lp-btn-ghost { display: none; }` trong `landing.css`. | **Đã sửa** |
| **FE-02** | Trung bình | Đợt 2 | Khi gặp HTTP `409` (bấm *Thu thập ngay* lúc đang tạm dừng) hoặc `422` (từ khóa trùng hoa/thường), giao diện chỉ báo chung chung `"Yêu cầu thất bại (HTTP 409)."` hoặc *"lưu cấu hình thất bại"* mà nuốt mất lý do tiếng Việt từ Backend. | `api.ts` không trích xuất trường `detail` của phản hồi `409`/`422`; `ApiApp.tsx` chỉ in mã trạng thái HTTP. | **Đã sửa** |
| **FE-03** | Trung bình | Đợt 2 | Sau khi mở tab `Cảnh báo` một lần, bộ đếm `10 giây` vẫn gọi ngầm `GET /sentiment-timeline` và `GET /alerts` liên tục dù người dùng đã chuyển sang tab khác; bộ đếm `/runs` `30 giây` cũng chạy ở các tab không liên quan. | Các tab đã mở được giữ ẩn trong DOM (`hidden={tab !== id}`), nhưng `useEffect` trong `AlertsTab.tsx` và `ApiApp.tsx` không kiểm tra tab đang hiển thị. | **Đã sửa** |
| **FE-04** | Trung bình | Đợt 3 | Chuyển sang nhãn hàng khác (hoặc tạo nhãn hàng mới) nhưng ô lọc ngày `Bình luận từ` / `Bình luận trước` và lỗi đỏ của nhãn hàng cũ vẫn còn hiển thị trong mục `Chi tiết phiên`. | `openBrand()`, `startNew()`, `removeSelected()` và `disconnect()` trong `ApiApp.tsx` chưa reset `runCommentFrom`, `runCommentUntil`, `runCommentFilters`, `runCommentFilterError`. | **Đã sửa** |
| **FE-05** | Trung bình | Đợt 3 | Sau khi phiên thu thập ở tab `Phiên tracking` hoàn tất (`Thành công`), quay sang tab `Tổng quan` vẫn hiện `0 bài viết, 0 bình luận` cho tới khi bấm tay *Tải lại tổng quan*. | `BrandSummary` (`OverviewTab.tsx`) chỉ tải 1 lần lúc mount đầu tiên, không lắng nghe thay đổi danh sách phiên đã hoàn tất hoặc sự kiện mở lại tab. | **Đã sửa** |
| **FE-06** | Nhẹ | Đợt 2 & 3 | Sau khi tạo nhãn hàng thành công, form chỉ xóa ô `Tên` mà để sót lại `Từ khóa` và `Số bài mỗi lượt` cũ; khi tắt `Đang bật` (tạm dừng) rồi lưu, thông báo vẫn ghi *"Lịch hoạt động khi dịch vụ lịch được bật."* | `saveNew()` chưa reset `keywords`/`config`; `saveSelected()` dùng cứng một chuỗi thông báo bất kể `config.active`. | **Đã sửa** |
| **FE-07** | Nhẹ | Đợt 2 & 3 | Bộ lọc thời gian/nền tảng ở tab `Nội dung` và `Lọc bình luận của phiên` không có nút đặt lại nhanh, phải xóa tay từng ô `datetime-local`. | Chưa có nút **Xóa bộ lọc** trên `ContentTab.tsx` và `ApiApp.tsx`. | **Đã sửa** |
| **FE-08** | Nhẹ | Đợt 2 & 3 | Trên nhãn hàng thu thập thật (`NVIDIA`), bấm *Đánh giá lại lần thu thập gần nhất* báo *"Chưa có lần thu thập demo nào."*; mô tả email cảnh báo còn chữ *"demo"*; nút *Đánh giá cửa sổ đã hoàn tất* sau khi đã lưu quy tắc vẫn hiện tooltip *"Cần lưu quy tắc trước khi đánh giá"*. | Chuỗi văn bản cứng trong `AlertsTab.tsx` chưa phân biệt nhãn hàng thường với nhãn hàng mô phỏng, và thuộc tính `title` chưa ẩn khi quy tắc đã khớp. | **Đã sửa** |
| **FE-09** | Nhẹ | Đợt 1 & 2 | Trang thiếu `<meta name="description">` (Lighthouse SEO `75/100`); Chrome DevTools cảnh báo 21 trường biểu mẫu chưa gắn thuộc tính `name` hoặc `id`. | `index.html` chưa khai báo thẻ mô tả; các thẻ `<input>`, `<select>`, `<textarea>` bọc trong `<label>` chưa đặt `name`. | **Đã sửa** |

---

## 4. Chi tiết chỉnh sửa theo từng tệp mã nguồn

### 4.1. `frontend/src/lib/api.ts` — Trích xuất `detail` an toàn cho HTTP `409` và `422`
- **Vấn đề:** Dự án có ràng buộc bảo mật rõ trong `tests/api.test.ts` (*không hiển thị nội dung lỗi thô tùy ý từ máy chủ ra giao diện*). Tuy nhiên, việc bỏ qua hoàn toàn body lỗi khiến người dùng không biết vì sao bị từ chối khi cấu hình đang tạm dừng (`409`) hoặc nhập trùng từ khóa (`422`).
- **Cách sửa:**
  - Bổ sung thuộc tính tùy chọn `readonly detail?: string` vào lớp `ApiError` (giữ nguyên `error.message` mặc định `'Không thể hoàn thành yêu cầu'`).
  - Khai báo danh sách trắng (`KNOWN_ERROR_DETAILS`) chứa đúng các thông báo nghiệp vụ tiếng Việt hợp lệ của Backend (`Cấu hình tracking đang tạm dừng`, `Đã có phiên đang chạy`, `Từ khóa phải khác nhau và không rỗng`, `Nhãn hàng đang có tác vụ hoạt động`, v.v.).
  - Khi nhận HTTP `409` hoặc `422`, hàm `extractSafeDetail()` đọc `detail` dạng chuỗi (từ `HTTPException`) hoặc mảng lỗi validation của Pydantic (`Value error, ...`) và **chỉ nhận giá trị nằm trong danh sách cho phép**; mọi chuỗi lạ hoặc lỗi hệ thống nội bộ đều bị loại bỏ.

### 4.2. `frontend/src/ApiApp.tsx` — Quản lý state, thông báo lỗi, bộ lọc và polling phiên
- **Hiển thị nguyên nhân lỗi cụ thể (`FE-02`):**
  - Cập nhật `fail()`: nếu `ApiError` có `detail`, hiển thị `Yêu cầu thất bại (HTTP 409): Cấu hình tracking đang tạm dừng.` (khi không có `detail`, giữ nguyên `Yêu cầu thất bại (HTTP 503).` để tương thích tuyệt đối với smoke test).
  - Cập nhật nhánh `tracking-failed` trong `saveNew()` và nhánh lỗi `setTracking` trong `saveSelected()` để kèm lý do trong ngoặc đơn, ví dụ: `Đã tạo ..., nhưng lưu cấu hình thất bại (Từ khóa phải khác nhau và không rỗng)...`.
- **Chống rò rỉ bộ lọc giữa các nhãn hàng & thêm nút Xóa bộ lọc (`FE-04`, `FE-07`):**
  - Thêm hàm `resetRunCommentFilter()` xóa sạch `runCommentFrom`, `runCommentUntil`, `runCommentFilters`, `runCommentFilterError` và `commentOffsets`, gọi đồng bộ trong `openBrand()`, `startNew()`, `removeSelected()` và `disconnect()`.
  - Thêm nút **Xóa bộ lọc** tại biểu mẫu `Lọc bình luận của phiên` khi đang có giá trị lọc hoặc lỗi lọc.
- **Làm sạch biểu mẫu tạo mới & thông báo trạng thái lịch (`FE-06`):**
  - Trong `saveNew()`: reset thêm `setKeywords('')` và `setConfig(initialConfig)` sau khi tạo xong; phân biệt thông báo khi tạo ở trạng thái đang bật so với tạm dừng.
  - Trong `saveSelected()`: đồng bộ lại `config`/`keywords` sau khi lưu và hiển thị rõ `"Đã lưu. Đã tạm dừng lịch thu thập của nhãn hàng này."` khi người dùng tắt `Đang bật`.
- **Tối ưu polling danh sách phiên & truyền tín hiệu làm mới (`FE-03`, `FE-05`):**
  - Khi không có phiên đang `queued`/`running`, chỉ giữ polling `30 giây` nếu người dùng đang đứng ở tab `Phiên tracking` hoặc `Tổng quan` và cửa sổ trình duyệt đang hiển thị (`document.visibilityState !== 'hidden'`).
  - Tính khóa `runsSummaryKey` từ các phiên đã kết thúc và truyền cùng cờ `active={tab === 'overview'}` xuống `BrandSummary`, truyền `active={tab === 'alerts'}` xuống `RunAlertTimeline`.
- **Thuộc tính biểu mẫu (`FE-09`):** Bổ sung `name` cho toàn bộ ô nhập cấu hình và lọc bình luận.

### 4.3. `frontend/src/workspace/OverviewTab.tsx` — Tự động làm mới `Tổng quan`
- **Cách sửa (`FE-05`):**
  - Nhận thêm `active` và `refreshKey` từ `ApiApp.tsx`.
  - Khi một phiên thu thập kết thúc (`refreshKey` đổi) hoặc khi người dùng mở lại tab `Tổng quan` (`active` chuyển sang `true`), tự động tải lại ngầm `getOverview` và `getSentimentTimeline` mà không làm nhấp nháy khung tải nếu đã có dữ liệu trước đó (chỉ hiện trạng thái đang tải khi tải lần đầu hoặc khi người dùng chủ động bấm nút *Tải lại tổng quan*).

### 4.4. `frontend/src/workspace/AlertsTab.tsx` — Ngắt polling ngầm & hoàn thiện câu chữ
- **Cách sửa (`FE-03`, `FE-08`, `FE-09`):**
  - Trong `RunAlertTimeline`: chỉ chạy tải dữ liệu và bộ đếm `setInterval(..., 10000)` khi `active === true` (đang mở tab `Cảnh báo`) và bỏ qua lượt gọi nếu `document.visibilityState === 'hidden'`. Khi rời sang tab khác, bộ đếm được dọn sạch ngay.
  - Khi bấm *Đánh giá lại lần thu thập gần nhất* trên nhãn hàng thu thập thường (`!point.demo`), hiển thị hướng dẫn rõ: *"Đánh giá theo từng lần thu thập chỉ áp dụng cho dòng dữ liệu mô phỏng; với nhãn hàng thường, hãy dùng mục Quy tắc cảnh báo bên dưới."*
  - Lược bỏ từ *"demo"* thừa trong mô tả mục *Email nhận cảnh báo*, chỉ hiển thị `title="Cần lưu quy tắc trước khi đánh giá"` khi quy tắc thực sự chưa lưu, và gắn `name` cho các trường nhập liệu.

### 4.5. `frontend/src/workspace/ContentTab.tsx` & `AnalysisTab.tsx`
- **Cách sửa (`FE-07`, `FE-09`):**
  - Thêm nút **Xóa bộ lọc** trên `ContentTab.tsx` khi có điều kiện lọc nền tảng/thời gian hoặc thông báo lỗi lọc, giúp quay về danh sách gốc chỉ với 1 cú nhấp.
  - Bổ sung thuộc tính `name` cho các ô chọn nền tảng và khoảng thời gian trên cả hai tab.

### 4.6. `frontend/src/workspace/landing.css`, `Landing.tsx` & `frontend/index.html`
- **Cách sửa (`FE-01`, `FE-09`):**
  - Thay vì ẩn `.lp-nav-actions .lp-btn-ghost` ở màn hình `<= 560px`, tinh chỉnh kích thước chữ, khoảng đệm và `flex-wrap: wrap` cho `.lp-nav` để cả hai nút **Đăng nhập** và **Tạo tài khoản** đều hiển thị gọn gàng trên màn hình di động (`390px`) mà không tràn ngang.
  - Thêm thẻ `<meta name="description" ...>` vào `frontend/index.html` và thuộc tính `name="accessToken"` vào `Landing.tsx`.

### 4.7. `frontend/tests/api.test.ts` — Bổ sung kiểm thử đơn vị hồi quy
- Thêm ca kiểm thử `trích xuất detail an toàn trong danh sách cho phép với lỗi 409 và 422, chặn nội dung lạ` xác minh cả 3 trường hợp:
  1. HTTP `409` với `detail` hợp lệ (`Cấu hình tracking đang tạm dừng`) → gán đúng `error.detail`.
  2. HTTP `422` định dạng mảng lỗi Pydantic (`Value error, Từ khóa phải khác nhau và không rỗng`) → làm sạch tiền tố và gán đúng `error.detail`.
  3. Nội dung lỗi lạ không thuộc danh sách cho phép (`internal stacktrace secret`) → `error.detail === undefined` và không rò rỉ trong `error.message`.

---

## 5. Ghi nhận hành vi hệ thống giữ nguyên theo thiết kế (Lưu ý khi vận hành & quay Demo)

1. **Lưu token trong bộ nhớ RAM khi nhấn F5:** Ứng dụng chủ đích không lưu access/refresh token vào `localStorage`/`sessionStorage` để giảm rủi ro XSS (`cognito.ts`, `ApiApp.tsx`). Khi nhấn F5 trên Dashboard, trang quay về Landing Page; bấm **Đăng nhập** sẽ tự động vào lại thẳng Dashboard nhờ cookie SSO trên Cognito mà không cần nhập lại mật khẩu. Khi quay video demo nên tránh bấm F5 trực tiếp.
2. **Đóng kết nối Keep-Alive sau khoảng nghỉ ~60 giây:** Sau khi dừng thao tác khoảng 1 phút qua CloudFront, yêu cầu kế tiếp đôi khi gặp `ERR_CONNECTION_CLOSED`; giao diện đã bắt lỗi an toàn và thao tác lại thành công ngay.
3. **Cách lấy mẫu 30 nội dung mới nhất của Phân tích AI (Backend):** Backend hiện chọn tối đa 30 bản ghi có `observed_at` mới nhất trong khoảng thời gian đã chọn. Khi một phiên thu thập nhiều bài viết tuần tự, 30 bình luận mới nhất thường tập trung ở bài viết được lưu sau cùng (đây là giới hạn lấy mẫu phía backend, không phải lỗi giao diện).

---

## 6. Kiểm chứng sau chỉnh sửa & Trạng thái triển khai

- **Kiểm thử đơn vị (`node --test`):** **19/19 ca kiểm thử ĐẠT** (`0` thất bại, `1` ca kiểm thử tích hợp phụ thuộc môi trường bỏ qua như mặc định).
- **Kiểm tra kiểu dữ liệu & Build Production (`npm run build`):** `tsc --noEmit && vite build` **ĐẠT** (`dist/` đóng gói thành công, `0` lỗi).
- **Trạng thái triển khai AWS:** Bản sửa đã hoàn tất và kiểm chứng trên mã nguồn cục bộ; cần đồng bộ thư mục `frontend/dist/` lên S3 bucket giao diện (`brand-tracking-demo-frontend-202611-frontendbucket-zlbh2jwx90d9`) và tạo CloudFront invalidation (`E16UVUGRUO3EVT`) khi có phiên đăng nhập AWS CLI/SSO.
