# Hướng dẫn làm việc nhóm

Tài liệu cho cả năm thành viên và các phiên AI khi sửa dự án. Nguyên tắc chính: **mỗi issue một nhánh, mỗi nhánh chỉ sửa đúng phần của issue đó**, gộp vào `main` qua pull request.

## Thành viên và tên viết tắt

| Viết tắt | Thành viên |
|---|---|
| TL | Trần Long (nhóm trưởng) |
| NL | Nguyễn Long |
| K | Khoa |
| N | Nam |
| H | Huy |

## Quy trình một việc

1. **Tạo issue trên GitHub** mô tả việc cần làm: vấn đề, phần bị ảnh hưởng (frontend, backend, hạ tầng, tài liệu…), tiêu chí hoàn thành. Gán cho người làm.
2. **Tạo nhánh từ `main` mới nhất:**
   ```
   git checkout main
   git pull
   git checkout -b TL-frontend-cai-thien-dang-nhap
   ```
3. **Làm và commit** trên nhánh đó. Chỉ sửa các tệp thuộc phạm vi issue (xem mục Phạm vi sửa).
4. **Chạy kiểm thử** của phần đã sửa (mục Kiểm thử).
5. **Push và tạo pull request** vào `main` (mục Pull request).
6. **Nhờ ít nhất một thành viên khác review**, sửa theo góp ý, rồi merge.
7. **Xóa nhánh** sau khi merge; quay về `main` và `git pull` trước khi bắt đầu việc tiếp theo.

## Đặt tên nhánh

Dạng: `<viết tắt>-<phần>-<nội dung>`

- Viết tắt tên người làm, in hoa: `TL`, `NL`, `K`, `N`, `H`.
- Phần: `frontend`, `backend`, `infra`, `docs`, `demo`, `report`…
- Nội dung ngắn gọn, **tiếng Việt không dấu**, các từ nối bằng dấu gạch ngang. Git không cho dấu cách trong tên nhánh.

| Ý định | Tên nhánh |
|---|---|
| TL - frontend cải thiện đăng nhập | `TL-frontend-cai-thien-dang-nhap` |
| K - backend sửa lỗi lịch thu thập | `K-backend-sua-loi-lich-thu-thap` |
| H - docs cập nhật báo cáo | `H-docs-cap-nhat-bao-cao` |

Một nhánh chỉ cho một issue. Việc khác thì tạo nhánh khác, kể cả khi nhỏ.

## Commit

- Mỗi commit một thay đổi có nghĩa, mô tả bằng tiếng Việt, mở đầu bằng loại: `feat:` (tính năng), `fix:` (sửa lỗi), `docs:` (tài liệu), `test:` (kiểm thử), `refactor:` (sắp xếp lại mã, không đổi hành vi), `chore:` (việc vặt). Ví dụ: `fix: worker không treo khi thiếu secret Firecrawl`.
- Ghi số issue nếu có: `fix: ... (#12)`.
- **Không commit** khóa API, mật khẩu, token, tệp `.env`, dữ liệu cá nhân hay dữ liệu thu thập thật.

## Phạm vi sửa

- **Chỉ sửa mã thuộc phần của issue.** Không sửa, định dạng lại hay "tiện tay tối ưu" mã ở phần khác, kể cả khi thấy lỗi.
- Thấy lỗi ở phần khác: tạo issue mới hoặc báo người phụ trách, ghi vào [developer/](developer/README.md) nếu là vấn đề kỹ thuật đáng lưu. Không sửa lẫn vào nhánh đang làm.
- **Tệp dùng chung** dễ xung đột khi nhiều người cùng sửa, cần báo trong nhóm trước khi đụng tới: `backend/app/models.py`, `backend/app/main.py`, `frontend/src/lib/api.ts`, `frontend/src/ApiApp.tsx`, các template `infrastructure/*.yaml`.
- **Migration database:** số migration (`0024_...`, `0025_...`) phải liên tiếp. Báo trong nhóm số mình dùng trước khi tạo; nếu `main` đã có số đó khi bạn merge thì đổi số và `down_revision`.
- Tài liệu phải cập nhật kèm theo thay đổi (theo [AGENTS.md](AGENTS.md)): tệp giai đoạn liên quan, [cấu trúc dự án](docs/project_file_structure.md) khi thêm/xóa tệp, [mapdocs.md](mapdocs.md) khi thêm/xóa tài liệu. Chỉ thêm hoặc sửa phần của mình, không viết lại phần người khác.

## Kiểm thử

| Phần | Lệnh (chạy trong thư mục tương ứng) |
|---|---|
| Backend | `python -m unittest discover -s tests` trong `backend/`. Kiểm thử database cần `TEST_DATABASE_URL` trỏ tới **PostgreSQL thử riêng, sạch, UTF-8** đã chạy migration; xem [backend/README.md](backend/README.md) |
| Migration | `python -m alembic upgrade head` rồi `python -m alembic check` trên database thử |
| Frontend | `npm run build` và `node --test --experimental-strip-types tests/*.test.ts` trong `frontend/` |
| Hạ tầng | Kiểm tra template theo [infrastructure/README.md](infrastructure/README.md) |

Không chạy kiểm thử trỏ vào database hay tài nguyên AWS đang dùng cho demo.

## Pull request

- Tạo PR vào `main`, tiêu đề ngắn gọn bằng tiếng Việt; trong mô tả ghi `Closes #<số issue>` để GitHub tự đóng issue khi merge.
- Mô tả gồm:
  - **Vấn đề:** vì sao cần thay đổi.
  - **Thay đổi:** sửa gì, ở tệp/phần nào.
  - **Kiểm thử:** đã chạy gì, kết quả (dán số kiểm thử đạt).
  - **Giới hạn:** những gì chưa làm hoặc chưa kiểm chứng.
- PR nhỏ, một mục đích. PR lẫn nhiều việc sẽ bị yêu cầu tách.
- Trước khi merge: cập nhật nhánh với `main` mới nhất (`git pull origin main`), giải quyết xung đột, chạy lại kiểm thử.
- Người review kiểm tra: đúng phạm vi issue, không đụng phần khác, có kiểm thử, có cập nhật tài liệu, không lộ bí mật.

## AWS và demo

- Stack demo (`brand-demo-minute-*`) đang được dùng để quay và thuyết trình, **có tính phí**. Chỉ triển khai lên đó mã đã merge vào `main`, và báo nhóm trưởng trước.
- Không tạo, xóa hay đổi tài nguyên AWS khi chưa thống nhất với nhóm trưởng; ngân sách toàn giai đoạn 30 USD.
- Thay đổi ảnh hưởng thao tác hoặc lệnh dùng khi demo phải cập nhật [demo/architecture.md](demo/architecture.md).

## Khi dùng AI hỗ trợ

- Đưa cho AI số issue, tên nhánh và phạm vi được sửa ngay từ đầu phiên. AI phải tuân theo quy tắc phạm vi trong [AGENTS.md](AGENTS.md).
- Tự đọc lại thay đổi AI tạo ra trước khi commit; người làm issue chịu trách nhiệm về PR.
