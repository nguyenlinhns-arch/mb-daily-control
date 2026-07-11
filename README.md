# MB Daily Control

Website công khai: https://nguyenlinhns-arch.github.io/mb-daily-control/

## Chuẩn vận hành tự động

Bộ điều khiển website dùng thứ tự cố định:

1. **A1 Core100** — một mã chính, 100 điểm/số.
2. **A1 Volume50** — một mã chính, 50 điểm/số, chỉ khi không có Core.
3. **MB X3 Growth32–34** — ba mã, 50 điểm/số, chỉ khi A1 A0.
4. **MB X2 Rescue** — cặp đảo rank-1, 15 điểm/số, chỉ khi A1 và X3 đều A0 và phanh pilot cho phép.
5. Không có phương pháp đạt thì **A0**.

Mỗi ngày tối đa một lệnh tiền thật. Tín hiệu tự động chỉ là `SYSTEM_SIGNAL_NOT_YET_CONFIRMED`; chưa có xác nhận trước quay thì không được tạo `actual_order` và không cộng P/L.

## Số đảo A1 — quy tắc vĩnh viễn

- Khi A1 Core hoặc A1 Volume đạt gate, số đảo chính thức đi kèm ở mức **50 điểm/số**.
- Core: mã chính 100 điểm; số đảo 50 điểm.
- Volume: mã chính 50 điểm; số đảo 50 điểm.
- Số đảo là cấu phần phụ thuộc vào mã A1 chính, không có gate độc lập và không được mở như lệnh riêng.
- Nếu mã chính tự đảo, gồm `00, 11, 22, 33, 44, 55, 66, 77, 88, 99`, chỉ đánh mã đó **một lần** theo mức của mã chính.
- Tuyệt đối không được ghi hai dòng, cộng hai lần điểm, nhân đôi vốn hoặc quyết toán hai lần cùng một mã tự đảo.
- Ví dụ: A1 Core 75 ⇒ `75 ×100 + 57 ×50`; A1 Volume 75 ⇒ `75 ×50 + 57 ×50`; A1 88 ⇒ chỉ `88` một lần, không có lệnh đảo thứ hai.

Khung X2 trên website không hiển thị bất kỳ chỉ số hiệu suất/backtest nào: tổng lệnh, thắng, thua, tỷ lệ thắng, lãi/lỗ hoặc Max DD đều bị loại vĩnh viễn.

## Mốc sớm nhất — bắt buộc tuyệt đối

Mọi lần rà soát và mọi payload website phải có mốc sớm nhất cho toàn bộ ứng viên được hiển thị của **A1, X2 và X3**:

- `earliest_eligible_date`
- `earliest_condition`
- `milestone_type`
- Số đảo A1 khác mã chính dùng loại mốc `DEPENDENT_REVERSE` và cùng ngày đủ điều kiện với mã chính.
- Riêng X3 còn bắt buộc có `earliest_basket_date`.

Mốc là **lower bound có điều kiện**, không phải cam kết. Mọi mốc phải được tính lại sau mỗi kỳ khóa đủ 27/27. Workflow sẽ dừng xuất tín hiệu hoặc chuyển sang `A0_DATA_FAIL` nếu một bộ dữ liệu mới đã tải thành công nhưng không qua gate 27/27, đối chiếu nguồn hoặc thiếu bất kỳ trường mốc nào.

## Đồng bộ vĩnh viễn lên website

Workflow `.github/workflows/sync-google-sheet.yml` chạy:

- **14:00** hằng ngày: kiểm tra lại kế hoạch từ dữ liệu đã khóa.
- **19:15**, **19:35**, **19:55**: lấy kết quả mới, retry, quyết toán và lập kế hoạch ngày hôm sau.
- Có thể chạy thủ công bằng `workflow_dispatch`.

Workflow `.github/workflows/enforce-a1-reverse.yml` chạy ngay sau mỗi lần payload/kế hoạch thay đổi và có các lượt bảo vệ sau lịch chính. Workflow này buộc áp dụng số đảo A1 50 điểm, loại mã trùng và kiểm tra không nhân đôi vốn/P&L.

Mỗi lượt thành công thực hiện liền mạch:

1. Tải XLSX từ Google Sheet nguồn `XSMB_Source_2024_2026_MB_v1.3`.
2. Chỉ chấp nhận kỳ đủ đúng 27 mã; lệch nguồn hoặc ngày lùi thì A0, không suy đoán.
3. Quyết toán lệnh đã được người dùng xác nhận, dùng `data/settlement-ledger.json` để chống cộng trùng và chỉ áp delta khi nguồn được sửa.
4. Tính lại Gan/Gmax/Score cho 00–99, A1 Core/Volume, X3 Growth và X2 Rescue.
5. Áp quy tắc số đảo A1 50 điểm; nếu đảo trùng mã chính thì không tạo lệnh thứ hai.
6. Tính mốc sớm nhất cho mọi ứng viên A1/X2/X3 và kiểm tra bắt buộc trước khi ghi file.
7. Ghi đồng thời:
   - `data/current.json` — payload website hiện hành;
   - `data/plans/YYYY-MM-DD.json` — bản kế hoạch theo ngày;
   - `data/review-ledger.json` — chỉ mục các lần rà soát;
   - `data/automation-status.json` — trạng thái pipeline và lỗi retry.
8. Commit lên `main`; GitHub Pages tự xuất bản. Website tự nạp lại `data/current.json` không cache sau mỗi 120 giây.

## Bảo vệ kế hoạch hợp lệ khi lỗi truy cập nguồn

Lỗi mạng, lỗi export Google Sheet hoặc lỗi truy cập nguồn công khai là **lỗi vận chuyển**, không phải bằng chứng rằng bộ dữ liệu đang hiển thị sai. Vì vậy:

- Không được ghi đè `data/current.json` bằng màn hình `A0_DATA_FAIL` chỉ vì một lượt tải nguồn thất bại.
- Giữ nguyên kế hoạch hợp lệ gần nhất, gồm đầy đủ mốc A1/X2/X3.
- Chỉ ghi lỗi vào `data/automation-status.json` và tự retry ở lượt kế tiếp.
- Chỉ chuyển sang A0 khi một bộ dữ liệu mới đã tải được nhưng thật sự thiếu 27 mã, lệch nguồn, ngày không hợp lệ hoặc không qua kiểm tra mốc bắt buộc.
- Khi lượt retry thành công, kế hoạch mới thay thế bản cũ và được GitHub Pages xuất bản.
