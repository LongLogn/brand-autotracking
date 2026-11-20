# Giai đoạn 3 — Backend và cơ sở dữ liệu

**19/11/2026:** Hai API bình luận tổng hợp và theo phiên nhận bộ lọc thời gian đăng `posted_from`/`posted_until`, đầu gồm và cuối không gồm; thiếu thời gian bị loại khi lọc. PostgreSQL 17 thử được tạo mới, migration đến `0010`, `alembic check` và toàn bộ 64 kiểm thử backend đều đạt; container, network và volume thử đã dọn. Client frontend hỗ trợ cả hai endpoint và giao diện kết nối áp dụng khoảng thời gian cho bình luận tổng hợp; chưa kiểm chứng lại trên AWS hoặc Chrome smoke. Xem [backend](../../backend/README.md) và [S1](s1_frontend.md).

**Tổng quan 17/11/2026:** `GET /brands/{id}/overview` trả số bài, bình luận và phiên đã lưu cùng phiên gần nhất; truy vấn giới hạn theo nhãn hàng thuộc tài khoản, tài khoản khác nhận 404. Các số là bản ghi đã lưu, có thể gồm nội dung trùng khi thiếu ID nguồn, không phải độ bao phủ hay phân loại cảm xúc. Kiểm thử backend với PostgreSQL tạm đạt. [Backend](../../backend/README.md).

**Lọc nội dung 17/11/2026:** API tổng hợp bài hỗ trợ lọc nguồn và khoảng thời gian đăng có múi giờ, đầu bao gồm và cuối không bao gồm; bài thiếu thời gian đăng không nằm trong kết quả khi lọc thời gian. 53 kiểm thử backend PostgreSQL và 16 kiểm thử frontend đạt; chưa kết luận dựa trên dữ liệu nguồn thật. [Backend](../../backend/README.md).

Ngày 16/11 bổ sung migration `0007_brand_create_key` và header `Idempotency-Key` UUID tùy chọn cho `POST /brands`: cùng chủ sở hữu và khóa với cùng tên trả cùng ID; tên khác trả 409; tài khoản khác có phạm vi riêng. Kiểm thử PostgreSQL với hai yêu cầu đồng thời đạt; nâng, hạ, nâng lại migration trên database thử và `alembic check` đạt. Khách hàng không gửi khóa vẫn tạo mới; cần chạy migration trước khi triển khai frontend mới. Xem [backend](../../backend/README.md).

**Cập nhật:** 16/11/2026. **Trạng thái:** Đang thực hiện; chưa hoàn thành.

- Ngày 16/11 bổ sung `PUT /brands/{id}` đổi tên, kiểm tra chủ sở hữu và đầu vào; client thử nghiệm có hàm tương ứng và tham số `limit`/`offset` cho các danh sách. Bộ 25 kiểm thử backend chạy trên PostgreSQL 17 tạm đã migration đều đạt, gồm kiểm tra tài khoản khác không đổi được tên. Client được kiểm thử riêng; giao diện vẫn chưa kết nối.

- [SRS](../software_requirements_specification.md) và [kiến trúc](../architecture_aws.md) mô tả yêu cầu và phương án dự thảo. [Backend](../../backend/README.md) có FastAPI API nhãn hàng, cấu hình, tạo phiên chờ và đọc phiên/bài/bình luận; xác minh Cognito access token, PostgreSQL cục bộ và worker thử nghiệm. `health` chỉ kiểm tra tiến trình, không kiểm tra DB. Chưa có scheduler; chưa xác minh Cognito thật, scope, worker với Firecrawl thật hay frontend kết nối; không triển khai công khai.
- Có thể chuẩn bị thiết kế song song với [kiểm chứng nguồn](s2_firecrawl.md), nhưng các trường và khả năng phụ thuộc nguồn chưa chốt.
- Tiếp theo: thiết kế dữ liệu, hợp đồng API và lỗi/trạng thái; thống nhất với frontend, sau đó thiết lập và kiểm thử môi trường backend, database và migration theo lộ trình.

## Kết quả kiểm tra ngày 15/11/2026

- Cài phụ thuộc trong môi trường ảo cục bộ; chạy Uvicorn và gọi `GET /health` qua HTTP thành công; tạo OpenAPI có route này. Endpoint không kiểm tra database.
- Khởi chạy PostgreSQL 17 trong container thử nghiệm riêng, chạy `alembic upgrade head`, kiểm tra bảng `users`, `brands`, `alembic_version`, kết nối `SELECT 1` và `alembic check` không phát hiện sai khác với mô hình hiện tại. Container và volume thử nghiệm đã được xóa sau kiểm thử.
- Chưa kiểm thử tải hoặc triển khai AWS. Cấu hình và cách chạy xem [backend/README.md](../../backend/README.md).
- Bổ sung kiểm thử với JWT RSA ký bằng khóa thử và PostgreSQL container: token thiếu, sai loại, hết hạn, sai client, chữ ký sửa bị từ chối; cấu hình xác thực lỗi trả 503; tài khoản B không thấy nhãn hàng A; dữ liệu đầu vào thừa/không hợp lệ bị từ chối. Chưa kiểm chứng Cognito, JWKS mạng thực, API Gateway, scope hoặc xóa/sửa nhãn hàng. Container và volume thử đã được dọn.
- Migration tạo cấu hình, từ khóa, nguồn, phiên/lượt, bài, bình luận, liên kết phiên/lượt và snapshot tương tác. Đã kiểm tra nâng/hạ migration trên PostgreSQL, `alembic check` không báo khác biệt; kiểm thử cấu hình, xác thực, truy cập chéo, dữ liệu không hợp lệ và snapshot theo phiên. Ràng buộc khóa ngoại ghép ngăn liên kết phiên–bài–bình luận khác nhãn hàng; kiểm thử các trường hợp trùng ID, thiếu ID và snapshot không có đối tượng. Worker cục bộ đã thử với provider giả; chưa chạy luồng worker với dữ liệu Firecrawl thật.

## Thiết kế sơ bộ để thống nhất

- Danh tính lấy từ Cognito sau khi xác minh access token; tất cả truy vấn nghiệp vụ ràng buộc chủ sở hữu, không lấy `owner_id` từ client. Hai bảng đầu chỉ chuẩn bị schema, chưa cung cấp đường truy cập nghiệp vụ.
- Mô hình dự kiến: `users` → `brands` → từ khóa, nguồn và cấu hình; phiên tracking có các lượt theo nguồn/từ khóa; bài và bình luận có định danh nguồn, liên kết đến phiên và snapshot chỉ số. Cảnh báo, phân loại và phân tích AI tham chiếu đúng nhãn hàng và dữ liệu đầu vào. Bảng cụ thể và chính sách xóa còn cần thống nhất.
- Trường thiếu từ nguồn biểu diễn `null`, phân biệt với số 0; trạng thái phiên cần phân biệt thành công, một phần, lỗi, bỏ qua và lượt thành công rỗng. Không suy luận bài/bình luận đầy đủ từ Markdown; loại nguồn và trường lấy được phụ thuộc [S2](s2_firecrawl.md).
- API dự kiến gồm tạo/liệt kê/cập nhật nhãn hàng, cấu hình tracking, lịch sử phiên và nội dung theo nhãn hàng. Cần chốt request/response, phân trang, xác thực và mã lỗi cùng frontend trước khi gọi đây là hợp đồng đã thống nhất. Không coi API ví dụ trong lộ trình là API đã chạy.

## Hợp đồng thảo luận với frontend

- Hiện `POST /brands` chỉ nhận tên, `GET /brands` trả danh sách có `limit`/`offset`; cấu hình lưu riêng qua `GET`/`PUT /brands/{id}/tracking`. API có đọc danh sách/chi tiết phiên, bài tổng hợp/theo phiên, bình luận theo bài; phản hồi hiện dùng snake_case cho dữ liệu phiên/bài, chưa khớp hoàn toàn với kiểu frontend và chưa được frontend/backend thống nhất. Chưa hỗ trợ lọc, API ghi kết quả hoặc phân loại/cảnh báo/AI.
- Ánh xạ các trường giao diện theo [types.ts](../../frontend/src/data/types.ts): thời điểm dùng ISO 8601 có múi giờ, chỉ số không khả dụng là `null`; `attempt.status` phân biệt `success`, `empty`, `failed` và phiên có thể `partial`. Kết quả phân tích giữ tham chiếu dẫn chứng thuộc đúng nhãn hàng. Danh sách nền tảng của frontend cần cập nhật sau kiểm chứng S2.
- Xếp hạng bài chỉ dựa trên chỉ số thực sự thu được và trong tập kết quả Search, không khẳng định tìm được bài tương tác cao nhất toàn nền tảng. Định nghĩa chỉ số và cách xử lý bài thiếu số liệu chưa được thống nhất; không thay thiếu bằng 0.
- Dự kiến lỗi 401 cho thiếu hoặc sai thông tin xác thực, 404 cho tài nguyên không thuộc chủ sở hữu hoặc không tồn tại, 422 cho đầu vào không hợp lệ; mã lỗi chi tiết và hình dạng JSON cần thống nhất trước khi triển khai. Không dựa vào JWT hay owner ID do client tự khai.

## Hợp đồng API thử nghiệm hiện tại

- Dùng `Authorization: Bearer <Cognito access token>`; 401 cho token không hợp lệ, 503 khi cấu hình hoặc dịch vụ JWKS không sẵn sàng, 404 khi không tìm thấy tài nguyên thuộc người dùng, 422 khi sai dữ liệu. Lỗi không bao gồm khóa hay token.
- `POST /brands` nhận `{"name":"..."}` trả `{"id":"UUID","name":"..."}`; `GET /brands?limit=50&offset=0` trả mảng các đối tượng cùng kiểu. `PUT /brands/{id}` đổi tên theo cùng định dạng; chưa hỗ trợ xóa nhãn hàng.
- `PUT /brands/{id}/tracking` nhận `keywords`, `platforms`, `frequency`, `runTime`, `timezone`, `postLimit`, `active`; `GET` trả cùng cấu trúc. Cấu hình có hiệu lực lưu trữ nhưng không tạo lịch. Ví dụ đầy đủ trong [README backend](../../backend/README.md).
- `POST /brands/{id}/runs` tạo phiên `queued`, 409 nếu cấu hình không phù hợp hoặc đã có phiên chờ/chạy; worker riêng nhận phiên. `GET /brands/{id}/runs`, `GET /brands/{id}/runs/{run_id}` (có `attempts`, `collection_limits`), `GET /brands/{id}/runs/{run_id}/mentions`, `GET /brands/{id}/runs/{run_id}/mentions/{post_id}/comments`, `GET /brands/{id}/mentions` và `GET /brands/{id}/mentions/{post_id}/comments` đọc dữ liệu có sẵn. Các danh sách nhận `limit` và `offset`. Chỉ số theo phiên lấy snapshot của phiên, còn tổng hợp lấy snapshot mới nhất; chưa lọc theo ngày/nguồn và chưa có tính toán cảm xúc.
- Backend cung cấp mô tả request/response chi tiết qua `/docs`; đây là hợp đồng phát triển tạm thời, chưa kết nối giao diện mẫu hoặc thống nhất là hợp đồng cuối cùng.
- API bài/bình luận báo `maybe_duplicate=true` khi thiếu ID nguồn. Chỉ số thiếu là `null`; API sắp theo lượt thích khả dụng, `null` xếp sau 0. Ràng buộc database ngăn liên kết chéo nhãn hàng và yêu cầu bài cha của bình luận thuộc cùng phiên. Migration `0006_comment_parent` bổ sung ràng buộc; nếu dữ liệu cũ vi phạm, migration sẽ thất bại để xử lý dữ liệu thay vì tự xóa. Chưa hỗ trợ thu thập các trang tiếp theo.
- CORS chỉ bật khi cấu hình `CORS_ORIGINS` là các origin cụ thể; HTTP chỉ dành cho localhost. Client frontend thử nghiệm và CORS đã được kiểm thử qua HTTP với backend, database tạm và xác thực giả; chưa chứng minh Cognito hoặc trình duyệt với dữ liệu thật hoạt động.
- `queued_at` ghi lúc tạo yêu cầu, `started_at` là `null` đến khi worker nhận. Client [frontend](../../frontend/src/lib/api.ts) đã được kiểm thử qua HTTP với backend thật và xác thực giả; chưa nối vào store/màn hình hiện tại, hợp đồng frontend vẫn chưa hoàn thiện.
- Migration thời điểm hàng chờ đã được kiểm thử nâng cấp dữ liệu cũ, hạ phiên bản với phiên chưa bắt đầu và nâng lại trên PostgreSQL tạm; `alembic check` không báo sai khác. Các kiểm thử hoàn tất ngày 15/11/2026 dùng database và JWT thử, không thay thế kiểm thử với Cognito/Firecrawl thực tế.

## Đối chiếu tích hợp giao diện ngày 16/11/2026

Đối chiếu `frontend/src/data/types.ts`, `frontend/src/lib/store.tsx`, `frontend/src/lib/api.ts` và mô hình phản hồi trong `backend/app/main.py` cho thấy store hiện đồng bộ và dùng fixture; client HTTP là bất đồng bộ. Không thể thay trực tiếp store mà giữ nguyên giả định dữ liệu mẫu.

- API tách tên nhãn hàng và cấu hình tracking thành hai yêu cầu; giao diện còn có `description` và `nextRunAt` nhưng API hiện không cung cấp. Lưu từng bước cần xử lý lỗi một phần và tải lại trạng thái đã lưu.
- Phiên chờ có `started_at=null`, trong khi kiểu `Run.startedAt` của giao diện bắt buộc là chuỗi; cần hiển thị thời điểm xếp hàng riêng, không giả làm thời điểm bắt đầu. `attempt.result_count` có thể null, không thay bằng 0.
- API bài trả nội dung và chỉ số nullable; giao diện còn yêu cầu từ khóa, danh sách phiên, cảm xúc và bình luận lồng nhau. Cần tải dữ liệu theo endpoint và thể hiện trường chưa có là không khả dụng; không gán cảm xúc hay suy ra từ khóa từ dữ liệu thiếu. Danh sách đã lưu có phân trang, cần xử lý các trang khi giao diện cần đầy đủ.
- Cảnh báo và phân tích AI chưa có API; phải phân biệt rõ dữ liệu mẫu với dữ liệu thật khi tích hợp, tránh hiển thị fixture như kết quả của tài khoản.

Bước tiếp theo: thống nhất cách thể hiện các trường chưa được backend cung cấp, sửa kiểu dữ liệu và luồng tải bất đồng bộ, sau đó kiểm thử tích hợp với xác thực thử trước khi kiểm chứng Cognito thật.

## Chuẩn bị tích hợp ngày 16/11/2026

- Ban đầu thêm lớp `frontend/src/lib/brand-workflow.ts`: khi tạo nhãn hàng thành công nhưng lưu cấu hình thất bại, trả lại ID để thử lại riêng bước cấu hình. Sau đó bổ sung khóa chống trùng như ghi ở đầu tài liệu; khóa giao diện không tồn tại qua lần tải lại trang.
- `frontend/src/lib/tracking-view.ts` tải chi tiết phiên và một trang bài, hoặc một trang bình luận; giữ riêng thời điểm chờ/bắt đầu và giữ `null` khác 0. Không coi số phần tử một trang là tổng số. Các lớp này chưa nối store hoặc màn hình.
- Chạy 11 kiểm thử client và tích hợp qua HTTP với FastAPI, PostgreSQL 17 tạm và xác thực giả: đều đạt; có kiểm tra tạo nhãn hàng, cấu hình và đọc phiên chờ. Container thử nghiệm đã dừng và tự xóa. `npm run build` thành công. Không chứng minh Cognito hoặc Firecrawl thật.
- Tiếp theo: tích hợp các luồng bất đồng bộ vào giao diện, xử lý trạng thái tải/lỗi và dữ liệu chưa khả dụng; không trộn fixture cảnh báo/AI với dữ liệu thật.
