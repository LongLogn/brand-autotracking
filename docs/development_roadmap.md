# Lộ trình phát triển dự án

## Mục đích

Tài liệu này giúp nhóm hình dung các giai đoạn cần thực hiện từ khi xây dựng giao diện đến khi hoàn thành và trình diễn hệ thống trên AWS. Đây là lộ trình dự kiến, không phải xác nhận các chức năng đã được triển khai. Các giai đoạn có thể thực hiện song song nếu có đủ thành viên.

Tài liệu liên quan: [SRS](software_requirements_specification.md) và [kiến trúc AWS](architecture_aws.md). Khi phạm vi hoặc thiết kế thay đổi, cập nhật các tài liệu tương ứng và điều chỉnh lộ trình.

Hiện trạng và bàn giao từng giai đoạn nằm trong [development-process](development-process/), theo tên `s<N>_<ten-tieng-anh>.md`. Lộ trình quy định kế hoạch và tiêu chí; tệp giai đoạn ghi kết quả đã có bằng chứng, việc còn lại và bước tiếp theo, kể cả sau khi hoàn thành.

## Hướng đi chính

Sau khi có giao diện ban đầu, nhóm nên ưu tiên **kiểm chứng Firecrawl và làm một luồng chạy thật từ đầu đến cuối**: khách hàng tạo nhãn hàng → hệ thống tìm dữ liệu → lưu vào cơ sở dữ liệu → giao diện hiển thị kết quả. Sau đó tiếp tục với cảnh báo, phân tích AI và hoàn thiện triển khai AWS.

Thứ tự phụ thuộc chính: chuẩn bị quyền và ngân sách → kiểm chứng nguồn Firecrawl → thống nhất phạm vi và hợp đồng API → hoàn thành một luồng dọc với dữ liệu thật → bổ sung lịch tự động, cảnh báo và AI → nghiệm thu trên AWS. Frontend, kiểm chứng nguồn và chuẩn bị backend có thể làm song song; không cần đợi hoàn thiện toàn bộ giao diện mới thử nguồn.

## Giai đoạn 0. Chuẩn bị làm việc và môi trường

**Việc cần làm**

- Thống nhất thời hạn, phạm vi trình diễn, người phụ trách và cách chia sẻ mã nguồn; mỗi đầu việc nên có người chịu trách nhiệm chính, người kiểm tra và bằng chứng hoàn thành.
- Kiểm tra tài khoản AWS và Firecrawl, quyền truy cập, khu vực AWS, hạn mức, quyền sử dụng mô hình Bedrock và khả năng ứng dụng trên AWS kết nối Firecrawl. Các lựa chọn và quyền cần được xác minh trong tài khoản thực tế.
- Lập dự toán chi phí và ngân sách; thiết lập AWS Budgets và giới hạn sử dụng phù hợp, lưu ý cảnh báo ngân sách không tự động ngăn mọi chi phí.
- Thiết lập kho mã, nhánh, quy trình review, hướng dẫn chạy local, cấu hình môi trường và quản lý bí mật; không đưa khóa hoặc mật khẩu vào Git.
- Thử triển khai một thành phần nhỏ lên AWS bằng hạ tầng dưới dạng mã (SAM hoặc CloudFormation) và theo dõi log để phát hiện vấn đề quyền, mạng và chi phí sớm.

**Kết quả cần đạt:** Nhóm có thể truy cập các dịch vụ cần thử, có ngân sách và cách theo dõi chi phí, dự án chạy được ở môi trường phát triển và có một kiểm chứng triển khai AWS ban đầu. Nếu chưa được cấp quyền dịch vụ, ghi rõ việc bị chặn và phương án xử lý, không đánh dấu bước đó đã xong.

## Giai đoạn 1. Chốt phạm vi và hoàn thiện frontend

**Việc cần làm**

- Kiểm tra các màn hình cần thiết: đăng nhập, danh sách nhãn hàng, cấu hình theo dõi, lịch sử tracking, nội dung tổng hợp, cảnh báo và phân tích AI.
- Ghi rõ màn hình nào dùng dữ liệu mẫu và chức năng nào chưa được kết nối.
- Chốt phạm vi phiên bản đầu: ít nhất một nguồn có thể thu thập dữ liệu thật, cảnh báo trong ứng dụng và chức năng phân tích AI.
- Thống nhất dữ liệu giữa frontend và backend, chẳng hạn thông tin của nhãn hàng và kết quả một phiên tracking.

**Kết quả cần đạt:** Frontend chạy được, các luồng sử dụng rõ ràng và có danh sách chức năng cần backend cung cấp.

## Giai đoạn 2. Kiểm chứng Firecrawl

Thực hiện sớm, có thể song song với frontend. Đây là bước kiểm tra tính khả thi cốt lõi của dự án.

**Việc cần làm**

- Dùng Firecrawl Search tìm từ khóa trên các nguồn dự kiến như Reddit, Facebook, TikTok và Threads.
- Dùng Firecrawl Scrape thử đọc một số URL thu được.
- Ghi nhận nguồn nào lấy được nội dung, liên kết, thời gian, lượt react, số bình luận và nội dung bình luận.
- Xem xét chi phí, quyền truy cập và điều kiện sử dụng của từng nguồn.
- Chọn ít nhất một nguồn khả thi để làm trước. Nếu không lấy được bình luận hoặc chỉ số cần thiết, ghi rõ hạn chế và thống nhất điều chỉnh phạm vi.

**Kết quả cần đạt:** Chương trình thử nghiệm tìm và đọc được dữ liệu thật qua Firecrawl; có kết quả ghi nhận khả năng và giới hạn của từng nguồn. Dữ liệu mẫu dùng để kiểm thử phải được ghi nhãn rõ.

**Điều kiện quyết định:** Với mỗi nguồn, lưu ngày thử, từ khóa, URL mẫu được phép truy cập, kết quả Search → Scrape, các trường thu được, lỗi và chi phí ước tính. Chỉ cam kết chức năng liên quan đến bình luận/react khi đã kiểm chứng nguồn cung cấp. Nếu không lấy được, thử nguồn khác được phép; nếu vẫn không đạt, báo nhóm/giảng viên, thống nhất thay đổi phạm vi và cập nhật SRS trước khi xem yêu cầu đó là hoàn thành. Fixture không chứng minh được khả năng thu thập dữ liệu thật.

## Giai đoạn 3. Thiết kế backend và cơ sở dữ liệu

**Việc cần làm**

- Thiết kế dữ liệu cho tài khoản, nhãn hàng, từ khóa, cấu hình, phiên tracking, bài viết, bình luận, cảnh báo và kết quả AI.
- Xác định API frontend cần, ví dụ:

  - `POST /brands`: tạo nhãn hàng.
  - `GET /brands`: xem danh sách nhãn hàng.
  - `PUT /brands/{id}/tracking`: cập nhật cấu hình theo dõi.
  - `GET /brands/{id}/runs`: xem các phiên tracking.
  - `GET /brands/{id}/mentions`: xem nội dung đã thu thập.

- Thống nhất dữ liệu trả về, phân trang, lỗi và cách phân biệt không có dữ liệu với không lấy được dữ liệu. Các đường dẫn API trên chỉ là ví dụ để nhóm hoàn thiện thiết kế.
- Thiết lập backend FastAPI và PostgreSQL chạy được ở môi trường phát triển.

**Kết quả cần đạt:** Có thiết kế database, API cơ bản và tài liệu API để frontend kết nối.

Hợp đồng API cần ghi kiểu dữ liệu, ví dụ request/response, xác thực, lỗi, trạng thái job và trường nullable; có migration để tạo và cập nhật schema. Các thành viên frontend và backend cùng kiểm tra hợp đồng trước khi tích hợp.

## Giai đoạn 4. Tài khoản và quản lý nhãn hàng

**Việc cần làm**

- Tích hợp Amazon Cognito cho đăng ký và đăng nhập.
- Kết nối frontend với backend sau khi đăng nhập.
- Xây dựng chức năng tạo, sửa, xem, xóa hoặc tạm dừng nhãn hàng theo chính sách được nhóm thống nhất.
- Lưu từ khóa, nền tảng, tần suất và giới hạn bài viết cho từng nhãn hàng.
- Kiểm tra tài khoản này không thể xem hoặc thay đổi dữ liệu của tài khoản khác.

**Kết quả cần đạt:** Người dùng có thể đăng nhập, tạo nhãn hàng và lưu cấu hình vào database.

## Giai đoạn 5. Tracking và kết nối dữ liệu thật

**Việc cần làm**

- Tích hợp chương trình Firecrawl thử nghiệm vào backend.
- Tìm kiếm theo từng từ khóa và nền tảng đã cấu hình; lưu dữ liệu khả dụng vào PostgreSQL.
- Lưu lịch sử phiên, thời gian, trạng thái, kết quả và lỗi; xử lý bài viết trùng theo thiết kế.
- Kết nối frontend để xem dữ liệu theo phiên và xem tổng hợp.
- Sau khi chạy thủ công thành công, bổ sung lịch tự động bằng EventBridge Scheduler và các tác vụ nền bằng Lambda, SQS, Step Functions theo kiến trúc đề xuất.

**Kết quả cần đạt:** Hoàn thành luồng cấu hình nhãn hàng → tracking → lưu dữ liệu → xem kết quả trên giao diện.

**Kiểm tra trước khi chuyển tiếp:** Chạy lại cùng dữ liệu không làm bài viết bị đếm trùng; lưu snapshot chỉ số theo phiên; phân biệt lượt thành công rỗng, thành công một phần và thất bại. Kiểm tra lịch tự động thực sự kích hoạt phiên và việc tạm dừng ngăn phiên mới. Chạy thủ công là bước trung gian, chưa đủ để nghiệm thu tracking theo lịch.

## Giai đoạn 6. Phân tích cảm xúc và cảnh báo

**Việc cần làm**

- Thử mô hình qua Amazon Bedrock để phân loại bài viết và bình luận thành tích cực, tiêu cực, trung lập hoặc không xác định.
- Cho phép cấu hình cảnh báo theo nhãn hàng và tính sự thay đổi nội dung tiêu cực giữa các khoảng thời gian có thể so sánh.
- Lưu và hiển thị cảnh báo trong ứng dụng; xử lý dữ liệu thiếu và hạn chế cảnh báo trùng theo SRS.
- Đánh giá thử bằng tập bình luận tiếng Việt do nhóm gán nhãn. Kết quả là ước lượng, không mặc định chính xác tuyệt đối.

**Kết quả cần đạt:** Với dữ liệu thử nghiệm vượt ngưỡng, người dùng thấy cảnh báo kèm lý do và số liệu.

**Kiểm tra trước khi chuyển tiếp:** Với ngưỡng tăng 50%, thử 10→15 tạo cảnh báo, 10→14 không tạo; thử 0→15 theo quy tắc ngưỡng tuyệt đối hoặc không đủ cơ sở. Kiểm tra hai cửa sổ khác phạm vi, thiếu phiên hoặc có nội dung chưa phân loại không tạo kết luận tăng trưởng sai; đánh giá lại không tạo cảnh báo lặp.

## Giai đoạn 7. AI đề xuất hướng phát triển

**Việc cần làm**

- Cho người dùng chọn nhãn hàng và khoảng thời gian phân tích.
- Lấy dữ liệu thuộc đúng tài khoản và gửi phần cần thiết đến Amazon Bedrock.
- Yêu cầu AI tổng hợp vấn đề, nhu cầu khách hàng và đề xuất hành động; gắn dẫn chứng từ nội dung thu thập.
- Hiển thị phạm vi dữ liệu, dẫn chứng và các giới hạn; thông báo rõ khi thiếu dữ liệu hoặc dịch vụ AI lỗi.

**Kết quả cần đạt:** Người dùng nhận được phân tích có căn cứ để tham khảo, ví dụ nhận diện góp ý về món cay kèm các nội dung liên quan.

**Kiểm tra trước khi chuyển tiếp:** Xác minh ID dẫn chứng thuộc đúng tập dữ liệu và tài khoản; kiểm tra dữ liệu rỗng, timeout, dịch vụ lỗi và nội dung nguồn chứa chỉ dẫn độc hại. Không coi dữ liệu nguồn là lệnh điều khiển AI.

## Giai đoạn 8. Triển khai AWS, kiểm thử và bảo vệ

Nên triển khai thử một phần nhỏ trên AWS từ giai đoạn backend để phát hiện sớm khó khăn; giai đoạn này hoàn thiện toàn hệ thống.

**Việc cần làm**

- Triển khai frontend, backend và cơ sở dữ liệu theo kiến trúc AWS; cấu hình các dịch vụ tracking, Bedrock, quyền IAM, quản lý bí mật và giám sát.
- Kiểm thử toàn bộ luồng với ít nhất hai tài khoản; kiểm tra dữ liệu trùng, lỗi thu thập, dữ liệu thiếu, cảnh báo và lỗi AI.
- Kiểm tra sao lưu và khôi phục; theo dõi chi phí AWS, Bedrock và Firecrawl theo ngân sách nhóm.
- Chuẩn bị sơ đồ kiến trúc, báo cáo, kịch bản hoặc video demo, cùng dữ liệu thử nghiệm. Phân biệt rõ dữ liệu thật và dữ liệu mẫu.

**Kết quả cần đạt:** Một bản demo chạy trên AWS và kịch bản chứng minh các chức năng chính hoạt động.

**Kiểm tra trước khi nghiệm thu:** Kiểm tra truy cập chéo hai tài khoản, sự kiện outbox/SQS được gửi lặp, log và cảnh báo vận hành, khôi phục dữ liệu từ bản sao lưu, cùng chi phí thực tế của kịch bản demo. Lưu kết quả thử và những giới hạn còn tồn tại; đối chiếu trực tiếp các tiêu chí nghiệm thu của SRS.

## Phối hợp và kiểm tra xuyên suốt

Nhóm có thể chia theo bốn luồng: **frontend và trải nghiệm**, **backend và dữ liệu**, **Firecrawl và xử lý nền**, **AWS, AI và kiểm thử**. Một người có thể đảm nhiệm nhiều luồng; nhóm tự điền tên và thời hạn theo nguồn lực thực tế, không coi đây là phân công đã chốt. Chỉ định một người điều phối tích hợp để xử lý phụ thuộc giữa các luồng.

- Thống nhất hợp đồng API trước khi frontend và backend tích hợp; review thay đổi và chạy thử tích hợp định kỳ.
- Với mỗi mốc, ghi người phụ trách, trạng thái, ngày mục tiêu, kết quả thử và liên kết mã/log hoặc tài liệu minh chứng. Tài liệu này là kế hoạch, không phải báo cáo tiến độ hiện tại.
- Kiểm thử, review bảo mật, kiểm tra bí mật và chi phí sau từng thay đổi quan trọng; không dồn toàn bộ đến ngày demo.
- Ưu tiên các chức năng MVP trong SRS. Tích hợp thêm nền tảng, email/SNS, Knowledge Bases hoặc AppConfig chỉ thực hiện sau khi luồng cốt lõi ổn định và còn thời gian/ngân sách.
- Nếu quyết định đã thống nhất khác với SRS hoặc kiến trúc, ghi nhận và cập nhật tài liệu nguồn liên quan; không tự coi đề xuất trong roadmap là yêu cầu đã được phê duyệt.

## Các việc nên bắt đầu ngay

1. Tiếp tục frontend và ghi rõ màn hình dùng dữ liệu mẫu, chức năng chưa kết nối và API cần dùng.
2. Phân công một thành viên kiểm chứng Firecrawl, ưu tiên nguồn có thể lấy cả bài viết và bình luận.
3. Một thành viên khác thiết kế database và API dựa trên SRS và các màn hình đã có.
4. Nối một luồng nhỏ chạy thật: đăng nhập → tạo nhãn hàng → chạy tracking → xem một bài viết thu thập được.

## Duy trì tài liệu

Khi nhóm hoàn thành hoặc thay đổi một giai đoạn, cập nhật tiến độ thực tế và bằng chứng liên quan nếu cần. Các quyết định quan trọng cần được cập nhật vào SRS hoặc kiến trúc trước; không coi một mục trong lộ trình là đã hoàn thành chỉ vì đã được liệt kê.
