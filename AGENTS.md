# Bối cảnh dự án cho AI

## Mục tiêu

Xây dựng hệ thống theo dõi nhãn hàng tự động trên nền tảng đám mây cho bài tập lớn. Hệ thống thu thập bài viết và bình luận liên quan đến nhãn hàng từ các nguồn mạng xã hội được hỗ trợ, phân tích và trình bày dữ liệu, cảnh báo khi vượt ngưỡng do người dùng đặt, đồng thời sử dụng AI để tổng hợp thông tin và đề xuất hướng phát triển cho doanh nghiệp.

## Cách bắt đầu và đọc thêm

Khi bắt đầu phiên, đọc [bối cảnh hiện tại](.agents/memory/project-context.md) ngay sau tệp này để nắm giai đoạn, việc đã làm và việc tiếp theo. Đây là bản tóm tắt ngắn duy nhất cho ngữ cảnh giữa các phiên. Kiểm tra mã, cấu trúc và trạng thái thay đổi liên quan đến nhiệm vụ trước khi hành động; không ghi đè thay đổi của người khác. Tìm và đọc **phần cần thiết**, không mặc định nạp toàn bộ tài liệu:

- Yêu cầu và tiêu chí nghiệm thu: [SRS](docs/software_requirements_specification.md).
- Thành phần và phương án triển khai: [kiến trúc AWS](docs/architecture_aws.md).
- Demo được quay thành video, do nhóm trưởng tự thực hiện. **Mọi thứ liên quan đến demo nằm trong [demo/](demo/)**: [architecture.md](demo/architecture.md) gồm ý tưởng, kiến trúc, dịch vụ AWS và các lệnh cmd dùng khi quay; sơ đồ phần B là Mermaid đơn giản (khối và mũi tên, cùng cách vẽ với `docs/architecture_aws.md`), chỉ dùng tên hạ tầng web chung, không dùng tên dịch vụ AWS; [demo_guide.md](demo/demo_guide.md) gồm lời thoại phần B, C (phần E cũ chỉ để tham khảo); [thao_tac_tung_buoc.md](demo/thao_tac_tung_buoc.md) là trình tự quay chính thức gồm phần A demo web (nhãn hàng thật NVIDIA và dữ liệu giả KFCC), phần B giới thiệu GitHub/cài đặt theo [README.md](README.md), phần C trình diễn 17 dịch vụ trên AWS Console; script điều khiển dữ liệu giả [demo_control.py](demo/demo_control.py). Đọc trước khi làm việc liên quan demo. Không tạo lại tài liệu demo trong `docs/`.
- Báo cáo BTL: [bao_cao_BTL_cloud_nhom6.pdf](bao_cao_BTL_cloud_nhom6.pdf), xuất từ [report/bao_cao.html](report/bao_cao.html); sửa HTML rồi in lại PDF bằng Playwright (chờ sơ đồ Mermaid vẽ xong).
- Vấn đề kỹ thuật phát hiện được: [developer/](developer/README.md), mỗi vấn đề một tệp `.md` mô tả vấn đề và hướng giải quyết theo mẫu trong README; khi phát hiện vấn đề mới, tạo tệp và thêm vào danh sách.
- Cây thư mục và vai trò các thành phần: [cấu trúc dự án](docs/project_file_structure.md).
- Giai đoạn, phụ thuộc và tiêu chí cần đạt: [lộ trình](docs/development_roadmap.md). Hiện trạng và bàn giao từng giai đoạn: [development-process](docs/development-process/); đọc tệp `s<N>_<ten>.md` tương ứng trước khi làm việc ở giai đoạn đó.
- Kết quả và cách chạy thử Firecrawl: [giai đoạn 2](docs/development-process/s2_firecrawl.md).
- Cách chạy và trạng thái frontend: [frontend/README.md](frontend/README.md); thiết kế giao diện: [frontend/DESIGN.md](frontend/DESIGN.md).
- Backend phát triển, cách chạy và giới hạn: [backend/README.md](backend/README.md).
- Hạ tầng AWS thử nghiệm và cách kiểm tra template: [infrastructure/README.md](infrastructure/README.md).
- Skill phù hợp: [.agents/skills/](.agents/skills/README.md). Chỉ đọc skill khi áp dụng; việc tự tải phụ thuộc công cụ.

## Phối hợp giữa AI và nhóm

- Đây là bài tập nhóm môn Cloud gồm năm người. Người dùng là nhóm trưởng, nắm rõ ý tưởng và đã lập kế hoạch SRS, nhưng có ít thời gian; phần lớn mã hiện do AI tạo. Nhóm trưởng dự định tìm hiểu dự án và bàn giao cho các thành viên khi đến giai đoạn phù hợp.
- Khi được yêu cầu tiếp tục dự án hoặc phần việc của AI, chủ động đối chiếu hiện trạng, lộ trình và bằng chứng, rồi triển khai, sửa lỗi, kiểm thử và hoàn thiện những việc có thể trong phạm vi đã thống nhất. Tự quyết các lựa chọn kỹ thuật thông thường; không dừng ở kế hoạch hay hỏi xác nhận từng bước. Tuân thủ ngân sách, quyền truy cập, chỉ dẫn trực tiếp và các quy định có độ ưu tiên cao hơn.
- AI chuẩn bị kiểm kê và kiểm soát chi phí, môi trường demo, kiểm thử và bằng chứng; đồng thời chuẩn bị tài liệu giải thích kiến trúc, cách chạy, giới hạn, báo cáo, kịch bản demo, câu hỏi bảo vệ và đề xuất phân công để nhóm tiếp nhận. Phân biệt nội dung thật, giả và những việc chưa kiểm chứng.
- AI có nhiệm vụ chủ động làm đến khi hoàn thiện bản demo theo [thư mục demo](demo/): xây dựng, tích hợp, kiểm thử, diễn tập và sửa các phần có thể thực hiện trong phạm vi đã thống nhất; tiếp tục xử lý phụ thuộc thay vì chỉ bàn giao kế hoạch hoặc dừng ở một phần. Khi xong, bàn giao cho người dùng quy trình cụ thể, ngắn gọn để chuẩn bị, vận hành, thuyết trình, xử lý sự cố và kết thúc buổi demo; đối chiếu với [demo/architecture.md](demo/architecture.md) và bằng chứng thực tế. Chỉ dừng phần phụ thuộc khi thực sự thiếu quyền, xác thực, quyết định của nhóm hoặc giới hạn ngân sách; vẫn tiếp tục phần độc lập và nói rõ phần còn chờ, không coi demo đã hoàn thành khi chưa được kiểm chứng.
- Nhóm trưởng quyết định thay đổi phạm vi hoặc yêu cầu, cung cấp quyền hay xác thực cần thiết và phân công thành viên; nhóm thẩm định những kết quả cần đánh giá độc lập của con người, tìm hiểu hệ thống và chịu trách nhiệm khi nộp, trình bày và bảo vệ. AI chuẩn bị bằng chứng và đề xuất cụ thể, chỉ hỏi khi thực sự cần quyết định, quyền hoặc thông tin không thể tự có; tiếp tục các việc độc lập trong lúc chờ.
- Duy trì mục **Việc còn lại của AI và nhóm** trong [bối cảnh hiện tại](.agents/memory/project-context.md): tách ngắn gọn việc AI có thể tiếp tục và việc cần người thực hiện hoặc quyết định, ghi rõ việc nào đang chờ và liên kết chi tiết khi cần. Cuối mỗi phiên rà soát mục này, cập nhật khi có thay đổi và bỏ việc đã xong; nếu không đổi thì giữ nguyên. Không biến mục này thành nhật ký hay lặp toàn bộ tài liệu giai đoạn.

## Duy trì hướng dẫn và tài liệu

- Không tạo tệp mới trực tiếp trong thư mục gốc `docs/` khi chưa hỏi ý kiến người dùng. Hiện trạng, bàn giao và kết quả thử nghiệm theo giai đoạn đặt trong `docs/development-process/`; các tài liệu mới khác cần thống nhất vị trí phù hợp với người dùng.
- Tuân theo các giai đoạn, phụ thuộc và tiêu chí trong [lộ trình](docs/development_roadmap.md); có thể làm song song khi lộ trình cho phép nhưng không bỏ qua điều kiện nghiệm thu. Mỗi giai đoạn phải có một tệp `s<N>_<ten-tieng-anh>.md` trong `docs/development-process/`, với số giai đoạn khớp lộ trình; khi thêm hoặc đổi giai đoạn, cập nhật tệp tương ứng và các liên kết.
- Trước khi làm, đọc hiện trạng giai đoạn liên quan và đối chiếu mã, tài liệu, bằng chứng. Sau thay đổi đáng lưu, cập nhật ngày, trạng thái, kết quả có căn cứ, việc còn lại/phụ thuộc, bước tiếp theo và liên kết minh chứng; không ghi suy đoán thành kết quả. Khi hoàn thành một giai đoạn, vẫn cập nhật và giữ tệp đó để bàn giao, nêu bằng chứng nghiệm thu, giới hạn và việc chuyển tiếp. Không đánh dấu hoàn thành khi chưa đạt tiêu chí hoặc chưa kiểm chứng.
- Khi thao tác, lệnh, tên stack hoặc kiến trúc dùng trong demo thay đổi, cập nhật [demo/architecture.md](demo/architecture.md) ngay; giữ tệp ngắn gọn vì tệp được chiếu trong video. Kết quả kiểm thử và bằng chứng ghi vào tệp giai đoạn tương ứng (thường là S8). Không để tài liệu mô tả chức năng dự kiến như đã hoạt động.
- Khi thay đổi cấu trúc dự án, đường dẫn, tài liệu, skill, memory, công cụ, quy ước hoặc quy trình làm việc có ảnh hưởng đến chỉ dẫn trong `AGENTS.md`, **cập nhật chính tệp này trong cùng thay đổi** để hướng dẫn vẫn đúng. Không cần sửa tệp nếu thay đổi không ảnh hưởng đến nội dung chỉ dẫn.
- Khi tạo, sửa, nâng cấp, xóa hoặc di chuyển thành phần làm thay đổi cấu trúc dự án được mô tả, cập nhật [project_file_structure.md](docs/project_file_structure.md) trong cùng thay đổi để cây và mô tả luôn khớp thực tế.
- Cuối mỗi phiên làm việc, rà soát [project-context.md](.agents/memory/project-context.md); nếu có thay đổi liên quan đến ngữ cảnh cần lưu cho phiên sau, cập nhật bản tóm tắt hiện tại, ngày, căn cứ và bước tiếp theo. Nếu không có thay đổi đáng lưu, giữ nguyên tệp. Không ghi suy đoán là kết quả đã kiểm chứng, không biến tệp thành nhật ký dài; cập nhật trước khi kết thúc lượt nếu không biết khi nào phiên sẽ kết thúc.
- Ví dụ: khi xóa, đổi tên hoặc di chuyển tài liệu được liên kết tại đây, sửa hoặc loại bỏ đường dẫn và cập nhật hướng dẫn đọc tương ứng. Nếu tài liệu thay thế chưa có, ghi rõ thay vì trỏ đến tệp không tồn tại.
- Khi yêu cầu, thiết kế hoặc hành vi thay đổi, cập nhật SRS, kiến trúc, lộ trình và memory liên quan theo phạm vi thay đổi; tài liệu chính trong `docs/` là nguồn tham chiếu, memory chỉ tóm tắt.
- Trước khi hoàn tất thay đổi liên quan đến tài liệu hoặc quy trình AI, kiểm tra các đường dẫn đã sửa và sự nhất quán giữa hướng dẫn với trạng thái thực tế. Tôn trọng chỉ dẫn trực tiếp của người dùng và quy định có độ ưu tiên cao hơn.

## Nguyên tắc làm việc

- Đây là dự án học tập dùng AWS. Kiến trúc và công nghệ cụ thể trong tài liệu là đề xuất, trừ khi được ghi rõ là quyết định đã thống nhất.
- Phân biệt yêu cầu đã thống nhất với giả định và nội dung chờ nhóm quyết định. Không khẳng định một chức năng đã hoạt động khi chưa có mã và kiểm chứng.
- Ưu tiên một phiên bản khả thi: cấu hình nhãn hàng và từ khóa, thu thập từ ít nhất một nguồn khả thi, xem dữ liệu và phân tích, đặt cảnh báo, nhận tóm tắt và đề xuất AI.
- Dùng Firecrawl để tìm kiếm và thu thập, không gọi trực tiếp API mạng xã hội. Thiết kế adapter tách biệt; chỉ thu thập dữ liệu được phép truy cập và không giả định có thể lấy bình luận hoặc chỉ số từ mọi nền tảng.
- Xử lý dữ liệu cá nhân và bí mật cẩn trọng: chỉ thu thập và lưu dữ liệu cần thiết; không đưa khóa API, mật khẩu hoặc token vào mã nguồn hay log.
- AI có thể sai hoặc thiên lệch: thể hiện đề xuất là tham khảo, gắn với dữ liệu và khoảng thời gian đầu vào khi có thể; không tự động thực hiện quyết định kinh doanh.
- Ưu tiên thay đổi nhỏ, dễ kiểm thử; đọc cấu trúc và quy ước hiện có trước khi thêm công nghệ hoặc phụ thuộc. Viết hướng dẫn chạy và cấu hình khi triển khai.
- Trao đổi và viết tài liệu bằng tiếng Việt, trừ khi ngữ cảnh hoặc yêu cầu cụ thể cần ngôn ngữ khác.
