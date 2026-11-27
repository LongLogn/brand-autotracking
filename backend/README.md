# Backend thử nghiệm

**Hủy phiên:** `POST /brands/{brand_id}/runs/{run_id}/cancel` chỉ cho chủ nhãn hàng hủy phiên `queued`; phiên thành `cancelled`, gọi lại cùng phiên trả thành công, phiên đã bắt đầu trả 409. Worker bỏ qua phiên đã hủy ngay cả khi thông điệp đã vào SQS. Chưa triển khai AWS.

## Demo theo phút: cảnh báo theo lần thu thập (27/11)

Migration `0020_run_alerts` thêm vào bảng `alerts` các cột `mode` (`window` | `run`), `run_id`, `previous_total`, `current_total`, `notified_at`, kèm ràng buộc một cảnh báo cho mỗi phiên. Hạ migration xóa các cảnh báo `run`.

- [demo_stream.py](app/demo_stream.py): kịch bản 3 đợt, mỗi đợt 1 bài và 100 bình luận giả: mốc 20 tiêu cực, đợt tiêu cực 40, đợt tích cực 5. Lũy kế lần lượt là 20/100, 60/200, 65/300.
- [demo_alerts.py](app/demo_alerts.py): sau mỗi phiên demo thành công:
  - gán nhãn giả lập theo câu mẫu (model `demo-fixture-labels`, không gọi Bedrock);
  - so sánh tỷ lệ tiêu cực lũy kế với lần trước theo quy tắc **bình luận**: `growth_percent`, `minimum_current`;
  - lưu tối đa một cảnh báo cho mỗi phiên;
  - gửi qua SES tới email cấu hình riêng theo nhãn hàng khi có `ALERT_SENDER_EMAIL` và `APP_BASE_URL`; `notified_at` được đánh dấu trước khi gọi SES, không chứng minh SES đã nhận yêu cầu.
- Chỉ áp dụng cho phiên có `demo_session`. Cảnh báo theo cửa sổ ngày cho dữ liệu thật không đổi.
- [demo_scheduler.py](app/demo_scheduler.py): lịch chỉ tự xếp tới `DEMO_AUTO_BATCHES` đợt. Đợt sau được xếp khi worker nhận sự kiện `{"demo_action": "release_next"}`.
- API:
  - `GET/PUT /brands/{id}/alert-recipients`: xem/thay th? t?i ?a 10 ??a ch? nh?n ri?ng theo nh?n h?ng; danh s?ch r?ng t?t g?i.
  - `GET/PUT /brands/{id}/alert-recipients`: xem hoặc thay thế tối đa 10 địa chỉ nhận; danh sách rỗng tắt gửi.
  - `GET /brands/{id}/sentiment-timeline`: tỷ lệ lũy kế sau từng phiên thành công gần nhất, tối đa 50 phiên.
  - `POST /brands/{id}/alerts/evaluate-latest-run`: đánh giá lại phiên demo gần nhất; nếu đã có cảnh báo thì trả lại cảnh báo đó, không tạo bản sao.
  - `GET /brands/{id}/alerts` trả thêm các trường mới.
- [server.py](app/server.py): entrypoint cho EC2 (`uvicorn app.server:app`). Khi `API_PATH_PREFIX=/api`, tiền tố này được bỏ để dùng lại các route sẵn có.
- Chạy kịch bản cục bộ (database `brand_demo` trên localhost, xem mục bên dưới): `python -m app.demo_stream --scenario --brand-id <UUID> --batches 2 --interval 5`. Lệnh in `demo_session=<id>`; chạy tiếp đợt tích cực bằng `--batches 1 --session-id <id>`. Cục bộ không gửi email.

**Đã kiểm thử 27/11:**
- PostgreSQL 18 UTF-8 riêng: migration đến `0020`, `alembic check` sạch, 132 kiểm thử backend đạt, không bỏ qua test nào. Trong đó [test_demo_alerts.py](tests/test_demo_alerts.py) kiểm tra:
  - đủ kịch bản và đúng một email;
  - đánh giá lại và gửi lỗi không tạo bản sao;
  - quy tắc tắt và lần mốc;
  - API và xóa nhãn hàng.
- Chrome cục bộ: xem [frontend README](../frontend/README.md).

**Trên AWS 27/11:** worker Lambda và API trên EC2 đã chạy đúng kịch bản; AI phân tích thành công sau khi nâng `maxTokens` lên 3000 (xem [S7](../docs/development-process/s7_ai_analysis.md)). **Chưa thử SNS gửi email thật.**

## Bộ sinh dữ liệu demo cục bộ (bước đầu)

`python -m app.demo_stream --brand-id <UUID> --batches 3 --interval 10 --comments 6` phát tối đa 20 đợt qua xử lý tracking hiện có, dừng bằng Ctrl+C. Trước đó cần database PostgreSQL riêng tên `brand_demo` trên localhost đã migration, cấu hình nhãn hàng đang hoạt động với nguồn TikTok và biến `DEMO_DATABASE_URL` trỏ tới database đó (URL không có query). Không dùng database chứa dữ liệu cần giữ. Chương trình không gọi Firecrawl; nội dung gắn `[DỮ LIỆU GIẢ]`, kết quả ghi nguồn `demo` và URL `.invalid`. Đã kiểm thử lưu hai phiên qua PostgreSQL, chưa kiểm thử giao diện; luồng AWS có công tắc riêng và chưa thử thực tế. Tiến độ xem [thư mục demo](../demo/architecture.md).

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

`DELETE /brands/{id}` chỉ cho chủ sở hữu xóa vĩnh viễn nhãn hàng và dữ liệu liên quan trong database. API trả 409 khi phiên đang chờ/chạy hoặc tác vụ phân loại/phân tích còn trạng thái đang chạy; đợi tác vụ kết thúc rồi thử lại. Giao diện yêu cầu xác nhận. Thao tác không xóa ngay dữ liệu có trong snapshot/backup, không xóa nội dung tại nguồn, không thu hồi dữ liệu đã gửi tới dịch vụ ngoài và không xóa bảng dự phòng credit dùng chung. Đã kiểm thử PostgreSQL cục bộ và xác nhận xóa qua CloudFront/Cognito/AWS; xem [S4](../docs/development-process/s4_accounts_brands.md).

Migration `0007_brand_create_key` bổ sung khóa chống tạo trùng tùy chọn cho `POST /brands`: gửi header `Idempotency-Key` dạng UUID. Cùng tài khoản, cùng khóa và cùng tên chuẩn hóa trả lại cùng nhãn hàng; cùng khóa với tên khác trả 409. Khóa thuộc phạm vi tài khoản; yêu cầu không có khóa vẫn tạo mới. Triển khai backend và migration trước frontend mới, đồng thời cho phép header này qua CORS. Khóa giao diện chỉ giữ trong bộ nhớ, nên tải lại hoặc đóng trang có thể mất khả năng thử lại với cùng khóa.

Migration `0008_credit_reservations` tạo bảng dự phòng credit Firecrawl theo ngày UTC. Chạy migration trước khi triển khai worker mới. Hạ migration sẽ xóa lịch sử dự phòng, có thể làm mất khả năng giữ hạn mức của ngày hiện tại; không hạ khi cần giữ giới hạn.

Migration `0009_tracking_outbox` tạo outbox, bao gồm sự kiện cho các phiên còn chờ từ schema cũ. Worker Lambda có chế độ gửi SQS/DLQ tùy chọn; mặc định vẫn quét PostgreSQL. Xem [hướng dẫn hạ tầng](../infrastructure/README.md) trước khi bật; hạ migration xóa outbox và không an toàn khi sự kiện còn chờ.

Migration `0010_tracking_lease` thêm lease cho worker. Trước khi nâng cấp, dừng các nguồn kích hoạt và chờ mọi worker phiên bản cũ kết thúc; sau migration triển khai đồng bộ worker mới rồi mới bật lại. Worker cũ không kiểm tra lease nên không được chạy song song với worker mới. Phiên `running` cũ không có lease vẫn được bộ quét đánh dấu quá hạn theo ngưỡng cũ.

Migration `0011_alert_rules` thêm bảng lưu quy tắc cho từng nhãn hàng và loại nội dung. Chạy migration trước backend mới; hạ migration xóa toàn bộ quy tắc đã lưu. `GET /brands/{id}/alert-rules` liệt kê, `PUT /brands/{id}/alert-rules/{post|comment}` lưu/bật/tắt quy tắc thuộc tài khoản hiện tại. Dữ liệu gồm `enabled`, `growth_percent` (số nguyên 0–1000), `window_days` (1–90), `minimum_current` (1–1.000.000), `absolute_threshold` (null hoặc 1–1.000.000).

Migration `0014_observation_evidence` lưu thời điểm/hash được quan sát trong phiên; bản ghi cũ giữ null, không tự giả định. Migration `0015_alert_history` lưu lịch sử và khóa chống trùng; hạ hai migration làm mất bằng chứng/lịch sử tương ứng. `POST /brands/{id}/alert-rules/{post|comment}/evaluate` nhận `{"window_end":"2026-01-03T00:00:00Z"}` (00:00 UTC đã qua) để đánh giá thủ công; `GET /brands/{id}/alerts` đọc lịch sử phân trang. Thiếu lịch, phiên, ID hoặc phân loại trả `insufficient_data`, không tạo cảnh báo. Lambda đánh giá sau phiên khi `ALERT_EVALUATION_ENABLED=true`, mặc định tắt; đánh giá thủ công đã thử qua AWS với dữ liệu giả, chưa chứng minh độ bao phủ thật. Chi tiết giới hạn tại [S6](../docs/development-process/s6_sentiment_alerts.md).

Migration `0012_sentiment_results` lưu nhãn cảm xúc gắn với hash nội dung, model và nhãn hàng; hạ migration xóa kết quả. Migration `0013_bedrock_call_budget` lưu lượt gọi Bedrock đã dự phòng trong ngày UTC; hạ migration xóa lịch sử hạn mức, không hạ khi cần giữ giới hạn. Lambda có bước phân loại tùy chọn sau phiên và API trả nhãn hiện tại, nhưng mặc định tắt; Bedrock và worker đã được thử giới hạn trên AWS, chưa nghiệm thu chất lượng phân loại đại diện. Bản ghi chưa phân loại, lỗi hoặc nội dung đã đổi thể hiện `unknown`; nhãn ở trang chi tiết phiên là theo nội dung hiện tại, không phải snapshot lịch sử. [S6](../docs/development-process/s6_sentiment_alerts.md).

Migration `0016_analysis_jobs` lưu yêu cầu và kết quả phân tích; hạ migration xóa lịch sử. `POST /brands/{id}/analyses` nhận `window_start`, `window_end` có múi giờ, khoảng tối đa 90 ngày và header `Idempotency-Key` UUID; dùng lại cùng khóa/khoảng không gọi model lần hai, khác khoảng trả 409. `GET /brands/{id}/analyses` trả lịch sử phân trang thuộc tài khoản. API chỉ chạy khi `ANALYSIS_ENABLED=true`, `ANALYSIS_MODEL_ID` hợp lệ và `BEDROCK_DAILY_CALL_LIMIT` dương; dùng chung bảng hạn mức với phân loại nên mọi worker phải dùng cùng giá trị. Không có dữ liệu, hết hạn mức hoặc provider lỗi tạo kết quả `failed`, không giả lập phân tích thành công. Yêu cầu quá hai phút theo đồng hồ database được đánh dấu `failed/timeout` khi đọc lịch sử, thử lại cùng khóa hoặc worker quét; kết quả đến muộn bị từ chối, không tự gọi lại. Đã thử Bedrock thật từ backend cục bộ với dữ liệu giả; kiểm tra ID dẫn chứng không xác minh ngữ nghĩa hay ngăn hết prompt injection. [S7](../docs/development-process/s7_ai_analysis.md).

Migration `0017_sentiment_version` đánh dấu phiên bản thuật toán phân loại; kết quả cũ không có hoặc khác phiên bản được coi là `unknown` đến khi phân loại lại. Không gán phiên bản mới cho dữ liệu cũ. Hạ migration làm mất thông tin phiên bản; cần kiểm tra kế hoạch phân loại lại trước khi triển khai.

Đánh giá cảm xúc: cài `requirements-dev.txt` (gồm boto3), cấu hình `DATABASE_URL` trỏ database dùng chung đã migration, AWS profile và Region. `python -m app.evaluate_sentiment --model-id <model>` chỉ in metadata, không gọi model; để chạy thật phải thêm `--execute --max-calls <N> --daily-call-limit <N>`. Mặc định nghỉ bốn giây giữa các lượt, dự phòng trong `bedrock_call_reservations` trước mỗi lời gọi và không hoàn khi lỗi. `--output <đường-dẫn-mới>` lưu báo cáo ID/nhãn/usage, không ghi đè. Giới hạn là số lượt trong database, không phải giới hạn chi phí hay toàn AWS; chỉ dùng dữ liệu được phép gửi và kiểm tra giá/quota trước khi chạy. Tập mặc định là dữ liệu giả do trợ lý tự tạo, chưa được nhóm thẩm định; xem [S6](../docs/development-process/s6_sentiment_alerts.md).

Migration `0018_sentiment_work` tạo hàng đợi phân loại bền vững và xếp lại các phiên đã kết thúc; `0019_bedrock_rate` giới hạn 10 lượt gọi Bedrock mỗi phút UTC trong cùng database. Khi bật phân loại, worker xử lý từng lô, dùng lease tám phút và từ chối kết quả đến sau khi mất lease; scheduler cần chạy để tiếp tục phần còn lại. Lỗi được thử lại sau năm phút tối đa ba lần, hết hạn mức phút hoặc ngày thì chờ cửa sổ tiếp theo; mục thất bại cần vận hành kiểm tra. `unknown` là kết quả hợp lệ và không tự thử lại. Hạ migration xóa hàng đợi hoặc dữ liệu hạn mức; dừng worker và lập kế hoạch bảo toàn trước khi thay đổi schema.

Giới hạn Bedrock dùng số lần gọi trong cùng database, không phải giới hạn USD; `SENTIMENT_MAX_CALLS_PER_RUN` giới hạn mỗi lô chứ không giới hạn tổng số lượt của phiên sau nhiều lô, còn `SENTIMENT_DAILY_CALL_LIMIT` giới hạn theo ngày; mặc định đều 0. Không hoàn dự phòng khi lỗi, timeout hoặc kết quả đến muộn; các worker phải dùng cùng giới hạn ngày và không được xóa bảng để vượt hạn mức. Hạn mức không bao gồm ứng dụng khác, không khóa chi phí model hay token; cần đối chiếu giá và theo dõi ngân sách. Bật tính năng có thể xử lý cả phiên cũ đã được xếp lại và phát sinh chi phí. Model, quyền và cách bật xem [hạ tầng](../infrastructure/README.md).

Khi frontend chạy khác origin, đặt `CORS_ORIGINS` thành danh sách origin cụ thể, cách nhau bằng dấu phẩy, ví dụ `http://localhost:5173`. Nếu không đặt, backend không bật CORS; các origin không có trong danh sách bị trình duyệt từ chối. Chỉ cho HTTP trên localhost, origin khác cần HTTPS; không dùng `*`.

Để dùng route nhãn hàng, cấu hình `COGNITO_ISSUER` là issuer HTTPS của user pool và `COGNITO_CLIENT_ID` là client ID tin cậy. API lấy JWKS từ issuer và kiểm tra chữ ký RS256, issuer, hạn, `token_use=access`, `client_id` và scope chính xác `brand-api/access`; token thiếu scope nhận 403. Chưa kiểm tra thu hồi token hoặc cấu hình API Gateway. Không tự khai `owner_id`: backend dùng `sub` đã xác minh. Luồng token Cognito thật với scope đã thử trên backend cục bộ.

Ví dụ nội dung `PUT /brands/{id}/tracking` (gửi kèm bearer token qua OpenAPI):

```json
{"keywords":["Starbucks"],"platforms":["tiktok"],"frequency":"daily","runTime":"08:00","timezone":"Asia/Ho_Chi_Minh","postLimit":1,"active":true}
```

API lưu cấu hình và thời điểm dự kiến; `active` không chứng minh dịch vụ lịch đang chạy. Nền tảng được lưu không có nghĩa đã được hỗ trợ. JWT hoặc dữ liệu cá nhân không đưa vào log. Xem `/docs` để biết hợp đồng tạm thời.

`PUT /brands/{id}` nhận `{"name":"Tên mới"}` để đổi tên nhãn hàng thuộc tài khoản hiện tại; trả 404 nếu không tìm thấy hoặc không thuộc tài khoản. API xóa được mô tả ở trên.

`GET /brands/{id}/overview` trả `post_count`, `comment_count`, `run_count` và `latest_run` (null khi chưa có phiên). Số lượng là bản ghi đã lưu của nhãn hàng thuộc tài khoản, không phản ánh độ bao phủ; bài hoặc bình luận thiếu ID nguồn có thể bị đếm trùng. API không suy ra cảm xúc từ dữ liệu này.

`GET /brands/{id}/mentions` có thể lọc bằng `source`, `posted_from` và `posted_until` cùng phân trang. Hai endpoint bình luận tổng hợp và theo phiên cũng nhận `posted_from` và `posted_until` để lọc theo thời gian đăng bình luận. Thời gian phải có múi giờ; khoảng gồm đầu và không gồm cuối. Khi lọc thời gian, bản ghi thiếu `posted_at` không được đưa vào kết quả. Giao diện hỗ trợ lọc bình luận tổng hợp và theo phiên.

`POST /brands/{id}/runs` tạo phiên `queued` và không tự gọi Firecrawl. Để worker cục bộ xử lý, sau khi cấu hình `DATABASE_URL` và `FIRECRAWL_API_KEY` trong môi trường của chính worker, chạy từ `backend/`:

```powershell
python -m app.worker --max-calls 3 --daily-estimated-credit-budget 20
```

Tham số bắt buộc giới hạn số lần gọi provider trong **mỗi phiên**, từ 1–10. Mặc định lấy một trang tìm kiếm và một trang bình luận; `--search-pages` và `--comment-pages` cho phép tối đa ba trang mỗi loại, mỗi trang tính vào hạn mức gọi. `collection_limits` trong chi tiết phiên ghi giới hạn đã áp dụng, không chứng minh dữ liệu đầy đủ. Nếu trang sau lỗi hoặc hết hạn mức, dữ liệu các trang trong cùng lời gọi chưa được lưu và lượt được ghi lỗi. Chỉ adapter TikTok được thử; nguồn khác ghi lỗi `unsupported_source`.

`--max-attempts` từ 1–3, mặc định 1, cho phép thử lại một số lỗi tạm thời; mỗi lần thử tính vào hạn mức gọi và có thể bị tính phí kể cả khi timeout. `--estimated-credit-budget` đặt ngân sách credit **ước tính** cho mỗi phiên, dự phòng `--estimated-credits-per-call` credit trước mỗi lần gọi, kể cả thử lại; không hoàn dự phòng nếu provider không tính phí. Để trống ngân sách thì không giới hạn theo ước tính. Đây không phải giới hạn cứng ở Firecrawl, không chia sẻ ngân sách giữa các phiên/worker và không ngăn vượt mức nếu giá thực tế cao hơn dự phòng; cần đối chiếu giá trước khi cấu hình và theo dõi Usage. Có thể thêm `--once` để xử lý tối đa một phiên rồi thoát. Tùy chọn `--stale-after-minutes 30` bật quét để đánh dấu lỗi phiên có lease hết hạn; phiên cũ không có lease dùng ngưỡng 30 phút. Lease mặc định 10 phút được gia hạn trước lời gọi và bằng heartbeat nền; worker không có lease hợp lệ không được ghi. Một lời gọi đã bắt đầu vẫn có thể phát sinh chi phí. CLI không tự chạy lại phiên thất bại; Lambda có tùy chọn phục hồi phiên quá hạn, mặc định tắt, xem hướng dẫn hạ tầng. Trước khi dùng dữ liệu thật cần xác nhận điều kiện sử dụng nguồn, điều khoản provider và chi phí. Worker CLI không tự xếp lịch.

`--daily-estimated-credit-budget` là bắt buộc cho CLI và `run_tracking`: trước mỗi lần gọi, các worker dùng cùng database dự phòng nguyên tử vào một bảng chung theo ngày UTC của database; kể cả timeout hay lỗi cũng không hoàn dự phòng. Hai giá trị ngân sách ngày và credit dự phòng mỗi lần phải giống nhau trên mọi worker; từ lần đặt chỗ đầu tiên trong ngày, cấu hình khác bị từ chối đến ngày UTC tiếp theo. Không xóa hoặc sửa bảng để vượt giới hạn. Giá trị 0 chặn mọi lời gọi. Database lỗi hoặc chưa migration cũng chặn lời gọi. Giới hạn này vẫn chỉ là ước tính: nó không bao gồm các ứng dụng hoặc khóa khác dùng Firecrawl ngoài database này, không ngăn tính phí vượt dự phòng, và không thay thế giới hạn tài khoản hay theo dõi Usage.

Nếu nhãn hàng được tạm dừng trong lúc phiên còn chờ, worker đánh dấu phiên đó `skipped` mà không gọi Firecrawl. Phiên đã chạy dùng bản chụp cấu hình lúc tạo và tiếp tục hoạt động.

Trong API, `queued_at` là thời điểm tạo yêu cầu; `started_at` là `null` khi worker chưa bắt đầu. Kết quả từng lượt giữ liên kết bài với từ khóa; API sắp bài và bình luận theo lượt thích khả dụng, với chỉ số thiếu đứng sau chỉ số đã biết. Bộ kiểm thử mạng và xác thực sử dụng dữ liệu giả; chúng không chứng minh quyền hoặc khả năng tích hợp với dịch vụ thật.

Kiểm thử: cài `pip install -r requirements-dev.txt`; chạy `python -m unittest discover -s tests -v` từ `backend/`. Các kiểm thử PostgreSQL cần `TEST_DATABASE_URL` trỏ tới **database thử nghiệm riêng đã chạy migration và dùng UTF-8**; khi thiếu biến chúng được bỏ qua. Không trỏ biến này đến dữ liệu thật. Trên Windows, cluster mặc định có thể dùng Windows-1252 và không lưu được tiếng Việt; chọn UTF-8 khi tạo cluster thử.

Lượt kiểm thử Chrome với Cognito, worker Lambda, Firecrawl và PostgreSQL AWS thật đã hiển thị bài và bình luận theo lịch trong môi trường tạm. Worker cục bộ vẫn phải chạy riêng; hướng dẫn worker Lambda và công tắc lịch xem [hạ tầng](../infrastructure/README.md), kết quả và giới hạn xem [S5](../docs/development-process/s5_tracking.md).

Worker Lambda ghi sự kiện trạng thái và số phiên quá hạn dưới dạng JSON, không ghi nội dung thu thập hoặc khóa. Template có alarm cho phiên lỗi/một phần/quá hạn, lỗi thực thi Lambda, thiếu invocation và DLQ; có thể gắn SNS topic. Stack CloudWatch tạm đã thử alarm bằng log giả và đường SNS → SQS tạm; template worker đầy đủ và kênh người dùng chưa được kiểm thử đầu cuối.
