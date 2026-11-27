# Giai đoạn 4 — Tài khoản và quản lý nhãn hàng

**27/11/2026 — Đăng ký email thật (đã triển khai, nhóm trưởng thử đạt):** Lambda PreSignUp trong [cognito-demo.yaml](../../infrastructure/cognito-demo.yaml) không còn chặn email thật: email thật nhận mã xác minh qua email mặc định Cognito (`COGNITO_DEFAULT`, `CONFIRM_WITH_CODE`, tiêu đề "Mã xác minh Brand Auto-Tracking"); nguồn đăng ký khác bị chặn. Cùng ngày, theo yêu cầu nhóm trưởng, Lambda **từ chối** miền thử (`example.invalid`, `example.com/org/net`) thay vì tự xác nhận; stack cập nhật `UPDATE_COMPLETE`, logic chạy cục bộ đúng; đã xóa 6 tài khoản giả `@example.invalid` khỏi pool (nhãn hàng của chúng trong database không còn chủ đăng nhập được). Đã kiểm: logic Lambda chạy cục bộ đúng các trường hợp; `validate-template` đạt; stack `brand-demo-minute-auth-20261127` `UPDATE_COMPLETE`; `describe-user-pool` xác nhận cấu hình email và nội dung tiếng Việt; branding giữ nguyên; trang `/signup` trả 200. Nhóm trưởng đã tạo tài khoản bằng email thật và mật khẩu, nhận mã và xác minh thành công trên web demo. Giới hạn: khoảng 50 email/ngày, email có thể vào Spam. Phương án đăng nhập Google đã thử chuẩn bị rồi **bỏ theo quyết định của nhóm trưởng** (cần trang chính sách quyền riêng tư để publish); stack và web đã gỡ Google, không còn identity provider.

**26/11/2026 — Cognito demo riêng:** Template [cognito-demo.yaml](../../infrastructure/cognito-demo.yaml) tự xác nhận/xác minh chỉ email `@example.invalid` trong pool cô lập; không gửi hay nhận mã. Chrome tự đăng ký, đăng nhập, tạo nhãn hàng qua API/RDS AWS và tiếp tục cảnh báo/AI trong câu chuyện demo đạt; frontend cục bộ. Cần dọn pool và stack thử. Đây không chứng minh xác minh email thật.

**23/11/2026 — Xóa nhãn hàng:** Người dùng chọn xóa vĩnh viễn sau xác nhận. API và giao diện đã bổ sung xóa dữ liệu liên quan trong database; API khóa nhãn hàng, kiểm tra chủ sở hữu, trả 409 nếu phiên tracking đang chờ/chạy hoặc phân loại/phân tích đang chạy. PostgreSQL 18 riêng chạy 116 kiểm thử backend đạt, gồm kiểm tra tài khoản khác, tác vụ hoạt động, xóa dữ liệu liên quan và xóa đồng thời với yêu cầu xếp phiên; build frontend đạt. Chrome với FastAPI/PostgreSQL riêng và xác thực giả tạo, xác nhận xóa và không còn thấy nhãn hàng, kể cả CORS DELETE. Kết quả Cognito/AWS được ghi bên dưới. Snapshot/backup có thể còn dữ liệu và thời hạn lưu chưa chốt. [SRS](../software_requirements_specification.md).

**Chuẩn bị thử xóa AWS:** Đã yêu cầu tạo `brand-delete-check-data-20261123` từ template database tạm, không dùng database cũ. Sau thử cần xóa stack data/API, artifact và tài khoản tạm; RDS/NAT phát sinh phí trong thời gian bật. Watchdog PID `14088` dự phòng xóa stack sau 65 phút; phải dọn và kiểm tra chủ động. Không coi là kiểm chứng cho tới khi có kết quả và xác nhận dọn.

Đã đóng gói backend mới và yêu cầu bật lại CloudFront cho phép thử. Watchdog PID `26612` dự phòng khôi phục index gốc và tắt phân phối sau 60 phút; cần chủ động khôi phục, invalidation, tắt và xác nhận sau thử. Hai stack `brand-demo-e2e-*` của lượt trước vẫn đang xóa tài nguyên mạng; RDS/NAT thử cũ không còn.

Stack `brand-delete-check-data-20261123` đã `CREATE_COMPLETE`; đã yêu cầu tạo `brand-delete-check-api-20261123`. Hai stack `brand-demo-e2e-*` của lượt trước đã `DELETE_COMPLETE`. Backend mới đã đóng gói và tải artifact thử; chưa chạy migration hoặc thử xóa AWS.

CloudFront đã bật; build thử mới trỏ API xóa thử đã tải lên, invalidation `I8PWWVTRQLE9B3174B7DCZV5L6` đang xử lý. Cần khôi phục index gốc và tắt sau thử; hai watchdog chỉ dự phòng.

API xóa thử đã `CREATE_COMPLETE`, migration trả `ok`; invalidation đã hoàn tất. Đang chạy Chrome với hai tài khoản Cognito tạm, chưa có kết quả cuối.

**Kết quả xóa qua AWS 23/11:** Chrome qua CloudFront/Cognito/API Gateway/Lambda/RDS thử: tài khoản khác gửi DELETE nhận 404; chủ sở hữu xác nhận xóa trên giao diện, API trả 200 và nhãn hàng biến mất khỏi danh sách. Kiểm thử đăng nhập, refresh, cách ly và logout cùng lượt đạt; hai tài khoản thử được harness xóa. Đã yêu cầu xóa hai stack thử, xóa artifact và log Lambda thử, phục hồi index gốc, yêu cầu invalidation `IAR926Y3AO71H1HG5WT2218BZG` và tắt CloudFront. Cần xác nhận CloudFront và hai stack dọn xong, gồm RDS/NAT. Phép thử này không kiểm tra xóa đồng thời với worker thật hoặc xóa dữ liệu trong backup.

CloudFront đã `Deployed`/tắt, stack frontend `UPDATE_COMPLETE`, invalidation hoàn tất; watcher frontend PID `26612` đã dừng. Hai asset JS và hai version index chỉ thuộc các lượt thử đã xóa khỏi bucket versioning. Hai stack xóa thử vẫn đang hoàn tất xóa; RDS/NAT thử không còn.

API stack xóa thử đã `DELETE_COMPLETE`; data stack từng `DELETE_FAILED` do phụ thuộc subnet. Sau khi kiểm tra không còn network interface trong các subnet còn lại, đã yêu cầu xóa data stack lần nữa; cần xác nhận xong và dừng watcher PID `14088`.

AWS sau đó xác nhận cả hai stack `brand-delete-check-*` đã `DELETE_COMPLETE`; watcher PID `14088` đã dừng.

**Đang chuẩn bị kiểm thử đăng ký:** Đã yêu cầu tạo stack Cognito/Lambda tạm `brand-signup-browser-20261123`, dùng trigger xác nhận email giả để thử giao diện đăng ký và đăng nhập. Cấu hình này không gửi/nhận mã và không phải pool sản phẩm. Watchdog PID `28044` dự phòng xóa sau 45 phút; cần chủ động xóa stack, tài khoản và log thử, xác nhận hoàn tất. Chưa có kết quả kiểm thử.

**Kết quả đăng ký giả lập 23/11:** Chrome mở nút tạo tài khoản trong frontend cục bộ, đăng ký email `example.invalid` qua Cognito pool tạm có trigger tự xác nhận/xác minh và trở lại màn hình quản lý sau đăng nhập; API là stub trả danh sách rỗng. Lượt đầu kịch bản chọn nhầm trường CSRF ẩn và không tạo tài khoản; sau điều chỉnh đã đạt. Tài khoản thử đã xóa, pool kiểm tra còn 0 người dùng, đã yêu cầu xóa stack và xóa log trigger. Phép thử không gửi/nhận mã, không dùng pool sản phẩm và không chứng minh luồng xác minh email thật.

AWS xác nhận stack `brand-signup-browser-20261123` đã `DELETE_COMPLETE`; watcher PID `28044` đã dừng.

**23/11/2026 — Hosting và tài khoản:** Chrome dùng URL CloudFront HTTPS qua Cognito/API Gateway/Lambda/RDS thử tạo nhãn hàng, lưu cấu hình, làm mới phiên, kiểm tra cách ly hai tài khoản và logout thành công. Tài khoản thử đã xóa. Stack tự đăng ký giả lập `brand-signup-check-20261123` đã `DELETE_COMPLETE`; vẫn chưa chứng minh đăng ký/xác minh email thật trên pool và giao diện sản phẩm. Xóa nhãn hàng được bổ sung sau lần thử này như ghi phía trên. [S8](s8_aws_delivery.md).

**23/11/2026 — Tự đăng ký với email giả:** Trong Cognito pool tạm riêng, gọi `SignUp` với địa chỉ `example.invalid`, trigger PreSignUp tự xác nhận và đánh dấu email đã xác minh; không có `CodeDeliveryDetails`. Đăng nhập `USER_PASSWORD_AUTH` và kiểm tra thuộc tính đã xác minh đạt; tài khoản thử đã xóa. Đây là cấu hình giả lập riêng, không phải luồng tự đăng ký qua giao diện/pool sản phẩm và không chứng minh gửi, nhận hoặc nhập mã. Stack `brand-signup-check-20261123` đang xóa; log thử đã xóa.

**23/11/2026 — Đang thử tự đăng ký giả lập:** Stack Cognito thử `brand-signup-check-20261123` đang tạo pool riêng với trigger tự xác nhận/xác minh email giả, không dùng pool sản phẩm và không chứng minh gửi/nhận mã. Watchdog PID `33736` dự kiến dọn sau một giờ; cần chủ động xóa và xác nhận.

**23/11/2026 — Quyết định dữ liệu thử:** Người dùng cho phép dùng email giả khi kiểm thử/demo. Các tài khoản Cognito thử có thể được tạo và xác minh giả lập để kiểm tra đăng nhập và cách ly; không coi đó là bằng chứng đã gửi/nhận mã xác minh hay hoàn tất luồng tự đăng ký. Không cần yêu cầu người dùng cung cấp hộp thư thật chỉ để có dữ liệu thử.

**23/11/2026 — AWS thử:** Chrome qua Cognito thật, API Gateway/Lambda và RDS thử mới xác nhận đăng nhập, refresh token, đăng xuất và hai tài khoản không xem/sửa được nhãn hàng của nhau. Hai tài khoản thử đã xóa; chưa kiểm thử đăng ký và xác minh email thật. [S8](s8_aws_delivery.md).

**22/11/2026 — Thử chuyển đến Cognito từ hosting:** Stack Cognito đã `UPDATE_COMPLETE`, giữ cả hai URL localhost và thêm callback/logout CloudFront. Chrome headless mở trang CloudFront, nút đăng nhập chuyển tới Cognito với PKCE S256 và callback đúng, không có lỗi trang. Chưa đăng nhập, xác minh email hoặc gọi API qua hosting; xem [S8](s8_aws_delivery.md).

**22/11/2026 — Chuẩn bị callback hosting:** Template Cognito thêm tham số tùy chọn cho callback/logout của demo, giữ hai địa chỉ localhost; AWS `validate-template` và `cfn-lint` đạt. Change set chỉ sửa `WebClient`, không thay thế, đã được yêu cầu thực thi; chưa xác nhận cập nhật hoặc kiểm thử callback qua hosting mới. [Hạ tầng](../../infrastructure/README.md), [S8](s8_aws_delivery.md).

Ngày 17/11 chuẩn bị thử đăng ký và xác minh email bằng hộp thư được kết nối, nhưng phiên AWS SSO hết hạn trước khi đọc cấu hình Cognito; chưa tạo tài khoản và chưa gửi email xác minh. Cần đăng nhập lại SSO để tiếp tục kiểm thử và dọn tài khoản thử sau đó.

Ngày 16/11 sau khi chuyển giao diện kết nối thành mặc định, kiểm thử lại bằng hai tài khoản Cognito thật, Chrome, backend và PostgreSQL cục bộ: đăng nhập, tạo nhãn hàng, refresh token, B không thấy hoặc đọc/sửa nhãn hàng A, và logout đạt. Tài khoản thử đã xóa, user pool trở lại 0 người dùng; database thử đã dọn. Chưa thử hoàn tất đăng ký bằng xác minh email, khôi phục tài khoản hay xóa tài khoản sản phẩm.

Sau migration `0007_brand_create_key`, chạy lại cùng kịch bản hai tài khoản Cognito thật qua frontend và backend cục bộ, bao gồm tạo nhãn hàng với header chống trùng: đạt đăng nhập, refresh, cách ly và logout. Hai tài khoản và database thử đã xóa; user pool xác nhận 0 người dùng.

**Cập nhật:** 23/11/2026. **Trạng thái:** Đã thử các luồng tài khoản và nhãn hàng trên AWS tạm; còn xác minh email thật và chính sách lưu bản sao.

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
