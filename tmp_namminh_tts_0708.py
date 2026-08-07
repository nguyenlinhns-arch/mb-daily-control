import asyncio
from pathlib import Path
import edge_tts

VOICE = "vi-VN-NamMinhNeural"
RATE = "-4%"
PITCH = "-8Hz"

segments = [
    "Lê Miền Bắc hôm nay, ngày bảy tháng tám năm hai nghìn không trăm hai mươi sáu. Một trăm số, hệ thống chỉ giữ lại bốn.",
    "Dữ liệu đến ngày sáu tháng tám năm hai nghìn không trăm hai mươi sáu đã được khóa.",
    "Hệ thống đang quét toàn bộ dải số từ không không đến chín chín.",
    "Bốn số cuối đang được ghép thành hai cặp đảo.",
    "Cặp thứ nhất: không năm, năm không.",
    "Cặp thứ hai: ba sáu, sáu ba. Lưu lại để đối chiếu tối nay.",
]

async def main():
    out = Path("tts_out")
    out.mkdir(exist_ok=True)
    for i, text in enumerate(segments, 1):
        comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
        await comm.save(str(out / f"seg{i}.mp3"))
    (out / "script.txt").write_text("\n".join(f"{i+1}. {s}" for i, s in enumerate(segments)), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
