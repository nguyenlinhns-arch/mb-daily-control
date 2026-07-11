# MB Daily Control

Website công khai: https://nguyenlinhns-arch.github.io/mb-daily-control/

## Chuẩn vận hành tự động

Bộ điều khiển website dùng thứ tự cố định:

1. **A1 Core100** — một mã, 100 điểm/số.
2. **A1 Volume50** — một mã, 50 điểm/số, chỉ khi không có Core.
3. **MB X3 Growth32–34** — ba mã, 50 điểm/số, chỉ khi A1 A0.
4. **MB X2 Rescue** — cặp đảo rank-1, 15 điểm/số, chỉ khi A1 và X3 đều A0 và phanh pilot cho phép.
5. Không có phương pháp đạt thì **A0**.

Mỗi ngày tối đa một lệnh tiền thật. Tín hiệu tự động chỉ là `SYSTEM_SIGNAL_NOT_YET_CONFIRMED`; chưa có xác nhận trước quay thì không được tạo `actual_order` và không cộng P/L.

Khung X2 trên website không hiển thị bất kỳ chỉ số hiệu suất/backtest nào: tổng lệnh, thắng, thua, tỷ lệ thắng, lãi/lỗ hoặc Max DD đều bị loại vĩnh viễn.

## Mốc sớm nhất — bắt buộc tuyệt đối

Mọi lần rà soát và mọi payload website phải có mốc sớm nhất cho toàn bộ ứng viên được hiển thị của **A1, X2 và X3**:

- `earliest_eligible_date`
- `earliest_condition`
- `milestone_type`
- Riêng X3 còn bắt buộc có `earliest_basket_date`.

Mốc là **lower bound có điều kiện**, không phải cam kết. Mọi mốc phải được tính lại sau mỗi kỳ khóa đủ 27/27. Workflow sẽ dừng xuất tín hiệu hoặc chuyển sang `A0_DATA_FAIL` nếu thiếu bất kỳ trường mốc nào.

## Đồng bộ vĩnh viễn lên website

Workflow `.github/workflows/sync-google-sheet.yml` chạy:

- **14:00** hằng ngày: kiểm tra lại kế hoạch từ dữ liệu đã khóa.
- **19:15**, **19:35**, **19:55**: lấy kết quả mới, retry, quyết toán và lập kế hoạch ngày hôm sau.
- Có thể chạy thủ công bằng `workflow_dispatch`.

Mỗi lượt thành công thực hiện liền mạch:

1. Tải XLSX từ Google Sheet nguồn `XSMB_Source_2024_2026_MB_v1.3`.
2. Chỉ chấp nhận kỳ đủ đúng 27 mã; lệch nguồn hoặc ngày lùi thì A0, không suy đoán.
3. Quyết toán lệnh đã được người dùng xác nhận, dùng `data/settlement-ledger.json` để chống cộng trùng và chỉ áp delta khi nguồn được sửa.
4. Tính lại Gan/Gmax/Score cho 00–99, A1 Core/Volume, X3 Growth và X2 Rescue.
5. Tính mốc sớm nhất cho mọi ứng viên A1/X2/X3 và kiểm tra bắt buộc trước khi ghi file.
6. Ghi đồng thời:
   - `data/current.json` — payload website hiện hành;
   - `data/plans/YYYY-MM-DD.json` — bản kế hoạch theo ngày;
   - `data/review-ledger.json` — chỉ mục các lần rà soát;
   - `data/automation-state.json` — trạng thái pipeline.
7. Commit lên `main`; GitHub Pages tự xuất bản. Website tự nạp lại `data/current.json` không cache sau mỗi 120 giây.

Nếu tải nguồn, khóa dữ liệu hoặc engine rà soát gặp lỗi, website chuyển thành **A0_DATA_FAIL** và vẫn ghi mốc lần khóa dữ liệu sớm nhất; tuyệt đối không giữ một lệnh cũ như thể còn hiệu lực.
