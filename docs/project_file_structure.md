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
│   │   ├── auth.py                       # Xác thực token Cognito
│   │   ├── config.py                     # Kiểm tra cấu hình CORS
│   │   ├── database.py                   # Kết nối database
│   │   ├── firecrawl.py                  # Client Firecrawl cho TikTok
│   │   ├── lambda_entry.py               # Điểm vào Lambda và migration
│   │   ├── lambda_worker.py              # Worker Lambda nhận phiên đã xếp
│   │   ├── main.py                       # API FastAPI
│   │   ├── models.py                     # Mô hình bảng database
│   │   ├── outbox.py                     # Phát sự kiện tracking sang SQS có giới hạn thử lại
│   │   ├── run_tracking.py               # Chạy một phiên tracking
│   │   ├── scheduler.py                  # Xếp phiên theo lịch và khóa nhãn hàng
│   │   ├── tracking.py                   # Điều phối và lưu kết quả tracking
│   │   └── worker.py                     # Nhận và xử lý phiên chờ
│   ├── migrations/                       # Cấu hình và các phiên bản schema
│   │   └── versions/                     # Migration PostgreSQL, gồm credit, outbox và lease
│   ├── tests/                            # Kiểm thử backend và trình duyệt
│   ├── alembic.ini                       # Cấu hình Alembic
│   ├── compose.yaml                      # PostgreSQL phát triển cục bộ
│   ├── requirements*.txt                # Phụ thuộc chạy và kiểm thử Python
│   └── README.md                         # Hướng dẫn và giới hạn backend
├── docs/                                 # Tài liệu dự án
│   ├── development-process/              # Hiện trạng và bàn giao từng giai đoạn
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
│   │   ├── ApiApp.tsx                    # Giao diện kết nối backend
│   │   ├── App.tsx                       # Router giao diện minh họa
│   │   ├── main.tsx                      # Điểm vào và chọn chế độ giao diện
│   │   └── styles.css                    # Kiểu trình bày chung
│   ├── tests/                            # Kiểm thử frontend và trình duyệt
│   ├── DESIGN.md                         # Thiết kế giao diện
│   ├── index.html                        # Trang HTML gốc
│   ├── package.json                      # Phụ thuộc và lệnh frontend
│   ├── package-lock.json                 # Phiên bản phụ thuộc đã khóa
│   ├── tsconfig.json                     # Cấu hình TypeScript
│   ├── vite.config.ts                    # Cấu hình Vite
│   └── README.md                         # Hướng dẫn chạy frontend
├── infrastructure/                       # Template hạ tầng AWS thử nghiệm
│   ├── aws-dev-api.yaml                  # Lambda, API Gateway và giám sát thử
│   ├── aws-dev-data.yaml                 # Mạng và PostgreSQL thử
│   ├── cognito.yaml                      # Cognito phát triển
│   └── README.md                         # Hướng dẫn hạ tầng
├── scripts/                              # Công cụ thử Firecrawl và provider
│   ├── firecrawl_probe.py                # Thử Search và Scrape
│   ├── package_lambda.py                 # Đóng gói backend cho Lambda thử
│   ├── tiktok_provider_probe.py          # Thử provider TikTok
│   └── test_tiktok_provider_probe.py     # Kiểm thử chương trình provider
├── UET_score_criterias/                  # Tài liệu và ảnh tiêu chí môn học
├── .gitignore                            # Quy tắc bỏ qua tệp Git
├── AGENTS.md                             # Chỉ dẫn làm việc cho AI
├── dontRead.txt                          # Tệp cục bộ, không khảo sát nội dung
├── LICENSE                               # Giấy phép dự án
├── README.md                             # Giới thiệu kho dự án
├── thlong_notes.md                       # Ghi chú dự án
└── web_ui_comment.txt                    # Nhận xét giao diện
```

`frontend/` gọi API trong `backend/`; backend xác thực qua Cognito, lưu dữ liệu vào PostgreSQL và dùng Firecrawl để thu thập. `infrastructure/` mô tả các thành phần AWS thử nghiệm, `scripts/` hỗ trợ kiểm chứng nguồn, còn `docs/` và `.agents/` lưu tài liệu cùng ngữ cảnh làm việc. Cây rút gọn các tệp kiểm thử, migration, khởi tạo và skill; không liệt kê tệp sinh tự động, môi trường ảo và thư viện cài đặt.
