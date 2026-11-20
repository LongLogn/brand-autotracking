# Backend thử nghiệm

Nền FastAPI và PostgreSQL cho phát triển; có API nhãn hàng, cấu hình, tạo phiên chờ và đọc phiên/bài/bình luận. Worker cục bộ nhận phiên chờ; scheduler thử nghiệm chạy khi được bật trong worker Lambda AWS. Route nghiệp vụ yêu cầu Cognito access token đã xác minh. Môi trường thử chưa đủ bảo vệ/vận hành để triển khai công khai.

Yêu cầu Python 3.11+, Docker Compose. Tại `backend/`, tạo `.venv`, cài `requirements.txt`. Đặt `POSTGRES_PASSWORD` và `DATABASE_URL` trong môi trường cục bộ bằng cách an toàn; database URL có dạng `postgresql+psycopg://brand_app:<password>@127.0.0.1:54329/brand_tracking` (mật khẩu cần mã hóa URL khi chứa ký tự đặc biệt). Dùng mật khẩu thử nghiệm riêng, không lưu vào Git hoặc log. Mật khẩu PostgreSQL được dùng khi volume mới được tạo; thay biến sau đó không đổi mật khẩu trong volume hiện có.

Ví dụ tạo mật khẩu ngẫu nhiên trong phiên PowerShell hiện tại, không dùng cho môi trường thật:

```powershell
$env:POSTGRES_PASSWORD = [guid]::NewGuid().ToString('N')
$env:DATABASE_URL = "postgresql+psycopg://brand_app:$env:POSTGRES_PASSWORD@127.0.0.1:54329/brand_tracking"
```

Giữ phiên này khi chạy các lệnh dưới đây. Sau khi đóng cửa sổ, cần khôi phục cùng mật khẩu theo cách lưu bí mật phù hợp để kết nối volume cũ; ví dụ ngẫu nhiên trên chỉ tiện cho lần chạy thử ban đầu.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d --wait
alembic upgrade head
uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000/docs` xem OpenAPI. Dừng container bằng `docker compose stop`; volume vẫn giữ dữ liệu. `GET /health` không kiểm tra database. Schema và API nghiệp vụ đang dự thảo trong [giai đoạn 3](../docs/development-process/s3_backend.md).

Migration `0006_comment_parent` yêu cầu mỗi bình luận gắn với phiên có bài cha trong cùng phiên. Nếu dữ liệu cũ vi phạm, migration dừng; kiểm tra và xử lý dữ liệu trước khi chạy lại, không tự xóa dữ liệu.

Migration `0007_brand_create_key` bổ sung khóa chống tạo trùng tùy chọn cho `POST /brands`: gửi header `Idempotency-Key` dạng UUID. Cùng tài khoản, cùng khóa và cùng tên chuẩn hóa trả lại cùng nhãn hàng; cùng khóa với tên khác trả 409. Khóa thuộc phạm vi tài khoản; yêu cầu không có khóa vẫn tạo mới. Triển khai backend và migration trước frontend mới, đồng thời cho phép header này qua CORS. Khóa giao diện chỉ giữ trong bộ nhớ, nên tải lại hoặc đóng trang có thể mất khả năng thử lại với cùng khóa.

Migration `0008_credit_reservations` tạo bảng dự phòng credit Firecrawl theo ngày UTC. Chạy migration trước khi triển khai worker mới. Hạ migration sẽ xóa lịch sử dự phòng, có thể làm mất khả năng giữ hạn mức của ngày hiện tại; không hạ khi cần giữ giới hạn.

Migration `0009_tracking_outbox` tạo outbox, bao gồm sự kiện cho các phiên còn chờ từ schema cũ. Worker Lambda có chế độ gửi SQS/DLQ tùy chọn; mặc định vẫn quét PostgreSQL. Xem [hướng dẫn hạ tầng](../infrastructure/README.md) trước khi bật; hạ migration xóa outbox và không an toàn khi sự kiện còn chờ.

Migration `0010_tracking_lease` thêm lease cho worker. Trước khi nâng cấp, dừng các nguồn kích hoạt và chờ mọi worker phiên bản cũ kết thúc; sau migration triển khai đồng bộ worker mới rồi mới bật lại. Worker cũ không kiểm tra lease nên không được chạy song song với worker mới. Phiên `running` cũ không có lease vẫn được bộ quét đánh dấu quá hạn theo ngưỡng cũ.

Khi frontend chạy khác origin, đặt `CORS_ORIGINS` thành danh sách origin cụ thể, cách nhau bằng dấu phẩy, ví dụ `http://localhost:5173`. Nếu không đặt, backend không bật CORS; các origin không có trong danh sách bị trình duyệt từ chối. Chỉ cho HTTP trên localhost, origin khác cần HTTPS; không dùng `*`.

Để dùng route nhãn hàng, cấu hình `COGNITO_ISSUER` là issuer HTTPS của user pool và `COGNITO_CLIENT_ID` là client ID tin cậy. API lấy JWKS từ issuer và kiểm tra chữ ký RS256, issuer, hạn, `token_use=access`, `client_id` và scope chính xác `brand-api/access`; token thiếu scope nhận 403. Chưa kiểm tra thu hồi token hoặc cấu hình API Gateway. Không tự khai `owner_id`: backend dùng `sub` đã xác minh. Luồng token Cognito thật với scope đã thử trên backend cục bộ.

Ví dụ nội dung `PUT /brands/{id}/tracking` (gửi kèm bearer token qua OpenAPI):

```json
{"keywords":["Starbucks"],"platforms":["tiktok"],"frequency":"daily","runTime":"08:00","timezone":"Asia/Ho_Chi_Minh","postLimit":1,"active":true}
```

API lưu cấu hình và thời điểm dự kiến; `active` không chứng minh dịch vụ lịch đang chạy. Nền tảng được lưu không có nghĩa đã được hỗ trợ. JWT hoặc dữ liệu cá nhân không đưa vào log. Xem `/docs` để biết hợp đồng tạm thời.

`PUT /brands/{id}` nhận `{"name":"Tên mới"}` để đổi tên nhãn hàng thuộc tài khoản hiện tại; trả 404 nếu không tìm thấy hoặc không thuộc tài khoản. Không có API xóa nhãn hàng.

`GET /brands/{id}/overview` trả `post_count`, `comment_count`, `run_count` và `latest_run` (null khi chưa có phiên). Số lượng là bản ghi đã lưu của nhãn hàng thuộc tài khoản, không phản ánh độ bao phủ; bài hoặc bình luận thiếu ID nguồn có thể bị đếm trùng. API không suy ra cảm xúc từ dữ liệu này.

`GET /brands/{id}/mentions` có thể lọc bằng `source`, `posted_from` và `posted_until` cùng phân trang. Hai endpoint bình luận tổng hợp và theo phiên cũng nhận `posted_from` và `posted_until` để lọc theo thời gian đăng bình luận. Thời gian phải có múi giờ; khoảng gồm đầu và không gồm cuối. Khi lọc thời gian, bản ghi thiếu `posted_at` không được đưa vào kết quả. Giao diện chưa có bộ lọc bình luận.

`POST /brands/{id}/runs` tạo phiên `queued` và không tự gọi Firecrawl. Để worker cục bộ xử lý, sau khi cấu hình `DATABASE_URL` và `FIRECRAWL_API_KEY` trong môi trường của chính worker, chạy từ `backend/`:

```powershell
python -m app.worker --max-calls 3 --daily-estimated-credit-budget 20
```

Tham số bắt buộc giới hạn số lần gọi provider trong **mỗi phiên**, từ 1–10. Mặc định lấy một trang tìm kiếm và một trang bình luận; `--search-pages` và `--comment-pages` cho phép tối đa ba trang mỗi loại, mỗi trang tính vào hạn mức gọi. `collection_limits` trong chi tiết phiên ghi giới hạn đã áp dụng, không chứng minh dữ liệu đầy đủ. Nếu trang sau lỗi hoặc hết hạn mức, dữ liệu các trang trong cùng lời gọi chưa được lưu và lượt được ghi lỗi. Chỉ adapter TikTok được thử; nguồn khác ghi lỗi `unsupported_source`.

`--max-attempts` từ 1–3, mặc định 1, cho phép thử lại một số lỗi tạm thời; mỗi lần thử tính vào hạn mức gọi và có thể bị tính phí kể cả khi timeout. `--estimated-credit-budget` đặt ngân sách credit **ước tính** cho mỗi phiên, dự phòng `--estimated-credits-per-call` credit trước mỗi lần gọi, kể cả thử lại; không hoàn dự phòng nếu provider không tính phí. Để trống ngân sách thì không giới hạn theo ước tính. Đây không phải giới hạn cứng ở Firecrawl, không chia sẻ ngân sách giữa các phiên/worker và không ngăn vượt mức nếu giá thực tế cao hơn dự phòng; cần đối chiếu giá trước khi cấu hình và theo dõi Usage. Có thể thêm `--once` để xử lý tối đa một phiên rồi thoát. Tùy chọn `--stale-after-minutes 30` bật quét để đánh dấu lỗi phiên có lease hết hạn; phiên cũ không có lease dùng ngưỡng 30 phút. Lease 10 phút được gia hạn trước mỗi lời gọi/trang/retry, không phải heartbeat nền; worker không có lease hợp lệ không được ghi. Một lời gọi đã bắt đầu vẫn có thể phát sinh chi phí. Worker không tự chạy lại phiên thất bại; trước khi dùng dữ liệu thật cần xác nhận điều kiện sử dụng nguồn, điều khoản provider và chi phí. Worker CLI không tự xếp lịch.

`--daily-estimated-credit-budget` là bắt buộc cho CLI và `run_tracking`: trước mỗi lần gọi, các worker dùng cùng database dự phòng nguyên tử vào một bảng chung theo ngày UTC của database; kể cả timeout hay lỗi cũng không hoàn dự phòng. Hai giá trị ngân sách ngày và credit dự phòng mỗi lần phải giống nhau trên mọi worker; từ lần đặt chỗ đầu tiên trong ngày, cấu hình khác bị từ chối đến ngày UTC tiếp theo. Không xóa hoặc sửa bảng để vượt giới hạn. Giá trị 0 chặn mọi lời gọi. Database lỗi hoặc chưa migration cũng chặn lời gọi. Giới hạn này vẫn chỉ là ước tính: nó không bao gồm các ứng dụng hoặc khóa khác dùng Firecrawl ngoài database này, không ngăn tính phí vượt dự phòng, và không thay thế giới hạn tài khoản hay theo dõi Usage.

Nếu nhãn hàng được tạm dừng trong lúc phiên còn chờ, worker đánh dấu phiên đó `skipped` mà không gọi Firecrawl. Phiên đã chạy dùng bản chụp cấu hình lúc tạo và tiếp tục hoạt động.

Trong API, `queued_at` là thời điểm tạo yêu cầu; `started_at` là `null` khi worker chưa bắt đầu. Kết quả từng lượt giữ liên kết bài với từ khóa; API sắp bài và bình luận theo lượt thích khả dụng, với chỉ số thiếu đứng sau chỉ số đã biết. Bộ kiểm thử mạng và xác thực sử dụng dữ liệu giả; chúng không chứng minh quyền hoặc khả năng tích hợp với dịch vụ thật.

Kiểm thử: cài `pip install -r requirements-dev.txt`; chạy `python -m unittest discover -s tests -v` từ `backend/`. Các kiểm thử PostgreSQL cần `TEST_DATABASE_URL` trỏ tới **database thử nghiệm riêng đã chạy migration**; khi thiếu biến chúng được bỏ qua. Không trỏ biến này đến dữ liệu thật.

Lượt kiểm thử Chrome với Cognito, worker Lambda, Firecrawl và PostgreSQL AWS thật đã hiển thị bài và bình luận theo lịch trong môi trường tạm. Worker cục bộ vẫn phải chạy riêng; hướng dẫn worker Lambda và công tắc lịch xem [hạ tầng](../infrastructure/README.md), kết quả và giới hạn xem [S5](../docs/development-process/s5_tracking.md).

Worker Lambda ghi sự kiện trạng thái và số phiên quá hạn dưới dạng JSON, không ghi nội dung thu thập hoặc khóa. Template có alarm cho phiên lỗi/một phần/quá hạn, lỗi thực thi Lambda, thiếu invocation và DLQ; có thể gắn SNS topic. Stack CloudWatch tạm đã thử alarm bằng log giả và đường SNS → SQS tạm; template worker đầy đủ và kênh người dùng chưa được kiểm thử đầu cuối.
