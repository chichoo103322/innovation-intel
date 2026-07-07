#!/usr/bin/env python3
"""常州人才·对标快讯 周报自动生成"""
import sys, json, shutil
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent
SCRIPT_DIR = PROJECT_DIR / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from generate_html_pdf import html_to_pdf, get_issue_numbers
from build_talent_html import build_talent_weekly_html


def main():
    json_path = PROJECT_DIR / "talent_weekly" / "report_weekly_data.json"
    if not json_path.exists():
        print(f"[错误] JSON 不存在: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now()
    date_cn = today.strftime("%Y年%m月%d日")
    issue, total = get_issue_numbers()

    html = build_talent_weekly_html(data, date_cn, issue, total)

    pdf_path = PROJECT_DIR / "talent_weekly" / f"常州人才·对标快讯_周报_{today.strftime('%Y%m%d')}.pdf"
    html_to_pdf(html, pdf_path)

    html_path = PROJECT_DIR / "talent_weekly" / f"常州人才·对标快讯_周报_{today.strftime('%Y%m%d')}.html"
    html_path.write_text(html, encoding="utf-8")

    # 分发到桌面
    desktop_dir = Path("/Users/jzxzhou/Desktop/人才快讯/周报")
    desktop_dir.mkdir(parents=True, exist_ok=True)
    dest = desktop_dir / pdf_path.name
    shutil.copy2(pdf_path, dest)

    print(f"PDF 已生成: {pdf_path}")
    print(f"已分发到: {dest}")
    print(f"期号: 2026年第{issue}期 / 总第{total}期")


if __name__ == "__main__":
    main()
