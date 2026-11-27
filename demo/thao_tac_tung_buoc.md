# Thao tác demo từng bước

Hướng dẫn chạy và quay phần **demo hệ thống** với dữ liệu giả của thương hiệu hư cấu **KFCC** (gà rán, burger, Coca). Tệp này đủ để làm từ đầu đến cuối; phần trình diễn các dịch vụ trên AWS Console làm riêng, sau phần này.

## 1. Những điều cần biết về dữ liệu giả

- **Hệ thống thật, dữ liệu giả.** Lệnh mô phỏng chỉ thay nguồn dữ liệu: không gọi Firecrawl mà tự sinh bài viết và bình luận. Đăng nhập, lưu trữ, hàng đợi, xử lý nền, cảnh báo, email và AI đều chạy thật trên AWS.
- **Mỗi lần chạy có 2 đợt.** Mỗi đợt gồm 1 bài viết và 100 bình luận; tỷ lệ tiêu cực được tính **cộng dồn**:

  | Đợt | Bài viết giả | Tiêu cực / tổng | Tỷ lệ | Thời điểm |
  |---|---|---|---|---|
  | 1 (phần lớn tích cực) | KFCC ra mắt combo gà rán mới. | 20 / 100 | 20%, chưa cảnh báo | khoảng 1 phút sau khi lệnh chạy xong |
  | 2 (tiêu cực tăng) | Khách hàng phản ánh về chất lượng gà rán KFCC. | 60 / 200 | 30% (tăng 50%), có **cảnh báo** và **email** | khoảng 3 phút sau đợt 1 |

- **Ví dụ bình luận giả:**
  - Tích cực: "Gà rán giòn rụm, ngon tuyệt.", "Burger bò phô mai rất đáng tiền.", "Combo gà rán kèm Coca mát lạnh."
  - Trung tính: "Mới thấy quảng cáo KFCC.", "Combo gà rán giá bao nhiêu nhỉ?"
  - Tiêu cực: "Gà rán bị khô, kém giòn.", "Burger nguội, bánh bị mềm.", "Coca hết ga khi giao tới."
- **Dấu hiệu nhận biết:** nội dung có tiền tố **[DỮ LIỆU GIẢ]**, nguồn ghi "Dữ liệu giả lập", liên kết dạng `.invalid` không mở được. Nhãn cảm xúc được **gán sẵn**; AI chỉ dùng để tóm tắt và đề xuất.
- **Mỗi lần chạy phải dùng một nhãn hàng MỚI.** Số liệu cộng dồn theo nhãn hàng, chạy lại trên nhãn hàng cũ sẽ ra số sai. Lượt tập và lượt quay phải là hai nhãn hàng khác nhau.
- **Điều kiện để có dữ liệu:** nhãn hàng có ít nhất 1 từ khóa, nguồn **chỉ TikTok**, trạng thái **đang theo dõi**.
- **Không bấm "Tạo phiên chờ"** trong tab Phiên tracking. Nút này tạo phiên thu thập thật, có thể làm lẫn dữ liệu.
- **Email:** SES đang ở chế độ sandbox, chỉ gửi được tới địa chỉ đã xác minh (email của nhóm trưởng). Thư có thể rơi vào mục Spam.

## 2. Các bước

### Bước 0. Chuẩn bị cmd (trước khi quay)

Mở **cmd** (không dùng PowerShell), dán cả khối:

```bat
cd /d E:\TaiLieuHocTap\Nam3_Ky1\Cloud\brand-autotracking
set AWS_PROFILE=profile-name-logn
set AWS_REGION=ap-southeast-1
set API_STACK=brand-demo-minute-api-20261127
aws sso login
```

Khi trình duyệt mở trang đăng nhập AWS, bấm cho phép. Để cửa sổ cmd này mở suốt buổi.

### Bước 1. Tạo tài khoản bằng email thật (web, Gmail)

1. Mở https://d1ymt5wg42h5sa.cloudfront.net, bấm **Tạo tài khoản**.
2. Nhập **email thật** (ví dụ Gmail) và **mật khẩu** tối thiểu **12 ký tự**, gồm chữ **hoa**, chữ **thường**, **số** và **ký tự đặc biệt**, ví dụ `Demo@2026Cloud`. Ghi lại để đăng nhập lại khi cần.
3. Mở hộp thư, tìm email **"Mã xác minh Brand Auto-Tracking"** từ `no-reply@verificationemail.com` (xem cả Spam), nhập mã 6 số vào trang Cognito.
4. Trình duyệt quay lại web và vào ứng dụng. Nếu chưa vào thẳng, bấm **Đăng nhập** bằng email và mật khẩu vừa tạo.

> Muốn quay lại cảnh "tài khoản mới": dùng một email khác, hoặc xóa người dùng cũ trong **Cognito → Users** trước khi quay (nhãn hàng cũ của tài khoản đó sẽ không còn hiện).

### Bước 2. Đăng ký theo dõi nhãn hàng (web)

1. Thanh bên trái, bấm **Thêm nhãn hàng**.
2. **Tên:** đặt tên mới mỗi lần, ví dụ `KFCC 01`.
3. **Từ khóa (mỗi dòng một từ):** `KFCC` và `gà rán KFCC`.
4. **Nền tảng:** chỉ chọn **TikTok**.
5. **Tần suất, giờ chạy, số bài mỗi lượt:** để mặc định.
6. Bấm **Tạo nhãn hàng** và kiểm tra nhãn hàng ở trạng thái **Đang theo dõi**.

### Bước 3. Đặt ngưỡng cảnh báo và email nhận (web, tab Cảnh báo)

1. Chọn nhãn hàng vừa tạo, mở tab **Cảnh báo**.
2. Ở thẻ quy tắc **Bình luận**:
   - bật **Bật quy tắc**;
   - **Ngưỡng tăng (%)** = `50`;
   - **Số nội dung tối thiểu** = `10`;
   - bấm **Lưu quy tắc**.
3. Mục **Email nhận cảnh báo**: nhập email đã xác minh, bấm **Lưu người nhận**.
4. Chép mã nhãn hàng: **nháy đúp vào ô chữ cái đại diện** của nhãn hàng (ô vuông màu ở đầu trang, cạnh tên nhãn hàng) để chép mã; dòng "Đã chép mã" hiện trong 2 giây. Mã không hiển thị trên màn hình, nên có thể làm ngay cả khi đang quay.

> Phải làm xong bước 3 **trước** khi chạy lệnh mô phỏng. Nếu chưa lưu quy tắc, đợt 2 sẽ không có cảnh báo.

### Bước 4. Bắt đầu mô phỏng dữ liệu (cmd)

Dán từng dòng. Thay `DAN_MA_VAO_DAY` bằng mã vừa sao chép:

```bat
set BRAND_ID=DAN_MA_VAO_DAY
python demo\demo_control.py start --stack %API_STACK% --brand-id %BRAND_ID%
```

- Lệnh in mã phiên, rồi báo **"Đang chờ CloudFormation cập nhật..."**. Chờ **1–2 phút** đến khi in **"Đã bật dòng dữ liệu demo…"**.
- **Không đóng cmd** và **không chạy lại lệnh** trong lúc chờ.
- Ghi nhớ giờ lệnh chạy xong; sẽ dùng ở bước 6.

### Bước 5. Đợt 1: dữ liệu ban đầu (web)

1. Quay lại web, tab **Cảnh báo**. Tab tự cập nhật mỗi 10 giây, không cần tải lại trang.
2. Khoảng 1 phút sau, tỷ lệ hiện **20/100 = 20%**, **chưa có cảnh báo**.
3. Mở tab **Nội dung** để xem bài viết "KFCC ra mắt combo gà rán mới" và các bình luận giả: phần lớn khen gà rán, burger.

### Bước 6. Phân tích AI trong lúc chờ đợt 2 (web, tab Phân tích AI)

Đợt 2 đến sau khoảng 3 phút; dùng thời gian này để demo AI trên dữ liệu đợt 1.

1. Mở tab **Phân tích AI**.
2. **Thu thập từ:** trước giờ chạy lệnh ở bước 4, ví dụ lùi lại 30 phút.
3. **Thu thập trước:** **giờ hiện tại**, tức đã qua và sau khi đợt 1 xuất hiện.
   - **Không đặt giờ trong tương lai**: hệ thống sẽ báo lỗi "Chọn khoảng thời gian đã qua…".
4. Bấm **Tạo phân tích**, chờ khoảng 10–30 giây.
5. Kết quả gồm 1–3 ý **bằng tiếng Việt**, mỗi ý có **Gợi ý** và phần **Dẫn chứng** là chính các câu bình luận. Với đợt 1, AI thường nhận xét khách khen gà rán, burger và dịch vụ, kèm vài phàn nàn nhỏ.
6. **Nói:** "AI chỉ gợi ý để tham khảo, gắn với dữ liệu và khoảng thời gian đã chọn; quyết định thuộc về doanh nghiệp."

### Bước 7. Đợt 2: phản hồi tiêu cực tăng, có cảnh báo và email (web, Gmail)

1. Quay lại tab **Cảnh báo**. Khoảng 3 phút sau đợt 1, tỷ lệ lên **60/200 = 30%** và xuất hiện **Cảnh báo: bình luận tiêu cực tăng**.
   - **Nói:** "Tỷ lệ tiêu cực tăng từ 20% lên 30%, tức tăng 50%, đạt ngưỡng đã đặt nên hệ thống cảnh báo."
2. Mở **Gmail**: có email cảnh báo (xem cả Spam). Bấm link trong email để mở thẳng trang cảnh báo trên web.
3. Bấm **Đánh giá lại lần thu thập gần nhất**: không tạo thêm cảnh báo trùng.
4. *(Tùy chọn)* Tab **Phân tích AI**: tạo phân tích lần 2, đặt **Thu thập trước** = giờ hiện tại. AI dùng tối đa 30 nội dung mới nhất, nên lần này sẽ tập trung vào các phàn nàn của đợt 2 (gà khô, giao chậm, Coca hết ga). So sánh với lần 1 để thấy hệ thống bắt được thay đổi.

### Bước 8. Kết thúc (cmd), bắt buộc

```bat
python demo\demo_control.py stop --stack %API_STACK%
```

- Lệnh tắt lịch mô phỏng, mất khoảng 1–2 phút. Phải chạy sau mỗi lần chạy; lần `start` tiếp theo sẽ **từ chối** nếu lịch còn bật.
- Lần chạy sau: dùng **nhãn hàng mới**, có thể giữ tài khoản cũ.

## 3. Lượt tập và lượt quay

1. **Lượt tập:** tạo tài khoản bằng một email thật, nhãn hàng `KFCC 01`. Chạy hết bước 1–8, nhất là kiểm tra email đến.
2. **Lượt quay:** email khác (hoặc xóa người dùng của lượt tập trong Cognito) để quay cảnh tạo tài khoản và nhận mã, nhãn hàng mới `KFCC 02`.

Thời lượng một lượt khoảng 10–12 phút; khi dựng video có thể cắt các đoạn chờ.

## 4. Khi gặp sự cố

| Tình huống | Cách xử lý |
|---|---|
| Không thấy email mã xác minh | Xem Spam, chờ 1–2 phút, bấm **Resend code**. Email mặc định của Cognito giới hạn khoảng 50 email/ngày |
| Đăng ký báo lỗi mật khẩu | Đủ 12 ký tự, có chữ hoa, chữ thường, số và ký tự đặc biệt |
| Đăng ký báo email đã tồn tại | Bấm **Đăng nhập** bằng email đó, hoặc dùng email khác |
| Quay về web với lỗi đăng nhập | Bấm lại **Đăng nhập**; nếu vẫn lỗi, dùng dự phòng: **Tạo tài khoản** với email đuôi `@example.invalid` (ví dụ `demo01@example.invalid`), tài khoản này được tự xác nhận, không cần mã |
| `start` báo "Dừng lịch trước…" | Chạy lệnh `stop` ở bước 8, chờ xong rồi chạy lại `start` |
| Lệnh báo hết phiên (token expired) | Chạy `aws sso login` |
| Quá 3 phút sau lệnh vẫn chưa có đợt 1 | Kiểm tra mã nhãn hàng, từ khóa, nguồn TikTok và trạng thái đang theo dõi |
| Phân tích AI báo "Chọn khoảng thời gian đã qua…" | **Thu thập trước** đang ở tương lai; đổi về giờ hiện tại |
| Phân tích AI báo "Không tạo được phân tích" | Bấm **Tạo phân tích** lại một lần; nếu vẫn lỗi, cắt đoạn đó khi dựng video |
| Có đợt 2 nhưng không có cảnh báo | Kiểm tra quy tắc **Bình luận** đã bật và lưu với ngưỡng 50, tối thiểu 10; bấm **Đánh giá lại lần thu thập gần nhất** |
| Không thấy email | Xem mục Spam; kiểm tra đã **Lưu người nhận** đúng email đã xác minh |
