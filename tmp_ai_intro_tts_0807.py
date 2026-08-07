import asyncio
from pathlib import Path
import edge_tts

TEXT = (
    "AI không còn là thứ xa vời. "
    "Bạn có thể dùng AI để viết nội dung, tìm ý tưởng, học tập và xử lý công việc nhanh hơn. "
    "Không cần biết công nghệ phức tạp. "
    "Bạn có thể bắt đầu với AI miễn phí. "
    "Chỉ cần nhắn tin cho Page, tôi sẽ hướng dẫn từng bước để bạn dùng ngay."
)

async def main():
    out = Path('tts_ai_intro')
    out.mkdir(exist_ok=True)
    communicate = edge_tts.Communicate(
        TEXT,
        voice='vi-VN-NamMinhNeural',
        rate='-4%',
        pitch='-8Hz',
        volume='+0%'
    )
    await communicate.save(str(out / 'ai_intro_namminh.mp3'))
    (out / 'script.txt').write_text(TEXT, encoding='utf-8')

asyncio.run(main())
