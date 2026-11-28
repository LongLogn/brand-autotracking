# Giới hạn tốc độ Bedrock Nova Lite

- **Ngày phát hiện:** 2026-11-28
- **Trạng thái:** Đã giải quyết (đã triển khai và thử tải trên AWS 28/11)
- **Thành phần liên quan:** Amazon Bedrock (Nova Lite APAC), `backend/app/sentiment.py`, `backend/app/analysis.py`, worker Lambda, API trên EC2

## Vấn đề

Buổi thuyết trình cuối có thể có nhiều học sinh cùng truy cập và bấm **Phân tích AI**. Phân loại cảm xúc và Phân tích AI dùng chung một giới hạn số lượt gọi Bedrock mỗi phút. Khi vượt giới hạn, người dùng nhận lỗi `rate_limited` và phải tự bấm lại; yêu cầu không được xếp hàng.

## Bằng chứng

- Service Quotas (ap-southeast-1, 28/11/2026): `Cross-region model inference requests per minute for Amazon Nova Lite` = **20**, `Adjustable = False`. Các model khác cũng thấp: Nova Pro 25, Nova Micro 20, Nova 2 Lite 20, Claude Sonnet 10.
- Hệ thống tự đặt 60 lượt/phút (migration `0022_bedrock_rate_60`, hằng `BEDROCK_MINUTE_LIMIT`), cao hơn quota AWS, nên khi đông người sẽ gặp lỗi throttling của AWS thay vì lỗi có kiểm soát.
- Phân loại cảm xúc gọi 1 lượt cho mỗi bình luận, mỗi lô tối đa 50 lượt (`SentimentMaxCallsPerRun=50`), có thể chiếm hết quota.
- Ngày 28/11 Phân tích AI từng báo `rate_limited` khi giới hạn còn 10/phút ([S5](../docs/development-process/s5_tracking.md)).

## Nguyên nhân

Quota mặc định của tài khoản AWS mới cho Nova Lite chỉ 20 lượt/phút và không tự tăng được. Thiết kế hiện tại tốn 1 lượt cho mỗi bình luận và trả lỗi ngay khi hết lượt thay vì chờ.

## Hướng giải quyết

Các phương án đã cân nhắc:

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| Tăng giới hạn hệ thống lên 300/phút | Sửa nhanh | Vô ích: AWS vẫn chặn ở 20/phút |
| Gửi yêu cầu tăng quota cho AWS Support | Giữ nguyên thiết kế | Không chắc được duyệt, không kịp buổi demo |
| Chuyển sang OpenRouter | Giới hạn cao hơn | Mất Bedrock khỏi kiến trúc AWS đã quay và viết báo cáo; gửi dữ liệu ra bên thứ ba; phải nạp tiền riêng |
| **Gộp nhiều bình luận vào một lượt + hàng đợi** | Giữ Bedrock, giảm số lượt khoảng 20 lần, không ai nhận lỗi | Mỗi lượt chậm hơn một chút; lô lỗi phải chạy lại |

Phương án được chọn (nhóm trưởng đồng ý ngày 28/11):

1. **Gộp phân loại cảm xúc:** một lượt Bedrock phân loại nhiều bình luận, trả nhãn kèm mã từng bình luận; bình luận thiếu nhãn được phân loại lại. Cỡ lô chọn bằng thử nghiệm: chạy cùng bộ bình luận thật với cỡ 1, 10, 20, 30, 50; đo tỷ lệ khớp nhãn, tỷ lệ thiếu/lệch mã, thời gian và token; chọn cỡ lớn nhất mà độ chính xác giảm không quá khoảng 2–3%.
2. **Hàng đợi cho yêu cầu AI:** khi hết lượt trong phút, yêu cầu được lưu vào hàng đợi và tự xử lý ở phút sau, giao diện hiện "đang chờ" thay vì lỗi.
3. Đặt giới hạn hệ thống khớp quota AWS (20 lượt/phút).

## Thử nghiệm chọn cỡ lô (28/11/2026)

Script [batch_size_experiment.py](../backend/app/batch_size_experiment.py) gọi Bedrock Nova Lite thật, giữ nhịp dưới 15 lượt/phút. Dữ liệu: 200 bình luận thật lấy ngẫu nhiên từ database demo (chỉ các nhãn do Nova Lite chấm từng câu, bỏ dữ liệu giả KFCC), không ghi lại database. Tổng chi phí dưới 0,05 USD.

**Lượt 1, so với nhãn chấm từng câu (200 bình luận), prompt lô ban đầu:**

| Cỡ lô | Khớp nhãn từng câu | Bỏ sót | Thời gian/lượt | Token vào/ra mỗi lượt |
|---|---|---|---|---|
| 1 (chấm lại từng câu, 40 câu) | 38/38 câu trả lời khớp; 2 lượt lỗi | 5% | 0,46 s | — |
| 10 | 73,5% | 0% | 0,56 s | 512 / 95 |
| 20 | 69,0% | 0% | 0,69 s | 780 / 185 |
| 30 | 66,5% | 0% | 0,81 s | 1009 / 262 |

Chẩn đoán: chỉ đổi sang prompt dạng lô (mỗi lượt vẫn 1 câu) đã còn 80% khớp, nên phần lớn độ lệch do cách viết prompt, không hẳn do gộp. Lệch nhiều nhất là `unknown → neutral` (câu mơ hồ). Vì nhãn từng câu cũng không phải đáp án chuẩn, AI tự gán nhãn độc lập cho 60 câu đầu để so sánh. Đây là nhãn do AI gán, **chưa được người thẩm định**.

**Lượt 2, sau khi chỉnh prompt lô** (nêu rõ chê, mỉa mai, than thở là negative; câu hỏi là neutral; đánh giá từng câu độc lập). So với nhãn AI tự gán, 60 câu:

| Cách chấm | Độ chính xác | Bắt câu tiêu cực (recall) | Độ chuẩn câu tiêu cực (precision) |
|---|---|---|---|
| Từng câu (cũ) | 61,7% | 79% | 79% |
| Lô 10 | 61,7% | 57% | 62% |
| **Lô 20 (chọn)** | **60,0%** | **64%** | **56%** |
| Lô 30 | 55,0% | 43% | 60% |

Kết luận: lô 10 và 20 ngang chấm từng câu về độ chính xác tổng (chênh 1 câu, trong sai số của mẫu nhỏ); lô 30 tụt rõ. Chọn **20 nội dung mỗi lượt** (`SENTIMENT_BATCH_SIZE`), đạt khoảng 340 bình luận/phút khi dùng 17 lượt. Giới hạn: mẫu nhỏ (60 câu, khoảng 14 câu tiêu cực), nhãn chuẩn do AI gán; khả năng bắt câu tiêu cực của bản lô vẫn thấp hơn chấm từng câu, cần nhóm kiểm tra thêm trên dữ liệu đại diện trước khi coi là tương đương.

## Kết quả và kiểm chứng

Mã (28/11/2026):

- **Phân loại theo lô:** `BedrockBatchSentimentClassifier`, `classify_run_batched` trong [sentiment.py](../backend/app/sentiment.py). Mỗi lượt gửi tối đa 20 nội dung (và tối đa 30.000 ký tự), model trả nhãn theo mã `C1…Cn`; nội dung bị bỏ sót được gửi lại riêng một lần. AWS throttling hoặc hết lượt phút thì dừng, hàng đợi bền vững `sentiment_work` thử lại phút sau, không tính là lỗi. Worker dùng bản lô; bản từng câu giữ cho công cụ đánh giá.
- **Chia quota theo phút:** `BEDROCK_MINUTE_LIMIT=20` khớp quota AWS. Phân loại nền chỉ được dùng 17 lượt/phút (`SENTIMENT_MINUTE_SHARE`, tham số `minute_limit` của `reserve_daily_call`), chừa tối thiểu 3 lượt/phút cho Phân tích AI; khi không có phân loại nền, phân tích dùng được cả 20.
- **Hàng đợi Phân tích AI:** migration [0023_analysis_queue](../backend/migrations/versions/0023_analysis_queue.py) thêm trạng thái `queued`, `next_attempt_at`, `attempts`, `started_at`. Yêu cầu mới vào hàng đợi và được thử ngay; hết lượt phút hoặc AWS throttling thì ở lại `queued`, không báo lỗi. Luồng nền [analysis_queue.py](../backend/app/analysis_queue.py) trong mỗi tiến trình API trên EC2 quét 3–4 giây/lần, xử lý theo thứ tự gửi, nhiều tiến trình an toàn nhờ `FOR UPDATE SKIP LOCKED`. Chờ quá 15 phút thì `queue_timeout`; quá 20 lần thử thì `rate_limited`. API trả `queue_position` (số yêu cầu đứng trước); giao diện hiện "Đang chờ đến lượt" và tự tải lại 4 giây/lần.

Kiểm thử cục bộ trên PostgreSQL 18 sạch: 149/149 kiểm thử backend đạt (thêm kiểm thử lô, bỏ sót, throttling, chia quota, hàng đợi, hết hạn chờ); `alembic check` sạch; hạ cấp/nâng lại `0023` đạt; frontend build và 18 kiểm thử đơn vị đạt.

Triển khai AWS (28/11/2026): artifact `demo-minute-20261127/backend-analysis-queue.zip`; stack `brand-demo-minute-api-20261127` `UPDATE_COMPLETE` với `SentimentMaxCallsPerRun=17`; migration Lambda trả `ok`; frontend tải lên CloudFront. Log worker: **trước khi sửa**, một lô 50 lượt chỉ thành công 22, 28 lượt lỗi do AWS chặn, và 8 công việc phân loại bị `failed` hẳn; **sau khi sửa**, 155 bình luận phân loại xong trong 8 lượt, 0 lỗi.

**Thử tải trên AWS (28/11/2026, sau khi EC2 chạy bản mới):** script chạy trên EC2 qua SSM tạo nhãn hàng tạm với 4 bài giả, gửi **30 yêu cầu Phân tích AI đồng thời** với Bedrock thật, trong lúc worker cũng đang phân loại lại 8 công việc cảm xúc bị lỗi trước đó. Kết quả: 20 yêu cầu xong ngay trong 1,5 giây, 10 yêu cầu vào `queued`; sang phút mới, luồng nền trên EC2 xử lý hết (log `analysis_queue_processed` 1+2+2+5). **30/30 thành công, 0 lỗi, không có log AWS throttling**; thời gian chờ thấp nhất/trung vị/cao nhất là 1/1/42 giây, tối đa 2 lần thử. Worker phân loại nhường lượt (`rate_limit_reached`, chờ phút sau) thay vì lỗi. Dữ liệu tạm đã xóa. 8 công việc cảm xúc từng `failed` vì AWS chặn đã được đặt lại `pending` để chạy lại bằng bản lô.

Việc còn lại: nhóm thẩm định chất lượng nhãn bản lô trên dữ liệu đại diện; có thể gửi yêu cầu tăng quota Nova Lite cho AWS Support nếu cần nhiều hơn.
