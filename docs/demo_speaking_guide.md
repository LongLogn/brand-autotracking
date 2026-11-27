# Hướng dẫn thuyết trình demo

**Cập nhật:** 26/11/2026. Kịch bản đã thử với dữ liệu giả trên AWS; môi trường thử được dọn sau kiểm thử, cần dựng lại và diễn tập trước buổi bảo vệ. Xem [kế hoạch demo](demo_presentation.md) và [S8](development-process/s8_aws_delivery.md) để biết bằng chứng và giới hạn.

## Trước khi vào phòng

- Người vận hành kiểm tra đường dẫn HTTPS, tài khoản AWS/SSO, giới hạn chi phí và CloudFront, API, database, Cognito demo; chuẩn bị email `@example.invalid` và mật khẩu thử an toàn. Email được xác nhận giả lập, không có mã gửi thật.
- Mở sẵn tab giao diện, sơ đồ, CloudFormation, EventBridge, SQS, Lambda và CloudWatch; xác định đúng stack demo. Chuẩn bị video/ảnh có ngày và nhãn giả lập để dự phòng. Không đưa thông tin đăng nhập lên slide.
- Bản dự phòng có sẵn: [video luồng chính](development-process/evidence/demo-core-20261126.mp4), ghi ngày 26/11, không âm thanh, đã cắt thời gian chờ và gắn nhãn dữ liệu giả. Video không trình diễn AI hoặc AWS Console; nói rõ đây là bản ghi, không phải lượt chạy trực tiếp.
- Nếu AI lỗi, dùng [ảnh kết quả AI đã lưu với dữ liệu giả](development-process/evidence/demo-ai-20261126.png), chụp ngày 26/11 từ lượt thử qua CloudFront. Ảnh không có nhãn giả trong chính giao diện, vì vậy luôn trình bày kèm dòng giải thích này; kết quả chỉ tham khảo.
- Chạy thử trọn vẹn trước giờ trình bày. Lệnh khởi động sau khi tạo thương hiệu có hai bước cập nhật CloudFormation và có thể mất vài phút; phân người giải thích kiến trúc hoặc trình bày dịch vụ trong lúc chờ. Nếu thời gian không cho phép, dùng thương hiệu đã chuẩn bị và nói rõ.

## 1. Giải thích kiến trúc

“Đây là hệ thống theo dõi thương hiệu trên AWS. Người dùng truy cập giao diện qua CloudFront; Cognito quản lý đăng nhập. API nhận cấu hình và lưu vào RDS. EventBridge, SQS và Lambda điều phối các phiên xử lý. Bedrock hỗ trợ phân tích; CloudWatch giúp theo dõi hoạt động.”

Chỉ trên sơ đồ đường đi từ người dùng đến dữ liệu và kết quả. Nêu rõ Firecrawl là dịch vụ ngoài AWS, còn nguồn giả lập phục vụ tình huống minh họa.

## 2. Dùng hệ thống và xem AWS

1. **Đăng ký và đăng nhập:** tạo tài khoản, giải thích bước xác nhận. Nếu tự xác nhận email giả, nói rõ đây là giả lập.
2. **Theo dõi thương hiệu:** tạo “Mây Tea”, nhập từ khóa, lịch và ngưỡng cảnh báo; lưu cấu hình.
3. **Dữ liệu phát sinh:** người vận hành lấy mã nhãn hàng trên giao diện demo và chạy lệnh `demo_control.py start` theo [hướng dẫn hạ tầng](../infrastructure/README.md); cập nhật AWS có thể mất vài phút, cần diễn tập và chuẩn bị phần trình bày trong lúc chờ. Quan sát các đợt bài và bình luận mới. Nói: “Đây là dữ liệu giả để minh họa; không phải nội dung thu thập trực tiếp.” Đã thử start/stop trên AWS; toàn bộ câu chuyện đang được diễn tập.
4. **Cảnh báo và AI:** dùng lịch sử giả đã chuẩn bị, chọn quy tắc bình luận tiêu cực: mỗi cửa sổ một ngày, ngưỡng tăng 50%, tối thiểu một; lưu và chọn “Đánh giá cửa sổ đã hoàn tất”. Nêu 10→15 và đánh giá lại không tạo thêm cảnh báo. Các nhãn lịch sử được gán sẵn, không phải kết quả Bedrock. Để phân tích phần lịch sử, chọn khoảng từ 07:00 giờ Việt Nam ba ngày trước mốc 07:00 gần nhất đã qua đến chính mốc đó; kiểm tra lại ngày theo dữ liệu demo. Xem đề xuất và dẫn chứng; giải thích AI đưa ra gợi ý tham khảo và có thể lỗi. Đã thử thành công qua CloudFront, nhưng cũng có lượt lỗi; dùng ảnh dự phòng nếu cần.
5. **AWS Console:** mở CloudFormation tìm đúng stack. Chỉ vào EventBridge rule, SQS, Lambda worker và CloudWatch; đối chiếu thời gian và ID phiên `demo_queued`/`tracking_run` với lịch sử trên ứng dụng. SQS có thể đã trống vì worker xử lý nhanh; log và trạng thái phiên cho thấy kết quả. Xem RDS và giải thích dữ liệu được lưu riêng tư.

Nếu phần nào chưa triển khai hoặc chạy lỗi, nói rõ và dùng kết quả đã lưu/video có nhãn thay vì giả vờ đang chạy trực tiếp. Tránh để lộ mật khẩu, token và dữ liệu cá nhân. Kết thúc bằng việc nêu giới hạn, dừng nguồn giả và kiểm tra tài nguyên theo [kế hoạch demo](demo_presentation.md).

## Sau khi trình bày

Người vận hành đợi các phiên kết thúc, chạy lệnh `demo_control.py stop`, kiểm tra lịch/mapping và hàng đợi. Theo [hướng dẫn hạ tầng](../infrastructure/README.md), kiểm kê và dừng hoặc dọn tài nguyên đúng môi trường, giữ bản sao theo quyết định của nhóm; xem lại chi phí sau khi billing cập nhật. Lệnh stop không dừng RDS hoặc NAT.
