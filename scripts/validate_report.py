#!/usr/bin/env python3
"""
创新常州·对标快讯 —— AI 输出后处理校验层
对 AI 生成的情报内容进行多维度自动校验，在输出前拦截错误。

校验维度：
  1. 机构名称准确性（科技委≠科委）
  2. 信源权威性（.gov.cn 域名占比）
  3. 日期格式与时效性
  4. 数据精度（金额/百分比格式校验）
  5. 禁用词扫描（空话套话检测）
  6. 创新洞察深度（字数+必含关键词）
  7. 五大产业赛道覆盖率
  8. 板块完整性

用法:
    from validate_report import validate_report, print_validation_report
    errors, warnings = validate_report(data, report_type="weekly")
    print_validation_report(errors, warnings)
"""
import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

PROJECT_DIR = Path(__file__).parent.parent
CACHE_DIR = PROJECT_DIR / "cache"


# ══════════════════════════════════════════════════════════════
# 校验常量
# ══════════════════════════════════════════════════════════════

# 机构名称黑名单：绝对不能出现的错误名称
NAME_BLACKLIST = {
    "科委": "❌ 政治性错误：应为「科技委」（全称「中国共产党XX省/市委科技委员会」，党委议事协调机构），不是政府部门的「科委」",
}

# 常见错误名称 -> 正确名称
NAME_CORRECTIONS = {
    "G60科技走廊": "G60科创走廊",
    "沿沪宁创新走廊": "沿沪宁产业创新带",
    "中以创新园": "中以常州创新园",
    "长三角科创中心": "长三角国际科技创新中心",
    "长三角国创中心": "长三角国家技术创新中心",
}

# 禁用词列表（空洞套话，出现任一即标记）
BANNED_PHRASES = [
    "值得借鉴", "有参考价值", "值得关注", "值得学习", "值得研究",
    "应该加强", "应该重视", "建议重视", "意义重大", "影响深远",
    "高度重视", "进一步加大", "不断深化", "持续优化", "大力推进",
]

# 创新洞察必须包含的关键词（至少匹配2类）
INSIGHT_REQUIRED_KEYWORDS = {
    "五大产业": ["AIDC", "算力", "智算中心", "具身智能", "人形机器人", "智能体",
               "未来存储", "新型存储", "液冷", "浸没式冷却",
               "氢能", "新型储能", "钙钛矿", "虚拟电厂", "未来能源"],
    "产业基础": ["新能源", "高端装备", "新能源汽车", "比亚迪", "理想", "中创新航", "蜂巢能源", "智能制造"],
    "竞争对比": ["苏州", "无锡", "南京", "南通", "万亿城市", "竞争", "差异化", "错位"],
    "政策抓手": ["三名工程", "双高协同", "科教城", "高新区", "名园", "名院", "名企", "产业园", "开发区"],
    "行动建议": ["牵头", "对接", "申报", "试点", "设立", "出台", "建设", "推进", "布局"],
    "经济工作与企业调研": ["经济工作会议", "企业调研", "卡脖子", "产业链短板", "人才缺口", "融资需求",
                     "链主", "专精特新", "市委全会", "市政府常务会议", "攻坚", "园区配套"],
}

# 信源域名评分
DOMAIN_SCORES = {
    ".gov.cn": 100,
    "cas.cn": 85, "cae.cn": 85, "stdaily.com": 85, "cnki.net": 85,
    "xinhuanet.com": 70, "people.com.cn": 70,
    "thepaper.cn": 70, "cls.cn": 70,
    "36kr.com": 60, "pedaily.cn": 60, "ccidconsulting.com": 60,
}

# 可信日期格式
DATE_PATTERN = re.compile(r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?")
DATE_PATTERN_SHORT = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})")
DATE_PATTERN_CN = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")


def validate_report(data: dict, report_type: str = "weekly") -> tuple[list, list]:
    """
    对 AI 生成的报告数据进行全面校验。

    参数:
        data: AI 生成的 JSON 数据（含 sections、weekly_overview 等）
        report_type: "daily" | "weekly" | "monthly"

    返回:
        (errors, warnings): errors 是必须修复的问题，warnings 是建议改进的问题
    """
    errors = []
    warnings = []
    today = datetime.now()

    sections = data.get("sections", [])
    if not sections:
        errors.append("[板块] 报告无任何板块数据，生成失败")
        return errors, warnings

    # ── 逐板块、逐条目校验 ──
    all_urls = []
    all_dates = []
    all_sources = []
    all_insights = []
    industry_coverage = set()
    total_items = 0

    for section in sections:
        sec_name = section.get("name", "未知板块")
        items = section.get("items", [])

        for i, item in enumerate(items):
            total_items += 1
            prefix = f"[{sec_name}][#{i+1}]"

            title = item.get("title", "")
            date_str = item.get("date", "")
            summary = item.get("summary", "")
            insight_raw = item.get("insight", "") or item.get("innovation_insight", "")
            if isinstance(insight_raw, list):
                insight = " | ".join(insight_raw)  # join for validation
            else:
                insight = insight_raw
            source = item.get("source", "")
            url = item.get("url", "")

            # ── 1. 机构名称黑名单检测 ──
            for wrong, msg in NAME_BLACKLIST.items():
                if wrong in title:
                    errors.append(f"{prefix} {msg}（标题含「{wrong}」: {title[:50]}...）")
                if wrong in summary:
                    errors.append(f"{prefix} {msg}（摘要含「{wrong}」）")
                if wrong in insight:
                    errors.append(f"{prefix} {msg}（洞察含「{wrong}」）")

            # ── 1b. 常见错误名称检测 ──
            for wrong, correct in NAME_CORRECTIONS.items():
                if wrong in title or wrong in summary or wrong in insight:
                    errors.append(f"{prefix} 名称错误：「{wrong}」应改为「{correct}」")

            # ── 2. 信源权威性检查 ──
            if url:
                all_urls.append(url)
                domain = _extract_domain(url)
                score = _score_domain(domain)
                if score == 0:
                    warnings.append(f"{prefix} 信源域名为未知来源（{domain}），请优先使用 .gov.cn")
                elif score < 60:
                    warnings.append(f"{prefix} 信源评分较低（{domain}={score}分），建议替换为更高权威信源")
            else:
                errors.append(f"{prefix} 缺少来源 URL —— 所有信息必须可追溯到原始信源，无URL条目视为未经验证")

            if source:
                all_sources.append(source)

            # ── 3. 日期格式与时效性校验 ──
            date_ok, date_msg = _validate_date(date_str, today, report_type)
            if not date_ok:
                errors.append(f"{prefix} {date_msg}")
            elif date_str and date_str != "近日":
                all_dates.append(date_str)

            # ── 3b. 事件日期交叉比对：报告日期必须等于爬虫采集的事件日期，而非网页发布日期 ──
            _check_date_against_event_date(prefix, url, date_str, errors, warnings)

            # ── 4. 数据精度校验 ──
            _check_number_precision(prefix, summary, insight, title, errors, warnings)

            # ── 5. 禁用词扫描 ──
            for phrase in BANNED_PHRASES:
                if phrase in insight:
                    errors.append(f"{prefix} 创新洞察含禁用词「{phrase}」，必须替换为具体可操作建议")
                if phrase in summary:
                    warnings.append(f"{prefix} 摘要含禁用词「{phrase}」")

            # ── 6. 创新洞察深度校验 ──
            _validate_insight_depth(prefix, insight_raw, summary, industry_coverage, errors, warnings)

            all_insights.append(insight)

            # ── 7. 摘要字数校验 ──
            if summary:
                if len(summary) < 60:
                    warnings.append(f"{prefix} 摘要过短（{len(summary)}字），应≥80字")
                elif len(summary) > 150:
                    warnings.append(f"{prefix} 摘要过长（{len(summary)}字），建议80-120字，最多150字")

    # ── 8. 板块级校验 ──
    for section in sections:
        sec_name = section.get("name", "未知板块")
        items = section.get("items", [])
        # 每板块 .gov.cn 占比
        gov_count = sum(1 for it in items if ".gov.cn" in (it.get("url", "")))
        if gov_count == 0:
            errors.append(f"[{sec_name}] 本板块无 .gov.cn 来源，至少需要1条")
        elif gov_count < 1:
            warnings.append(f"[{sec_name}] 本板块仅{gov_count}条 .gov.cn 来源，建议≥2条")

    # ── 9. 全局 .gov.cn 占比 ──
    if all_urls:
        gov_urls = [u for u in all_urls if ".gov.cn" in u]
        gov_ratio = len(gov_urls) / len(all_urls) * 100
        if gov_ratio < 20:
            errors.append(f"[全局] .gov.cn 信源占比仅 {gov_ratio:.0f}%（{len(gov_urls)}/{len(all_urls)}），应≥25%")
        elif gov_ratio < 30:
            warnings.append(f"[全局] .gov.cn 信源占比 {gov_ratio:.0f}%（{len(gov_urls)}/{len(all_urls)}），建议≥30%")

    # ── 10. 五大产业赛道覆盖率 ──
    industry_names = {
        "AIDC/算力基建": ["AIDC", "算力", "智算", "数据中心"],
        "具身智能": ["具身智能", "人形机器人", "智能体"],
        "未来存储": ["未来存储", "新型存储", "存储技术"],
        "未来能源": ["氢能", "新型储能", "钙钛矿", "虚拟电厂", "未来能源"],
        "液冷技术": ["液冷", "浸没式冷却"],
    }
    for ind_name, keywords in industry_names.items():
        for kw in keywords:
            if kw in str(all_insights) or kw in str(sections):
                industry_coverage.add(ind_name)
                break

    missing_industries = set(industry_names.keys()) - industry_coverage
    if missing_industries:
        warnings.append(f"[产业覆盖] 以下产业赛道未覆盖：{', '.join(missing_industries)}")

    # ── 11. 条目数校验 ──
    if report_type == "weekly":
        min_items, max_items = 8, 16
    elif report_type == "daily":
        # 日报受“当日发布”硬约束影响，允许 4-8 条甚至空板块；
        # 不用 8 条下限逼迫代理拿旧闻或低质量来源充数。
        min_items, max_items = 4, 12
    else:
        min_items, max_items = 8, 12
    if total_items < min_items:
        warnings.append(f"[总量] 仅{total_items}条信息，应≥{min_items}条")
    elif total_items > max_items:
        warnings.append(f"[总量] {total_items}条超过上限{max_items}条")

    return errors, warnings


def _extract_domain(url: str) -> str:
    """从 URL 提取域名"""
    m = re.search(r"https?://([^/]+)", url)
    return m.group(1) if m else ""


def _score_domain(domain: str) -> int:
    """域名评分"""
    for pattern, score in sorted(DOMAIN_SCORES.items(), key=lambda x: -len(x[0])):
        if pattern in domain:
            return score
    return 0


# ── 爬虫素材事件日期索引（模块级缓存） ──
_event_date_index = None


def _load_event_date_index() -> dict:
    """加载 crawled_sources.json，建立 URL → event_date 索引"""
    global _event_date_index
    if _event_date_index is not None:
        return _event_date_index
    _event_date_index = {}
    cache_file = CACHE_DIR / "crawled_sources.json"
    if not cache_file.exists():
        return _event_date_index
    try:
        import json
        with open(cache_file, "r", encoding="utf-8") as f:
            crawled = json.load(f)
        for dim, items in crawled.items():
            if not isinstance(items, list):
                continue
            for it in items:
                url = it.get("url", "")
                event_date = it.get("event_date", "")
                if url and event_date:
                    _event_date_index[url] = event_date
    except Exception:
        pass
    return _event_date_index


def _normalize_date_for_compare(date_str: str) -> str:
    """将各种日期格式归一化为 YYYYMMDD 便于比对"""
    if not date_str:
        return ""
    date_str = date_str.strip()
    m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})$", date_str)
    if m:
        return f"{int(m.group(1)):04d}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        return f"{int(m.group(1)):04d}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if m:
        return f"{int(m.group(1)):04d}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    return date_str


def _check_date_against_event_date(prefix: str, url: str, report_date: str,
                                    errors: list, warnings: list):
    """交叉比对报告日期与爬虫采集的事件日期。

    若报告日期等于网页发布日期（而非事件日期），说明 AI 用错了日期来源，报错。
    """
    if not url or not report_date or report_date.strip() == "近日":
        return

    index = _load_event_date_index()
    event_date = index.get(url, "")
    if not event_date:
        return

    report_norm = _normalize_date_for_compare(report_date)
    event_norm = _normalize_date_for_compare(event_date)

    if not report_norm:
        return

    if report_norm != event_norm:
        errors.append(
            f"{prefix} 日期错误：报告日期为「{report_date}」，"
            f"但爬虫从正文提取的事件日期为「{event_date}」。"
            f"请确认是否误用了网页发布日期而非事件实际发生日期。"
        )


def _validate_date(date_str: str, today: datetime, report_type: str) -> tuple[bool, str]:
    """校验日期格式和时效性"""
    if not date_str:
        return False, "缺少日期字段"

    if date_str.strip() == "近日":
        return True, ""

    # 尝试各种格式
    for pattern in [DATE_PATTERN_SHORT, DATE_PATTERN_CN, DATE_PATTERN]:
        m = pattern.search(date_str)
        if m:
            try:
                year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                d = datetime(year, month, day)
                # 不能是未来日期
                if d > today:
                    return False, f"日期为未来日期（{date_str}），当前为{today.strftime('%Y-%m-%d')}"
                # 时效性检查
                days_ago = (today - d).days
                if report_type == "daily" and days_ago > 3:
                    return False, f"日期{date_str}距今{days_ago}天，日报只采集近3天信息"
                elif report_type == "weekly" and days_ago > 14:
                    return False, f"日期{date_str}距今{days_ago}天，超过2周时效要求"
                elif report_type == "monthly" and days_ago > 35:
                    return False, f"日期{date_str}距今{days_ago}天，超过月报时效范围"
                return True, ""
            except ValueError:
                return False, f"日期格式无法解析: {date_str}"
    return False, f"日期格式不符合规范（应为 YYYY.M.D 或 YYYY年M月D日）: {date_str}"


def _check_number_precision(prefix: str, summary: str, insight: str, title: str,
                             errors: list, warnings: list):
    """检查金额/百分比的数据精度"""
    # 检查摘要中的金额是否有"约""近"等近似词（在 .gov.cn 来源中不应出现）
    money_approx = re.findall(r"(约\d+|近\d+|大约\d+|左右\d+)", summary)
    if money_approx and ".gov.cn" not in prefix:
        warnings.append(f"{prefix} 金额使用了近似值「{money_approx[0]}」，建议与原文精确一致")

    # 检查百分比是否有小数位丢失（如原文32.5%被简化为32%）
    pct_in_summary = re.findall(r"(\d+)%", summary)
    pct_in_insight = re.findall(r"(\d+)%", insight)
    for pct in pct_in_insight:
        if pct not in pct_in_summary:
            warnings.append(f"{prefix} 洞察中引用了摘要未出现的百分比 {pct}%，请确认数据来源")

    # 金额格式
    amounts = re.findall(r"(\d+[\.\d]*)\s*(亿|万|千|百)\s*(元)?", summary + insight)
    for amt, unit, _ in amounts[:20]:  # 只检查前20个
        try:
            val = float(amt)
            # 检查是否有不合理的精度（如 10.3456亿）
            if "." in amt and len(amt.split(".")[1]) > 2:
                warnings.append(f"{prefix} 金额精度异常（{amt}{unit}），建议保留1-2位小数")
        except ValueError:
            pass


def _validate_insight_depth(prefix: str, insight: str | list, summary: str,
                            industry_coverage: set, errors: list, warnings: list):
    """检查创新洞察的深度"""
    if isinstance(insight, list):
        insight_parts = [str(x).strip() for x in insight if str(x).strip()]
        insight_text = " | ".join(insight_parts)
    else:
        insight_text = str(insight or "").strip()
        insight_parts = [insight_text] if insight_text else []

    if not insight_text or len(insight_text) < 30:
        errors.append(f"{prefix} 创新洞察为空或过短（{len(insight_text) if insight_text else 0}字）")
        return

    # 字数检查：如果是 A/B/C 三版洞察，逐版检查，不按合并总长度误报。
    for idx, part in enumerate(insight_parts, start=1):
        plain = re.sub(r"^(方案[A-C]|[abcABC])[.．、:：\s-]*", "", part).strip()
        label = f"方案{idx}" if len(insight_parts) > 1 else "创新洞察"
        if len(plain) < 80:
            warnings.append(f"{prefix} {label}偏短（{len(plain)}字），建议120-200字")
        elif len(plain) > 220:
            warnings.append(f"{prefix} {label}过长（{len(plain)}字），应≤220字，精简直击要点")

    # 必须包含的关键词维度检查
    matched_dimensions = []
    for dim, keywords in INSIGHT_REQUIRED_KEYWORDS.items():
        if any(kw in insight_text or kw in summary for kw in keywords):
            matched_dimensions.append(dim)

    if len(matched_dimensions) < 3:
        missing = [d for d in INSIGHT_REQUIRED_KEYWORDS if d not in matched_dimensions]
        warnings.append(f"{prefix} 创新洞察深度不足，仅覆盖{len(matched_dimensions)}/6个维度，缺失：{', '.join(missing[:3])}")


def print_validation_report(errors: list, warnings: list) -> bool:
    """
    打印校验报告。返回 True 表示通过（无 error），False 表示存在问题。

    errors: 必须修复的问题（红色）
    warnings: 建议改进的问题（黄色）
    """
    print("\n" + "=" * 65)
    print("  后处理校验报告")
    print("=" * 65)

    if errors:
        print(f"\n  ❌ 错误 ({len(errors)} 项) —— 必须修复:")
        for e in errors:
            print(f"     {e}")

    if warnings:
        print(f"\n  ⚠️  警告 ({len(warnings)} 项) —— 建议改进:")
        for w in warnings[:20]:  # 不超过20条
            print(f"     {w}")
        if len(warnings) > 20:
            print(f"     ... 还有 {len(warnings) - 20} 条警告")

    if not errors and not warnings:
        print("\n  ✅ 全部校验通过，报告质量合格！")

    print(f"\n  结果: {len(errors)} 错误, {len(warnings)} 警告")

    # 保存校验日志
    log_dir = CACHE_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "validation_log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] 错误={len(errors)} 警告={len(warnings)}\n")
        for e in errors:
            f.write(f"  ERROR: {e}\n")
        for w in warnings:
            f.write(f"  WARN: {w}\n")

    print("=" * 65)
    return len(errors) == 0


# ══════════════════════════════════════════════════════════════
# 独立测试入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("用法: python3 validate_report.py <report.json> [daily|weekly|monthly]")
        sys.exit(1)

    json_file = sys.argv[1]
    report_type = sys.argv[2] if len(sys.argv) > 2 else "weekly"

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors, warnings = validate_report(data, report_type)
    passed = print_validation_report(errors, warnings)
    sys.exit(0 if passed else 1)
