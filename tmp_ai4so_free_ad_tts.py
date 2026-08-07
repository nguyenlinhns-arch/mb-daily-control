import asyncio
from pathlib import Path
import edge_tts

VOICE = 'vi-VN-NamMinhNeural'
RATE = '-4%'
PITCH = '-8Hz'
OUT = Path('tts_ai4so_ad')
OUT.mkdir(exist_ok=True)
segments = [
    ('seg1', 'AI miền Bắc bốn ét ô đang mở miễn phí trên Page Lê Miền Bắc.'),
    ('seg2', 'AI quét dải số từ không không đến chín chín, rồi phân tích theo phương pháp bốn ét ô.'),
    ('seg3', 'Mỗi ngày, hệ thống chọn bốn số, ghép thành hai cặp đảo.'),
    ('seg4', 'Không cài ứng dụng. Không thu phí.'),
    ('seg5', 'Muốn nhận phân tích hôm nay, bấm Nhắn tin và gửi từ khóa bốn ét ô.'),
]

async def main():
    (OUT / 'script.txt').write_text('\n'.join(f'{k}: {v}' for k, v in segments), encoding='utf-8')
    for old in OUT.glob('seg*.mp3'):
        old.unlink()
    for name, text in segments:
        c = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE, pitch=PITCH)
        await c.save(str(OUT / f'{name}.mp3'))

asyncio.run(main())
