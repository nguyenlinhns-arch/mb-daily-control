# MB Daily Control

Dashboard và pipeline vận hành hằng ngày cho phương pháp **MB FUSION4–180**.

## Lệnh đã khóa ngày 19/07/2026

- Hạng 1–3: **59, 78, 06 × 50 điểm**.
- Hạng 4: **10 × 30 điểm**.
- Tổng: **180 điểm**, vốn/lỗ tối đa **4.140.000đ** theo giá vốn
  23.000đ/điểm.
- Dữ liệu chỉ khóa đến hết 18/07/2026; kết quả 19/07 không được dùng khi chọn.

Fusion4 xếp hạng theo công thức đã khóa:

`0,75 × hạng Max4 + 0,25 × ưu tiên Max10 + 0,50 nếu thuộc tập Max10`

A1 được giữ ở lớp kiểm toán nghiên cứu; với cấu hình cố định bốn số, A1 không
thay đổi thứ tự chọn. Không dùng Core100/Other50, overlay hay gấp thếp.

## Đối soát đến 18/07/2026

Replay nhân quả của Fusion4 ngày 18/07 chọn `57, 55, 91, 54` theo mức
`50–50–50–30`. Mã 54 xuất hiện một nháy: vốn 4.140.000đ, trả 2.400.000đ,
P/L phương pháp **-1.740.000đ**. Đây là replay của sổ phương pháp, không phải
lệnh cá nhân thực tế.

Lệnh thực tế của từng người luôn tách riêng. Pipeline chỉ quyết toán dòng đã có
dữ liệu A:D; không tự gán lệnh, không tự ghi 0 và không suy diễn P/L cho người
không có lệnh.

## Tự động hóa lúc 19:15

Workflow `.github/workflows/fusion4-daily-1915.yml` chạy lúc 19:15
Asia/Bangkok, retry idempotent lúc 19:30 và 19:45:

1. đọc đủ 27/27 kết quả ngày hiện tại và đối chiếu hai tab lịch sử;
2. quyết toán lệnh Fusion4 đã khóa và các lệnh cá nhân thực tế đang có;
3. ghi Google Sheets rồi đọc lại đúng operation ID/hash;
4. tải runtime riêng tư, sinh và khóa kế hoạch cho ngày sau;
5. chỉ khi Sheets/readback đạt mới cập nhật JSON, website và đẩy nhánh `main`.

Thiếu kết quả, sai hash, thay đổi A:D trong lúc chạy, P/L có sẵn mâu thuẫn hoặc
Google trả lỗi đều làm pipeline dừng fail-closed; website gần nhất được giữ
nguyên. Lịch V32 cũ đã bị gỡ và chỉ còn rollback thủ công có xác nhận.

Các tab transaction hiện hành:

- nguồn: `FUSION4_Daily_Plan`, `FUSION4_Daily_Settlement`,
  `FUSION4_Automation_Log`;
- P/L: `Tự động hóa FUSION4`, `Nhật ký FUSION4`, `MB FUSION4` và năm tab cá
  nhân được ánh xạ bằng các slot `p1`–`p5`.

Sổ `MB FUSION4` là sổ phương pháp lý thuyết. Năm tab cá nhân là sổ lệnh thật;
hai phạm vi không được cộng lẫn.

## Thành phần chính

- `index.html`: dashboard tĩnh đã render, không cần API để hiện lệnh.
- `data/current.json`: payload công khai cùng nội dung với giao diện.
- `data/fusion4-*`: plan, settlement, state và transaction audit.
- `scripts/fusion4_engine.py`: wrapper xếp hạng Fusion4 trên runtime riêng tư.
- `scripts/fusion4_daily.py`: giao dịch fail-closed từ kết quả đến website.
- `scripts/fusion4_google_sheets_bridge.py`: snapshot, ghi Sheets và readback.
- `scripts/validate_dashboard.py`: chặn publish nếu HTML/JSON/vốn lệch nhau.

Repository cần secret `GOOGLE_SERVICE_ACCOUNT_JSON`. Service account phải có
quyền Editor ở file nguồn và file P/L, quyền Reader ở runtime Drive, đồng thời
được phép ghi các protected range cột E/H của năm tab cá nhân. ID file P/L nằm
trong tab ẩn `V32_Private_Config` để tương thích runtime và không xuất hiện trên
website.

Runtime/model không nằm trong repository công khai. Gói Drive được kiểm tra
SHA-256 `09bb4dbd6890f0d27c4f8519b72deb3b3b18c317c246c4a168182b51ed7a67d1`
và tree hash `1e06af9c8639099055380e136ee13f5f0c6399c9a437c9cc6150246f16b9fdf3`;
sai một byte thì pipeline dừng.

Trang công khai: <https://nguyenlinhns-arch.github.io/mb-daily-control/>

Google Sheet nguồn: <https://docs.google.com/spreadsheets/d/1iVAfqmS-TvP02U8FtKSM2nr_7Dsd7qi2qEGnWV6IK7w/edit>

Backtest là số liệu lịch sử, không bảo đảm kết quả tương lai.
