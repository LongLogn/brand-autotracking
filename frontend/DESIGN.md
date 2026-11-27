# Thiết kế giao diện — Brand Auto-Tracking

Ghi chú thiết kế theo skill `frontend-design` (`.agents/skills/frontend-design/SKILL.md`).

## Brief

- **Chủ đề:** theo dõi những gì mạng xã hội nói về một nhãn hàng (ví dụ chuỗi gà rán), cảnh báo khi nội dung tiêu cực tăng, AI tổng hợp và gợi ý.
- **Người dùng:** chủ doanh nghiệp nhỏ hoặc nhân viên marketing người Việt, không cần biết kỹ thuật.
- **Việc chính của giao diện:** trả lời nhanh ba câu: người ta đang nói gì, tiêu cực có đang tăng không, và dữ liệu này đủ tin đến đâu.

## Ý tưởng riêng cho đề bài này

SRS nhấn mạnh nhiều lần rằng dữ liệu có thể thiếu: trường "không khả dụng" khác với 0, phiên "thành công một phần", lượt rỗng khác lượt lỗi, cảnh báo không tính khi độ bao phủ không so sánh được, AI phải nêu phạm vi và dẫn chứng.

Vì vậy điểm nhấn duy nhất của giao diện là **ngôn ngữ hình ảnh của độ bao phủ**: mọi chỗ thiếu dữ liệu được vẽ bằng **vân gạch chéo** (hatch), nhất quán từ ô số liệu, cột biểu đồ, dải phiên tracking cho tới phạm vi phân tích AI. Người dùng học một lần là đọc được ở mọi màn hình. Phần còn lại giữ yên tĩnh.

## Token

| Tên | Hex | Vai trò |
|---|---|---|
| Giấy | `#F2F4F1` | Nền trang, xám hơi ngả lục |
| Mặt | `#FFFFFF` | Vùng nội dung chính |
| Mực | `#1A2E2A` | Chữ và cấu trúc, xanh thông đậm |
| Lam thao tác | `#2448B8` | Nút, liên kết, trạng thái chọn |
| Ớt | `#C8382F` | Tiêu cực, lỗi, cảnh báo |
| Lá | `#2F7D52` | Tích cực, thành công có dữ liệu |
| Sương | `#C5CCC6` | Vân gạch "không khả dụng", viền |

Trung lập dùng xám `#8C968F`. Màu cảm xúc chỉ dùng cho cảm xúc và trạng thái, không trang trí.

**Chữ:** một họ duy nhất, *Be Vietnam Pro*, được thiết kế cho dấu tiếng Việt. Thang chữ 13 / 15 / 18 / 24 / 34. Số dùng `tabular-nums`. Nhãn viết hoa đầu câu, không viết hoa toàn bộ.

**Bố cục:** thanh trái cố định là danh sách nhãn hàng (đối tượng chính của hệ thống). Mỗi nhãn hàng có các tab: Tổng quan, Nội dung, Phiên tracking, Cảnh báo, Phân tích AI, Cấu hình. Nội dung căn trái, dòng chữ dưới 80 ký tự. Các khu vực phân bằng khoảng trắng và dải nền, không băm thành các thẻ giống hệt nhau. Bo góc theo cấp: ô nhập 6px, vùng lớn 10px, ô dữ liệu nhỏ 2px.

```
┌────────────┬──────────────────────────────────────────────┐
│ Nhãn hàng  │ Gà rán ABC        Đang theo dõi · [Tạm dừng] │
│ ● Gà rán   │ Tổng quan  Nội dung  Phiên  Cảnh báo  AI  ⚙  │
│ ○ Trà sữa  ├──────────────────────────────────────────────┤
│ ○ Bún bò   │ 15 bình luận tiêu cực trong 7 ngày gần nhất, │
│            │ tăng 50% so với 7 ngày trước đó.             │
│ + Thêm     │ ▮▮▯▮▮▮▮ │ ▮▮▮▮▨▮▮   (vân gạch = thiếu)         │
│            │ Dải bao phủ: nền tảng × ngày                 │
└────────────┴──────────────────────────────────────────────┘
```

## Rà soát so với lối mặc định

- Bản nháp đầu dùng nền trắng, màu lam tím và các thẻ số liệu bo tròn có bóng. Đó là bộ thẻ SaaS mặc định, nên đã đổi sang nền giấy ngả lục, chữ xanh thông và bỏ bóng thẻ.
- Không dùng nhãn nhỏ viết hoa trên tiêu đề, chuỗi nối bằng dấu chấm giữa, font monospace cho số liệu, hay mũi tên sau liên kết.
- Phần mở đầu của Tổng quan là một câu tiếng Việt nói thẳng tình hình, kèm biểu đồ có phạm vi so sánh, không phải ô "số to, nhãn nhỏ".
- Chuyển động chỉ dùng khi người dùng thao tác (mở bình luận, lưu, chạy phân tích) và tôn trọng `prefers-reduced-motion`.

## Bản 2 — sửa theo nhận xét giao diện của nhóm trưởng

Nhận xét: nhiều chữ, quá đơn điệu, nội dung không phủ hết chiều ngang. Giữ nguyên thanh nhãn hàng bên trái và hàng tab.

- **Full màn hình:** bỏ mọi `max-width`. Tổng quan là lưới 3 cột (2 cột ≤1280px, 1 cột ≤860px). Nội dung và Phân tích AI có cột phụ bên trái; Cảnh báo và Cấu hình chia hai cột.
- **Ít chữ:** đoạn giải thích chuyển vào biểu tượng ⓘ (tooltip). Ghi chú dữ liệu mẫu thành một nhãn nhỏ ở đầu trang. Nội dung bài cắt còn 2 dòng.
- **Trực quan hơn:** biểu tượng (lucide-react), avatar chữ cái cho nhãn hàng, ô chỉ số kèm sparkline và % thay đổi, biểu đồ tròn cảm xúc, thanh theo nền tảng, thanh lượt chạy trong bảng phiên, ma trận nền tảng × từ khóa, dòng thời gian cảnh báo với ô "kỳ trước → kỳ này".
- **Giữ:** bảng màu, font Be Vietnam Pro, và vân gạch cho dữ liệu không khả dụng.
- **Đánh đổi có chủ ý:** ô "số to, nhãn nhỏ" là lối mặc định mà skill cảnh báo, nhưng nhận xét ưu tiên quét nhanh hơn đọc câu, nên được dùng. Ô có màu theo ý nghĩa, không trang trí.

## Bản 3 — giao diện kết nối backend (27/11)

Bản 2 chỉ áp dụng cho màn hình mẫu (`VITE_DEMO_MODE=true`). Giao diện dùng thật khi demo (`ApiApp.tsx`) vẫn là một trang dài, xếp chồng các biểu mẫu, nút và đoạn giải thích. Bản 3 đưa cùng ngôn ngữ thiết kế vào giao diện này, giữ nguyên logic gọi API.

- **Bố cục:** dùng lại thanh nhãn hàng màu mực bên trái và hàng tab của bản 2. Thứ tự tab theo kịch bản demo: Tổng quan, Cảnh báo, Phân tích AI, Nội dung, Phiên tracking, Cấu hình. Khi chưa chọn nhãn hàng, trang chính là biểu mẫu tạo nhãn hàng kèm ba bước sử dụng.
- **Điểm nhấn:** biểu đồ cột tỷ lệ bình luận tiêu cực theo từng lần thu thập. Cột mốc màu mực, cột có cảnh báo màu ớt, phần chưa phân loại vẽ bằng vân gạch như mọi dữ liệu thiếu khác. Khi có cảnh báo, khung đỏ ghi "20% → 30%" bằng chữ lớn. Màn hình đăng nhập lặp lại hình ảnh cột này.
- **Ít chữ:** giải thích phạm vi và giới hạn chuyển vào ⓘ. Trạng thái phiên, lượt thu thập và cảm xúc hiển thị bằng nhãn màu; số liệu không khả dụng vẫn dùng vân gạch.
- **Bố cục từng tab:** Phân tích AI, Nội dung và Phiên tracking có cột thao tác bên trái, kết quả bên phải. Mỗi nhận định AI là một thẻ đánh số, kèm gợi ý và mã dẫn chứng. Bài viết là lưới thẻ, viền trên mang màu cảm xúc.
- **Trang chào và đăng nhập (sửa theo góp ý "xấu, Cognito là gì"):** logo là bong bóng bình luận màu xanh thông có đường nhịp tín hiệu, đặt trên nền bạc hà, kèm chấm đỏ thông báo (bản ba cột tín hiệu trước đó bị chê xấu nên đã thay). Thương hiệu trong hình minh họa là "KFCC", một chuỗi gà rán hư cấu; chân trang ghi rõ là minh họa. Trang chào nền sáng, tiêu đề lớn "Nghe thấy lời phàn nàn trước khi nó lan rộng.". Bên phải là ảnh sản phẩm dựng bằng HTML: biểu đồ KFCC có cột vượt ngưỡng, bình luận về gà rán đi vào, email cảnh báo và tóm tắt AI. Đây là hiệu ứng duy nhất khi tải trang và tôn trọng `prefers-reduced-motion`. Nút gọi là "Đăng nhập", không nhắc Cognito. Trang đăng nhập Cognito dùng nền xanh thông có cột tín hiệu, form trắng bo 16px và nút màu lam thao tác.
- **Ràng buộc:** giữ tên nút, nhãn ô nhập, `role` và các câu thông báo mà kiểm thử trình duyệt và kịch bản thuyết trình dựa vào. CSS riêng đặt trong `src/workspace/workspace.css` với tiền tố `ws-`.
