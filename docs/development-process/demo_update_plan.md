# Kế hoạch cập nhật demo: dữ liệu theo phút, cảnh báo qua email

**Cập nhật:** 27/11/2026 · **Trạng thái:** đã chốt toàn bộ, gồm mục 4 (nhóm trưởng đồng ý ngày 27/11). **Code xong, kiểm thử cục bộ đạt, diễn tập trọn kịch bản trên AWS đạt; còn chờ thử email SNS thật.**

## 0. Kết quả triển khai 27/11

**Đã làm:**
- **Dữ liệu và cảnh báo:**
  - Kịch bản ba đợt: 20/100 → 60/200 → 65/300.
  - Nhãn giả lập gán theo câu mẫu, không gọi Bedrock.
  - Cảnh báo so tỷ lệ lũy kế giữa hai lần thu thập liên tiếp, chỉ áp dụng cho nhãn hàng demo.
  - Mỗi lần thu thập có tối đa một cảnh báo.
- **Email:** gửi qua SNS đến địa chỉ cố định, kèm link mở thẳng trang.
- **Database và API:** migration `0020_run_alerts`; thêm API dòng thời gian tỷ lệ và API đánh giá lại lần thu thập gần nhất.
- **Giao diện:** bảng "Cảnh báo theo lần thu thập" và banner cảnh báo; mở đúng nhãn hàng từ link email.
- **Vận hành:** `demo_control.py` gồm `start` (mốc và đợt tiêu cực tự động, cách nhau 3 phút), `release` (đợt tích cực) và `stop`.
- **Hạ tầng:**
  - Template mới `aws-demo-ec2-api.yaml`: EC2, Auto Scaling Group và ALB.
  - CloudFront chuyển `/api/*` đến ALB.
  - Stack worker thêm SNS, có thể tắt API Gateway.
  - Stack data thêm subnet công khai thứ hai.

Chi tiết: [backend](../../backend/README.md), [frontend](../../frontend/README.md), [hạ tầng](../../infrastructure/README.md#demo-theo-phút-dữ-liệu-giả-cảnh-báo-và-email-2711-chưa-thử-trên-aws).

**Bằng chứng:**
- **Backend:** PostgreSQL 18 riêng, migration đến `0020`, `alembic check` sạch, 132 kiểm thử đạt, không bỏ qua test nào.
- **Frontend:** build đạt; 18 kiểm thử đạt, 1 kiểm thử tích hợp bỏ qua.
- **Chrome cục bộ** (`demo-minute-browser.cjs`, xác thực giả):
  - mốc 20%, cảnh báo 30%;
  - đánh giá lại không tạo bản sao;
  - đợt tích cực 22%, không cảnh báo;
  - link email mở đúng nhãn hàng.
- **Template:** cfn-lint không báo lỗi cho bốn template.

**Diễn tập trên AWS 27/11 (đạt, trừ email):**

Môi trường dùng các stack sau, Region `ap-southeast-1`:
- `brand-demo-minute-data-20261127`, `-auth-`, `-api-` (worker Lambda, không có API Gateway), `-ec2-`;
- hosting cũ `brand-tracking-demo-frontend-20261122` đã cập nhật để chuyển `/api/*` đến ALB.

Kết quả:
- **Hạ tầng:**
  - Migration đến `0020` chạy qua Lambda đạt.
  - Hai EC2 (Amazon Linux 2023, Python 3.12) `healthy`, log API vào CloudWatch.
  - Gọi thẳng ALB từ Internet bị chặn.
  - Qua CloudFront: `/api/health` trả 200; `/api/brands` không token trả 401 JSON; `/auth/callback` trả `index.html`.
- **Chrome, script `frontend/tests/aws-demo-minute.cjs`, lượt 2:**
  - đăng ký giả và tạo nhãn hàng, quy tắc;
  - mốc 20/100 lúc 12:55:39;
  - đợt tiêu cực 60/200 lúc 12:59:33, kèm cảnh báo; đánh giá lại không tạo bản sao;
  - **AI thành công ngay lần đầu**: 30 mẫu, 3 chủ đề (quá ngọt, giao hàng chậm, khách thích sản phẩm), mỗi chủ đề 3 dẫn chứng;
  - `release` bắn đợt tích cực 65/300, không cảnh báo;
  - link email mở đúng nhãn hàng. Kết thúc với `DEMO_MINUTE_FLOW_OK`.
  - Video: [demo-minute-aws-20261127.webm](evidence/demo-minute-aws-20261127.webm).
- **Lỗi đã sửa trong lượt 1:**
  - *AI:* báo `provider_error` với `validation_stage=incomplete`, tức Bedrock không trả xong câu trả lời. Suy luận là đã chạm giới hạn 1024 token: câu trả lời tiếng Việt dài bị cắt. Nâng giới hạn thì thành công. Rất có thể đây cũng là nguyên nhân các lần lỗi AI trước đây. Đã nâng lên 3000 token, yêu cầu 1–3 nhận định ngắn, và ghi log `analysis_incomplete`.
  - *Link email:* gây vòng lặp đăng nhập sau callback; đã sửa.
- **Auto Scaling:**
  - Rolling update khi đổi bản backend: hai máy được thay lần lượt.
  - Target tracking tự thu nhỏ từ 2 xuống 1 máy khi CPU thấp. Lúc đó tắt máy duy nhất làm API gián đoạn khoảng 2–3 phút. Vì vậy đã đặt **tối thiểu 2 máy**.
  - Tắt một trong hai máy: 0/8 lần gọi API lỗi, Auto Scaling thay máy và có lại 2 máy `healthy` sau 102 giây.

**Chưa kiểm chứng:**
- **SNS gửi email thật:** chưa có địa chỉ nhận. Đã cảnh báo nhưng `notified_at=null` đúng như dự kiến.
- **Chi phí thực tế:** Cost Explorer có độ trễ.
- **Chất lượng phân tích AI:** một lượt thành công không chứng minh chất lượng hay độ ổn định.

**Giới hạn đã biết:**
- Đoạn CloudFront → ALB dùng HTTP, nên token đi không mã hóa trên đoạn này. Chấp nhận được cho demo dữ liệu giả, không dùng cho dữ liệu thật.
- Email có thể bị gửi trùng nếu Lambda dừng ngay sau khi gửi.

**Bước tiếp theo:**
1. Nhóm trưởng cung cấp hộp thư nhận cảnh báo.
2. Cập nhật stack `-api-` với `AlertEmail` và xác nhận subscription.
3. Chạy lại một lượt để thử email.
4. Xóa stack EC2 khi không diễn tập (khoảng 2 USD/ngày); stack data có RDS/NAT cũng tính phí.

Hướng dẫn nói theo kịch bản mới: [demo_speaking_guide.md](../demo_speaking_guide.md). Khi chốt xong, AI code theo tệp này rồi cập nhật [kế hoạch demo](../demo_presentation.md), [hướng dẫn thuyết trình](../demo_speaking_guide.md), [S6](s6_sentiment_alerts.md) và [S8](s8_aws_delivery.md).

## 1. Vì sao cần đổi

Kịch bản hiện tại dùng **hai loại dữ liệu giả**, rất khó giải thích trên lớp:

- **Các đợt "trực tiếp"**, cách nhau 1–3 phút: chỉ để thấy dữ liệu đi qua hệ thống, **không tạo cảnh báo**.
- **Hai ngày "lịch sử" nạp sẵn**, 10→15 bình luận tiêu cực: đây mới là phần **tạo ra cảnh báo**.

Lý do là cảnh báo gốc chạy chậm. Sau mỗi lần thu thập, hệ thống so sánh **hôm qua với hôm kia** (tính theo ngày trọn vẹn, mốc 00:00 UTC), nên dữ liệu lấy hôm nay phải **đến ngày mai** mới được tính. Trong vài phút demo, không thể thấy cảnh báo sinh ra từ chính dữ liệu vừa đổ về.

**Hướng mới:** chỉ giữ **một dòng dữ liệu**. Sau mỗi lần thu thập, hệ thống so sánh **ngay với lần thu thập trước** theo tỷ lệ bình luận tiêu cực. Khi vượt ngưỡng, hệ thống **gửi email cảnh báo** kèm link mở thẳng trang web.

## 2. Kịch bản dữ liệu

Thương hiệu giả là **Mây Tea**. Quy tắc cảnh báo: **tỷ lệ tiêu cực lũy kế tăng từ 50% trở lên so với lần thu thập trước**.

| Lần | Khi nào | Bình luận mới | Lũy kế (tiêu cực/tổng) | Tỷ lệ | Kết quả |
|---|---|---|---|---|---|
| Mốc | Ngay khi bật | 100 (20 tiêu cực) | 20/100 | 20% | Mốc để so sánh |
| Đợt tiêu cực | Khoảng 3 phút sau | 100 (40 tiêu cực) | 60/200 | 30% | 20% → 30% (+50%): **cảnh báo và gửi email** |
| Kiểm tra lại | Các lần sau, không có dữ liệu mới | 0 | 60/200 | 30% | Không tăng: **không có cảnh báo mới**. Cảnh báo cũ vẫn còn trong lịch sử, không bị trùng |
| Đợt tích cực | Người vận hành bật sau bước AI | 100 (5 tiêu cực) | 65/300 | ≈22% | Tỷ lệ giảm: không cảnh báo, xu hướng phục hồi |

Cảnh báo được lưu thành **lịch sử**: hệ thống không tự gỡ một cảnh báo khi tỷ lệ giảm. Như vậy đúng với ý nghĩa "đã từng có sự cố tại thời điểm này".

**Câu nói trên lớp:** *"Cứ 3 phút hệ thống thu thập một lần. Tỷ lệ tiêu cực tăng từ 20% lên 30%, vượt ngưỡng 50% đã đặt, nên hệ thống gửi email cảnh báo."*

## 3. Trình tự trình diễn hệ thống

Phần này chỉ gồm thao tác khi trình diễn, không gồm phần giải thích lý thuyết.

**Phân vai:**
- Một người nói.
- Một người vận hành web và chạy lệnh.
- Một máy, hoặc một tab, mở **AWS Console** để chỉ ra dịch vụ đang chạy ở từng phần.

### Mở đầu (một câu)

"Hệ thống chạy được với dữ liệu thật qua luồng Firecrawl." Kèm bằng chứng: một ảnh hoặc lịch sử thu thập thật đã lưu.

"Để mọi người dễ theo dõi, hôm nay nhóm dùng **dữ liệu giả** và không đi qua Firecrawl."

### Phần 1: Tạo tài khoản và lưu dữ liệu

1. Đăng ký bằng email giả `@example.invalid`, rồi đăng nhập. Nói rõ email được xác nhận giả lập.
2. Tạo nhãn hàng Mây Tea với từ khóa và quy tắc cảnh báo, rồi lưu.
3. Đăng xuất và đăng nhập lại: Mây Tea vẫn còn, tức dữ liệu đã nằm trong database.
4. Trên AWS Console:
   - **Cognito:** có tài khoản mới.
   - **CloudWatch:** log của API có yêu cầu tạo nhãn hàng.
   - **RDS:** database nằm trong mạng riêng.

### Phần 2 (trọng tâm): Cảnh báo qua email

1. Người vận hành bật bộ sinh dữ liệu. Lần thu thập mốc chạy ngay: 20/100.
2. **Đóng tab web.** Trong lúc chờ khoảng 3 phút, mở AWS Console để chỉ EventBridge, SQS và log worker của lần mốc.
3. Đợt tiêu cực về, tỷ lệ 20% → 30%. Hộp thư của thành viên demo **nhận email cảnh báo**.
4. Bấm link trong email để mở thẳng trang cảnh báo của Mây Tea: thấy lý do, các con số và các bình luận phàn nàn.

### Phần 3: AI phân tích và đề xuất

1. Từ trang cảnh báo, chạy phân tích AI cho khoảng thời gian vừa rồi.
2. Xem chủ đề chính ("quá ngọt", "giao hàng chậm"), đề xuất xử lý, và bấm dẫn chứng để thấy bình luận gốc.
3. Nói: AI chỉ gợi ý để tham khảo. Nhãn hàng có thể theo đề xuất hoặc tự xử lý; hệ thống không tự ra quyết định.
4. Nếu Bedrock lỗi, mở kết quả đã lưu và nói rõ đó là lần chạy trước.

### Phần 4: Phục hồi

1. Người vận hành bật **đợt tích cực**. Tỷ lệ giảm còn khoảng 22%, không có cảnh báo mới, cho thấy tình hình đã được xử lý.
2. *(Tùy chọn, nếu còn thời gian)* Xóa nhãn hàng bằng chức năng đã có, gồm bước xác nhận. Nhóm đã quyết định **không làm chức năng xóa tài khoản**.

**Kết thúc:** người vận hành tắt bộ sinh dữ liệu và dọn tài nguyên AWS sau buổi demo.

## 4. Các điểm cần chốt

Mỗi câu có đề xuất của AI (**in đậm**); nhóm có thể đổi.

1. **So sánh theo tỷ lệ hay số lượng?** **Đề xuất: tỷ lệ lũy kế**, kèm một số tối thiểu (ví dụ ít nhất 10 bình luận tiêu cực). Lý do: số lượng luôn tăng khi có thêm bình luận, nên dễ bị hỏi lại.
2. **Ngưỡng tương đối hay tuyệt đối?** **Đề xuất: tương đối** (20% → 30% là +50%), để dùng lại trường "tăng %" đã có trong quy tắc cảnh báo.
3. **Nhãn cảm xúc lấy từ đâu?** **Đề xuất: bộ sinh dữ liệu gán sẵn**, có đánh dấu là nhãn giả lập, để kết quả lần nào cũng đúng. Bedrock chỉ dùng cho phân tích AI.
4. **Khi nào đánh giá cảnh báo?** **Đề xuất: tự động ngay sau mỗi lần thu thập.** Chống trùng theo từng lần thu thập.
5. **Gửi email thế nào?** **Đề xuất: một SNS topic gửi đến email cố định của thành viên demo**, không gửi đến email của tài khoản đăng ký.
   - Địa chỉ email là tham số của stack, không ghi vào mã hay tài liệu. Xác nhận đăng ký nhận email trước buổi demo.
   - Nội dung email ngắn: tên nhãn hàng, tỷ lệ trước/sau, link CloudFront đến trang cảnh báo.
   - Trên lớp nói rõ: hệ thống thật sẽ gửi đến email của người dùng.
6. **Đợt tích cực bật thế nào?** **Đề xuất: người vận hành bật bằng lệnh khi đến lúc**, vì bước AI không cố định thời gian. Mốc và đợt tiêu cực chạy tự động, cách nhau 3 phút.
7. **Tần suất theo phút áp dụng cho đâu?** **Đề xuất: chỉ cho nhãn hàng demo** trong môi trường demo riêng. Nhãn hàng thật giữ lịch ngày/tuần.
8. **Bỏ dữ liệu lịch sử 10→15?** **Đề xuất: bỏ khỏi kịch bản chính**, giữ mã cũ làm dự phòng cho đến khi kịch bản mới diễn tập đạt.

## 4b. Chuyển API sang EC2 với Auto Scaling và Load Balancer

**Yêu cầu của nhóm trưởng (27/11):** máy chủ API chạy trên **EC2**, có **Auto Scaling** và **Load Balancing**. Hiện API chạy trên Lambda sau API Gateway.

**Đề xuất kiến trúc:**

```
Người dùng → CloudFront ─┬─ /         → S3 (giao diện)
                         └─ /api/*    → ALB → Auto Scaling Group (2 EC2, chạy FastAPI) → RDS
EventBridge → Lambda lập lịch → SQS → Lambda worker → RDS → SNS (email)
```

- **Chỉ chuyển API sang EC2.** Worker xử lý nền vẫn chạy trên Lambda qua SQS, vì phần này đã kiểm thử và hợp với kiểu việc theo hàng đợi. Mã FastAPI hiện có chạy được trực tiếp trên EC2 bằng uvicorn.
- **Auto Scaling Group:** tối thiểu 1, mong muốn 2, tối đa 3 máy `t3.micro`, chia ở 2 vùng sẵn sàng (AZ). Quy tắc co giãn: CPU trung bình trên 50% thì thêm máy.
- **ALB:** health check `/health`, phân tải đều cho các EC2.
- **HTTPS:** CloudFront là cổng HTTPS duy nhất, chuyển tiếp `/api/*` đến ALB. ALB chỉ nhận yêu cầu có header bí mật do CloudFront gắn vào. Không cần mua tên miền hay chứng chỉ riêng.
- **Mạng:**
  - EC2 đặt ở subnet công khai, nhưng security group chỉ nhận traffic từ ALB, để không phải dùng NAT (NAT đắt).
  - RDS chỉ nhận kết nối từ EC2 và Lambda.
  - Mật khẩu database lấy từ Secrets Manager qua IAM role của EC2.
- **Khởi tạo máy:** launch template cài Python và mã backend từ S3 artifact, chạy FastAPI bằng systemd. Không SSH; khi cần thì dùng SSM Session Manager.
- **Phần demo trên lớp:**
  - Mở EC2 → Target Group để thấy 2 máy `healthy`.
  - Tắt (terminate) một máy: web vẫn chạy, Auto Scaling tự tạo máy thay thế.
  - Tùy chọn: chạy một lệnh tạo tải để CPU tăng, Auto Scaling thêm máy. Bước này mất vài phút, nên làm trước buổi demo và chụp màn hình làm bằng chứng.

**Chi phí ước tính tại `ap-southeast-1`** (cần kiểm tra lại giá trước khi bật):
- ALB khoảng 0,6 USD/ngày.
- 2 máy `t3.micro` khoảng 0,65 USD/ngày.
- IPv4 công khai khoảng 0,5 USD/ngày.
- Tổng cộng **khoảng 2 USD mỗi ngày bật**, chưa tính RDS.

Nếu quên tắt cả tháng thì mất khoảng 60 USD, **vượt ngân sách 30 USD**. Vì vậy chỉ bật khi diễn tập hoặc demo, xong thì xóa stack.

**Đã chốt (27/11):**
- (a) Chỉ chuyển API sang EC2; worker giữ trên Lambda.
- (b) Môi trường demo bỏ API Gateway và Lambda API; template cũ vẫn giữ trong repo.
- (c) Không tạo tải trực tiếp trên lớp. Trực tiếp chỉ tắt một máy để thấy hệ thống tự phục hồi; phần tạo tải thì chiếu bằng chứng đã chụp trước.

Lý do: mục tiêu của bài tập lớn môn Cloud là thể hiện được việc dùng các dịch vụ cloud, trong đó có EC2, Auto Scaling và Load Balancing.

FastAPI đã tự xác minh JWT của Cognito ([auth.py](../../backend/app/auth.py)), nên vẫn an toàn khi bỏ JWT authorizer của API Gateway. Dù vậy, bước này vẫn phải kiểm thử lại trên ALB.

## 5. Phạm vi thay đổi dự kiến

- **Hạ tầng EC2 (theo mục 4b):** template mới gồm ALB, target group, launch template, Auto Scaling Group, security group, IAM role và chính sách co giãn. Thêm origin `/api/*` cho CloudFront; frontend gọi API qua cùng tên miền CloudFront. Cập nhật CORS, cấu hình Cognito và tài liệu [kiến trúc AWS](../architecture_aws.md).


Đây là ước lượng. Khi code phải đọc lại mã thật trước khi sửa.

- **Bộ sinh dữ liệu** ([demo_stream.py](../../backend/app/demo_stream.py), [demo_scheduler.py](../../backend/app/demo_scheduler.py)):
  - Sinh ba đợt theo kịch bản: mốc, tiêu cực, tích cực.
  - Gán nhãn giả lập khi lưu.
  - Mốc và đợt tiêu cực chạy tự động; đợt tích cực bật bằng lệnh.
- **Cảnh báo** ([alert_evaluation.py](../../backend/app/alert_evaluation.py), [alert_rules.py](../../backend/app/alert_rules.py)):
  - Thêm chế độ so sánh giữa hai lần thu thập liên tiếp theo tỷ lệ lũy kế, chỉ cho nhãn hàng demo.
  - Không đổi logic theo ngày.
- **Database:** có thể cần một migration để lưu cảnh báo gắn với một lần thu thập.
- **Worker:** đánh giá cảnh báo ngay sau mỗi lần thu thập demo thành công. Nếu cảnh báo mới được tạo, gửi một tin lên SNS, gửi đúng một lần.
- **Hạ tầng** ([infrastructure/](../../infrastructure/README.md)):
  - SNS topic, email subscription lấy từ tham số stack.
  - Quyền `sns:Publish` cho worker.
  - Địa chỉ CloudFront dùng cho link trong email.
- **Giao diện:**
  - Bảng theo thời gian: lần thu thập, tiêu cực/tổng, tỷ lệ, cảnh báo.
  - Link trực tiếp đến trang cảnh báo; nếu chưa đăng nhập thì đăng nhập xong quay về đúng trang đó.
- **Công cụ vận hành** ([demo_control.py](../../scripts/demo_control.py)): lệnh `start` không nạp lịch sử nữa; thêm lệnh bật đợt tích cực; lệnh `stop` giữ nguyên.
- **Tài liệu:** kế hoạch demo, hướng dẫn thuyết trình, S6, S8, hướng dẫn hạ tầng; SRS nếu thêm yêu cầu gửi email.

## 6. Những gì không làm

- Không gọi Firecrawl hay TikTok trong chế độ demo.
- Không đổi lịch thu thập và cảnh báo của nhãn hàng thật.
- Không dùng Bedrock để phân loại trong kịch bản chính.
- Không trình bày nhãn gán sẵn là kết quả của AI.
- Không gửi email đến địa chỉ người dùng tự đăng ký; không lưu địa chỉ email thật trong mã hoặc log.

## 7. Tiêu chí hoàn thành

1. **Kiểm thử cục bộ với PostgreSQL riêng:**
   - Có mốc 20/100.
   - Đợt tiêu cực đưa lên 60/200 và tạo đúng một cảnh báo.
   - Kiểm tra lại không tạo cảnh báo trùng.
   - Đợt tích cực không tạo cảnh báo.
   - Dữ liệu của tài khoản và nhãn hàng khác không bị ảnh hưởng.
2. **Kiểm thử gửi email:** dùng SNS giả khi chạy cục bộ; trên AWS nhận đúng một email, link mở đúng trang.
3. **Kiểm thử Chrome cục bộ:** đi đủ bốn phần.
4. **Diễn tập trên AWS qua CloudFront:**
   - Dữ liệu đi qua EventBridge → SQS → worker → RDS → SNS.
   - Giờ và mã phiên trong CloudWatch khớp với giao diện.
   - AI chạy được, hoặc có phương án dự phòng.
5. **Chi phí:** trong ngân sách 30 USD. Dọn tài nguyên sau khi thử.
6. **Bàn giao:** ghi video hoặc ảnh dự phòng mới; cập nhật hướng dẫn thuyết trình.

## 8. Rủi ro

- **EC2 và ALB tính phí theo giờ kể cả khi không dùng:** phải xóa stack sau mỗi lần diễn tập. Máy mới cần vài phút để khởi tạo và qua health check.

- **Email có thể đến chậm hoặc vào thư rác:** thử trước, đánh dấu không phải thư rác, và chuẩn bị mở web trực tiếp nếu email trễ.
- **EventBridge chạy theo nhịp mỗi phút:** đợt có thể trễ vài chục giây. Khi trình bày nên nói "khoảng 3 phút".
- **Lệnh `start` cập nhật CloudFormation mất vài phút:** bật trước khi vào phần 2.
- **Thêm chế độ cảnh báo thứ hai làm hệ thống phức tạp hơn:** phải giới hạn chế độ này cho demo và có kiểm thử riêng.
