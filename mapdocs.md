# Bản đồ tài liệu

Nơi tra cứu nhanh **tài liệu nào chứa nội dung gì**, giúp người và AI ở phiên mới tìm đúng chỗ cần đọc. Chỉ đọc phần liên quan đến việc đang làm, không cần đọc hết.

Khi thêm, đổi tên, di chuyển hoặc xóa tài liệu, cập nhật bảng tương ứng ở đây trong cùng thay đổi.

## Bắt đầu phiên

| Đọc khi | Tài liệu | Nội dung |
|---|---|---|
| Luôn đọc đầu tiên | [AGENTS.md](AGENTS.md) | Quy tắc điều phối cho AI: phạm vi sửa, cách làm việc, cách cập nhật tài liệu |
| Luôn đọc | [.agents/memory/project-context.md](.agents/memory/project-context.md) | Hiện trạng ngắn gọn, việc đã làm, việc còn lại của AI và nhóm |
| Luôn đọc | [CONTRIBUTING.md](CONTRIBUTING.md) | Cách đặt tên nhánh, làm issue, tạo pull request, phân vùng việc giữa các thành viên |
| Muốn hiểu dự án tổng quát | [README.md](README.md) | Giới thiệu, kiến trúc, cài đặt và triển khai |

## Yêu cầu, kiến trúc, kế hoạch

| Đọc khi | Tài liệu | Nội dung |
|---|---|---|
| Cần biết chức năng phải làm, tiêu chí nghiệm thu | [docs/software_requirements_specification.md](docs/software_requirements_specification.md) | SRS |
| Cần biết thành phần và dịch vụ AWS | [docs/architecture_aws.md](docs/architecture_aws.md) | Kiến trúc AWS, sơ đồ Mermaid |
| Cần biết giai đoạn, phụ thuộc, tiêu chí | [docs/development_roadmap.md](docs/development_roadmap.md) | Lộ trình S0–S8 |
| Cần tìm tệp mã hoặc vai trò thư mục | [docs/project_file_structure.md](docs/project_file_structure.md) | Cây thư mục và mô tả từng thành phần |

## Hiện trạng theo giai đoạn

Mỗi giai đoạn có một tệp trong [docs/development-process/](docs/development-process/), ghi kết quả có bằng chứng, giới hạn và việc còn lại. Đọc tệp của giai đoạn trước khi sửa phần đó.

| Giai đoạn | Tài liệu | Phạm vi |
|---|---|---|
| S0 | [s0_preparation.md](docs/development-process/s0_preparation.md) | Chuẩn bị, ngân sách, tài khoản |
| S1 | [s1_frontend.md](docs/development-process/s1_frontend.md) | Giao diện |
| S2 | [s2_firecrawl.md](docs/development-process/s2_firecrawl.md) | Firecrawl, credit, điều khoản nguồn |
| S3 | [s3_backend.md](docs/development-process/s3_backend.md) | Backend, database |
| S4 | [s4_accounts_brands.md](docs/development-process/s4_accounts_brands.md) | Tài khoản Cognito, nhãn hàng |
| S5 | [s5_tracking.md](docs/development-process/s5_tracking.md) | Thu thập, lịch, hàng đợi SQS, worker |
| S6 | [s6_sentiment_alerts.md](docs/development-process/s6_sentiment_alerts.md) | Phân loại cảm xúc, cảnh báo, email |
| S7 | [s7_ai_analysis.md](docs/development-process/s7_ai_analysis.md) | Phân tích và đề xuất AI (Bedrock) |
| S8 | [s8_aws_delivery.md](docs/development-process/s8_aws_delivery.md) | Triển khai AWS, kiểm thử đầu cuối, dọn tài nguyên |
| Bằng chứng | [docs/development-process/evidence/](docs/development-process/evidence/) | Ảnh, video kiểm thử |

## Vấn đề kỹ thuật

| Đọc khi | Tài liệu | Nội dung |
|---|---|---|
| Gặp lỗi, giới hạn, hành vi lạ | [developer/README.md](developer/README.md) | Danh sách vấn đề đã phát hiện, mỗi vấn đề một tệp mô tả vấn đề và hướng giải quyết |

## Mã nguồn theo phần

| Phần | Hướng dẫn | Mã chính |
|---|---|---|
| Backend (API, worker, database) | [backend/README.md](backend/README.md) | `backend/app/`, migration `backend/migrations/versions/`, kiểm thử `backend/tests/` |
| Thu thập Firecrawl/TikTok | [S2](docs/development-process/s2_firecrawl.md), [S5](docs/development-process/s5_tracking.md) | `firecrawl.py`, `adapters/tiktok.py`, `tracking.py`, `scheduler.py`, `lambda_worker.py` |
| Cảm xúc, cảnh báo | [S6](docs/development-process/s6_sentiment_alerts.md) | `sentiment.py`, `alert_rules.py`, `alert_evaluation.py`, `demo_alerts.py` |
| Phân tích AI | [S7](docs/development-process/s7_ai_analysis.md) | `analysis.py`, `analysis_queue.py` |
| Frontend | [frontend/README.md](frontend/README.md), [frontend/DESIGN.md](frontend/DESIGN.md) | `frontend/src/` (`ApiApp.tsx`, `workspace/`, `lib/api.ts`) |
| Hạ tầng AWS | [infrastructure/README.md](infrastructure/README.md) | Template CloudFormation `infrastructure/*.yaml` |
| Công cụ | — | `scripts/package_lambda.py` (đóng gói backend), probe Firecrawl |

## Demo, báo cáo, môn học

| Đọc khi | Tài liệu | Nội dung |
|---|---|---|
| Làm gì liên quan demo | [demo/architecture.md](demo/architecture.md) | Ý tưởng, kiến trúc, dịch vụ AWS, lệnh cmd khi quay (chiếu trong video, giữ ngắn) |
| Quay video | [demo/thao_tac_tung_buoc.md](demo/thao_tac_tung_buoc.md) | Trình tự quay chính thức phần A, B, C |
| Lời thoại | [demo/demo_guide.md](demo/demo_guide.md) | Lời thoại phần B, C |
| Điều khiển dữ liệu giả | [demo/demo_control.py](demo/demo_control.py) | Script dữ liệu giả KFCC |
| Sửa báo cáo | [report/bao_cao.html](report/bao_cao.html) | Nguồn báo cáo; in lại [PDF](bao_cao_BTL_cloud_nhom6.pdf) bằng Playwright |
| Tiêu chí chấm, lịch môn | [UET_score_criterias/](UET_score_criterias/) | Tiêu chí và ghi chú giảng viên |

## Hướng dẫn cho AI

| Đọc khi | Tài liệu | Nội dung |
|---|---|---|
| Cần skill chuyên biệt | [.agents/skills/README.md](.agents/skills/README.md) | Review, thiết kế giao diện |
| Cập nhật memory | [.agents/memory/README.md](.agents/memory/README.md) | Cách duy trì bối cảnh giữa các phiên |
