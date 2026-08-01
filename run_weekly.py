#!/usr/bin/env python3
"""
《创新常州·对标快讯》周报自动生成
JSON 数据 → HTML → PDF → 分发

用法:
    python3 run_weekly.py                                    # 从 weekly/report_weekly_<今日>.json 生成 PDF
    python3 run_weekly.py --json weekly/report_weekly_xxx.json  # 指定 JSON 文件
    python3 run_weekly.py --skip-distribute                  # 不分发
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent
SCRIPT_DIR = PROJECT_DIR / "scripts"
WEEKLY_DIR = PROJECT_DIR / "weekly"

sys.path.insert(0, str(SCRIPT_DIR))


def _extract_issue_from_html(path: Path) -> int:
    try:
        match = re.search(r"第\s*(\d+)\s*期", path.read_text(encoding="utf-8"))
        return int(match.group(1)) if match else 0
    except (OSError, ValueError):
        return 0


def _auto_issue_for_date(report_date: datetime) -> int:
    """同一报告日期复用期号；新日期才按历史周报顺延。"""
    current = WEEKLY_DIR / f"创新常州·对标快讯_周报_{report_date:%Y%m%d}.html"
    existing = _extract_issue_from_html(current) if current.exists() else 0
    if existing > 0:
        return existing
    return max(
        (_extract_issue_from_html(path)
         for path in WEEKLY_DIR.glob("创新常州·对标快讯_周报_*.html")),
        default=0,
    ) + 1


def _last_generated_issue() -> int:
    return max(
        (_extract_issue_from_html(path)
         for path in WEEKLY_DIR.glob("创新常州·对标快讯_周报_*.html")),
        default=0,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="《创新常州·对标快讯》周报生成")
    parser.add_argument("--json", type=str, default="", help="指定周报 JSON 文件")
    parser.add_argument("--skip-distribute", action="store_true", help="跳过桌面分发")
    parser.add_argument("--force", action="store_true", help="强制生成（跳过周五检测）")
    parser.add_argument("--issue", type=int, default=0, help="手动指定期号；默认按报告日期自动确定")
    args = parser.parse_args()

    print("=" * 60)
    print("  创新常州·对标快讯 — 周报自动生成（JSON → HTML → PDF）")
    print("=" * 60)

    today = datetime.now()
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    historical_issue = _last_generated_issue()
    print(f"[最近一期] 第{historical_issue}期" if historical_issue else "[最近一期] 暂无已生成周报")

    # 非周五提醒
    if today.weekday() != 4 and not args.force:
        print(f"[提示] 今天是周{today.weekday() + 1}，非周五。周报通常周五生成。")
        print("如需强制生成，请使用 --force")

    # 确定 JSON 文件
    if args.json:
        json_path = Path(args.json)
    else:
        today_stem = today.strftime("%Y%m%d")
        json_path = WEEKLY_DIR / f"report_weekly_{today_stem}.json"

    if not json_path.exists():
        print(f"[错误] JSON 文件不存在: {json_path}")
        print("请先准备周报数据文件（格式见 weekly/report_weekly_20260706.json）")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_items = sum(len(s.get("items", [])) for s in data.get("sections", []))
    print(f"[读入] {total_items} 条信息，分布在 {len(data.get('sections', []))} 个板块")

    # 校验
    from validate_report import validate_report, print_validation_report
    errors, warnings = validate_report(data, "weekly")
    print_validation_report(errors, warnings)

    # 生成 HTML → PDF
    from build_weekly_pdf import build_weekly_html
    from generate_html_pdf import html_to_pdf

    date_cn = today.strftime("%Y年%m月%d日")
    issue = args.issue if args.issue > 0 else _auto_issue_for_date(today)
    total = issue
    html = build_weekly_html(data, date_cn, issue, total)

    date_stem = today.strftime("%Y%m%d")
    output_pdf = WEEKLY_DIR / f"创新常州·对标快讯_周报_{date_stem}.pdf"
    output_pdf = html_to_pdf(html, output_pdf)

    # 保存 HTML
    html_path = WEEKLY_DIR / f"创新常州·对标快讯_周报_{date_stem}.html"
    html_path.write_text(html, encoding="utf-8")

    # 分发
    if not args.skip_distribute:
        sys.path.insert(0, str(SCRIPT_DIR))
        from distribute import save_desktop
        desktop_pdf = save_desktop(str(output_pdf), "weekly")
    else:
        desktop_pdf = None

    print(f"\n[完成] 周报已生成:")
    print(f"  PDF: {output_pdf}")
    if desktop_pdf:
        print(f"  桌面: {desktop_pdf}")
    print(f"  期号: 2026年第{issue}期 / 总第{total}期")
    print("=" * 60)


if __name__ == "__main__":
    main()
