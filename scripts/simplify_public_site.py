#!/usr/bin/env python3
"""Simplify the public website after the static build.

The paid report still uses all configured analytical inputs, but the public
website no longer publishes a catalogue of current numbers by method.  This
step also applies the white-red conversion theme and keeps the landing-page
copy tied to the historical rate that was rendered by the audited build.
"""
from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path


THEME_HREF = "/red-white-theme.css?v=20260814-1"
HOME_METHOD_SECTION = re.compile(
    r"\s*<section class=\"public-methods-v2\"[^>]*>.*?</section>\s*",
    re.DOTALL,
)
TODAY_METHOD_SECTION = re.compile(
    r"\s*<section class=\"seo-section public-methods\"[^>]*>.*?</section>\s*",
    re.DOTALL,
)
HISTORICAL_RATE = re.compile(
    r'<div class="historical-rate">\s*<p>.*?</p>\s*'
    r'<strong>(\d+)%</strong>\s*'
    r'<span>\s*(\d+)\s*/\s*(\d+)\s+ngày',
    re.DOTALL,
)


def write_if_changed(path: Path, content: str) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != content:
        path.write_text(content, encoding="utf-8")


def inject_theme(content: str) -> str:
    if THEME_HREF in content:
        return content
    if "</head>" not in content:
        raise ValueError("HTML page is missing </head>")
    return content.replace(
        "</head>",
        f'  <link rel="stylesheet" href="{THEME_HREF}">\n</head>',
        1,
    )


def replace_meta(content: str, attribute: str, key: str, value: str) -> str:
    pattern = re.compile(
        rf'(<meta\s+{re.escape(attribute)}="{re.escape(key)}"\s+content=")[^"]*(">)',
        re.IGNORECASE,
    )
    return pattern.sub(lambda match: f"{match.group(1)}{value}{match.group(2)}", content, count=1)


def replace_first(content: str, pattern: str, replacement: str, *, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=flags)
    if count != 1:
        raise ValueError(f"Expected exactly one match for: {pattern}")
    return updated


def simplify_home(content: str) -> str:
    content, removed = HOME_METHOD_SECTION.subn("\n", content, count=1)
    if removed != 1:
        raise ValueError("Home page must contain exactly one public method section before simplification")

    rate_match = HISTORICAL_RATE.search(content)
    if rate_match:
        rate, hit_days, total_days = rate_match.groups()
        hero_title = f'<h1><em>{rate}%</em> trong {total_days} ngày<br>đã đối chiếu</h1>'
        hero_lead = (
            f'<p class="hero-lead"><strong>{hit_days}/{total_days} ngày có ít nhất một trong bốn đầu ra '
            'xuất hiện trong kết quả đã công bố.</strong> Chỉ với 30.000đ, bạn nhận báo cáo phân tích '
            'ngày hôm nay đã khóa dữ liệu đến hết ngày hôm qua.</p>'
        )
        hero_proof = (
            '<p class="hero-proof-text">Thống kê lịch sử đã hoàn tất; không phải xác suất hoặc '
            'cam kết cho ngày hôm nay.</p>'
        )
        title = f"{rate}% trong {total_days} ngày đã đối chiếu – Báo cáo hôm nay | Lê Miền Bắc AI"
        description = (
            f"{hit_days}/{total_days} ngày trong cửa sổ lịch sử có đầu ra xuất hiện. "
            "Chỉ 30.000đ cho báo cáo phân tích ngày hôm nay; thống kê không bảo đảm kết quả tương lai."
        )
    else:
        hero_title = '<h1>Đang cập nhật báo cáo<br><em>ngày hôm nay</em></h1>'
        hero_lead = (
            '<p class="hero-lead"><strong>Hệ thống đang kiểm tra dữ liệu khóa đến ngày hôm qua.</strong> '
            'Thanh toán chỉ được mở sau khi báo cáo hôm nay hoàn tất kiểm tra.</p>'
        )
        hero_proof = '<p class="hero-proof-text">Không hiển thị lại dữ liệu của ngày cũ dưới ngày mới.</p>'
        title = "Đang cập nhật báo cáo hôm nay | Lê Miền Bắc AI"
        description = "Báo cáo hôm nay đang kiểm tra dữ liệu T−1 và chưa mở thanh toán khi dữ liệu chưa sẵn sàng."

    content = replace_first(
        content,
        r'(<section class="hero hero-simple" id="top">.*?<p class="eyebrow">.*?</p>)\s*<h1>.*?</h1>',
        lambda match: f"{match.group(1)}\n        {hero_title}",
        flags=re.DOTALL,
    )
    content = replace_first(
        content,
        r'<p class="hero-lead">.*?</p>',
        hero_lead,
        flags=re.DOTALL,
    )
    content = replace_first(
        content,
        r'<p class="hero-proof-text">.*?</p>',
        hero_proof,
        flags=re.DOTALL,
    )
    content = replace_first(
        content,
        r'<div class="hero-offer simple-hero-offer"><div>.*?</div><button class="button button-primary button-large" type="button" data-open-checkout>.*?</button></div>',
        '<div class="hero-offer simple-hero-offer"><div><small>CHỈ 30.000Đ · 01 BÁO CÁO HÔM NAY</small><strong>30.000đ</strong><span>Mục 4SO · 7 lớp phân tích · Hồ sơ nguồn</span></div><button class="button button-primary button-large" type="button" data-open-checkout>NHẬN BÁO CÁO HÔM NAY</button></div>',
        flags=re.DOTALL,
    )

    content = content.replace("Nhận báo cáo đầy đủ", "Nhận báo cáo hôm nay · 30K")
    content = content.replace(
        '<span>Nhận báo cáo hôm nay · 30K</span><strong>30.000đ</strong>',
        '<span>Nhận báo cáo hôm nay</span><strong>30.000đ</strong>',
    )
    content = replace_first(
        content,
        r'<p class="buy-copy">.*?</p>',
        '<p class="buy-copy">Chỉ với 30.000đ, bạn nhận đúng một báo cáo cho ngày hiển thị, gồm mục 4SO, kết luận tổng hợp từ 7 lớp phân tích, hồ sơ nguồn và giới hạn sử dụng.</p>',
        flags=re.DOTALL,
    )
    content = content.replace(
        ">Hiện thông tin chuyển khoản</button>",
        ">NHẬN BÁO CÁO HÔM NAY – 30.000Đ</button>",
    )
    content = content.replace(
        "Tôi đã chuyển khoản – gửi email xác nhận",
        "TÔI ĐÃ CHUYỂN KHOẢN – YÊU CẦU MỞ BÁO CÁO",
    )
    content = content.replace(
        "Hệ thống sẽ gửi email để chủ dịch vụ kiểm tra và xác nhận.",
        "Hệ thống sẽ gửi yêu cầu để chủ dịch vụ kiểm tra giao dịch và mở báo cáo.",
    )

    content = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", content, count=1, flags=re.DOTALL)
    content = replace_meta(content, "name", "description", description)
    content = replace_meta(content, "property", "og:title", title)
    content = replace_meta(content, "property", "og:description", description)
    content = replace_meta(content, "name", "twitter:title", title)
    content = replace_meta(content, "name", "twitter:description", description)
    content = content.replace(
        "Báo cáo phân tích dữ liệu XSMB đã công bố đến hết ngày liền trước, gồm kiểm tra nguồn, bảy phương pháp phân tích, so sánh cửa sổ 7/30/90 phiên và kết luận mô tả. Không bán số và không nhận cược.",
        "Báo cáo phân tích dữ liệu XSMB đã công bố đến hết ngày liền trước, gồm mục 4SO, bảy lớp phân tích, hồ sơ nguồn và giới hạn sử dụng. Không nhận cược hoặc trả thưởng.",
    )
    return content


def simplify_today_page(content: str) -> str:
    replacement = '''
    <section class="seo-section public-methods-summary" aria-labelledby="method-summary-title">
      <div class="seo-wrap">
        <div class="section-heading">
          <p class="eyebrow">BÁO CÁO TỔNG HỢP</p>
          <h2 id="method-summary-title">7 lớp phân tích, một kết luận rõ ràng</h2>
          <p>Website không công khai dãy số riêng lẻ theo từng phương pháp. Báo cáo hôm nay tổng hợp các lớp phân tích thành một nội dung ngắn gọn, có ngày khóa dữ liệu, hồ sơ nguồn và giới hạn sử dụng.</p>
          <a class="primary-cta" href="/#buy"><span>NHẬN BÁO CÁO HÔM NAY</span><span>30.000đ</span></a>
        </div>
      </div>
    </section>
    '''
    content, removed = TODAY_METHOD_SECTION.subn(replacement, content, count=1)
    if removed != 1:
        raise ValueError("Today SEO page must contain exactly one public method section")
    content = content.replace(
        '<h1><span class="phrase">Cho số Miền Bắc</span> <span class="phrase">hôm nay bằng AI</span></h1>',
        '<h1><span class="phrase">Báo cáo dữ liệu</span> <span class="phrase">XSMB hôm nay</span></h1>',
    )
    content = content.replace("KHUYẾN NGHỊ THEO NGÀY", "BÁO CÁO THEO NGÀY")
    content = re.sub(
        r'<p class="lead">.*?</p>',
        '<p class="lead">Báo cáo sử dụng dữ liệu XSMB đã công bố đến hết ngày hôm qua, kiểm tra đủ 27/27 mã và tổng hợp 7 lớp phân tích. Không công khai danh sách số rời rạc theo từng phương pháp.</p>',
        content,
        count=1,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<title>.*?</title>",
        "<title>Báo cáo dữ liệu XSMB hôm nay bằng AI | Lê Miền Bắc AI</title>",
        content,
        count=1,
        flags=re.DOTALL,
    )
    content = replace_meta(
        content,
        "name",
        "description",
        "Báo cáo dữ liệu XSMB hôm nay dùng dữ liệu khóa T−1, đủ 27/27 mã, 7 lớp phân tích và hồ sơ nguồn; không công khai dãy số riêng lẻ.",
    )
    return content


def correct_legal_copy(content: str) -> str:
    content = content.replace("bảy phương pháp phân tích", "bảy lớp phân tích")
    content = content.replace("các chỉ số của bảy phương pháp", "kết quả tổng hợp của bảy lớp phân tích")
    content = re.sub(
        r'<h3>Sản phẩm được cung cấp</h3><p>.*?</p>',
        '<h3>Sản phẩm được cung cấp</h3><p>Lê Miền Bắc AI cung cấp một loại sản phẩm: báo cáo phân tích dữ liệu cho ngày hiện tại, giá 30.000đ. Báo cáo ghi rõ ngày lập, ngày khóa dữ liệu, độ đầy đủ 27/27, hồ sơ nguồn, mục 4SO, bảy lớp phân tích, kết luận tổng hợp và giới hạn sử dụng.</p>',
        content,
        count=1,
        flags=re.DOTALL,
    )
    content = re.sub(
        r'<h3>Nội dung không cung cấp</h3><p>.*?</p>',
        '<h3>Nội dung không cung cấp</h3><p>Website không bán vé, nhận tiền cược, giữ tiền cược, đặt cược thay khách, trả thưởng, tư vấn tài chính hoặc cam kết kết quả tương lai. Các đầu ra trong báo cáo là kết quả mô hình thống kê, không phải bảo đảm thắng.</p>',
        content,
        count=1,
        flags=re.DOTALL,
    )
    return content


def simplify_sample_copy(content: str) -> str:
    content = content.replace("kết quả của 7 phương pháp", "kết quả tổng hợp từ 7 lớp phân tích")
    content = content.replace("<strong>7 phương pháp</strong>", "<strong>7 lớp phân tích</strong>")
    return content


def global_cleanup(content: str) -> str:
    content = content.replace("/#pricing", "/#buy")
    content = content.replace("<span>Xem gói</span><span>mở kết luận</span>", "<span>Xem báo cáo</span><span>hôm nay</span>")
    content = content.replace("Số hôm nay", "Báo cáo hôm nay")
    content = content.replace("MỞ KẾT LUẬN", "NHẬN BÁO CÁO")
    content = content.replace("7 phương pháp", "7 lớp phân tích")
    return inject_theme(content)


def process_site(output_root: Path) -> None:
    index = output_root / "index.html"
    if not index.exists():
        raise FileNotFoundError(f"Missing generated home page: {index}")

    home = simplify_home(index.read_text(encoding="utf-8"))
    write_if_changed(index, global_cleanup(home))

    today = output_root / "cho-so-mien-bac-hom-nay" / "index.html"
    if not today.exists():
        raise FileNotFoundError(f"Missing generated today page: {today}")
    today_content = simplify_today_page(today.read_text(encoding="utf-8"))
    write_if_changed(today, global_cleanup(today_content))

    legal = output_root / "legal.html"
    if legal.exists():
        write_if_changed(legal, global_cleanup(correct_legal_copy(legal.read_text(encoding="utf-8"))))

    sample = output_root / "mau-bao-cao.html"
    if sample.exists():
        write_if_changed(sample, global_cleanup(simplify_sample_copy(sample.read_text(encoding="utf-8"))))

    for page in output_root.rglob("*.html"):
        if page in {index, today, legal, sample}:
            continue
        write_if_changed(page, global_cleanup(page.read_text(encoding="utf-8")))

    public_methods = output_root / "ai-methods" / "public-methods.json"
    if public_methods.exists():
        public_methods.unlink()

    home_check = index.read_text(encoding="utf-8")
    today_check = today.read_text(encoding="utf-8")
    if "public-methods-v2" in home_check or "SỐ CÔNG KHAI HÔM NAY" in home_check:
        raise AssertionError("Public method catalogue still exists on the home page")
    if "data-current-methods" in today_check or "method-item" in today_check or "SỐ CÔNG KHAI HÔM NAY" in today_check:
        raise AssertionError("Public method numbers still exist on the today page")
    if THEME_HREF not in home_check or THEME_HREF not in today_check:
        raise AssertionError("White-red theme was not linked")
    if public_methods.exists():
        raise AssertionError("Public method JSON must not be deployed")
    for page in output_root.rglob("*.html"):
        if "/#pricing" in page.read_text(encoding="utf-8"):
            raise AssertionError(f"Broken pricing anchor remains in {page}")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "cho-so-mien-bac-hom-nay").mkdir(parents=True)
        (root / "ai-methods").mkdir(parents=True)
        (root / "index.html").write_text(
            '''<html><head><title>Old</title><meta name="description" content="old"><meta property="og:title" content="old"><meta property="og:description" content="old"><meta name="twitter:title" content="old"><meta name="twitter:description" content="old"></head><body><header><button data-open-checkout>Nhận báo cáo đầy đủ</button></header><section class="hero hero-simple" id="top"><p class="eyebrow">BÁO CÁO</p><h1>Old</h1><p class="hero-lead">Old</p><p class="hero-proof-text">Old</p><div class="hero-offer simple-hero-offer"><div><small>Old</small><strong>30.000đ</strong><span>Old</span></div><button class="button button-primary button-large" type="button" data-open-checkout>Old</button></div></section><div class="historical-rate"><p>CỬA SỔ</p><strong>83%</strong><span>25/30 ngày có ít nhất một đầu ra xuất hiện</span></div><section class="public-methods-v2"><article>11 22</article></section><p class="buy-copy">Old</p><button>Hiện thông tin chuyển khoản</button><button>Tôi đã chuyển khoản – gửi email xác nhận</button></body></html>''',
            encoding="utf-8",
        )
        (root / "cho-so-mien-bac-hom-nay" / "index.html").write_text(
            '''<html><head><title>Old</title><meta name="description" content="old"></head><body><h1><span class="phrase">Cho số Miền Bắc</span> <span class="phrase">hôm nay bằng AI</span></h1><p class="lead">Old</p><section class="seo-section public-methods"><div data-current-methods><article class="method-item">11 22</article></div></section></body></html>''',
            encoding="utf-8",
        )
        (root / "ai-methods" / "public-methods.json").write_text("{}", encoding="utf-8")
        process_site(root)
        assert "83%" in (root / "index.html").read_text(encoding="utf-8")
        assert not (root / "ai-methods" / "public-methods.json").exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.output_root and not args.self_test:
        parser.error("Provide --output-root and/or --self-test")
    if args.self_test:
        self_test()
    if args.output_root:
        process_site(args.output_root.resolve())


if __name__ == "__main__":
    main()
