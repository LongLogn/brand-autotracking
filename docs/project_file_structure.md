```text
brand-autotracking/
├── .agents/                              # Hướng dẫn và ngữ cảnh cho AI
│   ├── README.md                         # Giới thiệu thư mục .agents
│   ├── memory/                           # Ngữ cảnh giữa các phiên
│   │   ├── project-context.md            # Hiện trạng và bước tiếp theo
│   │   └── README.md                     # Hướng dẫn duy trì memory
│   └── skills/                           # Các hướng dẫn chuyên biệt
│       ├── README.md                     # Cách dùng và quản lý skill
│       ├── bmad-review/                  # Quy trình và công cụ review
│       └── frontend-design/              # Hướng dẫn thiết kế giao diện
├── backend/                              # API, xử lý tracking và database
│   ├── app/                              # Mã ứng dụng backend
│   │   ├── adapters/                     # Chuẩn hóa dữ liệu từng nguồn
│   │   │   └── tiktok.py                 # Chuẩn hóa bài và bình luận TikTok
│   │   ├── alert_rules.py                # Tính ngưỡng cảnh báo độc lập
│   │   ├── alert_evaluation.py           # Kiểm tra bằng chứng và lưu cảnh báo
│   │   ├── analysis.py                   # Chọn dữ liệu và kiểm chứng dẫn chứng phân tích AI
│   │   ├── auth.py                       # Xác thực token Cognito
│   │   ├── config.py                     # Kiểm tra cấu hình CORS
│   │   ├── database.py                   # Kết nối database
│   │   ├── demo_stream.py                # Kịch bản dữ liệu giả (mốc/tiêu cực/tích cực) và CLI cục bộ
│   │   ├── demo_scheduler.py             # Xếp các đợt demo hữu hạn cho worker AWS
│   │   ├── demo_history.py               # Lịch sử giả 10→15 cũ, giữ làm dự phòng
│   │   ├── demo_alerts.py                # Nhãn giả lập, cảnh báo theo lần thu thập và email SES
│   │   ├── evaluate_sentiment.py         # Đánh giá tập nhãn với giới hạn Bedrock
│   │   ├── firecrawl.py                  # Client Firecrawl cho TikTok
│   │   ├── lambda_entry.py               # Điểm vào Lambda và migration
│   │   ├── lambda_worker.py              # Worker Lambda nhận phiên đã xếp
│   │   ├── main.py                       # API FastAPI
│   │   ├── models.py                     # Mô hình bảng database
│   │   ├── outbox.py                     # Phát sự kiện tracking sang SQS có giới hạn thử lại
│   │   ├── run_tracking.py               # Chạy một phiên tracking
│   │   ├── scheduler.py                  # Xếp phiên theo lịch và khóa nhãn hàng
│   │   ├── server.py                     # Entrypoint uvicorn cho EC2 sau ALB/CloudFront
│   │   ├── sentiment.py                  # Adapter phân loại và lưu kết quả theo phiên bản nội dung
│   │   ├── tracking.py                   # Điều phối và lưu kết quả tracking
│   │   └── worker.py                     # Nhận và xử lý phiên chờ
│   ├── migrations/                       # Cấu hình và các phiên bản schema
│   │   └── versions/                     # Migration PostgreSQL, gồm theo dõi, cảm xúc và lịch sử cảnh báo
│   ├── tests/                            # Kiểm thử backend và trình duyệt
│   │   ├── aws_analysis_fixture.py       # Nạp dữ liệu giả có bảo vệ vào AWS thử
│   │   ├── aws_demo_brand.py             # Tạo thương hiệu thử qua Cognito/API AWS
│   │   ├── aws_queue_fixture.py          # Tạo lịch và lease thử trên AWS riêng
│   │   ├── aws_queue_e2e.py              # Kiểm thử SQS, lịch và phục hồi trên stack thử
│   │   ├── test_demo_stream.py           # Kiểm thử bộ sinh và giới hạn database demo
│   │   ├── test_demo_alerts.py           # Kiểm thử kịch bản theo phút, cảnh báo tỷ lệ và email
│   │   └── fixtures/                     # Tập đánh giá giả và báo cáo theo ID
│   ├── alembic.ini                       # Cấu hình Alembic
│   ├── compose.yaml                      # PostgreSQL phát triển cục bộ
│   ├── requirements*.txt                # Phụ thuộc chạy và kiểm thử Python
│   └── README.md                         # Hướng dẫn và giới hạn backend
├── demo/                                 # Mọi thứ phục vụ quay video demo
│   ├── architecture.md                   # Ý tưởng, kiến trúc, dịch vụ AWS và lệnh cmd khi quay
│   ├── thao_tac_tung_buoc.md             # Thao tác chi tiết: tài khoản, nhãn hàng KFCC, lệnh mô phỏng, sự cố
│   ├── demo_guide.md                     # Lời thoại phần B, C và trình tự demo dịch vụ AWS (phần E)
│   └── demo_control.py                   # Bật, bắn đợt tiếp theo và dừng dòng dữ liệu giả trên AWS
├── docs/                                 # Tài liệu dự án
│   ├── development-process/              # Hiện trạng và bàn giao từng giai đoạn
│   │   ├── evidence/                     # Bản dự phòng đã gắn nhãn dữ liệu giả
│   │   │   ├── demo-core-20261126.mp4    # Video rút gọn luồng đăng ký, dữ liệu và cảnh báo
│   │   │   ├── demo-ai-20261126.png      # Ảnh kết quả AI với dữ liệu giả đã lưu
│   │   │   └── demo-minute-aws-20261127.webm # Video diễn tập kịch bản theo phút trên AWS
│   │   ├── s0_preparation.md             # Chuẩn bị môi trường
│   │   ├── s1_frontend.md                # Giao diện
│   │   ├── s2_firecrawl.md               # Kiểm chứng Firecrawl
│   │   ├── s3_backend.md                 # Backend và cơ sở dữ liệu
│   │   ├── s4_accounts_brands.md         # Tài khoản và nhãn hàng
│   │   ├── s5_tracking.md                # Tracking và dữ liệu
│   │   ├── s6_sentiment_alerts.md        # Cảm xúc và cảnh báo
│   │   ├── s7_ai_analysis.md             # Phân tích AI
│   │   └── s8_aws_delivery.md            # AWS và nghiệm thu
│   ├── architecture_aws.md               # Kiến trúc AWS dự kiến
│   ├── development_roadmap.md            # Lộ trình và điều kiện hoàn thành
│   ├── project_file_structure.md         # Cây cấu trúc và quan hệ thư mục
│   └── software_requirements_specification.md # Yêu cầu hệ thống
├── frontend/                             # Ứng dụng giao diện React
│   ├── src/                              # Mã nguồn giao diện
│   │   ├── components/                   # Các thành phần dùng chung
│   │   ├── data/                         # Kiểu dữ liệu và dữ liệu mẫu
│   │   ├── lib/                          # API, Cognito và xử lý trạng thái
│   │   ├── pages/                        # Các màn hình minh họa
│   │   ├── workspace/                    # Trang chào (Landing), các tab của giao diện kết nối backend và CSS
│   │   ├── ApiApp.tsx                    # Giao diện kết nối backend: đăng nhập, thanh nhãn hàng, tab
│   │   ├── App.tsx                       # Router giao diện minh họa
│   │   ├── main.tsx                      # Điểm vào và chọn chế độ giao diện
│   │   └── styles.css                    # Kiểu trình bày chung
│   ├── public/                           # favicon.svg (logo bong bóng bình luận có nhịp tín hiệu)
│   ├── tests/                            # Kiểm thử frontend và trình duyệt, gồm demo-minute-browser.cjs (cục bộ) và aws-demo-minute.cjs (AWS)
│   ├── DESIGN.md                         # Thiết kế giao diện
│   ├── index.html                        # Trang HTML gốc
│   ├── package.json                      # Phụ thuộc và lệnh frontend
│   ├── package-lock.json                 # Phiên bản phụ thuộc đã khóa
│   ├── tsconfig.json                     # Cấu hình TypeScript
│   ├── vite.config.ts                    # Cấu hình Vite
│   └── README.md                         # Hướng dẫn chạy frontend
├── infrastructure/                       # Template hạ tầng AWS thử nghiệm
│   ├── aws-dev-api.yaml                  # Worker Lambda, SQS, SNS email cảnh báo; API Gateway tùy chọn
│   ├── aws-dev-data.yaml                 # Mạng và PostgreSQL thử
│   ├── aws-demo-data.yaml                # Mạng và PostgreSQL demo có chính sách backup/snapshot
│   ├── aws-demo-frontend.yaml            # S3 riêng tư, CloudFront và đường /api/* tới ALB
│   ├── aws-demo-ec2-api.yaml             # API FastAPI trên EC2, Auto Scaling Group và ALB
│   ├── cognito.yaml                      # Cognito phát triển
│   ├── cognito-branding/                 # Logo, nền và script áp giao diện cho trang đăng nhập Cognito
│   ├── cognito-demo.yaml                 # Cognito demo cô lập, giả lập xác minh email
│   └── README.md                         # Hướng dẫn hạ tầng
├── report/                               # Mã nguồn báo cáo BTL: bao_cao.html và images/ (ảnh giao diện KFCC)
├── scripts/                              # Công cụ thử Firecrawl và provider
│   ├── firecrawl_probe.py                # Thử Search và Scrape
│   ├── package_lambda.py                 # Đóng gói backend cho Lambda thử
│   ├── tiktok_provider_probe.py          # Thử provider TikTok
│   └── test_tiktok_provider_probe.py     # Kiểm thử chương trình provider
├── UET_score_criterias/                  # Tài liệu và ảnh tiêu chí môn học
├── .gitignore                            # Quy tắc bỏ qua tệp Git
├── bao_cao_BTL_cloud_nhom6.pdf         # Báo cáo BTL xuất từ report/bao_cao.html (Playwright, A4)
├── AGENTS.md                             # Chỉ dẫn làm việc cho AI
├── dontRead.txt                          # Tệp cục bộ, không khảo sát nội dung
├── LICENSE                               # Giấy phép dự án
├── README.md                             # Giới thiệu kho dự án
├── thlong_notes.md                       # Ghi chú dự án
└── web_ui_comment.txt                    # Nhận xét giao diện
```

`frontend/` gọi API trong `backend/`; backend xác thực qua Cognito, lưu dữ liệu vào PostgreSQL và dùng Firecrawl để thu thập. `infrastructure/` mô tả các thành phần AWS thử nghiệm, `scripts/` hỗ trợ kiểm chứng nguồn, còn `docs/` và `.agents/` lưu tài liệu cùng ngữ cảnh làm việc. Cây rút gọn các tệp kiểm thử, migration, khởi tạo và skill; không liệt kê tệp sinh tự động, môi trường ảo và thư viện cài đặt.
