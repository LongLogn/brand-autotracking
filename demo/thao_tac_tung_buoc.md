# Thao tác demo từng bước

Video gồm ba phần, quay theo thứ tự:

| Phần | Nội dung | Cửa sổ dùng | Thời lượng gợi ý |
|---|---|---|---|
| **A** | Demo hệ thống trên web (nhãn hàng thật NVIDIA + dữ liệu mô phỏng KFCC) | Trình duyệt web, Gmail, cmd | 6–8 phút (cắt đoạn chờ) |
| **B** | Mã nguồn và cách cài đặt trên GitHub | Trình duyệt GitHub | 4–5 phút |
| **C** | Các dịch vụ AWS trên AWS Console | Trình duyệt AWS Console | 6–8 phút |

**Chuẩn bị chung trước khi quay:**

- Tab web https://d1ymt5wg42h5sa.cloudfront.net và tab **Gmail**.
- Tab GitHub https://github.com/LongLogn/brand-autotracking (nhánh `main`, đã có README mới).
- Tab **AWS Console**: tài khoản `2033-5843-2497`, Region **Asia Pacific (Singapore) ap-southeast-1** (chọn ở góc trên bên phải). Sai Region thì CloudFormation, EC2, RDS… đều trống.
- Cửa sổ **cmd** đã làm bước A0.

---

# Phần A — Demo hệ thống trên web

## A.1. Những điều cần biết về dữ liệu giả

- **Hệ thống thật, dữ liệu giả.** Lệnh mô phỏng chỉ thay nguồn dữ liệu: không gọi Firecrawl mà tự sinh bài viết và bình luận. Đăng nhập, lưu trữ, hàng đợi, xử lý nền, cảnh báo, email và AI đều chạy thật trên AWS.
- **Mỗi lần chạy có 2 đợt.** Mỗi đợt gồm 1 bài viết và 100 bình luận; tỷ lệ tiêu cực được tính **cộng dồn**:

  | Đợt | Bài viết giả | Tiêu cực / tổng | Tỷ lệ | Thời điểm |
  |---|---|---|---|---|
  | 1 (phần lớn tích cực) | KFCC ra mắt combo gà rán mới. | 20 / 100 | 20%, chưa cảnh báo | khoảng 1 phút sau khi lệnh chạy xong |
  | 2 (tiêu cực tăng) | Khách hàng phản ánh về chất lượng gà rán KFCC. | 60 / 200 | 30% (tăng 50%), có **cảnh báo** và **email** | khoảng 1 phút sau đợt 1 |

- **Ví dụ bình luận giả:**
  - Tích cực: "Gà rán giòn rụm, ngon tuyệt.", "Burger bò phô mai rất đáng tiền.", "Combo gà rán kèm Coca mát lạnh."
  - Trung tính: "Mới thấy quảng cáo KFCC.", "Combo gà rán giá bao nhiêu nhỉ?"
  - Tiêu cực: "Gà rán bị khô, kém giòn.", "Burger nguội, bánh bị mềm.", "Coca hết ga khi giao tới."
- **Dấu hiệu nhận biết:** nội dung có tiền tố **[DỮ LIỆU GIẢ]**, nguồn ghi "Dữ liệu giả lập", liên kết dạng `.invalid` không mở được. Nhãn cảm xúc được **gán sẵn**; AI chỉ dùng để tóm tắt và đề xuất.
- **Mỗi lần chạy phải dùng một nhãn hàng MỚI.** Số liệu cộng dồn theo nhãn hàng, chạy lại trên nhãn hàng cũ sẽ ra số sai. Lượt tập và lượt quay phải là hai nhãn hàng khác nhau.
- **Điều kiện để có dữ liệu:** nhãn hàng có ít nhất 1 từ khóa, nguồn **chỉ TikTok**, trạng thái **đang theo dõi**.
- **Không bấm "Thu thập ngay" trên nhãn hàng mô phỏng (KFCC)** và **không xóa nhãn hàng** đang mô phỏng. Nút **Thu thập ngay** chỉ dùng cho nhãn hàng thật ở bước A2b.
- **Email:** SES đang ở chế độ sandbox, chỉ gửi được tới địa chỉ đã xác minh (email của nhóm trưởng). Thư có thể rơi vào mục Spam.

## A.2. Các bước

### Bước A0. Chuẩn bị cmd (trước khi quay)

Mở **cmd** (không dùng PowerShell), dán cả khối:

```bat
cd /d E:\TaiLieuHocTap\Nam3_Ky1\Cloud\brand-autotracking
set AWS_PROFILE=profile-name-logn
set AWS_REGION=ap-southeast-1
set API_STACK=brand-demo-minute-api-20261127
aws sso login
```

Khi trình duyệt mở trang đăng nhập AWS, bấm cho phép. Để cửa sổ cmd này mở suốt buổi.

### Bước A1. Tạo tài khoản bằng email thật (web, Gmail)

1. Mở https://d1ymt5wg42h5sa.cloudfront.net, bấm **Tạo tài khoản**.
2. Nhập **email thật** (ví dụ Gmail) và **mật khẩu** tối thiểu **12 ký tự**, gồm chữ **hoa**, chữ **thường**, **số** và **ký tự đặc biệt**, ví dụ `Demo@2026Cloud`. Ghi lại để đăng nhập lại khi cần.
3. Mở hộp thư, tìm email **"Mã xác minh Brand Auto-Tracking"** từ `no-reply@verificationemail.com` (xem cả Spam), nhập mã 6 số vào trang Cognito.
4. Trình duyệt quay lại web và vào ứng dụng. Nếu chưa vào thẳng, bấm **Đăng nhập** bằng email và mật khẩu vừa tạo.

> Muốn quay lại cảnh "tài khoản mới": dùng một email khác, hoặc xóa người dùng cũ trong **Cognito → Users** trước khi quay (nhãn hàng cũ của tài khoản đó sẽ không còn hiện).

### Bước A2. Đăng ký theo dõi nhãn hàng mô phỏng (web)

1. Thanh bên trái, bấm **Thêm nhãn hàng**.
2. **Tên:** đặt tên mới mỗi lần, ví dụ `KFCC 01`.
3. **Từ khóa (mỗi dòng một từ):** `KFCC` và `gà rán KFCC`.
4. **Nền tảng:** chỉ chọn **TikTok**.
5. **Tần suất, giờ chạy, số bài mỗi lượt:** để mặc định.
6. Bấm **Tạo nhãn hàng** và kiểm tra nhãn hàng ở trạng thái **Đang theo dõi**.

### Bước A2b (tùy chọn). Nhãn hàng thật thu thập bằng Firecrawl (web)

Cùng tài khoản, thêm một nhãn hàng có thật để chứng minh hệ thống thu thập dữ liệu thật. Làm **sau** bước A4 (khi `start` đã chạy xong) và trước bước A8: lệnh `stop` tạm dừng worker nên **Thu thập ngay** sẽ chờ đến lần `start` sau.

1. **Thêm nhãn hàng**: tên `NVIDIA`, từ khóa `Nvidia` (để đầu tiên) và `Jensen Huang`, nguồn **TikTok**, bấm **Tạo nhãn hàng**. Không nhập hai từ khóa chỉ khác hoa/thường (ví dụ `Nvidia` và `NVIDIA`): lưu cấu hình sẽ báo thất bại.
2. Tab **Cấu hình**: **Số bài mỗi lượt** = `3`, lưu.
3. Tab **Phiên tracking** → **Thu thập ngay**. Phiên chuyển **Đang chạy** sau tối đa 1 phút, xong sau khoảng 1–3 phút.
4. Tab **Nội dung**: xem bài TikTok và bình luận thật (mỗi bài một trang bình luận, khoảng 20–50). Bấm **Mở bài viết** hoặc bấm vào một bình luận để mở bài TikTok tương ứng (TikTok không có liên kết riêng cho từng bình luận).
5. Nhãn cảm xúc do AI (Bedrock) gán dần, khoảng 50 nội dung mỗi phút; tab **Tổng quan** có tỷ lệ tiêu cực sau 1–2 phút.
6. **Nói:** "Nhãn hàng này dùng dữ liệu thật thu qua Firecrawl và AI gán cảm xúc; còn KFCC dùng dữ liệu mô phỏng để chủ động tạo tình huống vượt ngưỡng và gửi email."

> Mỗi lần **Thu thập ngay** tốn khoảng 10–20 credit Firecrawl; giới hạn 200 credit/ngày. Không bấm liên tục.

### Bước A3. Đặt ngưỡng cảnh báo và email nhận (web, tab Cảnh báo)

1. Chọn nhãn hàng KFCC vừa tạo, mở tab **Cảnh báo**.
2. Ở thẻ quy tắc **Bình luận**:
   - bật **Bật quy tắc**;
   - **Ngưỡng tăng (%)** = `50`;
   - **Số nội dung tối thiểu** = `10`;
   - bấm **Lưu quy tắc**.
3. Mục **Email nhận cảnh báo**: nhập email đã xác minh, bấm **Lưu người nhận**.
4. Chép mã nhãn hàng: **nháy đúp vào ô chữ cái đại diện** của nhãn hàng (ô vuông màu ở đầu trang, cạnh tên nhãn hàng) để chép mã; dòng "Đã chép mã" hiện trong 2 giây. Mã không hiển thị trên màn hình, nên có thể làm ngay cả khi đang quay.

> Phải làm xong bước A3 **trước** khi chạy lệnh mô phỏng. Nếu chưa lưu quy tắc, đợt 2 sẽ không có cảnh báo.

### Bước A4. Bắt đầu mô phỏng dữ liệu (cmd)

Dán từng dòng. Dòng `stop` đầu tiên tắt lượt mô phỏng cũ nếu còn bật; thiếu dòng này, `start` báo **"Lượt mô phỏng trước vẫn đang bật"**. Chờ `stop` in **"Đã yêu cầu tắt lịch…"** (1–2 phút) rồi mới dán tiếp. Thay `DAN_MA_VAO_DAY` bằng mã vừa sao chép:

```bat
python demo\demo_control.py stop --stack %API_STACK%
set BRAND_ID=DAN_MA_VAO_DAY
python demo\demo_control.py start --stack %API_STACK% --brand-id %BRAND_ID% --interval-minutes 1
```

- `--interval-minutes 1`: hai đợt cách nhau khoảng 1 phút (bỏ tham số này thì cách 3 phút). Đợt 1 được xếp ngay khi lệnh chạy xong.
- Thời gian chờ chủ yếu là 1–2 phút CloudFormation cập nhật: có thể chạy bước A4 rồi **cắt đoạn chờ** khi dựng video.
- Lệnh in mã phiên, rồi báo **"Đang chờ CloudFormation cập nhật..."**. Chờ **1–2 phút** đến khi in **"Đã bật dòng dữ liệu demo…"**.
- **Không đóng cmd** và **không chạy lại lệnh** trong lúc chờ.
- Ghi nhớ giờ lệnh chạy xong; sẽ dùng ở bước A6.

### Bước A5. Đợt 1: dữ liệu ban đầu (web)

1. Quay lại web, tab **Cảnh báo**. Tab tự cập nhật mỗi 10 giây, không cần tải lại trang.
2. Khoảng 1 phút sau, tỷ lệ hiện **20/100 = 20%**, **chưa có cảnh báo**.
3. Mở tab **Nội dung** để xem bài viết "KFCC ra mắt combo gà rán mới" và các bình luận giả: phần lớn khen gà rán, burger.

### Bước A6. Phân tích AI (web, tab Phân tích AI)

Đợt 2 đến chỉ khoảng 1 phút sau đợt 1, nên có thể làm bước này **sau bước A7** (AI phân tích cả hai đợt, thấy rõ các phàn nàn mới).

1. Mở tab **Phân tích AI**.
2. **Thu thập từ:** trước giờ chạy lệnh ở bước A4, ví dụ lùi lại 30 phút.
3. **Thu thập trước:** **giờ hiện tại**, tức đã qua và sau khi đợt 1 xuất hiện.
   - **Không đặt giờ trong tương lai**: hệ thống sẽ báo lỗi "Chọn khoảng thời gian đã qua…".
4. Bấm **Tạo phân tích**, chờ khoảng 10–30 giây.
5. Kết quả gồm 1–3 ý **bằng tiếng Việt**, mỗi ý có **Gợi ý** và phần **Dẫn chứng** là chính các câu bình luận. Với đợt 1, AI thường nhận xét khách khen gà rán, burger và dịch vụ, kèm vài phàn nàn nhỏ.
6. **Nói:** "AI chỉ gợi ý để tham khảo, gắn với dữ liệu và khoảng thời gian đã chọn; quyết định thuộc về doanh nghiệp."

### Bước A7. Đợt 2: phản hồi tiêu cực tăng, có cảnh báo và email (web, Gmail)

1. Quay lại tab **Cảnh báo**. Khoảng 1 phút sau đợt 1, tỷ lệ lên **60/200 = 30%** và xuất hiện **Cảnh báo: bình luận tiêu cực tăng**.
   - **Nói:** "Tỷ lệ tiêu cực tăng từ 20% lên 30%, tức tăng 50%, đạt ngưỡng đã đặt nên hệ thống cảnh báo."
2. Mở **Gmail**, gõ `Brand Auto-Tracking` vào ô tìm kiếm: email cảnh báo đến ngay khi cảnh báo xuất hiện. Vì người gửi và người nhận là **cùng một Gmail**, thư có thể chỉ nằm ở **Tất cả thư** hoặc **Spam**, không hiện ở Hộp thư đến; nên mở sẵn kết quả tìm kiếm trước khi quay. Bấm link trong email để mở thẳng trang cảnh báo trên web.
3. Bấm **Đánh giá lại lần thu thập gần nhất**: không tạo thêm cảnh báo trùng.
4. *(Tùy chọn)* Tab **Phân tích AI**: tạo phân tích lần 2, đặt **Thu thập trước** = giờ hiện tại. AI dùng tối đa 30 nội dung mới nhất, nên lần này sẽ tập trung vào các phàn nàn của đợt 2 (gà khô, giao chậm, Coca hết ga). So sánh với lần 1 để thấy hệ thống bắt được thay đổi.

### Bước A8. Kết thúc mô phỏng (cmd), bắt buộc

```bat
python demo\demo_control.py stop --stack %API_STACK%
```

- Lệnh tắt lịch mô phỏng, mất khoảng 1–2 phút. Phải chạy sau mỗi lần chạy; lần `start` tiếp theo sẽ **từ chối** nếu lịch còn bật.
- Lần chạy sau: dùng **nhãn hàng mới**, có thể giữ tài khoản cũ.

## A.3. Lượt tập và lượt quay

1. **Lượt tập:** tạo tài khoản bằng một email thật, nhãn hàng `KFCC 01`. Chạy hết bước A1–A8, nhất là kiểm tra email đến.
2. **Lượt quay:** email khác (hoặc xóa người dùng của lượt tập trong Cognito) để quay cảnh tạo tài khoản và nhận mã, nhãn hàng mới `KFCC 02`.

Thời lượng một lượt khoảng 6–8 phút; khi dựng video có thể cắt các đoạn chờ.

## A.4. Khi gặp sự cố

| Tình huống | Cách xử lý |
|---|---|
| Không thấy email mã xác minh | Xem Spam, chờ 1–2 phút, bấm **Resend code**. Email mặc định của Cognito giới hạn khoảng 50 email/ngày |
| Đăng ký báo lỗi mật khẩu | Đủ 12 ký tự, có chữ hoa, chữ thường, số và ký tự đặc biệt |
| Đăng ký báo email đã tồn tại | Bấm **Đăng nhập** bằng email đó, hoặc dùng email khác |
| Quay về web với lỗi đăng nhập | Bấm lại **Đăng nhập**; nếu vẫn lỗi, đóng tab, mở lại link web rồi đăng nhập lại |
| Đăng ký báo "Please use a real email address" | Hệ thống chỉ nhận email thật; email thử như `@example.invalid` bị từ chối vì không nhận được mã |
| Tạo nhãn hàng báo "lưu cấu hình thất bại" | Từ khóa bị trùng (chỉ khác hoa/thường); xóa bớt rồi bấm **Thử lại lưu cấu hình** |
| Nhãn hàng thật báo lỗi `daily_estimated_credit_limit` | Hết 200 credit dự phòng trong ngày; dùng lại kết quả đã thu, hoặc nhờ AI nâng `WorkerDailyEstimatedCreditBudget` |
| `start` báo "Lượt mô phỏng trước vẫn đang bật" | Chạy lệnh `stop`, chờ xong rồi chạy lại `start` |
| Lệnh báo hết phiên (token expired) | Chạy `aws sso login` |
| Quá 3 phút sau `start` vẫn chưa có đợt 1 | Kiểm tra đã chép đúng mã của nhãn hàng **đang mở** (nháy đúp lại ô chữ cái), nhãn hàng chưa bị xóa, có từ khóa, nguồn TikTok, đang theo dõi; sai mã thì chạy `stop` rồi `start` lại với mã đúng |
| Phân tích AI báo "Chọn khoảng thời gian đã qua…" | **Thu thập trước** đang ở tương lai; đổi về giờ hiện tại |
| Phân tích AI báo "Không tạo được phân tích" | Bấm **Tạo phân tích** lại một lần; nếu vẫn lỗi, cắt đoạn đó khi dựng video |
| Có đợt 2 nhưng không có cảnh báo | Kiểm tra quy tắc **Bình luận** đã bật và lưu với ngưỡng 50, tối thiểu 10; bấm **Đánh giá lại lần thu thập gần nhất** |
| Không thấy email | Tìm `Brand Auto-Tracking` trong Gmail (xem **Tất cả thư**, **Spam**); kiểm tra đã **Lưu người nhận** đúng email đã xác minh SES. Nếu log worker có `"notified": true` thì email đã được gửi |

---

# Phần B — Mã nguồn và cách cài đặt (GitHub)

Mục tiêu: cho thấy hệ thống được tổ chức rõ ràng, ai cũng cài lại được, và toàn bộ hạ tầng AWS được viết bằng mã. **Không cần chạy lệnh cài đặt khi quay**, chỉ giải thích trên README.

### Bước B1. Trang chính repo và README

1. Mở https://github.com/LongLogn/brand-autotracking (nhánh `main`). README hiện ngay dưới danh sách thư mục.
2. Cuộn qua phần đầu README: tên dự án, link web demo, bảng **Chức năng**.
   - **Nói:** "Đây là mã nguồn của hệ thống vừa demo. README tóm tắt hệ thống làm gì: tài khoản, nhãn hàng, thu thập, phân loại cảm xúc, cảnh báo và phân tích AI."
3. Dừng ở sơ đồ **Kiến trúc** (GitHub tự vẽ sơ đồ).
   - **Nói:** "Người dùng vào qua CloudFront; giao diện nằm trên S3; API chạy trên các máy EC2 sau Load Balancer; dữ liệu ở RDS. Việc thu thập chạy nền: EventBridge mỗi phút gọi Lambda, phiên được xếp qua SQS, Lambda gọi Firecrawl, Bedrock và SES."

### Bước B2. Cấu trúc thư mục

1. Ở README, mục **Cấu trúc thư mục**; sau đó bấm vào từng thư mục trên GitHub:
   - `backend/` → `app/`: chỉ `main.py` (API), `lambda_worker.py` (worker), `sentiment.py` (AI cảm xúc), `demo_alerts.py` (cảnh báo).
   - `frontend/` → `src/`: giao diện React.
   - `infrastructure/`: các template CloudFormation.
   - **Nói:** "Backend viết bằng Python FastAPI, frontend bằng React. Cùng một gói backend chạy được cả trên EC2 (API) và Lambda (worker)."

### Bước B3. Cài đặt và chạy cục bộ

1. Về README, mục **Cài đặt và chạy cục bộ**.
2. Giải thích lần lượt ba khối lệnh:
   - **Backend:** tạo môi trường ảo Python, cài thư viện, `docker compose up` bật PostgreSQL cục bộ, `alembic upgrade head` tạo bảng, `uvicorn` chạy API.
   - **Frontend:** `npm install`, đặt địa chỉ API và Cognito, `npm run dev` mở giao diện ở `localhost:5173`. Không có Cognito thì bật `VITE_DEMO_MODE=true` để xem giao diện với dữ liệu mẫu.
   - **Kiểm thử:** chạy bộ kiểm thử backend và build frontend.
   - **Nói:** "Lập trình viên mới chỉ cần Python, Node.js và Docker là chạy được toàn bộ hệ thống trên máy cá nhân. Mật khẩu và khóa đều đặt qua biến môi trường, không ghi vào mã nguồn."

### Bước B4. Triển khai lên AWS bằng CloudFormation

1. README, mục **Triển khai lên AWS**: bảng 5 template theo thứ tự.
   - **Nói:** "Hạ tầng chia thành 5 lớp, mỗi lớp một stack: mạng và database; đăng nhập; web; worker; máy chủ API. Tách lớp để cập nhật hoặc tắt từng phần mà không ảnh hưởng dữ liệu, ví dụ xóa riêng máy chủ EC2 khi không dùng để tiết kiệm."
2. Bấm `infrastructure/aws-demo-ec2-api.yaml`, cuộn tới `AutoScalingGroup` (dòng có `MinSize`, `MaxSize`) và `LoadBalancer`.
   - **Nói:** "Đây là ví dụ hạ tầng viết bằng mã: nhóm Auto Scaling 1–3 máy, Load Balancer kiểm tra sức khỏe máy. Chạy lại template là dựng lại đúng môi trường này."
3. Quay lại README: lệnh `python scripts/package_lambda.py` đóng gói backend, và link [infrastructure/README.md](../infrastructure/README.md) cho tham số chi tiết.

### Bước B5. Tài liệu

1. README, mục **Tài liệu**; bấm `docs/` để thấy SRS, kiến trúc, lộ trình và `development-process/` (hồ sơ từng giai đoạn S0–S8).
   - **Nói:** "Nhóm làm theo lộ trình 9 giai đoạn, mỗi giai đoạn có hồ sơ kết quả và bằng chứng kiểm thử."

---

# Phần C — Các dịch vụ AWS trên Console

Đi theo **đường đi của dữ liệu**: người dùng vào web → đăng nhập → API → database → xử lý nền → AI và email → giám sát. Số (#) là số thứ tự dịch vụ ở mục C của [architecture.md](architecture.md). Chỉ **xem**, không bấm sửa hay xóa (trừ bước C5 tùy chọn).

### Bước C1. Toàn bộ hạ tầng → CloudFormation (#17)

- **Console → CloudFormation → Stacks**: gõ `brand-demo-minute` vào ô lọc, thấy 4 stack `data`, `auth`, `api`, `ec2` (`…_COMPLETE`); xóa lọc, gõ `frontend` để thấy stack web `brand-tracking-demo-frontend-20261122`. Các stack khác (`item1`, `dev-auth`, `review-data`) là bản thử cũ, không cần giới thiệu.
- Bấm `brand-demo-minute-ec2-20261127` → tab **Resources**: danh sách máy, Load Balancer, Auto Scaling do stack tạo ra.
- **Nói:** "Toàn bộ hạ tầng được dựng từ các template trên GitHub vừa xem. Mỗi stack là một lớp của hệ thống."

### Bước C2. Cổng vào web → CloudFront (#1), S3 (#2)

- **Console → CloudFront → Distributions** → `E16UVUGRUO3EVT`:
  - tab **General**: domain `d1ymt5wg42h5sa.cloudfront.net` trùng với địa chỉ web;
  - tab **Behaviors**: `/api/*` đi về Load Balancer, còn lại lấy từ S3.
- **Console → S3** → bucket `brand-tracking-demo-frontend-202611-frontendbucket-zlbh2jwx90d9`: `index.html` và thư mục `assets/`; tab **Permissions**: **Block all public access: On**.
- **Nói:** "Người dùng chỉ truy cập qua CloudFront bằng HTTPS. Các tệp giao diện nằm trong S3 riêng tư, chỉ CloudFront đọc được."

### Bước C3. Tài khoản → Cognito (#3)

- **Console → Cognito → User pools** → `brand-demo-minute-auth-20261127-simulated`:
  - **Users**: tài khoản tạo ở bước A1, **Confirmed**, email **Verified**;
  - **Authentication → Sign-up**: tự đăng ký bật, xác minh email; **Messaging → Message templates**: nội dung email mã xác minh tiếng Việt;
  - **Branding → Managed login**: trang đăng nhập cùng màu với web.
- **Nói:** "Cognito lo đăng ký, gửi mã xác minh, giữ mật khẩu và cấp token. Ứng dụng không lưu mật khẩu người dùng."

### Bước C4. Máy chủ API → ALB (#4), EC2 (#5), Auto Scaling (#6)

- **Console → EC2 → Load Balancers** → `brand--LoadB-vSwjfxoY0LWL`: hai Availability Zone.
- **EC2 → Target Groups** → `brand-Targe-OIRAOTIUEBJU` → **Targets**: 2 máy `healthy`; tab **Health checks**: đường dẫn `/health`.
- **EC2 → Auto Scaling Groups** → `brand-demo-minute-ec2-20261127-AutoScalingGroup-…`: **Desired 2, Min 2, Max 3**; tab **Automatic scaling**: giữ CPU trung bình 50%.
- **Nói:** "API chạy trên hai máy EC2 ở hai vùng sẵn sàng khác nhau. Load Balancer chỉ gửi yêu cầu tới máy khỏe; Auto Scaling luôn giữ đủ 2 máy và tự thêm máy khi tải cao."

### Bước C5 (tùy chọn). Chịu lỗi → tắt một máy EC2

- Chỉ làm khi Target Group đang có **2 máy `healthy`**.
- **EC2 → Instances**: chọn **một** máy của Auto Scaling Group → **Instance state → Terminate**.
- **Web:** tải lại trang, bấm qua vài tab: vẫn hoạt động.
- **Auto Scaling Groups → Activity**: Auto Scaling tự tạo máy thay thế (máy mới `healthy` sau vài phút; cắt đoạn chờ khi dựng video).
- **Nói:** "Một máy hỏng, Load Balancer chuyển yêu cầu sang máy còn lại, Auto Scaling tự tạo máy mới. Người dùng không bị gián đoạn."

### Bước C6. Dữ liệu → VPC (#13), RDS (#7), Secrets Manager (#15)

- **Console → RDS → Databases** → `brand-demo-minute-data-20261127-database-bj5fufh0xcnk` → **Connectivity & security**: `available`, **Publicly accessible: No**, VPC `vpc-04c05b770dcb4567d`; tab **Maintenance & backups**: sao lưu tự động hằng ngày (giữ 1 ngày).
- **Console → VPC → Your VPCs** → `vpc-04c05b770dcb4567d` → **Resource map**: subnet công khai (Load Balancer, NAT) và subnet riêng (database, Lambda).
- **Console → Secrets Manager** → `DbSecret-124jeKaV9kXn` (mật khẩu database) và `brand-tracking-item1-firecrawl-20261119` (khóa Firecrawl): chỉ tên, **không** bấm "Retrieve secret value".
- **Nói:** "Database nằm trong mạng riêng, không mở ra Internet. Mật khẩu database và khóa Firecrawl nằm trong Secrets Manager, không có trong mã nguồn."

### Bước C7. Xử lý nền → EventBridge (#8), SQS (#9), Lambda (#10), IAM (#14)

- **Console → EventBridge → Rules** → bấm **Go to Scheduled rules** (dòng vàng; hoặc menu trái **Scheduler → Scheduled rules**) → `brand-demo-minute-api-20261127-WorkerRule-…`: lịch `rate(1 minute)` (Enabled khi đang demo, Disabled sau `stop`).
- **Console → SQS**: `…-WorkerQueue-cVLydxZzsq8S` (hàng đợi phiên) và `…-WorkerDeadLetterQueue-sPv93MJxFwwO` (DLQ giữ phiên lỗi, 0 tin).
- **Console → Lambda** → `brand-demo-minute-api-20261127-WorkerFunction-…`:
  - **Configuration → Triggers**: SQS và EventBridge (trạng thái Disabled nếu vừa chạy `stop`);
  - **Monitor**: số lần gọi theo phút;
  - **Configuration → Permissions** → bấm tên role để sang **IAM**: chỉ quyền đọc hàng đợi, đọc secret, gọi Bedrock, gửi SES.
- **Nói:** "Mỗi phút EventBridge gọi Lambda; phiên thu thập được xếp qua SQS, nếu lỗi sẽ được thử lại rồi chuyển vào DLQ. Lambda chỉ chạy khi có việc, và chỉ có đúng những quyền cần dùng."

### Bước C8. AI và email → Bedrock (#11), SES (#12)

- **Console → Amazon Bedrock → Model catalog**: **Amazon Nova Lite** (model phân loại cảm xúc và phân tích).
- **Console → CloudWatch → Metrics → All metrics → Bedrock → By ModelId**: `apac.amazon.nova-lite-v1:0`, chỉ số **Invocations** có số liệu từ phần A.
- **Console → Amazon SES → Identities**: địa chỉ gửi **Verified**; **Account dashboard**: số email đã gửi.
- **Nói:** "Bedrock gán cảm xúc cho bình luận thật và tóm tắt nguyên nhân cho doanh nghiệp. Khi vượt ngưỡng, SES gửi email cảnh báo. SES đang ở chế độ sandbox nên chỉ gửi tới địa chỉ đã xác minh."

### Bước C9. Giám sát → CloudWatch (#16)

- **Console → CloudWatch → Log groups**:
  - `/brand-demo/brand-demo-minute-ec2-20261127/api`: các yêu cầu API, ví dụ `POST /api/brands … 201`;
  - `/aws/lambda/brand-demo-minute-api-20261127-WorkerFunction-…`: dòng `tracking_run`, `sentiment_run`, `demo_alert_evaluation`.
- **CloudWatch → Alarms**: `WorkerRunAlarm` (phiên thu thập lỗi hoặc chỉ thành công một phần), `WorkerDeadLetterAlarm` (tin vào DLQ), `WorkerInvocationAlarm`, hai alarm Target Tracking của Auto Scaling. Nếu `WorkerRunAlarm` đang **In alarm**, đó là do một phiên thu thập thật bị lỗi/một phần gần đây: dùng làm ví dụ alarm hoạt động.
- **Nói:** "Mọi thành phần ghi log về CloudWatch; các alarm báo khi phiên thu thập lỗi hoặc khi cần tăng giảm số máy."

### Tổng hợp

| Bước | Dịch vụ (#) |
|---|---|
| C1 | CloudFormation (17) |
| C2 | CloudFront (1), S3 (2) |
| C3 | Cognito (3) |
| C4, C5 | ALB (4), EC2 (5), Auto Scaling (6) |
| C6 | RDS (7), VPC (13), Secrets Manager (15) |
| C7 | EventBridge (8), SQS (9), Lambda (10), IAM (14) |
| C8 | Bedrock (11), SES (12) |
| C9 | CloudWatch (16) |

Đủ **17/17** dịch vụ. Firecrawl không thuộc AWS; chỉ được nhắc ở bước C6 (khóa trong Secrets Manager) và phần A2b.
