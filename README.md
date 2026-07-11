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

## Khối đầu tiên — A1 được ghim và X2/X3 luôn được thể hiện

Khối đầu dùng quy tắc `FIRST_BLOCK_A1_PINNED_X2_X3_STATUS_V3` và luôn giữ ba khu vực theo thứ tự **A1 → X2 → X3**.

### Khu vực A1

- Khi có A1 đạt, hiển thị toàn bộ selection A1 chính thức.
- **Mã A1 chính phải được khoanh tròn** để phân biệt với số đảo.
- Số đảo khác mã chính vẫn hiển thị cùng A1 theo luật 50 điểm.
- Nếu không có A1, giữ ô A1 nhưng **để trống**, không thay bằng mã Watch của phương pháp khác.

### Khu vực X2

- Luôn hiển thị đúng **02 số** của cặp X2 ưu tiên.
- X2 đạt gate: hiển thị đúng hai số của cặp đạt.
- X2 chưa đạt: vẫn hiển thị hai số của cặp rank-1 hiện hành để người dùng theo dõi, nhưng điểm/vốn bằng 0đ.
- Tỷ lệ thắng tham chiếu hiện hành của X2 Rescue35 là **65,71%**.

### Khu vực X3

- Luôn hiển thị đúng **03 số** của rổ X3 ưu tiên.
- X3 đạt gate: hiển thị đủ ba số của rổ đạt.
- X3 chưa đạt: vẫn hiển thị ba số top-ranked hiện hành để người dùng theo dõi, nhưng điểm/vốn bằng 0đ.
- Tỷ lệ thắng tham chiếu hiện hành của X3 Growth32–34 OOS là **69,70%**.

### Quy ước màu bắt buộc

- **Xanh lá = Đạt**.
- **Vàng chanh = Gần đạt**.
- **Đỏ = Không đạt**.

`Gần đạt` được dùng khi payload có nhãn GẦN/NEAR, candidate đã đạt cá thể nhưng bị lớp ưu tiên/phanh chặn, hoặc mốc sớm nhất có điều kiện không muộn hơn kỳ kế tiếp. Với X3, tổng HOT21 bằng 31 hoặc 35 cũng là cận gate 32–34.

Tỷ lệ thắng chỉ là tham chiếu lịch sử **cấp phương pháp**, không phải xác suất riêng của từng mã và không bảo đảm kết quả. Chỉ phương pháp được controller chọn có điểm/vốn; các số X2/X3 đạt nhưng bị ưu tiên chặn, gần đạt hoặc không đạt vẫn hiển thị với vốn 0đ.

Khung X2 chi tiết trên website tiếp tục không hiển thị bất kỳ chỉ số hiệu suất/backtest nào: tổng lệnh, thắng, thua, tỷ lệ thắng, lãi/lỗ hoặc Max DD đều bị loại vĩnh viễn. WR trong khối đầu là nhãn so sánh chung của phương pháp, không phải bảng hiệu suất X2.

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

Workflow `.github/workflows/enforce-a1-reverse.yml` và `.github/workflows/enforce-first-block.yml` chạy sau khi payload/kế hoạch thay đổi và có các lượt bảo vệ sau lịch chính. Hai workflow buộc áp dụng đồng thời:

- số đảo A1 50 điểm, loại mã tự đảo trùng;
- khối đầu theo `FIRST_BLOCK_A1_PINNED_X2_X3_STATUS_V3`;
- A1 chính được khoanh, không có A1 thì ô A1 để trống;
- X2 đúng 02 số, X3 đúng 03 số;
- màu Xanh lá/Vàng chanh/Đỏ đúng trạng thái;
- không nhân đôi vốn/P&L và không biến Shadow thành lệnh thật.

Mỗi lượt thành công thực hiện liền mạch:

1. Tải XLSX từ Google Sheet nguồn `XSMB_Source_2024_2026_MB_v1.3`.
2. Chỉ chấp nhận kỳ đủ đúng 27 mã; lệch nguồn hoặc ngày lùi thì A0, không suy đoán.
3. Quyết toán lệnh đã được người dùng xác nhận, dùng `data/settlement-ledger.json` để chống cộng trùng và chỉ áp delta khi nguồn được sửa.
4. Tính lại Gan/Gmax/Score cho 00–99, A1 Core/Volume, X3 Growth và X2 Rescue.
5. Áp quy tắc số đảo A1 50 điểm; nếu đảo trùng mã chính thì không tạo lệnh thứ hai.
6. Xây dựng khối đầu A1/X2/X3 và gắn đúng màu trạng thái.
7. Tính mốc sớm nhất cho mọi ứng viên A1/X2/X3 và kiểm tra bắt buộc trước khi ghi file.
8. Ghi đồng thời:
   - `data/current.json` — payload website hiện hành;
   - `data/plans/YYYY-MM-DD.json` — bản kế hoạch theo ngày;
   - `data/review-ledger.json` — chỉ mục các lần rà soát;
   - `data/automation-status.json` — trạng thái pipeline và lỗi retry.
9. Commit lên `main`; GitHub Pages tự xuất bản. Website tự nạp lại `data/current.json` không cache sau mỗi 120 giây.

## Bảo vệ kế hoạch hợp lệ khi lỗi truy cập nguồn

Lỗi mạng, lỗi export Google Sheet hoặc lỗi truy cập nguồn công khai là **lỗi vận chuyển**, không phải bằng chứng rằng bộ dữ liệu đang hiển thị sai. Vì vậy:

- Không được ghi đè `data/current.json` bằng màn hình `A0_DATA_FAIL` chỉ vì một lượt tải nguồn thất bại.
- Giữ nguyên kế hoạch hợp lệ gần nhất, gồm đầy đủ mốc A1/X2/X3 và khối đầu đã chuẩn hóa.
- Chỉ ghi lỗi vào `data/automation-status.json` và tự retry ở lượt kế tiếp.
- Chỉ chuyển sang A0 khi một bộ dữ liệu mới đã tải được nhưng thật sự thiếu 27 mã, lệch nguồn, ngày không hợp lệ hoặc không qua kiểm tra mốc bắt buộc.
- Khi lượt retry thành công, kế hoạch mới thay thế bản cũ và được GitHub Pages xuất bản.
