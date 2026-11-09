# ĐỀ CƯƠNG CHI TIẾT HỌC PHẦN: ĐIỆN TOÁN ĐÁM MÂY (CLOUD COMPUTING)

## 1. Thông tin chung
- **Tên học phần:** Điện toán đám mây (Cloud Computing)
- **Mã học phần:** UET.CN3134
- **Số tín chỉ:** 3 (30 lý thuyết / 30 thực hành / 90 tự học)
- **Học phần tiên quyết:** UET.CN2042 – Mạng máy tính

## 2. Mục tiêu học phần
- **Về kiến thức:** Trang bị kiến thức cơ bản về các thành phần chính cấu thành nên một hệ thống điện toán đám mây.
- **Về kỹ năng:** Trang bị kỹ năng thiết kế và lập trình cơ bản cho các chương trình ứng dụng chạy trên hệ thống điện toán đám mây.
- **Về mức độ tự chủ và trách nhiệm:** Rèn luyện thái độ chuyên nghiệp khi thực hiện các công việc trong một dự án triển khai hệ thống, mô tả các tài nguyên và chiến lược học tập phù hợp để tự học và nâng cao kiến thức liên tục.

## 3. Học liệu
**Học liệu bắt buộc:**
- [1] Ben Piper, David Clinton, "AWS Certified Cloud Practitioner Study Guide: Foundational (CLF-C02) Exam, Second Edition, 2023"

**Học liệu tham khảo:**
- [1] Lê Nguyễn Tuấn Thành, Phạm Mạnh Linh, "Big Data Analytics and Machine Learning for Industry 4.0: An Overview, 2021"
- [2] Bộ tài liệu bài giảng do giảng viên cung cấp

## 4. Chuẩn đầu ra học phần (CLO)
- **CLO1:** Áp dụng các khái niệm cơ bản về mạng máy tính, thành phần, giao thức để giải thích các nguyên lý hoạt động của Internet và các hệ thống điện toán nền Internet.
- **CLO2:** Vận dụng kiến thức chuyên sâu về định hướng Phát triển ứng dụng Internet và Điện toán Đám mây để đánh giá và lựa chọn các giải pháp công nghệ.
- **CLO3:** Vận dụng các giao thức và dịch vụ được sử dụng trong điện toán đám mây.
- **CLO4:** Triển khai một số hệ thống điện toán đám mây phổ biến như Amazon AWS, OpenStack Cloud.
- **CLO5:** Mô tả các tài nguyên và chiến lược học tập phù hợp để tự học và nâng cao kiến thức về điện toán đám mây một cách liên tục.

---

## 5. Nội dung giảng dạy chi tiết theo từng buổi học

### Buổi 1: Giới thiệu (Introduction)
- **Nội dung:** Tổng quan về học phần, giáo trình, hình thức thi/đánh giá. Hướng dẫn khai thác trang web Tài liệu của AWS.
- **Chuẩn đầu ra (LLO):** Nhận biết cấu trúc học phần; Khai thác trang web Tài liệu của AWS.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 3, trang 34 đến 36).
- **Bài giảng:** Slide Module 0 "Giới thiệu học phần".
- **Hoạt động thực hành:** Tìm tài liệu AWS theo yêu cầu.

### Buổi 2: Tổng quan về Điện toán đám mây (Overview of Cloud Computing)
- **Nội dung:** Khái niệm, đặc trưng, mô hình dịch vụ/triển khai, ưu điểm của Điện toán Đám mây; Khung AWS Cloud Adoption (AWS CAF).
- **Chuẩn đầu ra (LLO):** Nhận biết các khái niệm/đặc trưng; Định nghĩa các loại mô hình; Mô tả ưu điểm; Hiểu cơ bản về AWS CAF.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 1).
- **Bài giảng:** Slide Module 1 "Tổng quan về Điện toán Đám mây".
- **Hoạt động thực hành:** Cài đặt OpenStack với DevStack.

### Buổi 3: Kinh tế học Đám mây và Thanh toán 1 (Cloud Economics and Billing 1)
- **Nội dung:** Cơ sở định giá, Tổng chi phí sở hữu (TCO), Tổ chức AWS.
- **Chuẩn đầu ra (LLO):** Giải thích cơ sở định giá của AWS; Hiểu các khái niệm về TCO; Cách thiết lập cơ cấu tổ chức với AWS Organization.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 2, trang 13 đến 21).
- **Bài giảng:** Slide Module 2 "Kinh tế học Đám mây và Thanh toán" (Phần 1 đến 3).
- **Hoạt động thực hành:** Sử dụng HORIZON để quản lý tài nguyên trên OpenStack.

### Buổi 4: Kinh tế học Đám mây và Thanh toán 2, Cơ sở hạ tầng toàn cầu AWS
- **Nội dung:** Quản lý Thanh toán và Chi phí, Cơ sở hạ tầng Toàn cầu AWS, Tổng quan dịch vụ và danh mục dịch vụ của AWS.
- **Chuẩn đầu ra (LLO):** Dùng AWS Pricing Calculator; Hiểu Bảng điều khiển Thanh toán AWS; Phân biệt Vùng AWS/Vùng khả dụng/Vị trí biên; Nhận biết dịch vụ AWS.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 2, trang 13 đến 24).
- **Bài giảng:** Slide Module 2 (Phần 4-5), Module 3 "Tổng quan về Cơ sở hạ tầng Toàn cầu AWS".
- **Hoạt động thực hành:** Tạo Máy ảo và Cấu hình Mạng.

### Buổi 5: Bảo mật Đám mây AWS 1 (AWS Cloud Security 1)
- **Nội dung:** Mô hình chia sẻ trách nhiệm của AWS, Quản lý Danh tính và Truy cập AWS (IAM).
- **Chuẩn đầu ra (LLO):** Nhận biết mô hình chia sẻ trách nhiệm; Xác định trách nhiệm KH/AWS; Nhận biết IAM; Mô tả các loại thông tin xác thực bảo mật IAM.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 4 tr 56-59; chương 5 tr 65-73).
- **Bài giảng:** Slide Module 4 "Bảo mật Đám mây AWS" (Phần 1-2).
- **Hoạt động thực hành:** Cài đặt OpenStack với các Thành phần (Cấu hình Môi trường).

### Buổi 6: Bảo mật Đám mây AWS 2 (AWS Cloud Security 2)
- **Nội dung:** Bảo mật tài khoản, Bảo mật dữ liệu trên AWS, Đảm bảo tuân thủ.
- **Chuẩn đầu ra (LLO):** Các bước bảo mật tài khoản AWS; Cách bảo mật dữ liệu; Các chương trình tuân thủ AWS.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 5, trang 74 đến 75).
- **Bài giảng:** Slide Module 4 "Bảo mật Đám mây AWS" (Phần 3-6).
- **Hoạt động thực hành:** Cài đặt OpenStack với các thành phần (Keystone).

### Buổi 7: Mạng và Phân phối Nội dung 1 (Networking and Content Delivery 1)
- **Nội dung:** Kiến thức cơ bản về mạng, Amazon VPC.
- **Chuẩn đầu ra (LLO):** Nhận biết kiến thức mạng cơ bản; Mô tả mạng ảo trên đám mây với Amazon VPC.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 10, trang 183 đến 189).
- **Bài giảng:** Slide Module 5 "Mạng và Phân phối Nội dung" (Phần 1-2).
- **Hoạt động thực hành:** Cài đặt OpenStack với các Thành phần (Glance).

### Buổi 8: Mạng và Phân phối Nội dung 2 (Networking and Content Delivery 2)
- **Nội dung:** Mạng và bảo mật VPC, Amazon Route 53, Amazon CloudFront.
- **Chuẩn đầu ra (LLO):** Thiết kế kiến trúc VPC cơ bản; Xác định nhóm bảo mật; Nguyên tắc cơ bản của Route 53; Lợi ích CloudFront.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 10, trang 189 đến 192).
- **Bài giảng:** Slide Module 5 (Phần 3-6).
- **Hoạt động thực hành:** Cài đặt OpenStack với các Thành phần (Nova).

### Buổi 9: Kiểm tra giữa kỳ (Midterm exam)
- **Chuẩn đầu ra (LLO):** Nắm vững kiến thức tuần 1-8; Phân tích tình huống và triển khai hệ thống đám mây nhỏ.

### Buổi 10: Tính toán 1 (Compute 1)
- **Nội dung:** Tổng quan dịch vụ điện toán, Amazon EC2 và tối ưu hóa chi phí, Dịch vụ container.
- **Chuẩn đầu ra (LLO):** Tổng quan dịch vụ điện toán AWS; Lý do dùng Amazon EC2; Các chức năng xây dựng môi trường ảo EC2; Tối ưu hóa chi phí EC2; Chạy ứng dụng container.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 7, trang 119 đến 128).
- **Bài giảng:** Slide Module 6 "Compute" (Phần 1-4).
- **Hoạt động thực hành:** Cài đặt OpenStack với các thành phần (Neutron).

### Buổi 11: Tính toán 2, Lưu trữ 1 (Compute 2, Storage 1)
- **Nội dung:** Giới thiệu AWS Lambda, AWS Elastic Beanstalk, Amazon Elastic Block Store (Amazon EBS).
- **Chuẩn đầu ra (LLO):** Khi nào dùng Lambda/Elastic Beanstalk; Các loại lưu trữ; Chức năng Amazon EBS.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 7, trang 128 đến 129).
- **Bài giảng:** Slide Module 6 (Phần 5-6), Module 7 "Lưu trữ" (Phần 1).
- **Hoạt động thực hành:** Cài đặt OpenStack với các thành phần (Cinder).

### Buổi 12: Lưu trữ 2 (Storage 2)
- **Nội dung:** Amazon S3, Amazon EFS, Amazon S3 Glacier.
- **Chuẩn đầu ra (LLO):** Chức năng S3, EFS, Glacier; Phân biệt giữa EBS, S3, EFS và Glacier.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 8, trang 137 đến 146).
- **Bài giảng:** Slide Module 7 (Phần 2-4).
- **Hoạt động thực hành:** Làm quen với Cấu hình Cơ bản của AWS.

### Buổi 13: Cơ sở dữ liệu 1 (Database 1)
- **Nội dung:** Amazon RDS, Amazon DynamoDB.
- **Chuẩn đầu ra (LLO):** Chức năng RDS và DynamoDB.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 9, trang 159 đến 171).
- **Bài giảng:** Slide Module 8 "Cơ sở dữ liệu" (Phần 1-2).
- **Hoạt động thực hành:** VPC – Máy chủ web (AWS).

### Buổi 14: Cơ sở dữ liệu 2, Tự động mở rộng và giám sát 1
- **Nội dung:** Amazon Redshift, Amazon Aurora, Cân bằng tải đàn hồi (Elastic Load Balancing).
- **Chuẩn đầu ra (LLO):** Giải thích Redshift, Aurora; Phân phối lưu lượng bằng Cân bằng tải đàn hồi.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 9 tr 171-172; chương 11 tr 210-211).
- **Bài giảng:** Slide Module 8 (Phần 3-4), Module 10 (Phần 1).
- **Hoạt động thực hành:** Dịch vụ EC2 instance.

### Buổi 15: Tự động mở rộng và giám sát 2 (Automatic Scaling and Monitoring 2)
- **Nội dung:** Amazon CloudWatch, Amazon EC2 Auto Scaling, Phân công dự án.
- **Chuẩn đầu ra (LLO):** Giám sát tài nguyên với CloudWatch; Amazon EC2 Auto Scaling đáp ứng khối lượng công việc.
- **Đọc trước tài liệu:** Sách bắt buộc [1] (chương 6, trang 100 đến 104).
- **Bài giảng:** Slide Module 10 (Phần 2-3).
- **Hoạt động thực hành:** S3-EBS.
