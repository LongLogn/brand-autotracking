# Giai đoạn 4 — Tài khoản và quản lý nhãn hàng

Ngày 17/11 chuẩn bị thử đăng ký và xác minh email bằng hộp thư được kết nối, nhưng phiên AWS SSO hết hạn trước khi đọc cấu hình Cognito; chưa tạo tài khoản và chưa gửi email xác minh. Cần đăng nhập lại SSO để tiếp tục kiểm thử và dọn tài khoản thử sau đó.

Ngày 16/11 sau khi chuyển giao diện kết nối thành mặc định, kiểm thử lại bằng hai tài khoản Cognito thật, Chrome, backend và PostgreSQL cục bộ: đăng nhập, tạo nhãn hàng, refresh token, B không thấy hoặc đọc/sửa nhãn hàng A, và logout đạt. Tài khoản thử đã xóa, user pool trở lại 0 người dùng; database thử đã dọn. Chưa thử hoàn tất đăng ký bằng xác minh email, khôi phục tài khoản hay xóa tài khoản sản phẩm.

Sau migration `0007_brand_create_key`, chạy lại cùng kịch bản hai tài khoản Cognito thật qua frontend và backend cục bộ, bao gồm tạo nhãn hàng với header chống trùng: đạt đăng nhập, refresh, cách ly và logout. Hai tài khoản và database thử đã xóa; user pool xác nhận 0 người dùng.

**Cập nhật:** 16/11/2026. **Trạng thái:** Đang phát triển cục bộ; chưa có bằng chứng triển khai thực tế.

- Backend có API đổi tên nhãn hàng; kiểm thử với PostgreSQL và JWT thử xác nhận chủ sở hữu đổi được, tài khoản khác nhận 404 và tên rỗng bị từ chối. Chưa có chính sách/API xóa.
- Có giao diện thử API riêng cho danh sách, tạo và sửa tên/cấu hình, dùng access token nhập thủ công. Chưa kiểm chứng trên trình duyệt với Cognito thật; giao diện mẫu mặc định vẫn chưa kết nối. Chưa có API xóa.
- Kiểm thử trình duyệt với backend và PostgreSQL tạm, xác thực giả đã tạo, sửa và tải lại cấu hình, kể cả thử lại khi lưu lỗi; chưa chứng minh Cognito thật. Xem [S1](s1_frontend.md).
- Ngày 16/11 giao diện thử nghiệm thêm OAuth authorization code + PKCE. Kiểm thử Chrome qua Cognito thật và backend cục bộ xác minh access token, đọc danh sách nhãn hàng thành công; tài khoản thử được tạo không gửi email và xóa sau thử, user pool trở lại 0 người dùng. PostgreSQL tạm đã dọn. Chưa kiểm thử hai tài khoản qua Cognito thật, làm mới token, đăng xuất Cognito hoặc scope tại API Gateway/backend; giao diện mẫu mặc định chưa tích hợp.
- Kiểm thử tiếp với hai tài khoản Cognito thật tạo riêng, không gửi email: A đăng nhập và tạo nhãn hàng; B đăng nhập, không thấy nhãn hàng A trong danh sách, đọc cấu hình và đổi tên nhận 404. Frontend và backend chạy cục bộ, PostgreSQL tạm; hai tài khoản thử đã xóa và user pool trở lại 0 người dùng. Chưa kiểm thử cách ly worker trên AWS, làm mới token, đăng xuất Cognito hoặc scope.
- Đã bổ sung đăng xuất managed login cho giao diện thử và đăng ký logout URL localhost; stack Cognito `UPDATE_COMPLETE`. Kiểm thử Chrome với hai tài khoản Cognito thật xác nhận đăng xuất rồi yêu cầu đăng nhập lại. Endpoint logout không tự thu hồi token đã cấp; chưa làm mới token hoặc kiểm tra scope. Tài khoản và database thử đã dọn. [Tài liệu AWS](https://docs.aws.amazon.com/cognito/latest/developerguide/logout-endpoint.html).
- Ngày 16/11 backend yêu cầu scope `brand-api/access`, từ chối 403 khi thiếu hoặc không khớp chính xác; kiểm thử JWT giả và trình duyệt với hai tài khoản Cognito thật/backend cục bộ đều đạt. Frontend thử nghiệm làm mới token trong bộ nhớ trước hạn, gộp yêu cầu đồng thời; kiểm thử phản hồi giả đạt, chưa thử refresh với Cognito thật. 26 kiểm thử backend PostgreSQL và 15 kiểm thử frontend đạt; tài khoản và database thử đã dọn. API Gateway chưa triển khai.
- Tiếp đó bật tự đăng ký email trên Cognito dev và thêm nút tạo tài khoản vào giao diện thử; Chrome mở thành công trang đăng ký thật, chưa gửi/nhập mã xác minh email. Kiểm thử hai tài khoản Cognito thật qua API Gateway/Lambda/RDS thật xác nhận tạo nhãn hàng, cách ly, refresh token thật bằng cách điều chỉnh đồng hồ trang và đăng xuất. Giao diện mặc định vẫn là mẫu; chưa có chính sách chống lạm dụng, xóa tài khoản hoặc quy trình khôi phục tài khoản hoàn chỉnh.

- [Frontend](../../frontend/README.md) mô phỏng đăng nhập và quản lý nhãn hàng bằng dữ liệu mẫu; chưa kết nối Cognito hoặc backend.
- Cần backend, xác thực, lưu cấu hình và kiểm thử cách ly tài khoản theo [lộ trình](../development_roadmap.md).
- Tiếp theo: sau khi có hợp đồng và nền tảng backend phù hợp, triển khai luồng thật và lưu bằng chứng kiểm thử.
