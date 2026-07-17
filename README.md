# MB Daily Control

Dashboard vận hành tĩnh cho kế hoạch MB hằng ngày.

## Lệnh khóa 17/07/2026

- Phương pháp chính thức: **V32 · R868Y26 + Gate315 + Empirical Overdue Swap075 / A6_B8**
- Số: **01, 13, 31, 41, 83, 91**
- Mức: **30 điểm/số**
- Tổng: **180 điểm = 4.140.000đ** theo giá vốn 23.000đ/điểm
- Dữ liệu khóa đến hết **16/07/2026**; chưa dùng kết quả 17/07
- Overlay không kích hoạt: đề xuất `83 → 80`, biên `0,018481 < 0,75`

## Quy tắc vốn A6_B8

| Độ rộng | Điểm mỗi số |
|---|---:|
| N ≤ 6 | 30 |
| N = 7–8 | 25 |
| N ≥ 9 | 20 |

`Core100/Other50` đã ngừng áp dụng cho phương pháp này.

## Vận hành

- `index.html`: dashboard hoàn chỉnh, không phụ thuộc JavaScript hay API để hiển thị lệnh.
- `data/current.json`: dữ liệu máy đọc được, cùng kế hoạch với giao diện.
- `scripts/normalize_static_dashboard.py`: lớp an toàn được workflow Pages áp dụng trước khi deploy.
- `.github/workflows/pages.yml`: build và triển khai GitHub Pages từ nhánh `main`.

Trang công khai: <https://nguyenlinhns-arch.github.io/mb-daily-control/>

Google Sheet vận hành: <https://docs.google.com/spreadsheets/d/1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w/edit>

Backtest là số liệu lịch sử, không bảo đảm kết quả tương lai.
