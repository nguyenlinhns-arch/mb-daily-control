import asyncio
from pathlib import Path
import edge_tts

VOICE = 'vi-VN-NamMinhNeural'
RATE = '-4%'
PITCH = '-8Hz'
OUT = Path('tts_ai4so_ad')
OUT.mkdir(exist_ok=True)
segments = [
    ('seg1', 'AI miền Bắc bốn ét ô đang được mở miễn phí trên Page Lê Miền Bắc.'),
    ('seg2', 'Hệ thống quét toàn bộ dải số từ không không đến chín chín, rồi phân tích theo phương pháp bốn ét ô.'),
    ('seg3', 'Mỗi ngày, AI chọn ra bốn số và ghép thành hai cặp đảo để bạn lưu lại, đối chiếu.'),
    ('seg4', 'Không cần cài ứng dụng. Không thu phí sử dụng.'),
    ('seg5', 'Muốn nhận phân tích của ngày hôm nay, chỉ cần bấm Nhắn tin và gửi từ khóa bốn ét ô.'),
    ('seg6', 'AI miền Bắc bốn ét ô. Miễn phí trên Page Lê Miền Bắc.'),
]

async def main():
    (OUT / 'script.txt').write_text('\n'.join(f'{k}: {v}' for k, v in segments), encoding='utf-8')
    for name, text in segments:
        c = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE, pitch=PITCH)
        await c.save(str(OUT / f'{name}.mp3'))

asyncio.run(main())
