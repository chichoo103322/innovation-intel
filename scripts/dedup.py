#!/usr/bin/env python3
"""
去重管理 —— 防止连续日推出现重复信息
用法: python3 dedup.py check "标题或URL"     → 检查是否已用过
      python3 dedup.py mark "标题" "URL"      → 标记为已用
      python3 dedup.py clean                  → 清理30天前的旧记录
      python3 dedup.py status                 → 显示统计
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

CACHE_DIR = Path(__file__).parent.parent / "cache"
TRACK_FILE = CACHE_DIR / "used_items.json"


def load_tracking():
    if not TRACK_FILE.exists():
        return {"titles": {}, "urls": {}, "last_cleanup": ""}
    with open(TRACK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tracking(data):
    TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def auto_clean():
    """自动清理30天前的记录"""
    data = load_tracking()
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    cleaned = 0
    for store in ["titles", "urls"]:
        stale = [k for k, v in data[store].items() if v < cutoff]
        for k in stale:
            del data[store][k]
            cleaned += 1

    data["last_cleanup"] = today
    save_tracking(data)
    if cleaned:
        print(f"[清理] 已移除 {cleaned} 条超过30天的旧记录")


def normalize(text: str) -> str:
    """标准化文本用于匹配（去空格、截断）"""
    return text.strip().replace(" ", "").replace("\n", "")[:80]


def check_duplicate(title="", url=""):
    """检查是否已存在，返回 (is_dup, matched_date)"""
    data = load_tracking()
    auto_clean()

    if title:
        norm = normalize(title)
        for t, date in data["titles"].items():
            if normalize(t) == norm:
                return True, date

    if url:
        norm = normalize(url)
        for u, date in data["urls"].items():
            if normalize(u) == norm:
                return True, date

    return False, ""


def mark_used(title="", url=""):
    """标记条目为已使用"""
    data = load_tracking()
    today = datetime.now().strftime("%Y-%m-%d")

    if title:
        data["titles"][title.strip()] = today
    if url:
        data["urls"][url.strip()] = today

    save_tracking(data)


def get_recent_titles(days: int = 7):
    """获取最近N天已用的标题列表（用于日报生成时参考）"""
    data = load_tracking()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [t for t, d in data["titles"].items() if d >= cutoff]


def status():
    """显示统计信息"""
    data = load_tracking()
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cutoff_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    recent_7 = sum(1 for v in data["titles"].values() if v >= cutoff_7)
    recent_30 = sum(1 for v in data["titles"].values() if v >= cutoff_30)
    total = len(data["titles"])

    print(f"去重追踪状态:")
    print(f"  总条目: {total}")
    print(f"  近7天: {recent_7}")
    print(f"  近30天: {recent_30}")
    print(f"  最近7天已用标题:")
    for t in get_recent_titles(7):
        print(f"    - {t}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 dedup.py [check|mark|clean|status] [参数...]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "check":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        url = sys.argv[3] if len(sys.argv) > 3 else ""
        is_dup, date = check_duplicate(title, url)
        if is_dup:
            print(f"DUPLICATE:{date}")
        else:
            print("NEW")

    elif cmd == "mark":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        url = sys.argv[3] if len(sys.argv) > 3 else ""
        mark_used(title, url)
        print(f"[标记] 已记录: {title[:60]}...")

    elif cmd == "clean":
        auto_clean()

    elif cmd == "status":
        status()

    elif cmd == "recent":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        print("\n".join(get_recent_titles(days)))
