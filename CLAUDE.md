# Hệ thống đăng ký môn học trên AWS

Bài tập lớn môn Điện toán đám mây (UET.CN3134). Tên repo và `../TeamPrj` thuộc đề tài cũ, không dùng.

## Tài liệu
- `docs/software-requirements-specification.md`: yêu cầu, không nêu tên dịch vụ AWS
- `docs/architecture.md`: kiến trúc, rủi ro, thứ tự xây dựng
- `docs/demo_instruction.md`: kịch bản demo
- `score_criterias/`: tiêu chí chấm và đề cương (căn cứ xác định dịch vụ ngoài bài dạy)

## Trí nhớ
- Đầu phiên: đọc `.claude/memory/long-term.md` và `.claude/memory/short-term.md` nếu có.
- Cuối phiên, hoặc khi được yêu cầu: ghi đè `short-term.md`; chỉ thêm vào `long-term.md` điều còn đúng lâu dài.

## Trọng tâm
- Điểm nằm ở cách chọn và phối hợp dịch vụ AWS. Mỗi dịch vụ phải có lý do rõ ràng.
- Chức năng vừa phải, demo được trong một buổi. Ưu tiên giải pháp đơn giản.
- Chỉ dùng dữ liệu giả lập.

## Quyết định đã chốt (không tự đổi)
- Lượt 30 phút; hết giờ hoặc tự thoát đều chờ 30 phút.
- Phiếu đăng ký là DOCX kèm mã tra cứu.
- 3 vai trò: sinh viên, ban quản lý nhà trường, vận hành.
- Lý thuyết và thực hành cùng một lớp; một lớp có thể có nhiều buổi trong tuần.
- Đang học hoặc không đạt môn tiên quyết thì chưa được đăng ký môn sau.
## Quy tắc
- Hỏi trước khi tạo tài nguyên AWS tính phí. Bật Budgets trước; dựng bằng CloudFormation; xóa stack sau mỗi buổi.
- Không ghi con số như đã đo khi chưa đo. Số đo trái với luận điểm thì báo đúng số đo.
- Không để thông tin xác thực trong repo; dùng IAM role hoặc Secrets Manager.
- Chỉ commit khi được yêu cầu.
- Viết bằng tiếng Việt; tên file và code bằng tiếng Anh. Luôn viết "ban quản lý nhà trường".
- Làm từng bước nhỏ và kiểm thử thật trước khi báo xong.
