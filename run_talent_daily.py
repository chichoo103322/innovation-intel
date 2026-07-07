#!/usr/bin/env python3
"""常州人才·对标快讯 日报自动生成"""
import sys, json, argparse, re
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent
SCRIPT_DIR = PROJECT_DIR / "scripts"
CACHE_DIR = PROJECT_DIR / "cache"

sys.path.insert(0, str(SCRIPT_DIR))
from dedup import check_duplicate as check_dup_3layer, mark_pending, commit_pending, rollback_pending
from generate_html_pdf import html_to_pdf, get_issue_numbers
from build_talent_html import build_talent_daily_html
from validate_report import validate_report, print_validation_report
import shutil


def dedup_sections(sections):
    filtered = []
    skipped = 0
    for section in sections:
        new_items = []
        for item in section.get("items", []):
            title = item.get("title", "")
            url = item.get("url", "")
            policy_match = re.search(r'《([^》]+)》', title)
            policy = policy_match.group(1) if policy_match else ""
            is_dup, dup_date, reason = check_dup_3layer(
                title=title, url=url,
                date=item.get("date", ""), institution=item.get("source", ""), policy=policy
            )
            if is_dup:
                print(f"[去重] 跳过: {title[:50]}... ({reason})")
                skipped += 1
            else:
                new_items.append(item)
        if new_items:
            filtered.append({"name": section["name"], "items": new_items})
    if skipped:
        print(f"[去重] 共跳过 {skipped} 条")
    return filtered


def mark_pending_items(sections):
    for section in sections:
        for item in section.get("items", []):
            policy_match = re.search(r'《([^》]+)》', item.get("title", ""))
            policy = policy_match.group(1) if policy_match else ""
            mark_pending(
                title=item.get("title", ""), url=item.get("url", ""),
                date=item.get("date", ""), institution=item.get("source", ""), policy=policy
            )


def main():
    parser = argparse.ArgumentParser(description="常州人才·对标快讯 日报")
    parser.add_argument("--from-json", type=str, default="", help="从 JSON 生成")
    parser.add_argument("--force", action="store_true", help="强制覆盖")
    args = parser.parse_args()

    today = datetime.now()
    talent_dir = PROJECT_DIR / "talent_daily"
    desktop_dir = Path("/Users/jzxzhou/Desktop/人才快讯/日报")
    desktop_dir.mkdir(parents=True, exist_ok=True)

    if args.from_json:
        json_path = Path(args.from_json)
        if not json_path.exists():
            print(f"[错误] JSON 不存在: {json_path}")
            sys.exit(1)

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sections = data.get("sections", [])
        total_items = sum(len(s.get("items", [])) for s in sections)
        print(f"[读入] {total_items} 条信息，{len(sections)} 个板块")

        # 去重
        sections = dedup_sections(sections)
        remaining = sum(len(s.get("items", [])) for s in sections)
        if remaining == 0:
            print("[错误] 去重后无剩余条目")
            sys.exit(1)
        data["sections"] = sections

        # 校验
        errors, warnings = validate_report(data, "daily")
        print_validation_report(errors, warnings)

        # 暂存去重
        mark_pending_items(sections)

        # 生成 PDF
        today_stem = today.strftime("%Y-%m-%d")
        date_cn = today.strftime("%Y年%m月%d日")
        issue, total = get_issue_numbers()
        html = build_talent_daily_html(data, date_cn, issue, total)
        pdf_path = talent_dir / f"常州人才·对标快讯_{today_stem}.pdf"
        html_to_pdf(html, pdf_path)

        html_path = talent_dir / f"常州人才·对标快讯_{today_stem}.html"
        html_path.write_text(html, encoding="utf-8")

        # 分发
        dest = desktop_dir / pdf_path.name
        shutil.copy2(pdf_path, dest)
        print(f"[分发] 已保存到: {dest}")

        # 提交去重
        commit_pending()

        print(f"\n[完成] 人才日报已生成: {pdf_path}")
        return

    print("[提示] 用法: python3 run_talent_daily.py --from-json talent_daily/report_data_YYYY-MM-DD.json")


if __name__ == "__main__":
    main()
