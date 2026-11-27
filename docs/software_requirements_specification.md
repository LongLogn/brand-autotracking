# ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS)

**Bổ sung 27/11/2026:** Chủ nhãn hàng có thể hủy phiên tracking đang chờ; phiên đã bắt đầu không được hủy bằng thao tác này. Hệ thống hiển thị trạng thái đã hủy và không thực hiện thu thập cho phiên đó.

**Bổ sung 27/11/2026:** Người dùng quản lý tối đa 10 địa chỉ email nhận cảnh báo cho từng nhãn hàng thuộc quyền sở hữu; danh sách rỗng tắt email. Không mặc định lấy email đăng nhập. Bản demo hiện chỉ gửi khi cảnh báo theo lần thu thập; email cho dữ liệu thật cần hoàn thiện và nghiệm thu riêng.

## 1. Giới thiệu

Hệ thống theo dõi nhãn hàng tự động giúp khách hàng thu thập nội dung liên quan đến nhãn hàng trên mạng xã hội, nhận cảnh báo sớm về nội dung tiêu cực và sử dụng AI để phân tích, đề xuất hướng phát triển.

Khách hàng tạo tài khoản và quản lý danh sách nhãn hàng. Với mỗi nhãn hàng, khách hàng cấu hình các cụm từ khóa, nền tảng, tần suất theo dõi và số bài viết nổi bật cần thu thập trong mỗi lượt. Hệ thống thực hiện các phiên tracking, lưu dữ liệu và cung cấp chức năng xem nội dung, cảnh báo và phân tích bằng AI.

Các nền tảng dự kiến gồm TikTok, Facebook, Threads và Reddit. Danh sách tích hợp thực tế phụ thuộc vào khả năng truy cập, quyền và chính sách của từng nền tảng.

Để trình diễn, hệ thống có thể sử dụng nguồn dữ liệu giả lập được nhận diện rõ, chạy trong môi trường demo riêng và có giới hạn. Dữ liệu này không chứng minh khả năng thu thập từ mạng xã hội; các yêu cầu thu thập thật và giới hạn nguồn vẫn áp dụng. Kịch bản tại [thư mục demo](../demo/architecture.md).

### Thuật ngữ

- **Nhãn hàng:** Đối tượng khách hàng muốn theo dõi, ví dụ một thương hiệu nhà hàng.
- **Từ khóa:** Từ hoặc cụm từ tìm nội dung liên quan, bao gồm các biến thể có dấu, không dấu hoặc tên viết tắt.
- **Phiên tracking:** Một lần hệ thống tìm kiếm theo cấu hình của nhãn hàng trên các nền tảng đã chọn, thu thập dữ liệu khả dụng và lưu kết quả.
- **Bài viết nổi bật:** Bài viết được lựa chọn từ kết quả tìm kiếm theo cách xếp hạng được hệ thống hoặc nền tảng hỗ trợ.
- **Bình luận nổi bật:** Bình luận được lựa chọn dựa trên số lượt tương tác cảm xúc (react), nếu nguồn cung cấp dữ liệu.
- **Đề cập:** Bài viết hoặc bình luận liên quan đến nhãn hàng trong dữ liệu được thu thập.

## 2. Người dùng

- **Khách hàng:** Tạo tài khoản, quản lý nhãn hàng, cấu hình tracking, xem dữ liệu, thiết lập và nhận cảnh báo, yêu cầu AI phân tích.
- **Quản trị viên:** Theo dõi hoạt động hệ thống và xử lý vấn đề vận hành. Chức năng cụ thể sẽ được xác định sau.
- **Hệ thống bên ngoài:** Nền tảng mạng xã hội cung cấp dữ liệu và dịch vụ AI hỗ trợ phân tích.

## 3. Quy trình nghiệp vụ

1. Khách hàng đăng ký và đăng nhập.
2. Khách hàng tạo một hoặc nhiều nhãn hàng.
3. Với mỗi nhãn hàng, khách hàng khai báo từ khóa, chọn nền tảng, đặt tần suất tracking và số bài viết cần thu thập.
4. Đến lịch, hệ thống tìm kiếm, chọn bài viết nổi bật, thu thập thông tin bài viết và bình luận nổi bật có thể truy cập, rồi lưu kết quả thành một phiên tracking.
5. Khách hàng xem kết quả của từng phiên hoặc nội dung tổng hợp qua nhiều phiên.
6. Hệ thống theo dõi xu hướng nội dung tiêu cực và gửi cảnh báo khi điều kiện được đáp ứng.
7. Khách hàng yêu cầu AI phân tích dữ liệu và đề xuất hướng phát triển.

## 4. Yêu cầu chức năng

### 4.1. Tài khoản và truy cập

- **FR-01:** Khách hàng có thể đăng ký tài khoản, đăng nhập và đăng xuất.
- **FR-02:** Khách hàng chỉ được xem và thay đổi nhãn hàng, cấu hình và dữ liệu thuộc tài khoản của mình, trừ khi được cấp quyền theo thiết kế sau này.

### 4.2. Quản lý nhãn hàng và cấu hình tracking

- **FR-03:** Khách hàng có thể tạo, xem, cập nhật và xóa nhãn hàng trong danh sách của tài khoản.
- **FR-04:** Với mỗi nhãn hàng, khách hàng có thể thêm, sửa và xóa nhiều cụm từ khóa, ví dụ: “gà rán ABC”, “ga ran abc”, “abc”.
- **FR-05:** Khách hàng có thể chọn một hoặc nhiều nền tảng được hệ thống hỗ trợ cho từng nhãn hàng.
- **FR-06:** Khách hàng có thể cài đặt tần suất tracking cho từng nhãn hàng, ví dụ một lần mỗi ngày.
- **FR-07:** Khách hàng có thể đặt số lượng bài viết nổi bật cần thu thập trong một lượt truy cập, ví dụ 10 bài. Phạm vi áp dụng dự kiến được mô tả tại mục 10.
- **FR-08:** Khách hàng có thể bật hoặc tạm dừng tracking cho từng nhãn hàng. Cấu hình đang tạm dừng không chạy theo lịch cho đến khi được bật lại.
- **FR-09:** Hệ thống kiểm tra thông tin bắt buộc và thông báo khi cấu hình không hợp lệ.

### 4.3. Thu thập và lưu dữ liệu

- **FR-10:** Theo lịch đã cấu hình, hệ thống thực hiện phiên tracking bằng cách tìm kiếm từ khóa của nhãn hàng trên những nền tảng đã chọn và được hỗ trợ.
- **FR-11:** Trong mỗi lượt, hệ thống lựa chọn các bài viết nổi bật trong kết quả tìm kiếm, tối đa theo giới hạn cấu hình và khả năng cung cấp dữ liệu của nguồn.
- **FR-12:** Với mỗi bài viết, hệ thống lưu nội dung khả dụng, nền tảng, liên kết, thời gian đăng, số lượt react và số bình luận nếu nguồn cung cấp.
- **FR-13:** Với mỗi bài viết, hệ thống thu thập và lưu các bình luận nổi bật dựa trên số lượt react, trong phạm vi nguồn cho phép. Mỗi bình luận lưu nội dung, thời gian và số lượt react nếu khả dụng.
- **FR-14:** Hệ thống lưu thời điểm, trạng thái và kết quả của mỗi phiên tracking vào cơ sở dữ liệu, liên kết với nhãn hàng tương ứng.
- **FR-15:** Hệ thống hạn chế lưu trùng bài viết và bình luận có cùng định danh từ cùng nguồn. Một nội dung có thể xuất hiện trong nhiều phiên; hệ thống cần thể hiện được các phiên đã thu thập nội dung và chỉ số tương tác tại thời điểm thu thập nếu có.
- **FR-16:** Nếu một nền tảng hoặc tác vụ gặp lỗi, hệ thống ghi nhận trạng thái và thông báo phù hợp; dữ liệu đã thu thập thành công vẫn được lưu.

### 4.4. Xem nội dung theo dõi

- **FR-17:** Khách hàng có thể xem lịch sử các phiên tracking của từng nhãn hàng, bao gồm thời gian và trạng thái.
- **FR-18:** Khách hàng có thể mở một phiên để xem danh sách bài viết và bình luận nổi bật đã thu thập.
- **FR-19:** Khách hàng có thể xem nội dung tổng hợp qua nhiều phiên của một nhãn hàng.
- **FR-20:** Màn hình nội dung hiển thị thông tin khả dụng của bài viết, gồm liên kết, thời gian đăng, số lượt react, số bình luận và các bình luận nổi bật kèm số lượt react.
- **FR-21:** Khách hàng có thể lọc nội dung theo khoảng thời gian và nền tảng. Trường không được nguồn cung cấp phải được thể hiện là không khả dụng.

### 4.5. Cảnh báo nội dung tiêu cực

- **FR-22:** Hệ thống phân tích cảm xúc của bài viết và bình luận để nhận diện nội dung tiêu cực; nội dung không phân tích được phải được đánh dấu riêng.
- **FR-23:** Khách hàng có thể thiết lập, cập nhật và tắt quy tắc cảnh báo cho từng nhãn hàng. Quy tắc xác định chỉ số, ngưỡng và khoảng thời gian đánh giá; phương thức so sánh và các chỉ số hỗ trợ sẽ được xác định khi thiết kế.
- **FR-24:** Hệ thống theo dõi sự gia tăng của số bài viết và bình luận tiêu cực theo thời gian và tạo cảnh báo khi điều kiện của quy tắc được đáp ứng.
- **FR-25:** Cảnh báo cho biết nhãn hàng, thời gian, lý do, chỉ số quan sát và ngưỡng liên quan; khách hàng có thể xem lịch sử cảnh báo trong hệ thống.
- **FR-26:** Hệ thống có cơ chế hạn chế cảnh báo lặp lại cho cùng một tình huống. Kênh gửi ngoài hệ thống và quy tắc chống lặp cụ thể sẽ được xác định sau; riêng kịch bản demo đã chốt email qua SNS đến hộp thư cố định (mục 10.3).

### 4.6. Phân tích và đề xuất bằng AI

- **FR-27:** Khách hàng có thể yêu cầu AI phân tích dữ liệu đã thu thập của một nhãn hàng trong khoảng thời gian được chọn.
- **FR-28:** AI tổng hợp các nhận xét, nhu cầu hoặc vấn đề nổi bật và đề xuất hướng phát triển để khách hàng tham khảo. Ví dụ: phát hiện nhiều góp ý về món cay và đề xuất doanh nghiệp cân nhắc bổ sung món phù hợp.
- **FR-29:** Kết quả phân tích cho biết nhãn hàng, khoảng thời gian và phạm vi dữ liệu sử dụng; đề xuất được trình bày là gợi ý hỗ trợ quyết định.
- **FR-30:** Nếu không đủ dữ liệu hoặc dịch vụ AI không khả dụng, hệ thống thông báo và không trình bày kết quả chưa có căn cứ như sự thật.

## 5. Yêu cầu dữ liệu

Hệ thống cần quản lý tối thiểu:

- Tài khoản khách hàng và thông tin xác thực.
- Nhãn hàng và cấu hình theo dõi: từ khóa, nền tảng, tần suất, giới hạn bài viết và trạng thái.
- Phiên tracking: nhãn hàng, thời gian, trạng thái, nguồn thực hiện và kết quả hoặc lỗi.
- Bài viết, bình luận, liên kết nguồn, thời gian đăng và các chỉ số tương tác khả dụng; mối liên hệ giữa nội dung và các phiên thu thập.
- Kết quả phân tích cảm xúc, quy tắc cảnh báo, lịch sử cảnh báo và kết quả phân tích AI.

Thời hạn lưu, quy trình xóa và phạm vi dữ liệu cá nhân được lưu cần được xác định trước khi triển khai thực tế.

## 6. Yêu cầu phi chức năng

- **NFR-01 — Cloud:** Hệ thống được triển khai và trình diễn hoạt động trên hạ tầng public cloud hoặc private cloud; nhà cung cấp và kiến trúc chưa được chốt.
- **NFR-02 — Bảo mật:** Bảo vệ tài khoản, dữ liệu và thông tin xác thực dịch vụ; không đưa mật khẩu, khóa API hoặc token vào mã nguồn hay nhật ký. Dữ liệu truyền qua mạng phải được mã hóa.
- **NFR-03 — Quyền riêng tư và nguồn dữ liệu:** Chỉ thu thập và xử lý dữ liệu được phép truy cập, phù hợp với điều kiện của nguồn; chỉ lưu dữ liệu cần thiết.
- **NFR-04 — Độ tin cậy:** Ghi nhận lỗi và trạng thái phiên tracking; hỗ trợ xử lý hoặc thử lại tác vụ thất bại phù hợp với giới hạn của nguồn.
- **NFR-05 — Khả năng mở rộng:** Có thể bổ sung nền tảng hoặc thay đổi dịch vụ AI mà hạn chế ảnh hưởng đến các chức năng khác.
- **NFR-06 — Dễ sử dụng:** Giao diện thể hiện rõ trạng thái theo dõi, phiên thành công hoặc thất bại, dữ liệu rỗng và dữ liệu không khả dụng.
- **NFR-07 — Hiệu năng và chi phí:** Hệ thống đáp ứng quy mô bài tập và ngân sách nhóm; số người dùng, khối lượng dữ liệu và mục tiêu thời gian phản hồi cần được thống nhất.
- **NFR-08 — Chất lượng phân tích:** Kết quả cảm xúc và đề xuất AI là ước lượng, phụ thuộc dữ liệu và mô hình; hệ thống thể hiện phạm vi dữ liệu để khách hàng tự đánh giá.

## 7. Giới hạn và phụ thuộc

- Khả năng tìm kiếm, truy cập bài viết, bình luận và chỉ số tương tác phụ thuộc vào phương thức truy cập hợp lệ, quyền và chính sách của từng nền tảng.
- Không mặc định hệ thống có thể thu thập đầy đủ mọi nội dung hoặc chỉ số trên các nền tảng được nêu.
- Việc xếp hạng bài viết nổi bật, giới hạn số bình luận và cách xử lý kết quả trùng giữa các từ khóa phụ thuộc vào nguồn và quyết định thiết kế.
- Dịch vụ AI, nhà cung cấp cloud, công nghệ triển khai và các kênh cảnh báo ngoài ứng dụng chưa được lựa chọn.

## 8. Tiêu chí nghiệm thu dự kiến

1. Khách hàng đăng ký, đăng nhập và tạo được nhiều nhãn hàng; dữ liệu của các tài khoản được tách biệt.
2. Với một nhãn hàng, khách hàng cấu hình được nhiều từ khóa, ít nhất một nền tảng đã tích hợp, tần suất và giới hạn bài viết; có thể tạm dừng theo dõi.
3. Với nguồn thử nghiệm được phép truy cập và có dữ liệu phù hợp, hệ thống thực hiện phiên tracking theo lịch, lưu trạng thái và dữ liệu khả dụng; số bài thu thập không vượt giới hạn áp dụng cho lượt đó.
4. Khách hàng xem được kết quả từng phiên và nội dung tổng hợp; các trường bài viết và bình luận hiển thị khi nguồn cung cấp, dữ liệu thiếu được thể hiện rõ.
5. Với dữ liệu thử nghiệm thỏa mãn quy tắc cảnh báo tiêu cực đã cấu hình, hệ thống tạo cảnh báo và khách hàng xem được trong lịch sử.
6. Khách hàng yêu cầu được bản phân tích AI theo nhãn hàng và thời gian; kết quả nêu phạm vi dữ liệu và gợi ý, hoặc thông báo rõ khi không thể phân tích.

Đối với dữ liệu kiểm thử và demo, người dùng cho phép dùng địa chỉ email giả. Tài khoản do quản trị viên tạo hoặc đánh dấu đã xác minh bằng email giả chỉ chứng minh các luồng sau đăng nhập; không chứng minh email xác minh được gửi, nhận hoặc hoàn tất tự đăng ký. Điều này không thay đổi yêu cầu đăng ký và đăng nhập của sản phẩm.

## 9. Nội dung cần thống nhất

1. Nền tảng tích hợp trong phiên bản đầu tiên và phương thức truy cập hợp lệ cho từng nguồn.
2. Giới hạn bài viết tính theo từ khóa, nền tảng hay toàn bộ phiên; số bình luận nổi bật cho mỗi bài.
3. Tiêu chí chọn bài viết nổi bật, tần suất được hỗ trợ và múi giờ áp dụng cho lịch tracking.
4. Công thức đo tốc độ tăng nội dung tiêu cực, khoảng so sánh, ngưỡng mặc định và cách xử lý khi dữ liệu gốc bằng không.
5. Kênh gửi cảnh báo, quy tắc chống lặp và thời gian đánh giá cảnh báo.
6. Cách xác thực, nhà cung cấp cloud và AI, ngân sách, chỉ tiêu hiệu năng, thời hạn lưu và xử lý dữ liệu cá nhân.

## 10. Quy tắc nghiệp vụ đề xuất để triển khai và kiểm thử

Các quy tắc trong mục này là **giả định đề xuất**, chưa phải quyết định được khách hàng phê duyệt. Áp dụng thống nhất trong bản thử nghiệm; thay đổi sau khi nhóm xác nhận. Kết quả phụ thuộc dữ liệu thu thập được và không đại diện cho toàn bộ thảo luận trên mạng xã hội.

### 10.1. Lịch, phạm vi và phiên tracking

- Một phiên thuộc một nhãn hàng và gồm các lượt tìm kiếm cho từng cặp nền tảng và từ khóa đã bật. Giới hạn N bài áp dụng riêng cho mỗi cặp trong mỗi phiên; mỗi lượt lấy tối đa N kết quả có thể truy cập. N phải là số nguyên dương. Số lượng thực tế có thể nhỏ hơn N.
- Theo dõi lặp theo tần suất và múi giờ đã cấu hình; hệ thống hiển thị lịch dự kiến. Không chạy hai phiên đồng thời cho cùng nhãn hàng; nếu đến lịch khi phiên trước còn chạy, ghi nhận lượt bị bỏ qua. Cách khôi phục lịch bị bỏ lỡ sau sự cố cần xác nhận.
- Quy ước đang thử: lịch ngày dùng giờ đã đặt, hai lần/ngày thêm một lượt cách 12 giờ địa phương; lịch tuần chọn thứ của ngày bật hoặc đổi lịch. Bộ điều phối thử gộp các lịch bị lỡ thành một phiên, chưa phải quyết định vận hành cuối cùng.
- Lưu bản chụp cấu hình và thời điểm bắt đầu, kết thúc cho mỗi phiên. Thay đổi cấu hình chỉ áp dụng cho phiên bắt đầu sau khi lưu. Tạm dừng ngăn phiên mới, phiên đang chạy tiếp tục; lịch sử không bị thay đổi.
- Trạng thái phiên gồm đang chờ, đang chạy, thành công, thành công một phần, thất bại và bỏ qua. Phiên được yêu cầu nhưng worker chưa nhận ở trạng thái đang chờ; nếu cấu hình bị tạm dừng trước khi worker nhận thì phiên được đánh dấu bỏ qua. Một phiên thành công khi mọi lượt hoàn tất, kể cả không có kết quả; thành công một phần khi có lượt thành công và lượt thất bại; thất bại khi không lượt nào thành công. Lưu trạng thái, số kết quả và lỗi theo từng lượt để phân biệt rỗng với lỗi.
- Một bài trùng nhiều từ khóa được tính một lần theo cặp nền tảng và định danh nguồn, nhưng giữ liên kết với mọi lượt và phiên đã tìm thấy. Lưu chỉ số tương tác như ảnh chụp theo thời điểm thu thập; màn hình tổng hợp hiển thị bài duy nhất và chỉ số mới nhất trong phạm vi lọc. Nếu không có định danh ổn định, đánh dấu khả năng trùng và không bảo đảm khử trùng.
- Bình luận được nhận diện tương tự theo nguồn và định danh. Thứ tự nổi bật của bài phụ thuộc nguồn; bình luận được sắp theo react giảm dần khi chỉ số khả dụng. Số bình luận lấy và quy tắc khi bằng điểm hoặc thiếu react chờ xác nhận.
- Người dùng chọn xóa vĩnh viễn nhãn hàng và toàn bộ dữ liệu liên quan sau khi xác nhận. Bản thử xóa trong database của ứng dụng, bao gồm cấu hình/lịch, phiên, nội dung và kết quả phân tích; từ chối khi phiên đang chờ/chạy hoặc tác vụ phân loại/phân tích đang chạy, cho phép thử lại sau. Bản sao lưu/snapshot có thể còn chứa dữ liệu sau thao tác; thời hạn và xử lý xóa trong bản sao lưu cần được nhóm thống nhất. Nội dung tại nguồn không bị thao tác này xóa.

### 10.2. Quy tắc cảnh báo đề xuất

- Đánh giá sau khi phiên hoàn tất; chỉ đánh giá các nguồn có lượt thành công và hiển thị phạm vi, thời điểm thu thập và trạng thái không đầy đủ khi có lượt thất bại. Các bài và bình luận chưa phân tích được cảm xúc không tính là tiêu cực.
- Chỉ so sánh hai cửa sổ khi phạm vi nguồn, từ khóa, giới hạn thu thập và mức độ bao phủ có thể đối chiếu; cần kiểm tra cả hai cửa sổ có đủ lượt thu thập theo lịch thành công. Nếu cấu hình thay đổi, thiếu phiên hoặc lượt thất bại làm độ bao phủ không thể so sánh, đánh dấu không đủ dữ liệu và không tính tốc độ tăng, không coi dữ liệu thiếu là số 0. Tiêu chí xác định mức bao phủ đủ cần nhóm xác nhận.
- Với mỗi loại bài viết hoặc bình luận, đếm nội dung tiêu cực **duy nhất** theo định danh nguồn, dựa trên thời điểm thu thập đầu tiên trong từng cửa sổ; cùng nội dung không được đếm lại vì xuất hiện ở phiên khác. Định nghĩa cửa sổ và cách xử lý thiếu định danh cần xác nhận trước nghiệm thu chính thức.
- Mặc định đề xuất: so sánh số đếm của cửa sổ hiện tại với cửa sổ liền trước có cùng độ dài. Khi số trước lớn hơn 0, tốc độ tăng = (số hiện tại − số trước) / số trước × 100%. Kích hoạt khi tốc độ tăng lớn hơn hoặc bằng ngưỡng và số hiện tại đạt mức tối thiểu do quy tắc đặt. Khi số trước bằng 0, không tính tỷ lệ; áp dụng ngưỡng số lượng tuyệt đối nếu đã cấu hình, nếu không hiển thị không đủ cơ sở so sánh.
- Không coi dữ liệu chưa thu thập hoặc lỗi là số 0. Ghi rõ dữ liệu thiếu và không đánh giá nếu không có lượt thành công. Chỉ tạo tối đa một cảnh báo cho cùng quy tắc, loại nội dung và cửa sổ đánh giá; lần đánh giá lại cùng cửa sổ không tạo bản sao. Kênh gửi ngoài ứng dụng và điều kiện mẫu tối thiểu cần nhóm xác nhận.
- Ví dụ: cửa sổ trước có 10 bình luận tiêu cực, cửa sổ hiện tại có 15, ngưỡng tăng 50% và tối thiểu 5: tạo cảnh báo. Với 14 bình luận thì không tạo. Trường hợp 0 lên 15 không áp dụng tỷ lệ phần trăm; dùng ngưỡng tuyệt đối đã cấu hình hoặc báo không đủ cơ sở.

### 10.3. Cảnh báo trong kịch bản demo (nhóm trưởng chốt 27/11)

Chỉ áp dụng cho nhãn hàng demo dùng dữ liệu giả; quy tắc ở mục 10.2 cho dữ liệu thật không đổi.

- **Cách tính:** sau mỗi lần thu thập, tính tỷ lệ bình luận tiêu cực lũy kế (tiêu cực / tổng). Tạo cảnh báo khi tỷ lệ tăng so với lần thu thập trước từ "ngưỡng tăng (%)" của quy tắc bình luận trở lên, và số tiêu cực đạt mức tối thiểu.
  - Ví dụ: 20/100 (20%) lên 60/200 (30%), ngưỡng 50%: tạo cảnh báo.
  - 60/200 lên 65/300: tỷ lệ giảm, không cảnh báo.
- **Chống lặp:** mỗi lần thu thập có tối đa một cảnh báo; đánh giá lại không tạo bản sao.
- **Nhãn cảm xúc:** nhãn của dữ liệu giả được gán sẵn, không phải kết quả phân loại AI.
- **Kênh ngoài ứng dụng:** gửi email qua Amazon SNS đến **một hộp thư cố định của nhóm**, không gửi đến email tài khoản. Email có link mở thẳng trang cảnh báo. Gửi email cho từng khách hàng là phần mở rộng, chưa thuộc phạm vi.
- **Ngoài phạm vi:** không làm chức năng xóa tài khoản.

Phiên bản thử nghiệm hiện chốt cửa sổ tại 00:00 UTC, từ chối phiên xếp muộn hơn lịch 15 phút và giới hạn 5.000 dòng bằng chứng để tránh đánh giá khi thiếu cơ sở hoặc vượt tài nguyên. Nó chỉ dùng quan sát mới có thời điểm và hash, cùng phiên bản phân loại hiện tại; quan sát cũ thiếu bằng chứng không được suy đoán. Các giới hạn này là lựa chọn triển khai thử, chưa phải tiêu chí độ bao phủ đã được nhóm nghiệm thu. [Giai đoạn 6](development-process/s6_sentiment_alerts.md).

### 10.3. Căn cứ phân tích AI

- Bản phân tích nêu phạm vi thời gian, nền tảng, số lượng nội dung đưa vào, thời điểm dữ liệu và tình trạng thiếu dữ liệu; không khẳng định mẫu thu thập đại diện cho toàn bộ thị trường.
- Mỗi nhận định quan trọng và đề xuất cần liên kết đến nội dung nguồn hoặc mã nội dung đã lưu làm căn cứ khi có thể; số lượng hoặc tỷ lệ chỉ được nêu khi tính được từ tập dữ liệu xác định. Nội dung từ nguồn là dữ liệu để phân tích, không phải chỉ dẫn điều khiển hệ thống hoặc AI.
- Khi không có dữ liệu phù hợp hoặc không thể tạo kết quả có căn cứ, thông báo rõ và cho phép người dùng thử lại; không tự động thực hiện đề xuất thay khách hàng.

## 11. Kiểm chứng bổ sung

Các trường hợp dưới đây kiểm tra các quy tắc đề xuất tại mục 10; không thay thế việc xác nhận yêu cầu với nhóm.

1. **Lịch và tạm dừng (FR-06, FR-08, FR-10):** Với lịch mỗi ngày và một phiên đang chạy, khi đến lịch tiếp theo thì không tạo phiên chạy đồng thời; khi tạm dừng, không bắt đầu phiên mới, phiên hiện tại được hoàn tất.
2. **Giới hạn và trùng (FR-07, FR-11, FR-15, FR-19):** Với N = 10 và cùng một bài có cùng định danh xuất hiện ở hai từ khóa, mỗi lượt trả không quá 10 bài, màn hình tổng hợp hiển thị bài một lần và giữ thông tin các lượt đã tìm thấy.
3. **Lỗi một phần (FR-14, FR-16, FR-17):** Khi một lượt thành công nhưng rỗng và một lượt thất bại, phiên có trạng thái thành công một phần; màn hình phân biệt lượt rỗng với lượt lỗi và giữ dữ liệu thành công nếu có.
4. **Trường thiếu (FR-12, FR-13, FR-20):** Khi nguồn không cung cấp react, giao diện thể hiện không khả dụng thay vì 0.
5. **Cảnh báo (FR-22–FR-26):** Thử các giá trị 10→15 và 10→14 với ngưỡng 50%, sau đó đánh giá lại cùng cửa sổ; chỉ trường hợp đầu tạo một cảnh báo. Trường hợp 0→15 tuân theo quy tắc tuyệt đối hoặc không đủ cơ sở, không chia cho 0.
6. **Phân tích AI (FR-27–FR-30):** Với dữ liệu có căn cứ, kết quả chỉ ra phạm vi và dẫn chứng khả dụng; với tập rỗng hoặc dịch vụ lỗi, giao diện thông báo và không hiển thị đề xuất như kết quả phân tích thành công.
7. **Cô lập dữ liệu (FR-02):** Tài khoản A không thể xem hoặc thay đổi nhãn hàng, phiên, cảnh báo hay kết quả AI của tài khoản B, kể cả khi biết mã đối tượng.
8. **Cloud (NFR-01):** Bản trình diễn được triển khai trên public/private cloud, người kiểm thử truy cập được và thực hiện được luồng cấu hình, tracking với nguồn thử nghiệm và xem kết quả.

## 12. Phạm vi và chỉ tiêu cần xác nhận

MVP dự kiến bao gồm các chức năng tài khoản, ít nhất một nguồn khả thi, theo dõi theo lịch, nội dung theo phiên và tổng hợp, cảnh báo trong ứng dụng và phân tích AI. Tự động đăng bài, trả lời bình luận, thực hiện chiến dịch hoặc tự quyết định thay khách hàng nằm ngoài MVP. Các nền tảng và kênh cảnh báo khác chỉ bổ sung khi khả thi.

Hiện chưa có cam kết định lượng về độ trễ tracking, tốc độ phản hồi, số người dùng đồng thời, tính sẵn sàng, độ chính xác cảm xúc và chi phí. Trước nghiệm thu chính thức, nhóm cần xác định giá trị mục tiêu, dữ liệu và tải thử nghiệm, cách đo và ngưỡng đạt cho từng chỉ tiêu; không xem các yêu cầu định tính hiện tại là bằng chứng đã đạt chỉ tiêu định lượng. Cũng cần chốt khôi phục tài khoản, thời hạn lưu và cách xử lý dữ liệu đã xóa trong bản sao lưu, tính đầy đủ dữ liệu và hành vi khi nguồn thay đổi quyền truy cập.

