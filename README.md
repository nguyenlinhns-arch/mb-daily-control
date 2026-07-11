# MB Daily Control

Website công khai: https://nguyenlinhns-arch.github.io/mb-daily-control/

Dashboard XSMB hằng ngày dùng chuẩn **MB A1 Dual Core Volume Balance – Gan 21/12**:

- Core Strict: 50 điểm/số; vốn chuẩn 1.150.000đ/mã.
- Volume Balanced: 30 điểm/số; vốn chuẩn 690.000đ/mã.
- Tối đa một mã tiền thật mỗi ngày; có Core thì dừng, không đánh thêm Volume.
- X2, X3, Plus và các mã gần đạt chỉ hiển thị Shadow/Research khi chưa qua gate.
- Khung X2 trên website không hiển thị bất kỳ chỉ số hiệu suất/backtest nào: tổng lệnh, số lệnh thắng, số lệnh thua, tỷ lệ thắng, tổng lãi/lỗ, P/L hoặc Max DD đều bị loại vĩnh viễn.
- Xiên 2 dùng sổ riêng; lãi/lỗ chỉ ghi khi người dùng đã xác nhận đánh thật.
- Dữ liệu thiếu, lệch nguồn, chưa khóa hoặc không đủ 27 mã thì không tự suy đoán.

Nguồn dữ liệu vận hành: `XSMB_Source_2024_2026_MB_v1.3`.

## Đồng bộ kết quả tự động

Workflow `.github/workflows/sync-google-sheet.yml` chạy lúc **19:15** hằng ngày theo giờ Việt Nam, kèm hai lượt kiểm tra lại lúc **19:35** và **19:55**. Có thể chạy thủ công bằng `workflow_dispatch`.

Quy trình:

1. Tải bản XLSX mới nhất từ Google Sheet nguồn.
2. Đối chiếu các tab nguồn và chỉ nhận kỳ có đủ đúng 27 mã.
3. Không cho nguồn lùi ngày; nếu bộ 27 mã cùng ngày lệch dữ liệu đã cross-check thì workflow dừng để kiểm tra.
4. Cập nhật `data/current.json`: ngày khóa, 27 mã, unique, mã lặp và mức nhiễu.
5. Chỉ quyết toán `actual_order` có trạng thái xác nhận tiền thật (`REAL_PENDING`/`REAL_SETTLED`) đúng ngày quay.
6. Tự đối chiếu lô và toàn bộ cặp Xiên 2, tính vốn, tiền trả và P/L.
7. Ghi `data/settlement-ledger.json` theo ngày; chạy lại hoặc retry không cộng lãi/lỗ hai lần. Nếu kết quả nguồn được sửa, chỉ áp phần chênh lệch.
8. Cập nhật lũy kế Xiên 2 gồm số lệnh thắng, số lệnh thua và tổng lãi/lỗ.
9. Chỉ commit khi dữ liệu thực sự thay đổi; commit mới được GitHub Pages xuất bản lên website.

Trang web tự tải lại `data/current.json` sau mỗi 120 giây và luôn yêu cầu dữ liệu không cache.
