# Hướng dẫn demo

Phần B, C là lời thoại khi chiếu [architecture.md](architecture.md) trong VS Code (`Ctrl+Shift+V`); phần E là trình tự demo các dịch vụ AWS. Chữ nghiêng trong ngoặc là thao tác, không đọc ra.

## Phần B — Kiến trúc tổng quan

*(Cuộn đến phần B.)*

Để dễ hình dung, em xin đi theo đúng hành trình sử dụng hệ thống, từ bước ① đến bước ⑬, qua ba giai đoạn.

### B1. Người dùng đăng ký theo dõi nhãn hàng

*(Chỉ vào ①.)*
Đầu tiên, doanh nghiệp **tạo tài khoản và đăng nhập** qua dịch vụ đăng nhập. Mỗi tài khoản có dữ liệu riêng, tài khoản khác không xem được.

*(Chỉ vào ②.)*
Sau đó, người dùng **mở web**. Mọi truy cập đi qua một cổng HTTPS duy nhất, cổng này trả về giao diện web.

*(Chỉ vào ③, đi dọc tới Cơ sở dữ liệu.)*
Trên web, người dùng **đăng ký theo dõi một nhãn hàng**: nhập tên nhãn hàng, các từ khóa khách hàng hay dùng và ngưỡng cảnh báo. Ví dụ: báo cho tôi khi tỷ lệ bình luận tiêu cực tăng hơn 50%. Yêu cầu này đi qua bộ cân bằng tải tới một trong hai máy chủ API, rồi được **lưu vào cơ sở dữ liệu**. Từ đây, người dùng không cần làm gì thêm.

### B2. Hệ thống tự động theo dõi mỗi phút

*(Chuyển sang sơ đồ B2. Chỉ vào ④.)*
Đây là phần tự động. **Mỗi phút**, bộ hẹn giờ kiểm tra cơ sở dữ liệu xem nhãn hàng nào đến lịch theo dõi.

*(Chỉ vào ⑤, ⑥.)*
Với mỗi nhãn hàng đến lịch, hệ thống tạo một **phiên thu thập** và đưa vào **hàng đợi**. Hàng đợi giao từng phiên cho **bộ xử lý nền**. Nhờ có hàng đợi, nhiều nhãn hàng đến lịch cùng lúc cũng không làm hệ thống quá tải; phiên nào lỗi sẽ được thử lại.

*(Chỉ vào ⑦, Firecrawl, TikTok.)*
Bộ xử lý nền gửi từ khóa của nhãn hàng cho **Firecrawl**. Firecrawl tìm trên TikTok các bài viết khớp từ khóa, rồi lấy **bình luận** của từng bài và trả về cho hệ thống. Firecrawl chỉ đọc nội dung công khai.

*(Chỉ vào ⑧.)*
Tiếp theo, bộ xử lý nền gửi các bình luận cho **AI** để phân loại cảm xúc: tích cực, trung tính hay tiêu cực.

*(Chỉ vào ⑨, Cơ sở dữ liệu.)*
Toàn bộ bài viết, bình luận và nhãn cảm xúc được **lưu vào cơ sở dữ liệu**. Bình luận đã có từ lần trước thì không lưu lặp lại.

*(Chỉ vào ⑩ và khối Vượt ngưỡng.)*
Cuối cùng, hệ thống tính **tỷ lệ bình luận tiêu cực** và so với lần thu thập trước. Nếu tỷ lệ tăng vượt ngưỡng người dùng đã đặt, hệ thống **lưu cảnh báo và gửi email** cho doanh nghiệp ngay. Nếu không, hệ thống chờ lần thu thập sau. Vòng này lặp lại liên tục.

### B3. Người dùng xem kết quả và hỏi AI

*(Chuyển sang sơ đồ B3. Chỉ vào ⑪.)*
Khi doanh nghiệp mở web, máy chủ API đọc dữ liệu đã lưu và hiển thị **số liệu, biểu đồ tỷ lệ tiêu cực và các cảnh báo**.

*(Chỉ vào ⑫, ⑬.)*
Doanh nghiệp còn có thể bấm **Phân tích AI**. Máy chủ API gửi các bình luận trong khoảng thời gian đã chọn cho AI. AI **tóm tắt** khách hàng đang phàn nàn điều gì và **đề xuất** hướng xử lý, kèm dẫn chứng là các bình luận cụ thể. Đề xuất chỉ mang tính tham khảo; quyết định cuối cùng vẫn thuộc về doanh nghiệp.

*(Kết phần B.)*
Tóm lại: doanh nghiệp chỉ cần đăng ký một lần. Sau đó, cứ mỗi phút hệ thống tự thu thập qua Firecrawl, lưu trữ, phân tích cảm xúc bằng AI, và chủ động gửi email khi phản hồi tiêu cực tăng bất thường.

## Phần C — Dịch vụ AWS

*(Cuộn xuống phần C.)*

Tiếp theo, em xin giới thiệu các dịch vụ AWS mà nhóm dùng để xây dựng từng khối trong sơ đồ vừa rồi. Các dịch vụ được chia thành sáu nhóm.

**1. Truy cập và giao diện**
- **CloudFront** chính là cổng truy cập HTTPS. Đây là địa chỉ duy nhất của hệ thống. CloudFront trả giao diện web cho người dùng, và chuyển các yêu cầu có đường dẫn `/api` về phía backend. Nhờ vậy, web và API dùng chung một địa chỉ.
- **S3** lưu các tệp của giao diện web. Bucket để chế độ riêng tư, chỉ CloudFront được phép đọc.
- **Cognito** đảm nhận đăng ký, đăng nhập và cấp token cho người dùng. Nhóm không phải tự viết phần quản lý mật khẩu.

**2. Máy chủ ứng dụng**
- **Elastic Load Balancing**, cụ thể là Application Load Balancer, là bộ cân bằng tải. Nó liên tục kiểm tra sức khỏe từng máy và chỉ gửi yêu cầu tới máy đang hoạt động tốt.
- **EC2** là các máy chủ chạy API backend viết bằng FastAPI.
- **Auto Scaling** luôn giữ tối thiểu hai máy EC2. Khi một máy hỏng, nó tự tạo máy thay thế; khi CPU cao, nó tự thêm máy, tối đa ba máy.

**3. Dữ liệu**
- **RDS PostgreSQL** là cơ sở dữ liệu. AWS quản lý việc sao lưu và vận hành. Database nằm trong mạng riêng và không truy cập được từ Internet.

**4. Xử lý nền**
- **EventBridge** là bộ hẹn giờ, kích hoạt luồng thu thập mỗi phút.
- **SQS** là hàng đợi phiên thu thập. Đi kèm là một hàng đợi lỗi (DLQ) giữ lại các phiên xử lý thất bại nhiều lần.
- **Lambda** chạy phần lập lịch và bộ xử lý nền. Lambda chỉ chạy khi có việc và chỉ tính tiền theo thời gian chạy, nên phù hợp với các tác vụ ngắn, định kỳ.
- Riêng **Firecrawl** không thuộc AWS. Đây là dịch vụ bên ngoài mà bộ xử lý nền gọi để lấy bài viết và bình luận công khai.

**5. AI và thông báo**
- **Bedrock** cung cấp mô hình AI để phân loại cảm xúc, tóm tắt và đề xuất. Nhóm không phải tự huấn luyện mô hình.
- **SES** gửi email cảnh báo đến doanh nghiệp khi vượt ngưỡng.

**6. Nền tảng chung**: nhóm này không có khối riêng trong sơ đồ mà bao quanh toàn bộ hệ thống.
- **VPC** là mạng riêng của hệ thống, chia subnet public và private. Security Group chỉ cho máy EC2 nhận kết nối từ bộ cân bằng tải, nên bên ngoài không gọi thẳng vào máy chủ được.
- **IAM** cấp quyền tối thiểu cho từng thành phần. Ví dụ, bộ xử lý nền chỉ được đọc hàng đợi, gọi AI và gửi email.
- **Secrets Manager** giữ mật khẩu database. Mật khẩu không nằm trong mã nguồn; ứng dụng chỉ lấy ra khi chạy.
- **CloudWatch** thu thập log và chỉ số của API và bộ xử lý nền, đồng thời đặt cảnh báo vận hành.
- **CloudFormation** giúp toàn bộ hạ tầng được viết thành mã. Nhóm có thể dựng lại hoặc xóa sạch môi trường chỉ bằng một lệnh.

*(Kết phần giới thiệu, chuyển sang demo.)*
Với kiến trúc này, hệ thống hoàn toàn có khả năng triển khai thực tế: trước đó nhóm đã thu thập thành công dữ liệu thật từ mạng xã hội trên môi trường AWS. Trong phần demo sau đây, để dễ quan sát và có thể lặp lại, nhóm em sẽ dùng dữ liệu giả lập. Các bước lưu trữ, xếp hàng, xử lý, cảnh báo và phân tích AI vẫn chạy thật trên AWS.

## Phần E — Trình tự demo các dịch vụ AWS

> **Lưu ý (27/11):** người dùng đã chốt demo hệ thống trước theo [thao_tac_tung_buoc.md](thao_tac_tung_buoc.md), không xen AWS Console; phần trình diễn dịch vụ AWS làm riêng sau. Trình tự dưới đây còn theo kiểu xen kẽ và còn bước `release` đã bỏ, cần viết lại thành phần trình diễn AWS riêng.

Đi theo đúng hành trình B1 → B2 → B3: mỗi bước làm trên **web** hoặc **cmd**, rồi chuyển sang **AWS Console** để chỉ ra dịch vụ vừa xử lý. Số trong ngoặc, ví dụ (#3), là số thứ tự dịch vụ ở mục C. Lệnh cmd lấy ở mục D của [architecture.md](architecture.md).

### Chuẩn bị trước khi quay

- **Cửa sổ:** VS Code (`architecture.md` và tệp này), cmd đã chạy bước D0, trình duyệt có tab web và tab **Gmail**, trình duyệt AWS Console ở Region **Singapore (ap-southeast-1)**.
- **Mở sẵn các tab Console theo thứ tự dùng:** CloudFront, S3, Cognito, EC2 (Target Groups), CloudWatch (Log groups), RDS, Secrets Manager, CloudFormation, EventBridge, Lambda, SQS, SES, CloudWatch (Metrics), EC2 (Instances), Auto Scaling Groups.
- **Kiểm tra trạng thái ban đầu:** rule EventBridge đang **Disabled**; Target Group có 2 máy `healthy`.

---

### Bước 1. Mở web → CloudFront (#1), S3 (#2)

- **Web:** mở https://d1ymt5wg42h5sa.cloudfront.net, trang chào hiện ra.
- **Console → CloudFront → Distributions** → distribution `E16UVUGRUO3EVT`:
  - tab **General**: domain `d1ymt5wg42h5sa.cloudfront.net` trùng với địa chỉ web;
  - tab **Behaviors**: `/api/*` đi về Load Balancer, còn lại lấy từ S3.
- **Console → S3** → bucket `brand-tracking-demo-frontend-202611-frontendbucket-…`: thấy `index.html` và thư mục `assets/`.
- **Nói:** "Trang web em vừa mở được CloudFront phân phối qua HTTPS, các tệp giao diện nằm trong S3."

### Bước 2. Tạo tài khoản và đăng nhập → Cognito (#3)

- **Web:** bấm **Tạo tài khoản**, nhập email dạng `ten@example.invalid` và mật khẩu, rồi đăng nhập.
- **Console → Cognito → User pools** → `brand-demo-minute-auth-20261127-simulated` → **Users** → tải lại: tài khoản vừa tạo xuất hiện.
- **Nói:** "Cognito quản lý tài khoản; môi trường demo xác nhận email giả lập nên không cần mã xác minh."

### Bước 3. Đăng ký theo dõi nhãn hàng → ALB (#4), EC2 (#5), CloudWatch (#16), RDS (#7), VPC (#13), Secrets Manager (#15)

- **Web:**
  1. **Thêm nhãn hàng**: nhập tên, từ khóa, rồi **Tạo nhãn hàng**.
  2. Tab **Cảnh báo**: ở quy tắc **Bình luận**, bật quy tắc, **Ngưỡng tăng** `50`, **Số nội dung tối thiểu** `10`, rồi **Lưu quy tắc**.
  3. Cùng tab, mục **Email nhận cảnh báo**: nhập email đã xác minh SES, rồi **Lưu người nhận**.
  4. Sao chép **mã nhãn hàng** để dùng ở bước 4.
- **Console → EC2 → Target Groups** → `brand-Targe-OIRAOTIUEBJU` → **Targets**: 2 máy `healthy`.
  **Nói:** "Yêu cầu tạo nhãn hàng đi qua Load Balancer, tới một trong hai máy EC2 chạy API."
- **Console → CloudWatch → Log groups** → `/brand-demo/brand-demo-minute-ec2-20261127/api`: tìm dòng `"POST /api/brands HTTP/1.1" 201 Created` đúng thời điểm vừa bấm (hoặc chạy bước D2 trong cmd).
- **Console → RDS → Databases** → `brand-demo-minute-data-…-database` → **Connectivity & security**:
  - trạng thái `available`, **Publicly accessible: No**;
  - VPC `vpc-04c05b770dcb4567d` và Security Group.
  **Nói:** "Nhãn hàng vừa tạo được lưu trong RDS. Database nằm trong VPC riêng, không mở ra Internet."
- **Console → Secrets Manager** → `DbSecret-124jeKaV9kXn`: chỉ tên secret, **không** bấm "Retrieve secret value".
  **Nói:** "Mật khẩu database nằm ở Secrets Manager, không có trong mã nguồn."

### Bước 4. Bật theo dõi tự động → CloudFormation (#17), EventBridge (#8)

- **cmd:** dán bước **D3** (`set BRAND_ID=…` rồi `python demo\demo_control.py start …`).
- **Console → CloudFormation → Stacks** → `brand-demo-minute-api-20261127`: trạng thái `UPDATE_IN_PROGRESS`, sau đó `UPDATE_COMPLETE`, khoảng 1–2 phút.
  **Nói:** "Toàn bộ hạ tầng được quản lý bằng CloudFormation; lệnh vừa rồi cập nhật cấu hình để bật lịch thu thập."
- **Console → EventBridge → Rules** → `brand-demo-minute-api-20261127-WorkerRule-…`: chuyển từ **Disabled** sang **Enabled**, lịch `rate(1 minute)`.
  **Nói:** "Từ giờ, cứ mỗi phút EventBridge sẽ kích hoạt việc thu thập."

### Bước 5. Lần thu thập đầu tiên → Lambda (#10), SQS (#9), IAM (#14), CloudWatch (#16)

- **Web:** khoảng 1 phút sau, tab **Cảnh báo**: lần mốc **20/100 = 20%**, chưa có cảnh báo.
- **Console → Lambda** → `brand-demo-minute-api-20261127-WorkerFunction-…` → **Monitor**: số lần gọi (Invocations) tăng.
- **Console → SQS** → `brand-demo-minute-api-20261127-WorkerQueue-…` → **Monitoring**: có tin nhắn được gửi và nhận. DLQ vẫn 0 tin, tức không có phiên lỗi.
  **Nói:** "EventBridge gọi Lambda xếp phiên vào SQS, SQS giao phiên cho Lambda worker xử lý."
- **Console → Lambda → Configuration → Permissions** → bấm vào tên role để sang **IAM**: chỉ các policy `WorkerQueueAccess`, `SendAlertEmail`, quyền gọi Bedrock.
  **Nói:** "Mỗi thành phần chỉ có đúng những quyền cần dùng."
- **Console → CloudWatch → Log groups** → `/aws/lambda/brand-demo-minute-api-20261127-WorkerFunction-…`: tìm `demo_queued`, `demo_alert_evaluation`.

### Bước 6. Phản hồi tiêu cực tăng → cảnh báo trên web và email qua SES (#12)

- **Web:** khoảng 3 phút sau lần mốc, tab **Cảnh báo**: tỷ lệ lên **60/200 = 30%**, xuất hiện **Cảnh báo: bình luận tiêu cực tăng**.
  **Nói:** "Tỷ lệ tăng từ 20% lên 30%, tức tăng 50%, đạt ngưỡng đã đặt."
- **Gmail:** email cảnh báo đến (có thể nằm trong Spam). Bấm link trong email để mở thẳng trang cảnh báo.
- **Console → Amazon SES → Account dashboard**: số email đã gửi tăng (có thể chậm vài phút).
  Bằng chứng tức thời: log worker có dòng `demo_alert_evaluation` với `"notified": true`.
  **Nói:** "Worker phát hiện vượt ngưỡng và gửi email qua SES ngay cho doanh nghiệp."
- **Web:** bấm **Đánh giá lại lần thu thập gần nhất**, không có cảnh báo trùng.

### Bước 7. Phân tích AI → Bedrock (#11)

- **Web:** tab **Phân tích AI**:
  - **Thu thập từ**: khoảng 1 giờ trước;
  - **Thu thập trước**: bằng giờ hiện tại hoặc sớm hơn, nhưng sau lần cảnh báo (không được đặt giờ tương lai);
  - bấm **Tạo phân tích**, chờ kết quả và mở vài dẫn chứng.
- **Console → CloudWatch → Metrics → All metrics → Bedrock → By ModelId**: model `apac.amazon.nova-lite-v1:0`, chỉ số **Invocations** tăng.
  **Nói:** "API gọi Amazon Bedrock, mô hình Nova Lite, để tóm tắt và đề xuất. Đề xuất chỉ mang tính tham khảo."
- **Lưu ý:** không nói nhãn cảm xúc của dữ liệu demo do Bedrock tạo. Các nhãn này được gán sẵn.

### Bước 8. Phản hồi tích cực (chỉ trên web)

- **cmd:** chạy bước **D5** (`release`).
- **Web:** khoảng 10 giây sau, **65/300 ≈ 22%**, không có cảnh báo mới.
  **Nói:** "Sau khi doanh nghiệp xử lý, tỷ lệ tiêu cực giảm và hệ thống không cảnh báo nữa."

### Bước 9. Khả năng chịu lỗi → EC2 (#5), ALB (#4), Auto Scaling (#6)

- **Console → EC2 → Instances**: chọn **một** trong hai máy của Auto Scaling Group → **Instance state → Terminate**.
- **Web:** tải lại trang và bấm qua vài tab, mọi thứ vẫn hoạt động.
- **Console → EC2 → Target Groups → Targets**: máy vừa tắt chuyển sang `draining`, máy còn lại vẫn `healthy`.
- **Console → EC2 → Auto Scaling Groups** → tab **Activity**: Auto Scaling tự khởi chạy máy thay thế. Máy mới thành `healthy` sau vài phút; có thể cắt đoạn chờ khi dựng video.
  **Nói:** "Một máy hỏng thì Load Balancer chuyển hết yêu cầu sang máy còn lại, Auto Scaling tự tạo máy mới. Người dùng không bị gián đoạn."
- **Lưu ý:** chỉ làm khi đang có đủ 2 máy `healthy`.

### Bước 10. Kết thúc → EventBridge (#8)

- **cmd:** chạy bước **D6** (`stop`).
- **Console → EventBridge → Rules**: rule trở lại **Disabled**.
  **Nói:** "Em tắt lịch thu thập để kết thúc demo."
- **Web:** quay về tab **Tổng quan** để chốt lại toàn bộ luồng.

### Tổng hợp dịch vụ đã demo

| Bước | Dịch vụ (#) |
|---|---|
| 1 | CloudFront (1), S3 (2) |
| 2 | Cognito (3) |
| 3 | ALB (4), EC2 (5), RDS (7), VPC (13), Secrets Manager (15), CloudWatch (16) |
| 4 | EventBridge (8), CloudFormation (17) |
| 5 | SQS (9), Lambda (10), IAM (14) |
| 6 | SES (12) |
| 7 | Bedrock (11) |
| 9 | Auto Scaling (6) |

Đủ **17/17** dịch vụ ở mục C. Firecrawl không thuộc AWS và không được gọi trong dữ liệu demo.
