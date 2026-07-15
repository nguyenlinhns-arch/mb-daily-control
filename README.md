# MB Daily Control

Website công khai: https://nguyenlinhns-arch.github.io/mb-daily-control/

## Phương pháp Production

Tên chính thức: **MB ROLL30 30/30 Production – Core100/Other50**.

- `30/30` là mục tiêu độ phủ: có tín hiệu trong mọi phiên của cửa sổ 30 kỳ, không phải mức 30 điểm.
- A1 Core: 100 điểm cho mã chính.
- Mọi mã được cấp vốn khác: 50 điểm/mã.
- Không có mức được cấp vốn dưới 50 điểm.
- Không martingale, không tăng điểm sau thua, không cộng chồng cùng mã; mã trùng chỉ giữ mức cao nhất.

Thứ tự controller:

1. Khóa dữ liệu đủ 27/27 đến ngày `t−1`.
2. Chạy Natural song song: A1 canonical, X2 RBK Exact và X3 Profit.
3. Nếu Natural A0, xét ROLL7 trước.
4. Nếu vẫn A0, ROLL30 bắt buộc chọn Rescue để giữ độ phủ 30/30.
5. Rescue chọn cặp hợp lệ có TV21 cao nhất; primary là chân Gan thấp hơn, thêm cover khi H21 cover ≥ 6. Nếu pool cặp rỗng, dùng X3 generator top1.
6. Xiên 2 và các giỏ phụ bị tắt trong cấu hình này.

## Kế hoạch 15/07/2026

Dữ liệu khóa đến 14/07/2026:

- Natural: A0.
- ROLL7: không kích hoạt.
- ROLL30 Rescue: **31 × 50 điểm + 13 × 50 điểm**.
- Tổng: **100 điểm**, vốn **2.300.000đ**.
- Không đánh thêm 54–45, Flex, Min-1 hoặc Xiên 2.

Định danh đồng bộ:

- `Report_Run_ID`: `RPT_MB_20260715_ROLL30_V2_CORE100_OTHER50`
- `Config_ID`: `MB_ROLL30_30_OF_30_PROD_V2_CORE100_OTHER50_20260715`
- `Data_Lock_Date`: `2026-07-14`
- `Content_Hash`: `9e8aa12fe0dd0fbc003bbbfa6fbbe77934364cf6a771052c35ba28559cc8c757`

## Đồng bộ website

Pipeline tải nguồn, kiểm tra 27/27, quyết toán lệnh đã xác nhận, lập kế hoạch ngày kế tiếp, ghi `data/current.json` và `data/plans/YYYY-MM-DD.json`, rồi render `index.html` để GitHub Pages xuất bản.

Lỗi truy cập nguồn chỉ cập nhật trạng thái lỗi; không được ghi đè kế hoạch hợp lệ gần nhất. Một kế hoạch chỉ được coi là đồng bộ khi `Report_Run_ID`, `Config_ID`, `Data_Lock_Date` và `Content_Hash` khớp giữa payload, trang công khai và file vận hành.

