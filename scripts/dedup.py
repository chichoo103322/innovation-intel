#!/usr/bin/env python3
"""
三层去重管理系统 —— 防止日报/周报/月报出现重复信息

用法:
  python3 dedup.py check "标题" "URL"           → 检查是否已用（精确+模糊）
  python3 dedup.py similar "标题"                → 查相似标题（返回相似度最高的条目）
  python3 dedup.py mark "标题" "URL"             → 标记为已用（精确记录）
  python3 dedup.py pending "标题" "URL"          → 写入待确认区
  python3 dedup.py commit                        → 将待确认区提交为正式记录
  python3 dedup.py rollback                      → 清空待确认区（生成失败时回滚）
  python3 dedup.py clean                         → 清理30天前的旧记录
  python3 dedup.py status                        → 显示统计
  python3 dedup.py fingerprint "date|inst|name"  → 检查事实指纹是否重复
"""
import json
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

CACHE_DIR = Path(__file__).parent.parent / "cache"
TRACK_FILE = CACHE_DIR / "used_items.json"
PENDING_FILE = CACHE_DIR / "pending_items.json"


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

def load_tracking():
    if not TRACK_FILE.exists():
        return {"titles": {}, "urls": {}, "fingerprints": {}, "last_cleanup": ""}
    with open(TRACK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tracking(data):
    TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_pending():
    if not PENDING_FILE.exists():
        return {"titles": {}, "urls": {}, "fingerprints": {}}
    with open(PENDING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pending(data):
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def auto_clean():
    """自动清理30天前的记录"""
    data = load_tracking()
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    cleaned = 0
    for store in ["titles", "urls", "fingerprints"]:
        if store not in data:
            data[store] = {}
        stale = [k for k, v in data[store].items() if v < cutoff]
        for k in stale:
            del data[store][k]
            cleaned += 1

    data["last_cleanup"] = today
    save_tracking(data)
    if cleaned:
        print(f"[清理] 已移除 {cleaned} 条超过30天的旧记录")


# ---------------------------------------------------------------------------
# 文本标准化
# ---------------------------------------------------------------------------

def normalize(text: str, for_fuzzy: bool = False) -> str:
    """标准化文本用于匹配"""
    t = text.strip().replace(" ", "").replace("\n", "").replace("\r", "")
    if for_fuzzy:
        # 去标点、去括号内容、保留核心词
        t = re.sub(r'[《》""''「」【】（）()\[\]{}:：、，,。；;！!？?…—\-·]', '', t)
        t = re.sub(r'[“”‘’]', '', t)  # 中文引号
    return t


def extract_keywords(text: str) -> set:
    """从标题中提取关键词（2字以上非停用词）"""
    stopwords = {'的', '了', '在', '是', '和', '与', '及', '或', '对', '为', '以',
                 '将', '已', '被', '把', '向', '从', '到', '等', '其', '于', '之',
                 '一个', '这个', '该', '据', '称', '发布', '印发', '出台', '提出',
                 '表示', '指出', '报道', '显示', '披露'}
    # 简单分词：按标点、空格切分
    tokens = re.split(r'[\s,，、。；;！!？?“”‘’《》【】\(\)\[\]{}:：…—\-·]', text)
    return {t for t in tokens if len(t) >= 2 and t not in stopwords}


def similarity(a: str, b: str) -> float:
    """计算两段文本的相似度（0~1），基于关键词 Jaccard + 字面重叠"""
    # 关键词 Jaccard 相似度
    kw_a = extract_keywords(a)
    kw_b = extract_keywords(b)
    if not kw_a or not kw_b:
        return 0.0
    jaccard = len(kw_a & kw_b) / len(kw_a | kw_b)

    # 字面重叠度（最长公共子序列比例）
    na = normalize(a, True)
    nb = normalize(b, True)
    shorter = min(len(na), len(nb))
    if shorter == 0:
        return jaccard

    # 简单字符级重叠度
    overlap = sum(1 for c in set(na) if c in set(nb))
    char_sim = overlap / len(set(na) | set(nb)) if set(na) | set(nb) else 0

    # 加权：Jaccard 70% + 字符重叠 30%
    return jaccard * 0.7 + char_sim * 0.3


def make_fingerprint(date: str = "", institution: str = "", policy_name: str = "") -> str:
    """生成关键事实指纹：日期+机构+政策名 -> hash"""
    import hashlib
    core = f"{date}|{institution}|{policy_name}"
    return hashlib.md5(core.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# 第一层：精确匹配（标题/URL 完全相同）
# ---------------------------------------------------------------------------

def check_exact(title: str = "", url: str = "") -> tuple:
    """精确匹配检查。返回 (is_dup, matched_date, matched_key)"""
    data = load_tracking()
    auto_clean()

    if title:
        norm = normalize(title)
        for t, date in data["titles"].items():
            if normalize(t) == norm:
                return True, date, t

    if url:
        norm = normalize(url)
        for u, date in data["urls"].items():
            if normalize(u) == norm:
                return True, date, u

    return False, "", ""


# ---------------------------------------------------------------------------
# 第二层：模糊匹配（相似度 > 阈值）
# ---------------------------------------------------------------------------

def check_similar(title: str = "", threshold: float = 0.65) -> list:
    """查找相似标题，返回 [(相似度, 已用标题, 日期), ...]，按相似度降序"""
    data = load_tracking()
    auto_clean()

    if not title:
        return []

    results = []
    norm_new = normalize(title)
    for t, date in data["titles"].items():
        sim = similarity(title, t)
        if sim >= threshold:
            results.append((sim, t, date))

    results.sort(key=lambda x: x[0], reverse=True)
    return results


# ---------------------------------------------------------------------------
# 第三层：事实指纹（同一事件的不同报道）
# ---------------------------------------------------------------------------

def check_fingerprint(fp: str) -> tuple:
    """检查指纹是否已存在。返回 (is_dup, matched_date)"""
    data = load_tracking()
    if fp in data.get("fingerprints", {}):
        return True, data["fingerprints"][fp]
    return False, ""


# ---------------------------------------------------------------------------
# 综合去重检查
# ---------------------------------------------------------------------------

def check_duplicate(title: str = "", url: str = "",
                    date: str = "", institution: str = "", policy: str = "") -> tuple:
    """三层综合去重检查。返回 (is_dup, date, reason)"""
    # 第一层：精确匹配
    is_dup, matched_date, matched = check_exact(title, url)
    if is_dup:
        return True, matched_date, f"精确匹配: {matched[:60]}"

    # 第二层：模糊匹配
    similar = check_similar(title, threshold=0.65)
    if similar:
        sim, t, d = similar[0]
        if sim >= 0.80:
            return True, d, f"高度相似({sim:.0%}): {t[:60]}"
        elif sim >= 0.65:
            print(f"[去重告警] 标题相似度 {sim:.0%}: '{title[:60]}' vs '{t[:60]}' (于{d}使用)")

    # 第三层：事实指纹
    if date or institution or policy:
        fp = make_fingerprint(date, institution, policy)
        is_dup, matched_date = check_fingerprint(fp)
        if is_dup:
            return True, matched_date, f"事实指纹重复: {fp}"

    return False, "", ""


# ---------------------------------------------------------------------------
# 标记与事务管理
# ---------------------------------------------------------------------------

def mark_used(title: str = "", url: str = "",
              date: str = "", institution: str = "", policy: str = ""):
    """直接标记为已用（精确记录）"""
    data = load_tracking()
    today = datetime.now().strftime("%Y-%m-%d")

    if title:
        data["titles"][title.strip()] = today
    if url:
        data["urls"][url.strip()] = today
    if date or institution or policy:
        fp = make_fingerprint(date, institution, policy)
        data.setdefault("fingerprints", {})[fp] = today

    save_tracking(data)


def mark_pending(title: str = "", url: str = "",
                 date: str = "", institution: str = "", policy: str = ""):
    """写入待确认区（事务性标记，需 commit 后才生效）"""
    pending = load_pending()
    today = datetime.now().strftime("%Y-%m-%d")

    if title:
        pending["titles"][title.strip()] = today
    if url:
        pending["urls"][url.strip()] = today
    if date or institution or policy:
        fp = make_fingerprint(date, institution, policy)
        pending.setdefault("fingerprints", {})[fp] = today

    save_pending(pending)
    print(f"[待确认] 已暂存 {len(pending['titles'])} 条，等待 PDF 生成成功后提交")


def commit_pending():
    """将待确认区提交为正式去重记录（PDF 生成成功后调用）"""
    pending = load_pending()
    if not pending.get("titles") and not pending.get("urls"):
        print("[提交] 无待确认条目")
        return

    data = load_tracking()
    for store in ["titles", "urls", "fingerprints"]:
        if store in pending:
            data.setdefault(store, {}).update(pending[store])

    save_tracking(data)

    # 清空待确认区
    save_pending({"titles": {}, "urls": {}, "fingerprints": {}})

    count = sum(len(v) for v in pending.values())
    print(f"[提交] 已确认 {count} 条去重记录")


def rollback_pending():
    """清空待确认区（生成失败时调用）"""
    pending = load_pending()
    count = sum(len(v) for v in pending.values())
    save_pending({"titles": {}, "urls": {}, "fingerprints": {}})
    if count:
        print(f"[回滚] 已清除 {count} 条待确认记录（生成失败回滚）")


# ---------------------------------------------------------------------------
# 跨报告去重
# ---------------------------------------------------------------------------

def check_cross_report(title: str = "", days: int = 7) -> list:
    """检查该条目是否出现在其他报告中（日报 vs 周报）"""
    data = load_tracking()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    results = []
    if title:
        norm = normalize(title, True)
        for t, date in data["titles"].items():
            if date >= cutoff and normalize(t, True) == norm:
                results.append((t, date))

    # 模糊匹配
    similar = check_similar(title, threshold=0.75)
    for sim, t, date in similar:
        if date >= cutoff and (t, date) not in results:
            results.append((t, date))

    return results


# ---------------------------------------------------------------------------
# 状态查询
# ---------------------------------------------------------------------------

def status():
    """显示统计信息"""
    data = load_tracking()
    pending = load_pending()
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cutoff_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    recent_7 = sum(1 for v in data["titles"].values() if v >= cutoff_7)
    recent_30 = sum(1 for v in data["titles"].values() if v >= cutoff_30)
    total = len(data["titles"])
    fp_count = len(data.get("fingerprints", {}))
    pending_count = len(pending.get("titles", {}))

    print(f"去重追踪状态:")
    print(f"  总条目: {total} (标题) + {fp_count} (指纹)")
    print(f"  近7天: {recent_7} | 近30天: {recent_30}")
    print(f"  待确认区: {pending_count} 条")
    print(f"  最近7天已用标题:")
    for t in get_recent_titles(7):
        print(f"    - {t}")


def get_recent_titles(days: int = 7):
    """获取最近N天已用的标题列表"""
    data = load_tracking()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [t for t, d in data["titles"].items() if d >= cutoff]


def get_recent_urls(days: int = 7):
    """获取最近N天已用的URL列表"""
    data = load_tracking()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [u for u, d in data["urls"].items() if d >= cutoff]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 dedup.py [check|similar|mark|pending|commit|rollback|clean|status|fingerprint|recent|cross] [参数...]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "check":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        url = sys.argv[3] if len(sys.argv) > 3 else ""
        is_dup, date, reason = check_duplicate(title, url)
        if is_dup:
            print(f"DUPLICATE:{date}:{reason}")
        else:
            print("NEW")

    elif cmd == "similar":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.65
        results = check_similar(title, threshold)
        if results:
            for sim, t, d in results:
                print(f"SIMILAR({sim:.0%}): {t[:80]} (于{d})")
        else:
            print("NO_SIMILAR")

    elif cmd == "mark":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        url = sys.argv[3] if len(sys.argv) > 3 else ""
        mark_used(title, url)
        print(f"[标记] 已记录: {title[:60]}...")

    elif cmd == "pending":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        url = sys.argv[3] if len(sys.argv) > 3 else ""
        mark_pending(title, url)
        print(f"[待确认] 已暂存: {title[:60]}...")

    elif cmd == "commit":
        commit_pending()

    elif cmd == "rollback":
        rollback_pending()

    elif cmd == "clean":
        auto_clean()

    elif cmd == "status":
        status()

    elif cmd == "fingerprint":
        fp = sys.argv[2] if len(sys.argv) > 2 else ""
        is_dup, date = check_fingerprint(fp)
        print(f"DUPLICATE:{date}" if is_dup else "NEW")

    elif cmd == "recent":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        print("\n".join(get_recent_titles(days)))

    elif cmd == "cross":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
        results = check_cross_report(title, days)
        if results:
            for t, d in results:
                print(f"CROSS_DUP: {t[:80]} (于{d})")
        else:
            print("NO_CROSS_DUP")
