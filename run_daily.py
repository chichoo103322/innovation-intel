#!/usr/bin/env python3
"""
《创新常州·对标快讯》日报自动生成
JSON 数据 → HTML → PDF → 分发

用法:
    python3 run_daily.py --from-json daily/report_data_xxx.json  # 从 JSON 生成 PDF
    python3 run_daily.py --collect                                 # 输出 JSON 模板
    python3 run_daily.py --sample                                  # 使用示例数据预览
    python3 run_daily.py --skip-distribute                         # 不分发
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent
SCRIPT_DIR = PROJECT_DIR / "scripts"
CACHE_DIR = PROJECT_DIR / "cache"
CONFIG_FILE = PROJECT_DIR / "config" / "settings.yaml"


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def load_config():
    """简易 YAML 加载"""
    config = {}
    current_section = None
    current_subsection = None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("---"):
                continue
            indent = len(line) - len(line.lstrip())

            if indent == 0 and ":" in stripped:
                key, _, val = stripped.partition(":")
                key, raw_val = key.strip(), val.strip()
                if raw_val:
                    config[key] = _parse_val(_clean_val(raw_val))
                    current_subsection = None
                else:
                    current_section = key
                    config[current_section] = {}
                    current_subsection = None
            elif indent == 2 and ":" in stripped and not stripped.startswith("-"):
                key, _, val = stripped.partition(":")
                key, raw_val = key.strip(), val.strip()
                if raw_val and current_section:
                    config[current_section][key] = _parse_val(_clean_val(raw_val))
                elif raw_val is None or raw_val == "":
                    if current_section:
                        current_subsection = key
                        if current_subsection not in config[current_section]:
                            config[current_section][current_subsection] = {}
            elif indent == 4 and ":" in stripped and current_subsection:
                key, _, val = stripped.partition(":")
                key = key.strip()
                config[current_section][current_subsection][key] = _parse_val(_clean_val(val))
    return config


def _parse_val(val: str):
    if val == "true":
        return True
    if val == "false":
        return False
    try:
        return int(val)
    except ValueError:
        return val


def _clean_val(raw_val: str) -> str:
    """提取冒号后的值，去掉注释和引号"""
    v = raw_val.strip()
    if " #" in v:
        v = v.split(" #")[0].strip()
    if "  #" in v:
        v = v.split("  #")[0].strip()
    if v.startswith('"') and v.endswith('"'):
        v = v[1:-1]
    elif v.startswith("'") and v.endswith("'"):
        v = v[1:-1]
    return v


# ---------------------------------------------------------------------------
# 去重（三层：精确匹配 + 模糊匹配 + 事实指纹）
# ---------------------------------------------------------------------------

def dedup_sections(sections: list[dict]) -> list[dict]:
    sys.path.insert(0, str(SCRIPT_DIR))
    from dedup import check_duplicate as check_dup_3layer

    filtered = []
    skipped = 0
    for section in sections:
        new_items = []
        for item in section.get("items", []):
            title = item.get("title", "")
            url = item.get("url", "")
            date_i = item.get("date", "")
            source = item.get("source", "")
            # 提取政策名用于指纹
            import re
            policy_match = re.search(r'《([^》]+)》', title)
            policy = policy_match.group(1) if policy_match else ""

            is_dup, dup_date, reason = check_dup_3layer(
                title=title, url=url,
                date=date_i, institution=source, policy=policy
            )
            if is_dup:
                print(f"[去重] 跳过: {title[:50]}... ({reason})")
                skipped += 1
            else:
                new_items.append(item)
        if new_items:
            filtered.append({"name": section["name"], "items": new_items})
    if skipped:
        print(f"[去重] 共跳过 {skipped} 条重复信息")
    return filtered


def mark_dedup_pending(sections: list[dict]):
    """写入待确认区（事务性标记，PDF成功后才提交）"""
    sys.path.insert(0, str(SCRIPT_DIR))
    from dedup import mark_pending

    for section in sections:
        for item in section.get("items", []):
            import re
            policy_match = re.search(r'《([^》]+)》', item.get("title", ""))
            policy = policy_match.group(1) if policy_match else ""
            mark_pending(
                title=item.get("title", ""),
                url=item.get("url", ""),
                date=item.get("date", ""),
                institution=item.get("source", ""),
                policy=policy
            )
    print(f"[去重] 已暂存所有条目至待确认区")


def commit_dedup():
    """PDF生成成功后，提交去重记录"""
    sys.path.insert(0, str(SCRIPT_DIR))
    from dedup import commit_pending
    commit_pending()


def rollback_dedup():
    """生成失败时回滚去重记录"""
    sys.path.insert(0, str(SCRIPT_DIR))
    from dedup import rollback_pending
    rollback_pending()


# ---------------------------------------------------------------------------
# 分发
# ---------------------------------------------------------------------------

def do_distribute(file_path: str):
    sys.path.insert(0, str(SCRIPT_DIR))
    from distribute import save_desktop

    print(f"\n=== 分发报告: {file_path} ===\n")
    save_desktop(file_path, "daily")
    print("=== 分发完成 ===")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="《创新常州·对标快讯》日报自动生成")
    parser.add_argument("--dry-run", action="store_true", help="仅采集分析，不生成文件")
    parser.add_argument("--skip-distribute", action="store_true", help="不分发")
    parser.add_argument("--force", action="store_true", help="强制生成，跳过周末/重复检测")
    parser.add_argument("--sample", action="store_true", help="使用示例数据")
    parser.add_argument("--collect", action="store_true",
                        help="仅采集信源+输出搜索简报（供 Claude Code 搜索+写作）")
    parser.add_argument("--from-json", type=str, default="",
                        help="从预写的报告 JSON 文件生成 HTML/PDF（跳过 AI 调用）")
    args = parser.parse_args()

    print("=" * 60)
    print("  创新常州·对标快讯 — 日报自动生成流水线")
    print("=" * 60)

    today = datetime.now()
    today_stem = today.strftime("%Y-%m-%d")
    daily_dir = PROJECT_DIR / "daily"

    # 周末自动跳过
    if today.weekday() >= 5 and not args.force and not args.collect:
        print(f"[跳过] 今天是周末，不生成日报。如需强制生成请使用 --force")
        return

    # ── 模式 1: --from-json（从预写 JSON 生成报告）──
    if args.from_json:
        from_json_path = Path(args.from_json)
        if not from_json_path.exists():
            print(f"[错误] JSON 文件不存在: {from_json_path}")
            sys.exit(1)
        with open(from_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sections = data.get("sections", [])
        if not sections:
            print("[错误] JSON 中无 sections 数据")
            sys.exit(1)
        total_items = sum(len(s.get("items", [])) for s in sections)
        print(f"[读入] {total_items} 条信息，分布在 {len(sections)} 个板块")

        # 去重
        sections = dedup_sections(sections)
        remaining = sum(len(s.get("items", [])) for s in sections)
        if remaining == 0:
            print("[错误] 去重后无剩余条目")
            sys.exit(1)
        print(f"[去重后] 剩余 {remaining} 条信息")
        data["sections"] = sections

        # 校验
        config = load_config()
        sys.path.insert(0, str(SCRIPT_DIR))
        from validate_report import validate_report, print_validation_report
        errors, warnings = validate_report(data, "daily")
        print_validation_report(errors, warnings)

        from fact_check import fact_check_against_sources, print_fact_check_report
        crawled_cache = CACHE_DIR / "crawled_sources_daily.json"
        if crawled_cache.exists():
            with open(crawled_cache, "r", encoding="utf-8") as f:
                crawled_data = json.load(f)
            fc_result = fact_check_against_sources(data, crawled_data)
            print_fact_check_report(fc_result)

        # 去重记录
        mark_dedup_pending(sections)

        # 检查是否已有今日 PDF
        today_pdf = daily_dir / f'创新常州·对标快讯_{today_stem}.pdf'
        if today_pdf.exists() and not args.force:
            print(f"[跳过] 今日日报已存在: {today_pdf}")
            return

        # 生成 HTML → PDF
        from generate_html_pdf import build_daily_html, html_to_pdf
        from generate_html_pdf import get_issue_numbers
        issue, total = get_issue_numbers()
        date_cn = today.strftime("%Y年%m月%d日")
        html = build_daily_html(data, date_cn, issue, total)
        pdf_path = html_to_pdf(html, today_pdf)

        html_path = daily_dir / f'创新常州·对标快讯_{today_stem}.html'
        html_path.write_text(html, encoding="utf-8")

        # 分发
        if not args.skip_distribute:
            do_distribute(str(pdf_path))

        print(f"\n[完成] 今日日报已生成并分发: {pdf_path}")
        print("=" * 60)
        return

    # ── 模式 2: --collect（输出 JSON 模板供手动填写）──
    if args.collect:
        all_dimensions = ["各地科技委动态", "上海（长三角）国创中心资讯", "科创政策速览", "改革举措"]

        print(f"\n{'='*65}")
        print(f"  日报 JSON 模板（请填写后使用 --from-json 生成 PDF）")
        print(f"{'='*65}\n")

        template = {
            "sections": [
                {"name": d, "items": [
                    {"title": "", "date": "", "summary": "", "insight": ["方案A：", "方案B：", "方案C："], "source": "", "url": ""}
                ]} for d in all_dimensions
            ]
        }
        template_path = daily_dir / "report_data_template.json"
        template_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[模板] 已写入: {template_path}")
        print(f"  填写完成后运行: python3 run_daily.py --from-json {template_path}")
        return

    # ── 模式 3: --sample（使用示例数据快速预览）──
    if args.sample:
        sys.path.insert(0, str(SCRIPT_DIR))
        from generate_html_pdf import build_daily_html, html_to_pdf, get_issue_numbers
        from generate_html_pdf import _sample_data

        data = _sample_data()
        sections = data.get("sections", [])
        total_items = sum(len(s.get("items", [])) for s in sections)
        print(f"[示例] {total_items} 条示例信息")

        today_pdf = daily_dir / f'创新常州·对标快讯_{today_stem}.pdf'
        issue, total = get_issue_numbers()
        date_cn = today.strftime("%Y年%m月%d日")
        html = build_daily_html(data, date_cn, issue, total)
        pdf_path = html_to_pdf(html, today_pdf)

        html_path = daily_dir / f'创新常州·对标快讯_{today_stem}.html'
        html_path.write_text(html, encoding="utf-8")

        print(f"[完成] 示例日报: {pdf_path}")
        return

    # ── 无参数默认：提示使用方法 ──
    print("[提示] 请使用以下方式之一：")
    print(f"  python3 run_daily.py --from-json daily/report_data_YYYYMMDD.json")
    print(f"  python3 run_daily.py --collect  （输出 JSON 模板）")
    print(f"  python3 run_daily.py --sample   （使用示例数据快速预览）")


if __name__ == "__main__":
    main()
