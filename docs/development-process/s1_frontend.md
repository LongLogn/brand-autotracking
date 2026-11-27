# Giai đoạn 1 — Phạm vi và frontend

**27/11/2026 — Giao diện kết nối chia tab:** Theo góp ý "xấu, nhiều chữ", giao diện kết nối backend chuyển từ một trang dài sang thanh nhãn hàng bên trái và 6 tab, kèm biểu đồ tỷ lệ tiêu cực theo lần thu thập. Logic API giữ nguyên. Thiết kế xem [DESIGN.md](../../frontend/DESIGN.md#bản-3--giao-diện-kết-nối-backend-2711).
- Đã kiểm chứng: build, 18 kiểm thử đơn vị (1 bỏ qua như trước), Chrome cục bộ với FastAPI xác thực giả và PostgreSQL 18 tạm: `demo-minute-browser.cjs`, `demo-browser.cjs`, `browser-smoke.cjs` đạt sau khi thêm bước mở tab.
- Đã tải lên CloudFront demo ngày 27/11; trang mở và chuyển Cognito đúng. Chưa chạy lại các script AWS (`aws-demo-*.cjs`, `cognito-browser.cjs`) trên bản mới.
- Ảnh (API giả lập): [tổng quan](evidence/ui-redesign-20261127-overview.png), [cảnh báo](evidence/ui-redesign-20261127-alerts.png), [AI](evidence/ui-redesign-20261127-analysis.png).

**26/11/2026 — Demo giả lập:** Chrome cục bộ, frontend/API/PostgreSQL riêng và xác thực giả đã thử tạo nhãn hàng, phát hai đợt, hiển thị nguồn giả không có liên kết giả, nạp lịch sử giả và đánh giá cảnh báo 10→15 không lặp; xem [kịch bản](../../frontend/tests/demo-browser.cjs) và [thư mục demo](../../demo/architecture.md). Chưa thử với Cognito/AWS.

**26/11/2026 — Kiểm thử tích hợp cục bộ:** Kiểm thử client tích hợp đã đạt với FastAPI và PostgreSQL 18 UTF-8 riêng, xác thực giả; Chrome smoke đạt với frontend, API và worker giả trên cùng database. Các tiến trình đã dừng. Đây không phải kiểm chứng Cognito/Firecrawl thật hoặc chất lượng AI. Thư mục PostgreSQL thử còn lại do lệnh dọn bị từ chối; xem [S3](s3_backend.md).

**23/11/2026 — Nhãn nguồn trong chế độ mẫu:** Sửa nhãn Reddit/Threads/Facebook thành dữ liệu minh họa, không khẳng định đã kiểm chứng thu thập; TikTok ghi rõ chưa mô phỏng ở chế độ mẫu nhưng đã được thử trong bản kết nối. Build và 18 kiểm thử frontend đạt, một tích hợp riêng bỏ qua. Phạm vi nguồn thật xem [S2](s2_firecrawl.md), [S5](s5_tracking.md).

**22/11/2026 — Kiểm thử tích hợp:** Client API và Chrome smoke đạt trên PostgreSQL 18 riêng với xác thực và provider giả. Đã sửa worker thử xử lý đúng phiên do trình duyệt tạo, kể cả khi còn phiên chờ khác. Chưa kiểm chứng Cognito hoặc Firecrawl thật trong phép thử này. [Kịch bản](../../frontend/tests/browser-smoke.cjs), [worker giả](../../backend/tests/browser_fake_worker.py).

**Cảnh báo 22/11/2026:** Giao diện kết nối cho phép lưu và tải lại quy tắc theo loại nội dung; thông báo rõ quy tắc chưa được đánh giá và chưa tạo cảnh báo. Chrome smoke với FastAPI/PostgreSQL 18 và xác thực giả đạt; xem [S6](s6_sentiment_alerts.md).

**22/11/2026:** Chi tiết phiên có điều khiển lọc thời gian đăng bình luận, dùng múi giờ thiết bị và giữ bộ lọc khi chuyển trang bình luận; áp dụng bộ lọc xóa kết quả cũ để người dùng mở lại. Build đạt, 17 kiểm thử frontend đạt và một kiểm thử tích hợp phụ thuộc môi trường được bỏ qua. Chrome smoke với FastAPI, PostgreSQL 18 cục bộ, xác thực và worker giả đạt, bao gồm khoảng thời gian không hợp lệ, tham số gửi và kết quả rỗng. Không phải kiểm thử Cognito hay Firecrawl thật. [Frontend](../../frontend/README.md).

**Lọc bình luận 19/11/2026:** Giao diện kết nối áp dụng khoảng thời gian đang chọn cho cả bài và bình luận tổng hợp; client hỗ trợ tham số thời gian cho cả bình luận tổng hợp và theo phiên. Build production đạt; 16 kiểm thử frontend đạt, 1 kiểm thử tích hợp phụ thuộc môi trường được bỏ qua. Chưa chạy lại Chrome smoke hoặc dữ liệu thật trong lượt này; màn hình chi tiết phiên chưa có điều khiển lọc bình luận riêng. [Frontend](../../frontend/README.md).

**Nội dung tổng hợp 17/11/2026:** Giao diện kết nối đã thêm phần đọc bài và bình luận tổng hợp từ API của nhãn hàng, phân trang, trạng thái tải/lỗi và làm mới; giữ chỉ số thiếu khác 0. `npm run build` và 16 kiểm thử frontend hiện có đạt. Chrome headless với backend và PostgreSQL tạm, xác thực và provider giả đã tạo phiên, chạy worker, tải bài và bình luận theo phiên lẫn tổng hợp; kịch bản browser smoke đạt và môi trường thử đã dọn. Chưa chứng minh nguồn hay Cognito thật trong lượt này. Cảnh báo và AI vẫn chưa nối dữ liệu thật. [Frontend](../../frontend/README.md).

**Tổng quan 17/11/2026:** Giao diện hiển thị số bài, bình luận, phiên và trạng thái phiên gần nhất từ API, kèm giới hạn về bản ghi thiếu ID và chưa phân tích cảm xúc. Build, kiểm thử client và Chrome headless với backend/PostgreSQL tạm cùng xác thực/provider giả đạt; đã sửa lỗi hai thành phần dùng cùng khóa React gây nhân bản khi cập nhật và thêm kiểm tra hồi quy. Tài nguyên thử đã dọn. [S3](s3_backend.md).

**Lọc nội dung 17/11/2026:** Giao diện đã thêm lọc bài theo nền tảng và thời gian đăng theo múi giờ thiết bị, hiển thị thời gian đăng bài/bình luận và nêu rõ bài thiếu thời gian bị loại khi lọc. Build, 16 kiểm thử frontend, 53 kiểm thử backend và Chrome smoke với xác thực/provider giả, PostgreSQL tạm đạt; tài nguyên thử đã dọn. Chưa hỗ trợ lọc riêng bình luận theo ngày. [S3](s3_backend.md).

**Cập nhật 17/11/2026:** Giao diện hiển thị lịch dự kiến từ backend, tự cập nhật danh sách phiên và mặc định một bài để phù hợp worker thử giới hạn hai lời gọi. Chrome với Cognito, API và worker AWS thật đã hiển thị dữ liệu của phiên chạy thủ công và theo lịch; build và kiểm thử Chrome hồi quy với backend/PostgreSQL tạm đạt. Xem [S5](s5_tracking.md); các màn hình tổng quan, cảnh báo và AI chưa nối dữ liệu thật.

Ngày 16/11 giao diện kết nối backend/Cognito trở thành mặc định; chế độ mẫu chỉ bật bằng `VITE_DEMO_MODE=true` và có nhãn minh họa. Có trạng thái tải và báo thiếu cấu hình Cognito; build và 16 kiểm thử frontend đạt. Kiểm thử Chrome với backend/PostgreSQL tạm, xác thực và worker giả đạt, bao gồm trạng thái tải và lỗi HTTP 503; kiểm thử lại hai tài khoản Cognito thật qua backend cục bộ đạt đăng nhập, refresh, cách ly và logout. Đã dọn tài khoản và database thử. Chưa chuyển các màn hình tổng quan, cảnh báo và AI sang dữ liệu thật. [Hướng dẫn](../../frontend/README.md).

Khi tạo nhãn hàng mất phản hồi hoặc server lỗi, giao diện báo kết quả chưa xác định và chặn tạo lại cho đến khi người dùng xác nhận đã kiểm tra danh sách. Backend hỗ trợ khóa chống tạo trùng theo tài khoản; giao diện giữ khóa trong bộ nhớ cho lần thử lại. Chrome với backend và PostgreSQL thử mô phỏng server đã tạo nhưng phản hồi mất, sau đó thử lại cho cùng một nhãn hàng. Tải lại trang làm mất khóa; xem [S3](s3_backend.md).

Khi tải cấu hình thất bại, giao diện khóa form và cung cấp nút tải lại; kiểm thử Chrome mô phỏng lỗi mạng, xác nhận không thể sửa trước khi tải thành công. Database và tiến trình thử đã dọn.

**Cập nhật:** 23/11/2026. **Trạng thái:** Đang thực hiện; các luồng chính đã thử qua frontend kết nối, còn giới hạn nghiệm thu và nguồn như các cập nhật phía trên.

- [Frontend](../../frontend/README.md) có giao diện React, TypeScript và Vite với các màn hình chính, dùng dữ liệu mẫu; chưa kết nối API, Cognito hay Firecrawl. Tài liệu có hướng dẫn chạy nhưng lượt cập nhật hiện trạng này chưa chạy lại ứng dụng.
- Trước tích hợp đã có client API thử nghiệm và trạng thái phiên chờ, khi đó chưa nối client với store hoặc Cognito; giao diện dùng dữ liệu mẫu.
- Ngày 16/11 bổ sung các lớp thử nghiệm tạo nhãn hàng/cấu hình và đọc dữ liệu tracking theo trang; 11 kiểm thử client và HTTP với backend, PostgreSQL tạm và xác thực giả đạt, build thành công. Chưa nối các lớp vào màn hình; chi tiết và giới hạn tại [S3](s3_backend.md).
- Ban đầu ngày 16/11 bổ sung giao diện thử API riêng: nhập access token trong bộ nhớ, tạo/sửa nhãn hàng và cấu hình, xếp phiên, xem kết quả theo trang. Thời điểm đó giao diện mẫu vẫn mặc định và chưa kiểm thử Cognito. Cấu hình hiện tại và giới hạn tại [frontend/README.md](../../frontend/README.md).
- Kiểm thử trình duyệt Chrome headless với backend HTTP, PostgreSQL tạm và xác thực giả: tạo nhãn hàng, sửa/tải lại cấu hình, tạo và xem phiên chờ, ngắt kết nối, mô phỏng lỗi lưu cấu hình rồi thử lại không tạo trùng đều đạt. Đã sửa lỗi cho phép chỉnh form khi cấu hình đang tải. Kiểm thử chưa chạy worker hoặc xác thực thật; database tạm đã được xóa. Kịch bản: [browser-smoke.cjs](../../frontend/tests/browser-smoke.cjs).
- Chưa có bằng chứng chốt nguồn MVP, thống nhất hợp đồng dữ liệu frontend/backend hoặc nghiệm thu toàn bộ luồng giao diện.
- Tiếp theo: kiểm tra các màn hình và luồng, thống nhất phạm vi và dữ liệu cần backend cung cấp theo [lộ trình](../development_roadmap.md).



**Kiểm thử dữ liệu thật 16/11/2026:** Chrome tạo nhãn hàng và phiên → worker Firecrawl thật → PostgreSQL tạm → giao diện hiển thị một bài và 20 bình luận. Giao diện tự tải lại danh sách khi phiên đang chờ/chạy; worker vẫn phải chạy riêng. Xác thực trong lượt này là giả, database thử đã dọn; chưa chứng minh triển khai AWS hoặc lịch tự động. Build frontend đạt. [S5](s5_tracking.md).
