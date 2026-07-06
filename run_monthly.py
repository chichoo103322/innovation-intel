#!/usr/bin/env python3
"""
《创新常州·对标快讯》月报自动生成
JSON 数据 → HTML → PDF → 分发

用法:
    python3 run_monthly.py                                       # 从 monthly/report_monthly_<今日>.json 生成 PDF
    python3 run_monthly.py --json monthly/report_monthly_xxx.json  # 指定 JSON 文件
    python3 run_monthly.py --skip-distribute                     # 不分发
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).parent
SCRIPT_DIR = PROJECT_DIR / "scripts"
MONTHLY_DIR = PROJECT_DIR / "monthly"

sys.path.insert(0, str(SCRIPT_DIR))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="《创新常州·对标快讯》月报生成")
    parser.add_argument("--json", type=str, default="", help="指定月报 JSON 文件")
    parser.add_argument("--skip-distribute", action="store_true", help="跳过桌面分发")
    parser.add_argument("--force", action="store_true", help="强制生成（跳过月末检测）")
    args = parser.parse_args()

    print("=" * 60)
    print("  创新常州·对标快讯 — 月报自动生成（JSON → HTML → PDF）")
    print("=" * 60)

    today = datetime.now()

    # 非月末提醒
    if not (today + timedelta(days=1)).day == 1 and not args.force:
        print(f"[提示] 今天不是本月最后一天。月报通常在月末生成。")
        print("如需强制生成，请使用 --force")

    # 确定 JSON 文件
    if args.json:
        json_path = Path(args.json)
    else:
        today_stem = today.strftime("%Y%m%d")
        json_path = MONTHLY_DIR / f"report_monthly_{today_stem}.json"

    if not json_path.exists():
        print(f"[错误] JSON 文件不存在: {json_path}")
        print("请先准备月报数据文件")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_items = sum(len(s.get("items", [])) for s in data.get("sections", []))
    print(f"[读入] {total_items} 条信息，分布在 {len(data.get('sections', []))} 个板块")

    # 生成 HTML → PDF
    from generate_html_pdf import build_monthly_html, html_to_pdf, get_issue_numbers

    date_cn = today.strftime("%Y年%m月%d日")
    issue, total = get_issue_numbers()
    html = build_monthly_html(data, issue, total, date_cn)

    date_fn = today.strftime("%Y%m")
    output_pdf = MONTHLY_DIR / f"创新常州·对标快讯_月报_{date_fn}.pdf"
    output_pdf = html_to_pdf(html, output_pdf)

    # 同时保存到桌面
    desktop_dir = Path.home() / "Desktop" / "创新情报" / "月报"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_pdf = desktop_dir / f"创新常州·对标快讯_月报_{date_fn}.pdf"
    import shutil
    shutil.copy2(str(output_pdf), str(desktop_pdf))

    # 保存 HTML
    html_path = MONTHLY_DIR / f"创新常州·对标快讯_月报_{date_fn}.html"
    html_path.write_text(html, encoding="utf-8")

    # 分发
    if not args.skip_distribute:
        from distribute import save_desktop
        save_desktop(str(output_pdf), "monthly")

    print(f"\n[完成] 月报已生成:")
    print(f"  PDF: {output_pdf}")
    print(f"  桌面: {desktop_pdf}")
    print(f"  期号: 2026年第{issue}期 / 总第{total}期")
    print("=" * 60)


if __name__ == "__main__":
    main()
