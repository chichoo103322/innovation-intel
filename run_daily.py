#!/usr/bin/env python3
"""
《创新常州·对标快讯》日报全自动流水线
搜索 → 分析 → HTML → PDF → 去重 → 分发

使用 DeepSeek API（内置联网搜索），国内直连，无需 Anthropic API Key。
交付方只需注册 DeepSeek 获取 API Key（注册即送免费额度，约 ¥1/百万token）。

用法:
    python3 run_daily.py                          # 生成今日日报
    python3 run_daily.py --dry-run                # 仅搜索分析，不生成文件不分发
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
                    # 二级键值对（如 max_items_per_dimension: 3）
                    config[current_section][key] = _parse_val(_clean_val(raw_val))
                elif raw_val is None or raw_val == "":
                    # 二级 subsection（如 channels 下的 email:）
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


def get_model(config: dict) -> str:
    return config.get("deepseek_model", "deepseek-chat")


# ---------------------------------------------------------------------------
# 系统提示词
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一位资深科技创新情报分析师，服务于常州市科技创新决策。请使用联网搜索功能采集最新科技创新情报，生成当日的《创新常州·对标快讯》日报。

## 核心规则

1. **时效性**：只采集近3天内发布的信息，每条必须标注发布日期
2. **信源优先级**：
   - 第一优先：.gov.cn 政务官方（most.gov.cn, miit.gov.cn, ndrc.gov.cn, kxjst.jiangsu.gov.cn, stcsm.sh.gov.cn, changzhou.gov.cn 等）
   - 第二优先：权威平台（cas.cn, cae.cn, stdaily.com, cnki.net 等）
   - 第三优先：媒体智库（36kr.com, pedaily.cn, ccidconsulting.com 等）
3. **每板块至少1条来自 .gov.cn 政务官方**
4. **内容质量要求**：
   - 摘要80-120字，用短句。只写核心事实：谁做了什么、金额多少、时间节点、关键数据。砍掉所有背景铺垫和评价性语言
   - 每条必须有差异化价值，同一板块内避免选题雷同或观点重复
   - 优先选取对常州有直接对标价值的信息（同类城市做法、可复制的政策工具、可对接的平台资源）
5. **每条必须有「创新洞察」**：80-120字，点明常州可做什么+怎么做+对接什么资源。禁止"值得借鉴""有参考价值"等空话。
6. **每条必须有信息来源链接（URL）**

## 创新洞察 · 常州关切方向（作为分析视角丰富洞察内容，而非替代4个搜索维度）

撰写创新洞察时，可在原有分析框架基础上，适当结合以下常州重点方向，使建议更具体：

- **AI 基础设施**：AIDC、算力基建、液冷技术、AI 产业园布局，"算力+硬件+场景+生态"全链条
- **前沿产业**：具身智能、未来存储、未来能源等赛道的竞争动态与政策布局
- **三名工程**（名园名院名企）：中以常州创新园、科教城、龙头企业如何在外部创新资源中借力
- **双高协同**：高新区与高水平大学协同创新，校地合作新模式、新型研发机构经验
- **政策工具**：研发补贴、人才引进、金融支持、场景开放等创新政策

注意：以上是分析视角的丰富，不是每条的硬性要求。核心仍然是4个维度的情报采集与分析。对不相关的条目，不需要强行关联。

## 搜索维度

请按以下4个维度分别搜索，每维度2-3条，总计8-12条：

### 维度1：各地科技委动态
搜索各省市科技委最新会议、部署、决策

### 维度2：上海（长三角）国创中心资讯
搜索长三角国际科技创新中心、G60科创走廊、沿沪宁产业创新带最新动态

### 维度3：科创政策速览
搜索万亿城市最新科技创新政策、产业扶持政策

### 维度4：改革举措
搜索科技体制改革、科技成果转化、科技金融改革最新进展

## 输出格式

完成搜索和分析后，你必须以如下 JSON 格式输出（不要包含任何其他文字，只输出 JSON）：

```json
{
  "sections": [
    {
      "name": "各地科技委动态",
      "items": [
        {
          "title": "信息标题",
          "date": "2026.7.X",
          "summary": "80-120字，用短句直击核心。只写谁+做了什么+关键数据+时间节点，不铺垫不评价",
          "insight": "80-120字，点明常州可做什么+怎么做+对接什么资源，具体可操作，禁止空话套话",
          "source": "来源机构名称",
          "url": "原文URL"
        }
      ]
    }
  ]
}
```

记住：只输出 JSON，不要有任何解释、前缀或后缀文字。"""


def build_user_prompt(today_cn: str) -> str:
    """构建当日的用户消息"""
    return f"""今天是{today_cn}。请按照以下搜索要求完成今日情报采集与整理。

## 搜索要求

每个维度必须使用 site: 限定词优先命中政务官方信源。每个维度额外补充常州重点关切方向的搜索。

### 维度1 · 各地科技委动态（至少1条来自 .gov.cn）
搜索：
- site:gov.cn "科技委" "会议" "2026年7月"
- site:most.gov.cn "科技委" OR "科技创新"
- site:jiangsu.gov.cn "科技委"
- "省委科技委 全体会议 2026年7月"
- "科技委 科技创新 部署 2026年7月"

### 维度2 · 上海（长三角）国创中心资讯（至少1条来自 .gov.cn）
搜索：
- site:most.gov.cn "长三角" "国际科技创新中心"
- site:stcsm.sh.gov.cn "张江" OR "科创中心"
- site:shanghai.gov.cn "国际科技创新中心"
- "长三角 国际科技创新中心 2026年7月"
- "G60科创走廊" OR "沿沪宁产业创新带" "2026年7月"

### 维度3 · 科创政策速览（至少1条来自 .gov.cn）
搜索：
- site:gov.cn "科技创新政策" "2026"
- site:beijing.gov.cn OR site:shanghai.gov.cn OR site:shenzhen.gov.cn "产业政策"
- site:changzhou.gov.cn "科技创新" OR "产业政策"
- "万亿城市 科技创新 产业政策 2026年7月"
- "AI数据中心" OR "算力基建" OR "液冷" "产业政策 2026"
- "具身智能" OR "未来能源" OR "未来存储" "政策 2026"

### 维度4 · 改革举措（至少1条来自 .gov.cn）
搜索：
- site:gov.cn "科技体制改革" OR "科技成果转化"
- site:most.gov.cn "改革" "2026"
- "科技成果转化" "先投后股" OR "赋权改革" "2026年7月"
- "科技金融" "改革" "试点" "2026年7月"
- "AI产业链" OR "算力+硬件+场景+生态" "创新链"
- "校地合作" OR "新型研发机构" OR "高新区 高水平大学 协同"

## 筛选标准
每条结果逐一过：
1. 来自优先信源（政务官方 > 权威平台 > 媒体智库）？
2. 发布日期在近3天内（即{today_cn}前后）？
3. 内容不重复？
4. 对常州是否有直接对标价值？（优先选取可复制的政策工具、可对接的平台资源、同类城市的竞争动态）
5. 摘要是否去掉了冗余的铺垫和背景，直击核心？

## 创新洞察写作要求
每条 insight 写作时请自检：
- 是否点明了常州具体可以怎么做？（不写"值得借鉴""有参考价值"等空话）
- 是否结合了常州 AIDC、具身智能、未来存储、未来能源、液冷、三名工程、双高协同等重点方向？
- 是否给出了可操作的下一步建议？（对接什么部门、抢占什么先机、规避什么风险）

请现在开始逐维度搜索并分析，最终只输出 JSON。"""


# ---------------------------------------------------------------------------
# DeepSeek API 调用（内置联网搜索）
# ---------------------------------------------------------------------------

def call_deepseek(api_key: str, model: str, today_cn: str) -> list[dict]:
    """调用 DeepSeek API（开启联网搜索），返回 sections 列表"""
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    print(f"[搜索] 正在通过 DeepSeek API（联网搜索）采集今日情报...")
    print(f"[模型] {model}")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(today_cn)},
        ],
        max_tokens=16000,
        temperature=0.3,
        extra_body={"enable_web_search": True},
    )

    text = response.choices[0].message.content or ""
    print(f"[响应] 收到 {len(text)} 字回复")

    # 从文本中提取 JSON（可能被 markdown 代码块包裹）
    json_str = text.strip()
    if json_str.startswith("```"):
        lines = json_str.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        json_str = "\n".join(lines).strip()

    try:
        data = json.loads(json_str)
        return data.get("sections", [])
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: {e}")
        print(f"[调试] 返回内容前500字:\n{text[:500]}")
        sys.exit(1)


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
    parser.add_argument("--dry-run", action="store_true", help="仅搜索分析，不生成文件")
    parser.add_argument("--skip-distribute", action="store_true", help="不分发")
    parser.add_argument("--force", action="store_true", help="强制生成，跳过周末/重复检测")
    args = parser.parse_args()

    print("=" * 60)
    print("  创新常州·对标快讯 — 日报自动生成流水线")
    print("=" * 60)

    today = datetime.now()

    # 周末自动跳过
    if today.weekday() >= 5 and not args.force:
        print(f"[跳过] 今天是周末，不生成日报。如需强制生成请使用 --force")
        return

    # 今天已生成过则跳过（配合 launchd 高频触发，避免重复跑API）
    daily_dir = PROJECT_DIR / "daily"
    today_stem = today.strftime("%Y-%m-%d")
    today_pdf = daily_dir / f'创新常州·对标快讯_{today_stem}.pdf'
    if today_pdf.exists() and not args.force:
        print(f"[跳过] 今日日报已存在: {today_pdf}")
        return

    config = load_config()
    api_key = get_api_key(config)
    if not api_key:
        print("[错误] 未找到 DEEPSEEK_API_KEY。")
        print("请设置环境变量: export DEEPSEEK_API_KEY='sk-...'")
        print("或在 config/settings.yaml 中配置 deepseek_api_key")
        sys.exit(1)

    model = get_model(config)
    today = datetime.now()
    today_cn = today.strftime("%Y年%m月%d日")

    # 1. 调用 DeepSeek API 搜索 + 分析
    sections = call_deepseek(api_key, model, today_cn)

    if not sections:
        print("[错误] DeepSeek 未返回任何情报数据")
        sys.exit(1)

    total_items = sum(len(s.get("items", [])) for s in sections)
    print(f"[结果] 采集到 {total_items} 条信息，分布在 {len(sections)} 个板块")

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

    # 3. 生成 HTML → PDF
    sys.path.insert(0, str(SCRIPT_DIR))
    from generate_html_pdf import build_daily_html, html_to_pdf

    date_cn = today.strftime("%Y年%m月%d日")
    html = build_daily_html(sections, date_cn)
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
