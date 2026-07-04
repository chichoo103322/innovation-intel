#!/usr/bin/env python3
"""
分发脚本 —— 将日报/周报/月报复制到桌面/创新情报/{日报,周报,月报}/
用法: python3 distribute.py --type daily --file <报告文件路径>
"""
import sys
import os
import shutil
from pathlib import Path


def save_desktop(file_path: str, report_type: str):
    """保存报告到桌面对应子目录"""
    from run_daily import load_config
    try:
        cfg = load_config()
        output_dir = cfg.get("desktop_output_dir", "")
    except Exception:
        output_dir = ""
    if not output_dir:
        output_dir = str(Path.home() / "Desktop" / "创新情报")

    # 日报/周报/月报 存入对应子目录
    sub_dirs = {"daily": "日报", "weekly": "周报", "monthly": "月报"}
    sub = sub_dirs.get(report_type, "其他")
    dest_dir = os.path.join(output_dir, sub)
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    dest = os.path.join(dest_dir, os.path.basename(file_path))
    shutil.copy2(file_path, dest)
    print(f"[分发] 已保存到: {dest}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="分发创新情报报告")
    parser.add_argument("--type", choices=["daily", "weekly", "monthly"], required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    save_desktop(args.file, args.type)
