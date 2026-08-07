import asyncio
from pathlib import Path
import edge_tts

VOICE = 'vi-VN-NamMinhNeural'
RATE = '-4%'
PITCH = '-8Hz'
OUT = Path('tts_ai4so_master_ad')
OUT.mkdir(exist_ok=True)
segments = [
    ('seg1', 'AI miền Bắc bốn ét ô là hệ thống phân tích dữ liệu số mỗi ngày.'),
    ('seg2', 'Từ một trăm số, hệ thống liên tục lọc và giữ lại nhóm tín hiệu nổi bật.'),
    ('seg3', 'Dữ liệu được khóa trước khi phân tích, sau đó quét toàn bộ dải từ không không đến chín chín.'),
    ('seg4', 'Bốn ét ô tiếp tục đánh giá nhịp xuất hiện và cấu trúc cặp đảo.'),
    ('seg5', 'Theo thống kê ba mươi ngày gần đây, tỷ lệ đạt khoảng tám mươi phần trăm, tương đương hai mươi ba đến hai mươi bốn ngày.'),
    ('seg6', 'AI đang mở miễn phí trên Page Lê Miền Bắc. Bấm Nhắn tin và gửi từ khóa bốn ét ô để nhận phân tích hôm nay.'),
]

async def main():
    (OUT / 'script.txt').write_text('\n'.join(f'{k}: {v}' for k, v in segments), encoding='utf-8')
    for name, text in segments:
        c = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE, pitch=PITCH)
        await c.save(str(OUT / f'{name}.mp3'))

asyncio.run(main())
