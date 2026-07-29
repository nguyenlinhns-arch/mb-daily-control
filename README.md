# MB MAX V03 Dashboard

Dashboard GitHub Pages cho MB MAX V03.

## Chức năng

- Tạo lệnh chuẩn để gửi ChatGPT: chạy MB MAX V03, cập nhật kết quả, kiểm tra lệnh phanh, quét số mạnh và xuất báo cáo ngày.
- Ledger lãi/lỗ lưu trên trình duyệt bằng `localStorage`.
- Tự tính chuỗi thắng/thua Live, lũy kế tháng, đỉnh tháng, drawdown và trạng thái Capital Protection.
- Watchlist số mạnh và checklist Publication Contract.

## Triển khai GitHub Pages

1. Tạo repository mới trên GitHub, ví dụ `mb-max-v03-dashboard`.
2. Upload toàn bộ nội dung thư mục này lên repository.
3. Vào `Settings` -> `Pages`.
4. Chọn `Build and deployment` -> `GitHub Actions`.
5. Push lên nhánh `main`. Workflow `.github/workflows/pages.yml` sẽ tự deploy.

Với repo `nguyenlinhns-arch/mb-daily-control`, link công khai là:

```text
https://nguyenlinhns-arch.github.io/mb-daily-control/
```

## Chạy thử local

```bash
python3 -m http.server 4173
```

Sau đó mở:

```text
http://localhost:4173
```

## Lưu ý vận hành

Website không tự bịa số và không tự xuống tiền. Final codes chỉ hợp lệ khi có artifact canonical `PUBLISHED+PASS+HASH_MATCH` theo đúng mô tả MB MAX V03.
