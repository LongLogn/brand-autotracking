# Hướng dẫn demo: Hệ thống đăng ký môn học

Tài liệu này dành cho nhóm thực hiện, dùng để chuẩn bị video demo và buổi thuyết trình. Yêu cầu chi tiết nằm ở [software-requirements-specification.md](software-requirements-specification.md).

**Trạng thái:** bản nháp, theo [architecture.md](architecture.md). Hệ thống chưa được xây dựng, nên lệnh chạy và kết quả đo sẽ được điền sau. Dịch vụ có thể thay đổi sau khi đo.

## 1. Thông điệp chính

Demo phải cho thấy: **nhóm biết chọn và phối hợp các dịch vụ AWS để giải quyết một bài toán thực tế**, mỗi dịch vụ đều có lý do cụ thể. Giải pháp phải an toàn, chịu được lúc mở phiên, không vượt sĩ số và tiết kiệm chi phí ngày thường.

Load balancing và auto scaling chỉ là một phần của giải pháp. Việc chúng có đủ cho bài toán tranh chỗ hay không chưa được đo; nếu số đo cho kết quả khác dự kiến, nhóm phải trình bày đúng số đo.

### Các dịch vụ AWS cần thể hiện

Dịch vụ nào nằm ngoài đề cương được liệt kê tại [architecture.md](architecture.md); khi demo nên nêu rõ các dịch vụ cộng thêm đó.

| Nhóm | Dịch vụ dự kiến | Vai trò trong hệ thống | Thể hiện ở |
|---|---|---|---|
| Mạng và phân phối | VPC, Route 53, ACM, CloudFront | Tách mạng công khai và riêng tư, HTTPS, cache trang và hàng chờ | Video cấu hình, cảnh 2 |
| Bảo mật | IAM, Security Group, KMS, WAF, Cognito | Phân quyền, mã hóa, chặn truy cập bất thường, đăng nhập | Video cấu hình, cảnh 2, 4 |
| Tính toán | EC2, ALB, Auto Scaling, Lambda | Chạy ứng dụng, co giãn, xử lý nền | Cảnh 1, 2, 4, 5 |
| Lưu trữ | S3 | Trang tĩnh, file nhập, phiếu DOCX | Cảnh 1, 4 |
| Cơ sở dữ liệu | DynamoDB | Toàn bộ dữ liệu của hệ thống, giữ đúng sĩ số | Cảnh 3, 5 |
| Tích hợp | SQS, EventBridge, SES, SNS | Việc nền có thử lại, chạy theo lịch, email xác nhận, cảnh báo | Cảnh 1, 5 |
| Giám sát | CloudWatch | Số đo, dashboard, cảnh báo | Cảnh 2, 5, 6 |
| Chi phí | Budgets, Cost Explorer, Pricing Calculator | Kiểm soát và so sánh chi phí | Cảnh 6 |
| Tự động hóa | CloudFormation | Dựng và xóa hạ tầng | Video cài đặt |

Mỗi dịch vụ trong bài phải trả lời được hai câu: **vì sao dùng** và **nếu không dùng thì sao**. Không thêm dịch vụ chỉ để danh sách dài hơn.

## 2. Hai sản phẩm cần chuẩn bị

| | Video demo | Thuyết trình |
|---|---|---|
| Mục đích | Chứng minh quá trình cài đặt, cấu hình và test (yêu cầu của đề bài) | Kể lại bài toán, giải pháp và kết quả |
| Nội dung | Đầy đủ các phần ở mục 4 và 5 | Slide, số đo, trích đoạn video và cảnh 4 chạy trực tiếp |
| Dữ liệu | Giả lập | Giả lập |

Thời lượng thuyết trình chưa được thông báo, nên cần chỉnh lại khi có thông tin. Hạn nộp báo cáo bản mềm và demo là 5 ngày trước ngày báo cáo.

## 3. Chuẩn bị trước khi quay

**Hạ tầng**
- [ ] Bật cảnh báo AWS Budgets.
- [ ] Dựng toàn bộ hạ tầng bằng IaC để bật và tắt được nhanh.
- [ ] Máy tạo tải chạy riêng, không dùng laptop, và có theo dõi CPU của máy này để loại trừ nghẽn phía tạo tải.
- [ ] Mở sẵn dashboard giám sát với các chỉ số: p95, tỷ lệ lỗi, số máy, số người trong hàng chờ, số lượt đang có.

**Dữ liệu giả lập**
- [ ] Không dùng dữ liệu sinh viên thật.
- [ ] Có 5.000 tài khoản sinh viên, cùng các file lớp học, sinh viên và kết quả học tập.
- [ ] Có một lớp "hot" ít chỗ để demo tranh chỗ, ví dụ 60 chỗ.
- [ ] Có sẵn các sinh viên mẫu cho từng trường hợp bị từ chối: trùng lịch, chưa đạt môn tiên quyết, vượt tín chỉ.
- [ ] Tắt chức năng đăng ký sẵn khi đo tải tranh chỗ.

**Tài khoản demo**
- [ ] Một tài khoản ban quản lý nhà trường, một tài khoản vận hành, một sinh viên mẫu.

## 4. So sánh ba cấu hình

Chạy **cùng một kịch bản tải** trên cả ba cấu hình và ghi số đo, để thấy giá trị của từng nhóm dịch vụ khi được thêm vào.

| Cấu hình | Nội dung | p95 | Tỷ lệ lỗi | Vượt sĩ số | Chi phí |
|---|---|---|---|---|---|
| 1 | Một EC2, DynamoDB, không hàng chờ | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| 2 | Thêm ALB, Auto Scaling theo tải | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| 3 | Thêm hàng chờ, CloudFront, lịch công suất | Chưa đo | Chưa đo | Chưa đo | Chưa đo |

Không đưa con số ước lượng vào bảng này. Lưu kết quả và ảnh dashboard của từng lần chạy.

## 5. Kịch bản demo

Thời lượng dưới đây là đề xuất.

| Cảnh | Hành động | Cần cho thấy | Dịch vụ dự kiến | Thời lượng | Hình thức |
|---|---|---|---|---|---|
| 1 | Ban quản lý nhà trường nhập file lỗi, sửa rồi nhập lại, tạo phiên | File lỗi không được áp dụng; lịch công suất được tạo | Cognito, S3, Lambda, EventBridge | 1 phút | Video |
| 2 | 5.000 sinh viên giả lập vào khi mở phiên | Số máy đã tăng trước giờ mở; hàng chờ hoạt động, đến số thì trang hiện lời mời; chỉ cấp lượt đến mức tối đa | Route 53, CloudFront, S3, WAF, ALB, EC2, Auto Scaling, CloudWatch | 2 phút | Video |
| 3 | Nhiều sinh viên giành chỗ cuối của lớp hot | Đúng 60 người thành công, số còn lại được báo hết chỗ | DynamoDB | 1 phút | Video |
| 4 | Sinh viên mẫu đăng ký, bị từ chối vì trùng lịch, đổi lớp, tải phiếu DOCX | Lý do từ chối rõ ràng; đổi lớp không mất lớp cũ; phiếu có mã tra cứu | Cognito, DynamoDB, Lambda, S3 | 2 phút | Trực tiếp |
| 5 | Ngắt một máy khi đang tải cao, chạy đối soát; rồi làm Lambda xử lý nền lỗi khi hủy lớp | Tỷ lệ lỗi hồi phục; đăng ký đã báo thành công không mất; đối soát bằng 0; tin lỗi vào DLQ, có cảnh báo, gửi lại thành công | ALB, Auto Scaling, DynamoDB, Lambda, SQS, CloudWatch, SNS | 2 phút | Video |
| 6 | Đóng phiên, xem công suất giảm và so sánh chi phí | Số máy giảm; chi phí cả năm so với giữ công suất đỉnh quanh năm | CloudWatch, Budgets, Cost Explorer, Pricing Calculator | 1 phút | Video và slide |

**Lời dẫn gợi ý**
1. "Nếu nhập sai dữ liệu, hệ thống không áp dụng dòng nào. Đồng thời lịch tăng công suất đã được tạo theo giờ mở phiên."
2. "Máy mới cần vài phút mới sẵn sàng, nên hệ thống tăng công suất trước giờ mở thay vì đợi tải tăng."
3. "Đây là câu hỏi quan trọng nhất của bài toán: nhiều người giành một chỗ thì có vượt sĩ số không?"
4. "Đây là những gì một sinh viên thực sự nhìn thấy."
5. "Ngắt một máy ngay lúc tải cao và kiểm tra có mất dữ liệu không. Việc nền bị lỗi cũng không mất, vì còn lưu trong DLQ để gửi lại."
6. "Hệ thống chỉ tốn công suất cao trong thời gian thực sự cần."

## 6. Nội dung video

1. **Giới thiệu:** bài toán và kiến trúc.
2. **Cài đặt:** dựng hạ tầng bằng IaC, có thể tua nhanh phần chờ.
3. **Cấu hình:** đi qua từng nhóm dịch vụ ở mục 1: mạng, bảo mật, tính toán, lưu trữ, cơ sở dữ liệu, tích hợp, giám sát, chi phí. Nói rõ lý do chọn từng dịch vụ.
4. **Test:** so sánh ba cấu hình (mục 4) và kịch bản demo (mục 5).
5. **Kết quả:** bảng số đo và so sánh chi phí.

Khi quay: không để lộ khóa truy cập hay thông tin bí mật, giữ đồng hồ và số đo trong khung hình, và không dựng cắt làm thay đổi kết quả.

## 7. Phương án dự phòng khi thuyết trình

| Sự cố | Cách xử lý |
|---|---|
| Hệ thống không chạy được khi diễn trực tiếp | Chuyển sang đoạn video đã quay của cảnh 4 |
| Mạng yếu | Dùng video đã tải sẵn về máy và mở slide ngoại tuyến |
| Hạ tầng đã tắt | Dựng lại trước giờ thuyết trình theo thời gian đã đo khi diễn tập; dự phòng bằng video |
| Giảng viên hỏi về số đo | Mở kết quả đo và ảnh dashboard đã lưu |

## 8. Sau mỗi buổi

- [ ] Lưu số đo và ảnh dashboard.
- [ ] Xóa tài nguyên bằng IaC, kiểm tra không còn tài nguyên tính phí, đặc biệt là NAT Gateway và ALB.
- [ ] Kiểm tra chi phí trên Cost Explorer.

## 9. Việc còn thiếu

- [ ] Thử lớp hot để chốt cách giữ chỗ.
- [ ] Viết lệnh chạy cụ thể cho từng cảnh.
- [ ] Điền số đo thật vào mục 4.
- [ ] Phân công người trình bày từng cảnh.
- [ ] Hỏi thời lượng thuyết trình và ngày báo cáo.
- [ ] Diễn tập toàn bộ ít nhất một lần.
