# Tài liệu đặc tả yêu cầu: Hệ thống đăng ký môn học

| Thuộc tính | Nội dung |
|---|---|
| Phiên bản | 0.8 (bản rút gọn) |
| Cập nhật | 09/11/2026 |
| Học phần | Điện toán đám mây (UET.CN3134), bài tập lớn |
| Người đọc | Nhóm thực hiện, giảng viên |
| Góc nhìn | Người dùng cuối: hệ thống phải làm gì, chưa quy định cách xây dựng |

## 1. Bài toán

Ngày thường, hệ thống đăng ký môn học có rất ít người dùng, khoảng 200 lần truy cập mỗi ngày. Khi mở đăng ký, có thể có đến 5.000 sinh viên vào trong 5 phút và giành chỗ trong cùng một số lớp. Thời gian mở đăng ký tối đa khoảng 27 ngày/năm, tức khoảng 7% số ngày. Các con số này là giả định, chưa có số liệu thực.

Điều đó gây ra ba vấn đề:
- **Sinh viên:** hệ thống dễ quá tải đúng lúc cần nhất, và việc giành được chỗ phụ thuộc vào tốc độ mạng hơn là một quy tắc rõ ràng.
- **Ban quản lý nhà trường:** chỉ một sai sót khi nhiều người đăng ký cùng lúc cũng có thể làm lớp vượt sĩ số.
- **Nhà trường:** giữ công suất đỉnh quanh năm thì lãng phí, giữ công suất thấp thì quá tải khi mở đăng ký.

**Hướng tiếp cận:** chỉ một số sinh viên được thao tác cùng lúc, số còn lại xếp hàng theo quy tắc công khai. Công suất được tăng theo lịch đăng ký và giảm khi hết nhu cầu.

**Phạm vi:** hệ thống được thiết kế theo yêu cầu dùng thật, nhưng trong bài tập lớn chỉ dùng tài khoản và dữ liệu giả lập. Muốn dùng thật, nhà trường cần chấp thuận và phải bổ sung kết nối đăng nhập của trường, nguồn dữ liệu đào tạo thật, đánh giá bảo mật và dữ liệu cá nhân, đo tải với số liệu thật.

## 2. Thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| Phiên | Một đợt mở đăng ký, khoảng 2–3 ngày. Một năm có dưới 10 phiên, gồm phiên chính và phiên bổ sung. |
| Lớp | Đơn vị đăng ký, có một mã lớp và một sĩ số. Đăng ký một lớp là đăng ký toàn bộ các buổi lý thuyết và thực hành của lớp đó; một lớp có thể có nhiều buổi trong tuần. |
| Hàng chờ | Nơi sinh viên đợi khi số người đang đăng ký đã đạt mức tối đa. |
| Lượt | 30 phút sinh viên được đăng ký, hủy, đổi lớp. |
| Thời gian chờ | 30 phút sau khi kết thúc lượt, chưa được nhận lượt mới. |
| Chế độ chỉ đọc | Trạng thái tạm khóa thay đổi dữ liệu khi có sự cố; vẫn xem và in được. |

## 3. Vai trò

| Vai trò | Được làm | Cách có tài khoản |
|---|---|---|
| Sinh viên | Đăng ký, hủy, đổi lớp, xem và in kết quả của bản thân | Từ danh sách nhà trường, dùng email trường cấp; không tự tạo |
| Ban quản lý nhà trường | Nhập dữ liệu, quản lý lớp và phiên, xem thống kê, tra cứu phiếu | Cấp sẵn, không tự tạo |
| Vận hành | Theo dõi hệ thống, bật chỉ đọc, chỉnh lịch công suất và mức lượt, chạy đối soát; không sửa được lớp hay đăng ký | Cấp sẵn, không tự tạo |

Không có tài khoản toàn quyền.

## 4. Yêu cầu chức năng

### 4.1. Bắt buộc

| Mã | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| FR-01 | Sinh viên đăng nhập bằng email trường cấp | Email ngoài danh sách bị từ chối. |
| FR-02 | Xem và tìm lớp | Mỗi lớp hiển thị môn, tín chỉ, lịch các buổi, giảng viên, giảng đường, số chỗ còn lại. Số chỗ có thể trễ tối đa 10 giây; kết quả khi gửi mới là căn cứ. |
| FR-03 | Xếp hàng khi đông | Sinh viên thấy vị trí và thời gian ước tính. Trang nhắc giữ trang mở để không bỏ lỡ lượt. Khi đến lượt, trang tự hiện lời mời bắt đầu và phát âm báo. |
| FR-04 | Lượt 30 phút | Có đồng hồ đếm ngược. Hết giờ thì tự out. Tự thoát có hộp xác nhận báo sẽ phải chờ 30 phút. |
| FR-05 | Đăng ký lớp | Nhận ngay kết quả thành công hoặc lý do từ chối theo mục 5.2. Đã báo thành công thì chỗ được giữ. |
| FR-06 | Hủy và đổi lớp | Đổi lớp là một thao tác trọn vẹn: lớp mới không đạt thì vẫn ở lớp cũ. |
| FR-07 | Xem lớp đã đăng ký và thời khóa biểu tuần | Hiển thị đúng thứ, tiết, phòng, tuần học, xem được cả ngoài lượt. |
| FR-08 | Tải phiếu đăng ký DOCX kèm mã tra cứu | File chỉ gồm lớp đăng ký thành công. Ban quản lý nhà trường nhập mã thì biết phiếu còn khớp với đăng ký hiện tại hay không. |
| FR-09 | Ban quản lý nhà trường nhập file đầu kỳ | Kiểm tra và xem trước khi áp dụng; có dòng lỗi thì báo theo dòng và không áp dụng dòng nào. Không nhập lại file lớp của kỳ đã có đăng ký. |
| FR-10 | Ban quản lý nhà trường thêm, sửa, hủy lớp | Mở được lớp mới khi phiên đang mở. Không giảm sĩ số xuống dưới số đã đăng ký. Hủy lớp thì sinh viên trong lớp thấy thông báo. |
| FR-11 | Ban quản lý nhà trường tạo phiên | Đặt được kỳ, giờ mở, giờ đóng, giới hạn tín chỉ. Đúng giờ thì tự mở, tự đóng. |
| FR-12 | Vận hành theo dõi hệ thống | Một trang hiển thị số người đang có lượt, số người trong hàng chờ, tỷ lệ lỗi, thời gian phản hồi. |
| FR-13 | Lịch công suất theo phiên và mức lượt tối đa | Khi có phiên mới, lịch được tạo để tăng công suất trước giờ mở và giảm khi hết hàng chờ. Vận hành chỉnh được lịch và mức lượt tối đa. |
| FR-14 | Chế độ chỉ đọc | Khi bật: khóa thay đổi dữ liệu, vẫn xem và in được, trang có thông báo. Theo quy tắc BR-07. |
| FR-15 | Đối soát sau phiên | Báo số lớp vượt sĩ số, số sinh viên trùng lịch và số đăng ký trùng. Kết quả phải bằng 0. |

### 4.2. Nên có

Làm sau khi xong nhóm Bắt buộc.

| Mã | Yêu cầu | Tiêu chí chấp nhận |
|---|---|---|
| FR-16 | Giỏ môn dự kiến | Soạn trước phiên, không giữ chỗ. Gửi trong lượt thì xử lý từng lớp theo thứ tự và trả kết quả từng lớp. |
| FR-17 | Email xác nhận | Có email khi đăng ký, hủy, đổi lớp và khi lớp bị hủy. Email lỗi không ảnh hưởng kết quả đăng ký. |
| FR-18 | Thống kê nhu cầu | Theo từng lớp: số đã đăng ký, chỗ còn, số sinh viên bị từ chối do hết chỗ, lớp chưa đủ sĩ số tối thiểu khi đóng phiên. Hệ thống không tự hủy lớp. |
| FR-19 | Đăng ký sẵn | Ban quản lý nhà trường nhập file đăng ký sẵn trước phiên; sinh viên hủy hoặc đổi được trong lượt. Tắt khi đo tải tranh chỗ. |
| FR-20 | Sao lưu và khôi phục | Có bản sao lưu trước và sau mỗi phiên; đã diễn tập khôi phục. |
| FR-21 | Nhật ký thao tác | Ghi lại thao tác của sinh viên, ban quản lý nhà trường và vận hành để giải quyết khiếu nại. |

### 4.3. Để sau, không làm ở bản đầu

- Tiến độ chương trình học, xuất lịch `.ics`, báo cáo công bằng sau phiên.
- Chia khung giờ theo khóa hoặc ngành, ngoại lệ thêm vào lớp đã đầy.
- Danh sách chờ khi lớp đầy, báo khi lớp có chỗ trống, phát hiện gian lận tự động.
- Kiểm tra trùng giảng đường hoặc giảng viên khi nhập file.
- Học phí, nhập điểm, chức năng cho giảng viên, ứng dụng di động riêng, chatbot AI.

## 5. Quy tắc nghiệp vụ

### 5.1. Lượt và hàng chờ

| Mã | Quy tắc |
|---|---|
| BR-01 | Mỗi lượt 30 phút, do hệ thống tính. Đóng trình duyệt, đăng xuất hay mất mạng không dừng đồng hồ. |
| BR-02 | Hết giờ hoặc tự thoát đều phải chờ 30 phút mới được xếp hàng lại. Các lớp đã đăng ký thành công vẫn được giữ. |
| BR-03 | Mỗi sinh viên chỉ có một lượt và một vị trí, kể cả khi dùng nhiều thiết bị. Tải lại trang không làm đổi vị trí. |
| BR-04 | Hàng chờ mở trước giờ mở phiên 15 phút. Tại giờ mở, những người đang đợi được xếp ngẫu nhiên; người đến sau xếp theo thứ tự đến. |
| BR-05 | Khi đến lượt, sinh viên có 5 phút để xác nhận và suất được giữ trong thời gian đó. Quá 5 phút thì về cuối hàng, không bị tính thời gian chờ. |
| BR-06 | Mỗi tài khoản bị giới hạn 2 thao tác/giây; vượt mức thì nhận thông báo thử lại sau. |
| BR-07 | Khi bật chỉ đọc: mọi lượt kết thúc và không tính thời gian chờ, hàng chờ giữ nguyên thứ tự. Khi tắt, người bị ngắt được cấp lại lượt trước. Lượt hết giờ trong lúc hệ thống ngừng phục vụ cũng không tính thời gian chờ. |

### 5.2. Điều kiện đăng ký

Chỉ đăng ký, hủy, đổi lớp được khi phiên đang mở và sinh viên đang có lượt.

| Mã | Điều kiện | Thông báo khi từ chối |
|---|---|---|
| BR-10 | Lớp còn chỗ | "Lớp đã hết chỗ." kèm các lớp cùng môn còn chỗ |
| BR-11 | Không có buổi nào trùng lịch với lớp đã đăng ký | "Trùng lịch với lớp [mã lớp]." |
| BR-12 | Đã đạt các môn tiên quyết; đang học hoặc không đạt thì chưa được đăng ký | "Chưa đạt môn tiên quyết: [tên môn]." |
| BR-13 | Tổng tín chỉ trong kỳ không vượt mức tối đa của chương trình. Dưới mức tối thiểu chỉ cảnh báo | "Vượt quá [N] tín chỉ cho phép." |
| BR-14 | Đúng khóa, ngành và chương trình được phép | "Lớp này không dành cho bạn." |
| BR-15 | Học lại môn không đạt khi môn đó cho phép. Học cải thiện chỉ với điểm trong danh sách được cải thiện | "Bạn không thuộc diện được học lại hoặc cải thiện môn này." |
| BR-16 | Không đăng ký hai lớp cùng môn trong một kỳ, không đăng ký môn đang học. Gửi lại một yêu cầu không tạo đăng ký trùng | "Bạn đã đăng ký hoặc đang học môn này." |

## 6. Dữ liệu

Bản demo chỉ dùng dữ liệu giả lập. File nhập có định dạng Excel theo mẫu của hệ thống.

| File | Các cột chính |
|---|---|
| Lớp học | Mã kỳ, mã môn, tên môn, tín chỉ, mã lớp, sĩ số, sĩ số tối thiểu, loại buổi, thứ, tiết, tuần, giảng viên, giảng đường, môn tiên quyết, khóa, ngành và chương trình được phép, cho phép học lại, cho phép cải thiện |
| Sinh viên | Mã sinh viên, họ tên, email, khóa, ngành, chương trình |
| Kết quả học tập | Mã sinh viên, mã môn, kỳ học, trạng thái (Đang học, Đạt, Không đạt), điểm chữ |
| Đăng ký sẵn (FR-19) | Mã kỳ, mã sinh viên, mã lớp |

- Mỗi buổi học là một dòng. Một lớp có nhiều buổi thì nhiều dòng, nhưng chỉ đăng ký một lần và chỉ tính một chỗ.
- Một môn có nhiều dòng kết quả: đã có dòng Đạt thì là Đạt; nếu không thì lấy kỳ mới nhất.
- Phiếu DOCX gồm thông tin sinh viên, kỳ học, các lớp đã đăng ký thành công, tổng tín chỉ, thời điểm in và mã tra cứu. Mỗi lần in tạo một mã mới.
- Dữ liệu mẫu theo sổ tay UET 2020–2021, cần đối chiếu bản mới nhất: tối thiểu 14 tín chỉ (chuẩn) hoặc 16 (chất lượng cao, chuẩn quốc tế), tối đa 25; điểm F phải học lại, điểm D và D+ được cải thiện; lớp mở khi có từ 20 sinh viên.

## 7. Yêu cầu chất lượng

Các con số là **mục tiêu đề xuất**, sẽ được đo và ghi trong báo cáo.

| Mã | Yêu cầu | Mục tiêu | Cách đo |
|---|---|---|---|
| NFR-01 | Đúng dữ liệu | Không lớp nào vượt sĩ số, không trùng lịch, không đăng ký trùng | Đối soát sau kiểm thử tải |
| NFR-02 | Không mất kết quả | Mọi đăng ký đã báo thành công vẫn còn, kể cả khi có sự cố | Đối chiếu nhật ký công cụ kiểm thử với dữ liệu |
| NFR-03 | Tốc độ đăng ký khi cao điểm | 95% yêu cầu có kết quả trong 2 giây, lỗi dưới 1% | Kiểm thử tải tại mức lượt tối đa |
| NFR-04 | Chịu được lúc mở phiên | 5.000 sinh viên đăng nhập và vào hàng trong 5 phút; 95% thao tác xem trong 3 giây | Kiểm thử tải |
| NFR-05 | Thời gian chờ đến lượt | 95% sinh viên có lượt đầu tiên trong 3 giờ, tương ứng khoảng 800 lượt cùng lúc nếu ai cũng dùng hết 30 phút | Tính từ mức lượt đã đo |
| NFR-06 | Chịu lỗi | Một thành phần hỏng thì hệ thống vẫn phục vụ, lỗi trở lại dưới 1% trong 5 phút | Ngắt một thành phần khi đang tải cao |
| NFR-07 | Chi phí | Chi phí cả năm thấp hơn ít nhất 50% so với giữ công suất đỉnh quanh năm | Tính từ công suất đã đo |
| NFR-08 | Bảo mật | Mỗi vai trò chỉ xem được dữ liệu theo mục 3; dữ liệu được mã hóa khi truyền và khi lưu | Thử truy cập chéo, kiểm tra cấu hình |

Giao diện dùng tiếng Việt và dùng được trên điện thoại.

## 8. Kịch bản demo

1. Ban quản lý nhà trường nhập file và tạo phiên; công suất được tăng theo lịch.
2. 5.000 sinh viên giả lập vào hàng khi mở phiên, hệ thống chỉ cấp lượt đến mức tối đa (NFR-04, BR-04).
3. Nhiều sinh viên giành chỗ cuối của một lớp, chỉ đủ người được nhận (NFR-01, NFR-03).
4. Một sinh viên đăng ký, đổi lớp, tải phiếu DOCX (FR-05, FR-06, FR-08).
5. Ngắt một thành phần khi đang tải cao, rồi đối soát (NFR-02, NFR-06, FR-15).
6. Đóng phiên, công suất giảm, trình bày so sánh chi phí (FR-13, NFR-07).

## 9. Giả định và câu hỏi còn mở

**Giả định:**
- Phiên đăng ký chỉ mở sau khi kỳ trước đã kết thúc và đã nhập kết quả. Nếu chưa có điểm, sinh viên sẽ bị BR-12 chặn.
- Số liệu 5.000 sinh viên, 200 lần truy cập mỗi ngày và 27 ngày/năm chưa có căn cứ thực tế.

**Câu hỏi còn mở:**
- Q-01: Ban quản lý nhà trường có được chỉnh hoặc tắt thời gian chờ cho từng phiên không?
- Q-02: Mức lượt tối đa là bao nhiêu? Chốt sau khi đo tải.
- Q-03: Có chấp nhận các mục tiêu ở mục 7 không? Xem lại sau khi đo tải.
