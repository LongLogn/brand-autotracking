# Hướng dẫn thuyết trình demo

**Cập nhật:** 27/11/2026.

Kịch bản theo phút đã diễn tập trọn vẹn trên AWS thật ngày 27/11, qua CloudFront, Cognito demo, EC2 sau ALB, worker Lambda và Bedrock, với dữ liệu giả. **Email cảnh báo qua SNS chưa được thử** vì lúc diễn tập chưa có địa chỉ nhận. Bằng chứng và giới hạn xem [kế hoạch cập nhật demo](development-process/demo_update_plan.md).

**Phân vai:**
- **Người nói:** kể câu chuyện.
- **Người vận hành:** thao tác trên web và chạy lệnh.
- **Một máy hoặc một tab AWS Console:** chỉ ra dịch vụ đang chạy ở từng phần.

## Trước khi vào phòng

- **Dựng môi trường** theo [hướng dẫn hạ tầng](../infrastructure/README.md#demo-theo-phút-dữ-liệu-giả-cảnh-báo-và-email-2711-chưa-thử-trên-aws), rồi đăng nhập SSO.
- **Kiểm tra API:** `https://<FrontendUrl>/api/health` phải trả 200.
- **Kiểm tra EC2:** Target Group có 2 máy `healthy`.
- **Kiểm tra email:** hộp thư nhận cảnh báo đã xác nhận subscription SNS. Đánh dấu thư từ AWS Notifications là không phải spam.
- **Mở sẵn các tab:**
  - giao diện web;
  - hộp thư;
  - AWS Console: CloudFormation, EC2 (Target Group, Auto Scaling Group), Lambda, SQS, CloudWatch Logs, SNS, Cognito, RDS.
- **Chuẩn bị bản dự phòng:** [video diễn tập AWS 27/11](development-process/evidence/demo-minute-aws-20261127.webm). Video không âm thanh, dữ liệu giả, chạy trọn kịch bản. Trong video có AI, nhưng không có email hay AWS Console. Khi dùng phải nói rõ đây là bản ghi.

## Mở đầu (một câu)

"Hệ thống chạy được với dữ liệu thật qua luồng Firecrawl; để mọi người dễ theo dõi, hôm nay nhóm dùng **dữ liệu giả** và không đi qua Firecrawl."

## Phần 1 — Tạo tài khoản và lưu dữ liệu

1. Bấm **Tạo tài khoản**, đăng ký bằng email `...@example.invalid`. Nói: "Email demo được xác nhận giả lập."
2. Tạo nhãn hàng **Mây Tea** với từ khóa "Mây Tea".
3. Bật quy tắc **Bình luận tiêu cực**: ngưỡng tăng 50%, số tối thiểu 10, rồi lưu.
4. Bấm **Ngắt kết nối**, đăng nhập lại: Mây Tea vẫn còn, tức dữ liệu nằm trong database.
5. Trên Console:
   - **Cognito:** có tài khoản vừa tạo.
   - **CloudWatch** `/brand-demo/<stack>/api`: log `POST /api/brands`, ghi rõ mã máy EC2 đã xử lý yêu cầu.

## Phần 2 — Dữ liệu giả và cảnh báo qua email

1. Người vận hành sao chép **mã nhãn hàng** trên giao diện, rồi chạy:
   `python scripts/demo_control.py start --stack <stack-api-demo> --brand-id <mã>`
   Lệnh mất khoảng 1 phút.
2. Lần thu thập **mốc** xuất hiện sau khoảng 1 phút: 20/100, tỷ lệ 20%.
3. **Đóng tab web.** Trong lúc chờ, mở Console:
   - EventBridge rule chạy mỗi phút;
   - SQS;
   - log worker `demo_queued` và `tracking_run`.
4. **Khoảng 4 phút sau mốc**, đợt tiêu cực về: 60/200, tỷ lệ 30%, có cảnh báo, và **hộp thư nhận email**. Nói: "Tỷ lệ tiêu cực tăng từ 20% lên 30%, vượt ngưỡng 50% đã đặt."
5. **Bấm link trong email:** trang mở thẳng phần "Cảnh báo theo lần thu thập" và hiện dòng "Bạn mở từ email cảnh báo". Nếu phiên Cognito đã hết thì đăng nhập lại.
6. Bấm **Đánh giá lại lần thu thập gần nhất**: hệ thống báo đã có cảnh báo và không tạo bản sao.

## Phần 3 — AI phân tích và đề xuất

1. Ở mục **Phân tích AI**, chọn khoảng thời gian:
   - từ khoảng 1 giờ trước;
   - đến một phút tròn **sau** lúc đợt tiêu cực về (ví dụ đợt về lúc 12:59:33 thì chọn 13:00, và chờ qua 13:00).
2. Bấm **Tạo phân tích**. Lượt diễn tập 27/11 trả về 3 chủ đề: quá ngọt, giao hàng chậm, khách vẫn thích sản phẩm; mỗi chủ đề có 3 dẫn chứng.
3. Nói: "AI chỉ gợi ý để tham khảo. Nhãn hàng có thể làm theo hoặc tự xử lý."
4. Nếu AI lỗi: nói rõ lượt này Bedrock không trả kết quả hợp lệ, rồi mở video dự phòng.

## Phần 4 — Phục hồi và Auto Scaling

1. Người vận hành chạy `python scripts/demo_control.py release --stack <stack-api-demo>`. Khoảng 10 giây sau có đợt tích cực: 65/300, tỷ lệ 22%, không cảnh báo.
2. **Auto Scaling, làm trực tiếp:**
   - Mở EC2 → Auto Scaling Groups, thấy 2 máy.
   - Terminate một máy.
   - Web vẫn chạy bình thường.
   - Khoảng 2 phút sau, Auto Scaling tạo máy mới và Target Group lại có 2 máy `healthy`.
   - Lượt thử 27/11: 0/8 lần gọi lỗi, phục hồi sau 102 giây.
   - Nói: "Load Balancer chỉ gửi yêu cầu đến máy khỏe. Auto Scaling giữ đủ số máy và thêm máy khi CPU trên 50%."
3. **Chỉ nói, không làm:** nhóm từng thấy target tracking tự **thu nhỏ** từ 2 xuống 1 máy khi CPU thấp. Vì vậy cấu hình demo đặt tối thiểu 2 máy.

## Khi gặp sự cố

| Sự cố | Cách xử lý |
|---|---|
| Đăng ký lỗi | Dùng tài khoản demo đã tạo sẵn |
| Email đến chậm | Mở web trực tiếp và cho xem cảnh báo; nói email có thể trễ |
| Đợt dữ liệu chậm | Mỗi đợt chạy theo nhịp EventBridge 1 phút; chờ thêm 1–2 phút hoặc dùng video |
| AI lỗi | Dùng video, nói rõ là bản ghi |

## Sau khi trình bày

1. Chạy `python scripts/demo_control.py stop --stack <stack-api-demo>`.
2. **Xóa stack EC2 ngay**: EC2 + ALB tốn khoảng 2 USD/ngày.
3. Dọn các stack còn lại theo [hướng dẫn hạ tầng](../infrastructure/README.md).

Lệnh `stop` không dừng RDS, NAT hay EC2.
