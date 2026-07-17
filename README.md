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

## Tự động hóa V32 lúc 06:00

Workflow `.github/workflows/v32-daily-0600.yml` chạy lúc 06:00 Asia/Bangkok và
retry idempotent lúc 06:15, 06:30. Thứ tự giao dịch cố định:

1. đọc đủ 27/27 kết quả kỳ trước và snapshot A:D của năm sổ cá nhân;
2. quyết toán lệnh V32 đã khóa;
3. ghi Google Sheets, rồi đọc lại đúng operation ID/hash;
4. tải engine/model V32 từ Google Drive riêng tư, kiểm tra SHA-256 + manifest,
   rồi sinh lệnh kỳ kế tiếp;
5. chỉ khi bước 3 đạt mới cập nhật `current.json`, HTML và đẩy `main` để Pages deploy.

Nếu thiếu kết quả, sai hash, A:D cá nhân đổi trong lúc chạy, P/L có sẵn mâu
thuẫn hoặc Google trả lỗi, workflow dừng và giữ nguyên website gần nhất. Retry
không ghi trùng. Pipeline chỉ quyết toán dòng cá nhân đã có; không tự gán cùng
một lệnh và không tự ghi 0 cho người không có lệnh.

### Một lần duy nhất để kích hoạt ghi Google Sheets

Repository cần hai GitHub Actions secrets:

- `GOOGLE_SERVICE_ACCOUNT_JSON`: JSON của service account; runtime chỉ yêu cầu
  Sheets và Drive read-only scope;
- `MB_PNL_SHEET_ID`: ID riêng của file “Sổ theo dõi lãi lỗ hàng ngày”.

Bật Google Sheets API và Google Drive API trong project của service account.
Chia sẻ file nguồn và file P/L cho `client_email` với quyền Editor; thêm chính
email đó vào mọi protected range đang bao phủ cột E hoặc H của năm tab cá nhân
(kể cả protection toàn tab). Chia sẻ riêng file runtime
`mb-v32-engine-20260717-1e06af9c.tar.gz` trong thư mục Drive
`MB Daily Control - Private Runtime` với quyền Reader. Không bật link sharing.

Engine/model không nằm trong repository công khai. File Drive được khóa bằng
SHA-256 `09bb4dbd6890f0d27c4f8519b72deb3b3b18c317c246c4a168182b51ed7a67d1`
và tree hash `1e06af9c8639099055380e136ee13f5f0c6399c9a437c9cc6150246f16b9fdf3`;
sai một byte thì workflow dừng trước khi đọc dữ liệu vận hành. Secret chỉ được
inject ở bước tải engine, snapshot và apply; không xuất hiện trong bước cài
dependency, chạy engine, test hay publish.

Các tab transaction chính thức:

- nguồn: `V32_Daily_Plan`, `V32_Daily_Settlement`, `V32_Automation_Log`;
- P/L: `Tự động hóa V32`, `Nhật ký tự động V32` và năm tab cá nhân được ánh
  xạ bằng các slot riêng tư `p1`–`p5` trong chính file P/L.

Năm slot đã được ánh xạ trực tiếp tới năm tab hiện hữu, kể cả slot thứ năm.
Repository công khai chỉ dùng khóa `p1`–`p5`; tên thật chỉ được đọc từ tab cấu
hình riêng tư trong file P/L khi workflow chạy.

## Bảo vệ V32

Các workflow sinh kế hoạch Core100/Other50 cũ được giữ lại chỉ để rollback thủ công. Chúng không còn chạy theo `push`, `schedule` hoặc `workflow_run`; muốn kích hoạt phải dispatch bằng tay và nhập chính xác `ENABLE_LEGACY`. Nhờ vậy automation cũ không thể ghi đè kế hoạch V32 đang khóa.

Trang công khai: <https://nguyenlinhns-arch.github.io/mb-daily-control/>

Google Sheet vận hành: <https://docs.google.com/spreadsheets/d/1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w/edit>

Backtest là số liệu lịch sử, không bảo đảm kết quả tương lai.
