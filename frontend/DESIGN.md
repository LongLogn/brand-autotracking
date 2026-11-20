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

## Bản 2 — sửa theo nhận xét (`web_ui_comment.txt`)

Nhận xét: nhiều chữ, quá đơn điệu, nội dung không phủ hết chiều ngang. Giữ nguyên thanh nhãn hàng bên trái và hàng tab.

- **Full màn hình:** bỏ mọi `max-width`. Tổng quan là lưới 3 cột (2 cột ≤1280px, 1 cột ≤860px). Nội dung và Phân tích AI có cột phụ bên trái; Cảnh báo và Cấu hình chia hai cột.
- **Ít chữ:** đoạn giải thích chuyển vào biểu tượng ⓘ (tooltip). Ghi chú dữ liệu mẫu thành một nhãn nhỏ ở đầu trang. Nội dung bài cắt còn 2 dòng.
- **Trực quan hơn:** biểu tượng (lucide-react), avatar chữ cái cho nhãn hàng, ô chỉ số kèm sparkline và % thay đổi, biểu đồ tròn cảm xúc, thanh theo nền tảng, thanh lượt chạy trong bảng phiên, ma trận nền tảng × từ khóa, dòng thời gian cảnh báo với ô "kỳ trước → kỳ này".
- **Giữ:** bảng màu, font Be Vietnam Pro, và vân gạch cho dữ liệu không khả dụng.
- **Đánh đổi có chủ ý:** ô "số to, nhãn nhỏ" là lối mặc định mà skill cảnh báo, nhưng nhận xét ưu tiên quét nhanh hơn đọc câu, nên được dùng. Ô có màu theo ý nghĩa, không trang trí.
