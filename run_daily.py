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

## ⛔ 事实准确性红线（最高优先级）

1. **所有信息必须来自搜索结果原文**，严禁编造、推测、或基于常识补全。未搜到具体数据的，不得虚构数字。
2. **每条必须标注发布日期**，日期必须与搜索结果中原文一致。
3. **每条必须有信息来源链接（URL）**，URL 必须是搜索结果中的真实链接。
4. **名称必须准确**：是"市委科技委员会""省委科技委员会"，不是"科委"。"科技委"是党委议事协调机构，与历史上的政府"科委"完全不同。
5. **会议日期、发布文件名称、金额、数据**等关键信息必须与搜索到的原文严格一致，不得近似或编造。
6. **自行交叉验证**：对同一事件搜索至少2个不同信源确认。若信源间有矛盾，优先采信 .gov.cn 官方信源，并标注"据XX官方发布"。

## 核心规则

1. **时效性**：只采集近3天内发布的信息
2. **信源优先级**：
   - 第一优先：.gov.cn 政务官方（国家级：most.gov.cn, miit.gov.cn, ndrc.gov.cn, cnipa.gov.cn, cgct.cn, service.most.gov.cn；省级：kxjst.jiangsu.gov.cn, stcsm.sh.gov.cn, kjt.zj.gov.cn, gdstc.gd.gov.cn；市级：各市科技局/发改委/工信局官网。重点关注政策发布、项目申报、公示公告、工作动态、规划文件）
   - 第二优先：权威平台（cas.cn, cae.cn, 各行业学会, 省产研院, 各行业技术研究院, 国家级重点实验室, 产业技术创新战略联盟, stdaily.com, cnki.net, wap.chinacos.cn, kczg.org.cn 等）
   - 第三优先：媒体智库（瞭望智库, 赛迪智库, 长城战略咨询, 中国信通院CAICT, 知领, 华信研究院, 甲子光年, 张通社研究院, 上海科技智库, 上海华略智库, 36氪研究院, 投资界研究院, pedaily.cn, ccidconsulting.com 等）
3. **每板块至少1条来自 .gov.cn 政务官方**
4. **内容质量要求**：
   - 摘要80-120字，用短句。只写核心事实：谁做了什么、金额多少、时间节点、关键数据。砍掉所有背景铺垫和评价性语言
   - 每条必须有差异化价值，同一板块内避免选题雷同或观点重复
   - 优先选取对常州有直接对标价值的信息（同类城市做法、可复制的政策工具、可对接的平台资源）

## 搜索维度（4维度 + 5产业关键词交叉搜索）

### 维度1：各地科技委动态
搜索各省市委科技委员会最新会议、部署、决策。注意：科技委是党委议事协调机构（全称"市委/省委科技委员会"），不是政府部门的"科委"。

### 维度2：上海（长三角）国创中心资讯
搜索长三角国际科技创新中心、G60科创走廊、沿沪宁产业创新带最新动态

### 维度3：科创政策速览
搜索万亿城市最新科技创新政策、产业扶持政策

### 维度4：改革举措
搜索科技体制改革、科技成果转化、科技金融改革最新进展

### 维度5：常州重点产业赛道情报（交叉搜索，融入以上4个维度）
以下5个方向不作为独立板块，而是交叉融入上述4个维度的搜索中，每个维度至少覆盖1-2个产业方向：
- **AIDC/算力基建**：AI数据中心、智算中心、算力补贴政策、产业园布局
- **具身智能**：人形机器人、智能体经济、产业政策、实训基地
- **未来存储**：新型存储技术、产业规划、标准制定
- **未来能源**：氢能、新型储能、钙钛矿、虚拟电厂等政策与产业动态
- **液冷技术**：数据中心液冷、浸没式冷却等标准与产业布局

以上5个方向搜索时加入关键词"算力+硬件+场景+生态""AI产业链""创新链"等，构建全链条视野。

## 创新洞察写作规范（每条80-120字）

### 必须做到（缺一不可）：
1. **对标常州产业基础**：结合常州新能源、高端装备、新能源汽车等既有优势产业，指明如何嫁接新技术、新赛道
2. **分析竞争态势**：对比苏州/无锡/南京/南通等周边城市的同类布局，指出常州的差异化空间或紧迫性
3. **明确操作路径**：点明常州市委市政府哪个部门可牵头、对接什么具体资源（中以常州创新园/科教城/高新区等名园名院名企）
4. **扣合三名工程/双高协同**：至少部分条目关联常州"名园名院名企"三名工程、高新区与高水平大学协同创新等政策抓手
5. **可落地建议**：给出下一步行动的具体方向，而非笼统的"加强""重视"

### 严禁出现：
- "值得借鉴""有参考价值""值得关注"等空话套话
- 脱离常州实际的泛泛建议
- 照搬原文不做本地化转化的分析
- 数字/政策名称与原文不符

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
          "insight": "80-120字，结合常州产业基础和竞争态势，点明可做什么+怎么做+对接什么资源+涉及的常州政策抓手",
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

## ⛔ 事实准确性自检
每条信息发布前必须过：
1. 标题中的机构名称是否与原文一致？（注意是"市委/省委科技委员会"，简称"科技委"，不是"科委"）
2. 会议日期是否与原文一致？若原文未明确日期，标注"近日"
3. 金额、百分比等数据是否与原文严格一致？不得四舍五入或近似
4. 是否有对应 .gov.cn 原文链接？若无，标注信源层级
5. 同一条信息是否有2个以上信源交叉确认？若仅1个信源，优先 .gov.cn

## 搜索要求

每个维度必须使用 site: 限定词优先命中政务官方信源。

### 维度1 · 各地科技委动态（至少1条来自 .gov.cn）
注意：搜索"科技委"而非"科委"，科技委全称"市委科技委员会"或"省委科技委员会"。
搜索：
- site:gov.cn "科技委" "会议" OR "全体会议" OR "部署"
- site:most.gov.cn "科技委" OR "科技创新"
- site:jiangsu.gov.cn "科技委" "会议"
- site:changzhou.gov.cn "科技委"
- "省委科技委" OR "市委科技委" "全体会议" "2026年7月"

### 维度2 · 上海（长三角）国创中心资讯（至少1条来自 .gov.cn）
搜索：
- site:most.gov.cn "长三角" "国际科技创新中心"
- site:stcsm.sh.gov.cn "张江" OR "科创中心"
- site:shanghai.gov.cn "国际科技创新中心"
- "长三角" "G60科创走廊" OR "沿沪宁产业创新带"
- "长三角 科技创新 协同"

### 维度3 · 科创政策速览（至少1条来自 .gov.cn）
搜索：
- site:gov.cn "科技创新政策" "2026"
- site:beijing.gov.cn OR site:shanghai.gov.cn OR site:shenzhen.gov.cn OR site:nanjing.gov.cn OR site:suzhou.gov.cn "产业政策" OR "科技创新"
- site:changzhou.gov.cn "科技创新" OR "产业政策"
- "万亿城市 科技创新 产业政策 2026年7月"
- "AIDC" OR "AI数据中心" OR "算力基建" OR "液冷" "产业政策" OR "产业园" "2026"
- "具身智能" OR "未来能源" OR "未来存储" "政策" OR "产业布局" "2026"
- "算力+硬件+场景+生态" OR "AI产业链" OR "创新链"

### 维度4 · 改革举措（至少1条来自 .gov.cn）
搜索：
- site:gov.cn "科技体制改革" OR "科技成果转化" "2026"
- site:most.gov.cn "改革" "2026"
- "科技成果转化" "先投后股" OR "赋权改革" OR "科技金融"
- "校地合作" OR "新型研发机构" OR "高新区 高水平大学 协同"
- "三名工程" OR "名园名院名企" OR "双高协同"

### 产业交叉搜索（融入以上4个维度，不单独成板块）
在搜索以上4个维度时，每个维度额外追加以下产业关键词的交叉搜索，确保至少覆盖3-4个方向：
- "AIDC" OR "智算中心" OR "算力补贴" — 各地AI数据中心布局
- "具身智能" OR "人形机器人" OR "智能体经济" — 前沿产业政策与园区
- "未来存储" OR "新型存储" — 存储技术产业动态
- "未来能源" OR "氢能" OR "新型储能" OR "钙钛矿" — 新能源创新链
- "液冷" OR "浸没式冷却" — 数据中心散热技术与标准

## 信息筛选标准
每条结果逐一过：
1. 信源是否权威可信？优先 .gov.cn
2. 日期是否在近3天内（即{today_cn}前后）？
3. 信息是否充实？必须有具体政策名称/金额/数据/主体
4. 对常州是否有直接对标价值？优先选取可复制的政策工具、可对接的平台资源、同类城市（苏州/无锡/南京/南通等）的竞争动态
5. 摘要是否去掉了冗余的铺垫和背景，直击核心？

## 创新洞察写作要求（每条必检）
每条 insight 写完后请逐条自检：
1. 是否结合了常州的既有产业基础（新能源、高端装备、新能源汽车等）？
2. 是否分析了常州与苏州/无锡/南京/南通等周边城市的竞争态势？
3. 是否关联了常州"三名工程"（中以常州创新园/科教城/龙头企业）或"双高协同"（高新区+高水平大学）等政策抓手？
4. 是否给出了具体可操作的下一步行动建议？
5. 是否避免了"值得借鉴""有参考价值"等空话套话？
6. 建议中的数字、政策名称是否与搜索结果一致？

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
    from generate_docx import get_issue_numbers

    issue, total = get_issue_numbers()
    date_cn = today.strftime("%Y年%m月%d日")
    html = build_daily_html(sections, date_cn, issue, total)
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
