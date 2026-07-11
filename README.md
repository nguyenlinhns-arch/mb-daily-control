# MB Daily Control

Website công khai: https://nguyenlinhns-arch.github.io/mb-daily-control/

Dashboard XSMB hằng ngày dùng chuẩn **MB A1 Dual Core Volume Balance – Gan 21/12**:

- Core: 100 điểm; vốn chuẩn 2.300.000đ/mã.
- Volume: 50 điểm; vốn chuẩn 1.150.000đ/mã.
- Tối đa một mã tiền thật mỗi ngày.
- X2 và X3 luôn hiển thị số mạnh nhất; nếu chưa qua gate phải ghi “Chưa đạt, chọn số mạnh nhất” và giữ 0 điểm/vốn 0.
- Xiên 2 không có lựa chọn mới sẽ xóa toàn bộ cặp cũ.
- Lãi/lỗ chỉ ghi khi người dùng đã xác nhận đánh thật.

Nguồn dữ liệu vận hành: `XSMB_Source_2024_2026_MB_v1.3`.

## Đồng bộ tự động

Workflow `.github/workflows/sync-google-sheet.yml` chạy tự động lúc **19:20** và **19:50** hằng ngày theo giờ Việt Nam, đồng thời có thể chạy thủ công.

Quy trình:

1. Tải bản XLSX mới nhất từ Google Sheet nguồn.
2. Chỉ nhận kỳ có đủ 27 mã.
3. Cập nhật `data/current.json`: ngày khóa, 27 mã, unique, mã lặp và mức nhiễu.
4. Nếu `actual_order` đã được ghi ở trạng thái `PENDING`, tự đối chiếu lô và toàn bộ cặp Xiên 2, tính vốn, tiền trả và P/L.
5. Chỉ commit khi dữ liệu thực sự thay đổi.
6. Commit mới tự kích hoạt workflow GitHub Pages để xuất bản website.

Trang tự tải lại dữ liệu sau mỗi 120 giây và không dùng cache cho `data/current.json`.
