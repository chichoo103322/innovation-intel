#!/usr/bin/env python3
"""
《创新常州·对标快讯》日报全自动流水线
真实信源采集 → AI 摘要+洞察 → HTML → PDF → 去重 → 分发

新管线：不再使用 AI 联网搜索（存在编造风险），改为：
  1. crawler.py 从 .gov.cn 等权威网站真实采集近3天信息
  2. AI 基于真实素材进行摘要和洞察（不联网，不编造）
  3. 双层校验（validate_report + fact_check）

用法:
    python3 run_daily.py                          # 生成今日日报
    python3 run_daily.py --dry-run                # 仅采集分析，不生成文件不分发
    python3 run_daily.py --skip-distribute        # 跳过邮件/飞书/桌面分发
"""

import sys
import os
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


def get_api_key(config: dict) -> str:
    """从环境变量或配置文件获取 DeepSeek API Key"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    return config.get("deepseek_api_key", "")


# ---------------------------------------------------------------------------
# 去重
# ---------------------------------------------------------------------------

def dedup_sections(sections: list[dict]) -> list[dict]:
    sys.path.insert(0, str(SCRIPT_DIR))
    from dedup import check_duplicate

    filtered = []
    skipped = 0
    for section in sections:
        new_items = []
        for item in section.get("items", []):
            is_dup, date = check_duplicate(
                title=item.get("title", ""),
                url=item.get("url", "")
            )
            if is_dup:
                print(f"[去重] 跳过: {item.get('title', '')[:50]}... (已于{date}使用)")
                skipped += 1
            else:
                new_items.append(item)
        if new_items:
            filtered.append({"name": section["name"], "items": new_items})
    if skipped:
        print(f"[去重] 共跳过 {skipped} 条重复信息")
    return filtered


def mark_dedup(sections: list[dict]):
    sys.path.insert(0, str(SCRIPT_DIR))
    from dedup import mark_used

    for section in sections:
        for item in section.get("items", []):
            mark_used(title=item.get("title", ""), url=item.get("url", ""))
    print(f"[去重] 已标记所有条目")


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
    args = parser.parse_args()

    print("=" * 60)
    print("  创新常州·对标快讯 — 日报自动生成流水线（新管线）")
    print("=" * 60)

    today = datetime.now()

    # 周末自动跳过
    if today.weekday() >= 5 and not args.force:
        print(f"[跳过] 今天是周末，不生成日报。如需强制生成请使用 --force")
        return

    # 今天已生成过则跳过
    daily_dir = PROJECT_DIR / "daily"
    today_stem = today.strftime("%Y-%m-%d")
    today_pdf = daily_dir / f'创新常州·对标快讯_{today_stem}.pdf'
    if today_pdf.exists() and not args.force:
        print(f"[跳过] 今日日报已存在: {today_pdf}")
        return

    config = load_config()
    api_key = get_api_key(config)
    if not api_key and not args.sample:
        print("[错误] 未找到 DEEPSEEK_API_KEY。")
        print("请设置环境变量: export DEEPSEEK_API_KEY='sk-...'")
        print("或在 config/settings.yaml 中配置 deepseek_api_key")
        sys.exit(1)

    today = datetime.now()
    today_cn = today.strftime("%Y年%m月%d日")

    # 1. 新管线：真实信源采集 + AI 摘要洞察
    sys.path.insert(0, str(SCRIPT_DIR))
    from generate_html_pdf import get_daily_data, build_daily_html, html_to_pdf

    data = get_daily_data(api_key=api_key, sample=args.sample)
    sections = data.get("sections", [])

    if not sections:
        print("[错误] 未获取到任何情报数据")
        sys.exit(1)

    total_items = sum(len(s.get("items", [])) for s in sections)
    print(f"[结果] 基于真实素材生成 {total_items} 条信息，分布在 {len(sections)} 个板块")

    # 2. 去重
    sections = dedup_sections(sections)
    remaining = sum(len(s.get("items", [])) for s in sections)
    if remaining == 0:
        print("[错误] 去重后无剩余条目，今日可能已生成过日报")
        sys.exit(1)
    print(f"[去重后] 剩余 {remaining} 条信息")

    if args.dry_run:
        print("\n[Dry-run] 预览内容:")
        for section in sections:
            print(f"\n  【{section['name']}】")
            for item in section.get("items", []):
                print(f"    ► {item.get('title', '')} ({item.get('date', '')})")
                print(f"      来源: {item.get('source', '')}")
                print(f"      URL: {item.get('url', '')}")
        return

    # ── 后处理校验管道 ──
    if not args.sample and api_key:
        print("\n" + "=" * 65)
        print("  启动后处理校验管道（日报）")
        print("=" * 65)

        # 第1层：正则后处理校验
        from validate_report import validate_report, print_validation_report
        errors, warnings = validate_report(data, "daily")
        print_validation_report(errors, warnings)

        if errors:
            print("\n⚠️  校验发现错误，但仍继续生成 PDF（错误已标记在日志中）")

        # 第2层：事实核查（基于采集素材比对）
        from fact_check import fact_check_against_sources, print_fact_check_report
        crawled_cache = CACHE_DIR / "crawled_sources_daily.json"
        if crawled_cache.exists():
            with open(crawled_cache, "r", encoding="utf-8") as f:
                crawled_data = json.load(f)
            fc_result = fact_check_against_sources(data, crawled_data)
            fc_passed = print_fact_check_report(fc_result)
            if not fc_passed:
                print("\n⚠️  事实核查发现疑点，请人工复核")
        else:
            print("\n  ⚠️  无采集素材缓存，跳过事实核查")

    # 3. 生成 HTML → PDF
    from generate_docx import get_issue_numbers

    issue, total = get_issue_numbers()
    date_cn = today.strftime("%Y年%m月%d日")
    html = build_daily_html(data, date_cn, issue, total)
    pdf_path = html_to_pdf(html, today_pdf)

    # 保存 HTML
    html_path = daily_dir / f'创新常州·对标快讯_{today_stem}.html'
    html_path.write_text(html, encoding="utf-8")

    # 4. 去重记录
    mark_dedup(sections)

    # 5. 分发
    if not args.skip_distribute:
        do_distribute(str(pdf_path))

    print(f"\n[完成] 今日日报已生成并分发: {pdf_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
