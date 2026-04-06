from weasyprint import HTML
from flask import render_template_string
import uuid, os

OUTPUT_FOLDER = "outputs"

TEMPLATES = {
    "viet_truyenthong": {"name": "Việt Truyền Thống", "desc": "Phở, Cơm niêu, Mộc mạc (Nâu/Kem)"},
    "quan_nhau":        {"name": "Quán Nhậu / BBQ",   "desc": "Cá tính, Nổi bật (Đen/Vàng)"},
    "tra_sua":          {"name": "Trà Sữa / Ăn Vặt",  "desc": "Tươi sáng, Bo tròn (Xanh/Hồng)"},
    "cafe_modern":      {"name": "Cafe Hiện Đại",     "desc": "Tối giản, Sang trọng (Trắng/Đen)"},
    "cafe_highlight":   {"name": "Cafe Nổi Bật",      "desc": "Vàng cam, hút mắt (Cafe Muối)"},
    "cafe_traditional": {"name": "Cafe Truyền Thống", "desc": "Nâu gỗ, mộc mạc (Cafe Phin)"},
}

def render_menu_pdf(menu_data: dict, shop_name: str, template_key: str = "viet_truyenthong", watermark: bool = True) -> str:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    base = os.path.join(os.path.dirname(__file__), "templates", "menu_template")
    path = os.path.join(base, f"{template_key}.html")
    with open(path, encoding="utf-8") as f: html_str = f.read()

    html_content = render_template_string(html_str, shop_name=shop_name, groups=menu_data["groups"])
    filename = f"{uuid.uuid4().hex}.pdf"
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    HTML(string=html_content, base_url=".").write_pdf(filepath)
    return filename
