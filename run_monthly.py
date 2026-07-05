#!/usr/bin/env python3
"""
《创新常州·对标快讯》月报自动生成
联网搜索 → 月度战略分析 → HTML → PDF → 分发
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).parent
SCRIPT_DIR = PROJECT_DIR / "scripts"

sys.path.insert(0, str(SCRIPT_DIR))


def main():
    print("=" * 60)
    print("  创新常州·对标快讯 — 月报自动生成（HTML→PDF）")
    print("=" * 60)

    from generate_html_pdf import generate_monthly

    # 获取 API Key
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        from run_daily import load_config, get_api_key as gk
        api_key = gk(load_config())

    if not api_key and "--sample" not in sys.argv:
        print("[提示] 无 API Key，使用示例数据")
        sys.argv.append("--sample")

    sample = "--sample" in sys.argv

    # 判断是否是月末
    today = datetime.now()
    month_cn = today.strftime("%Y年%m月")
    if not (today + timedelta(days=1)).day == 1 and "--force" not in sys.argv:
        print(f"[提示] 今天不是本月最后一天。月报通常在月末生成。")
        print("如需强制生成，请使用 --force")
        if "--force" not in sys.argv:
            return

    # 输出路径
    date_fn = today.strftime("%Y%m")
    output = PROJECT_DIR / "monthly" / f"创新常州·对标快讯_月报_{date_fn}.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)

    pdf_path = generate_monthly(api_key=api_key if not sample else None,
                                output_path=str(output), sample=sample)

    # 分发
    from distribute import save_desktop
    print("\n=== 分发月报 ===")
    save_desktop(str(pdf_path), "monthly")
    print("=== 完成 ===")


if __name__ == "__main__":
    main()
