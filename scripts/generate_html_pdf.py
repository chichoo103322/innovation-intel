#!/usr/bin/env python3
"""
使用 frontend-design 美学生成 HTML → 转 PDF 周报
设计方向：Editorial Intelligence Report — 权威、克制、信息优先
"""
import sys
import json
import os
from pathlib import Path
from datetime import date

PROJECT_DIR = Path(__file__).parent.parent
SCRIPT_DIR = Path(__file__).parent

# ── 内容获取 ──────────────────────────────────────────

WEEKLY_SYSTEM_PROMPT = """你是一位资深科技创新情报分析师，服务于常州市科技创新决策。请使用联网搜索功能，系统采集本周科技创新领域重要动态，撰写《创新常州·对标快讯》周报。

## ⛔ 事实准确性红线（最高优先级）

1. **所有信息必须来自搜索结果原文**，严禁编造、推测、或基于常识补全。未搜到具体数据的，宁可写"加快推进"也不虚构数字。
2. **每条必须标注发布日期**，日期必须与搜索结果中原文一致。若原文未明确日期，标注"近日"。
3. **每条必须有信息来源链接（URL）**，URL 必须是搜索结果中的真实链接。
4. **名称必须准确**：是"市委科技委员会""省委科技委员会"，简称"科技委"，不是"科委"。"科技委"是党委议事协调机构——2023年机构改革后从"领导小组"升格为实体化运作的委员会。
5. **会议日期、发布文件名称、金额、数据**等关键信息必须与搜索到的原文严格一致，不允许近似值或编造。
6. **自行交叉验证**：对同一事件搜索至少2个不同信源确认。若信源间有矛盾，优先采信 .gov.cn 官方信源，并在 summary 中注明"据XX官方发布"。

## 核心原则

1. **时效性**：采集本周内发布的信息
2. **信源优先级**：
   - 第一优先：.gov.cn 政务官方（国家级：most.gov.cn, miit.gov.cn, ndrc.gov.cn, cnipa.gov.cn, cgct.cn, service.most.gov.cn；省级：kxjst.jiangsu.gov.cn, stcsm.sh.gov.cn, kjt.zj.gov.cn, gdstc.gd.gov.cn；市级：各市科技局/发改委/工信局官网。重点关注政策发布、项目申报、公示公告、工作动态、规划文件）
   - 第二优先：权威平台（cas.cn, cae.cn, 各行业学会, 省产研院, 各行业技术研究院, 国家级重点实验室, 产业技术创新战略联盟, stdaily.com, cnki.net, wap.chinacos.cn, kczg.org.cn 等）
   - 第三优先：媒体智库（瞭望智库, 赛迪智库, 长城战略咨询, 中国信通院CAICT, 知领, 华信研究院, 甲子光年, 张通社研究院, 上海科技智库, 上海华略智库, 36氪研究院, 投资界研究院, pedaily.cn, thepaper.cn, cls.cn 等）
3. **每板块至少1条来自 .gov.cn 政务官方**
4. **信息密度要求**：
   - 摘要80-120字，用短句。只写核心事实：谁做了什么、金额多少、时间节点、关键数据。砍掉背景铺垫和评价
   - 每条必须有独立价值，同一板块内避免选题雷同
   - 优先选取对常州有直接对标价值的信息

## 搜索维度（4维度 + 5产业赛道交叉搜索）

### 维度1：各地科技委动态（3条，至少1条来自 .gov.cn）
搜索各省市委科技委员会最新会议、部署、决策。注意：科技委是党委议事协调机构（全称"市委/省委科技委员会"），不是政府部门的"科委"。

### 维度2：上海（长三角）国创中心资讯（3条，至少1条来自 .gov.cn）
搜索长三角国际科技创新中心、G60科创走廊、沿沪宁产业创新带最新动态

### 维度3：科创政策速览（3条，至少1条来自 .gov.cn）
搜索万亿城市最新科技创新政策、产业扶持政策

### 维度4：改革举措（3条，至少1条来自 .gov.cn）
搜索科技体制改革、科技成果转化、科技金融改革最新进展

### 产业赛道交叉搜索（融入以上4个维度）
以下5个方向不作为独立板块，而是交叉融入上述4个维度的搜索中：
- **AIDC/算力基建**：AI数据中心、智算中心、算力补贴政策、AI产业园布局
- **具身智能**：人形机器人、智能体经济、产业政策、实训基地
- **未来存储**：新型存储技术、产业规划、标准制定
- **未来能源**：氢能、新型储能、钙钛矿、虚拟电厂等政策与产业动态
- **液冷技术**：数据中心液冷、浸没式冷却等标准与产业布局

以上5个方向搜索时加入关键词"算力+硬件+场景+生态""AI产业链""创新链"等，构建全链条视野。

## 创新洞察写作规范（每条80-120字）

### 必须做到：
1. **对标常州产业基础**：结合常州新能源、高端装备、新能源汽车等既有优势产业，指明如何嫁接新技术赛道
2. **分析竞争态势**：对比苏州/无锡/南京/南通等周边万亿城市的同类布局，指出常州的差异化空间或紧迫性
3. **明确操作路径**：点明常州市委市政府哪个部门可牵头、对接什么具体资源（中以常州创新园/科教城/高新区等）
4. **扣合三名工程/双高协同**：关联常州"名园名院名企"三名工程、高新区与高水平大学协同创新
5. **可落地建议**：给出下一步行动的具体方向

### 严禁出现：
- "值得借鉴""有参考价值""值得关注"等空话套话
- 脱离常州实际的泛泛建议
- 照搬原文不做本地化转化的分析
- 数字/政策名称与原文不符

## 输出格式

完成搜索和分析后，你必须以如下 JSON 格式输出（不要包含任何其他文字，只输出 JSON）：

```json
{
  "weekly_overview": "150-200字本周综述，概括本周最重要的动态和趋势，点明对常州的整体启示，结合常州产业基础和竞争格局",
  "sections": [
    {
      "name": "各地科技委动态",
      "items": [
        {
          "title": "信息标题",
          "date": "2026.7.X",
          "summary": "80-120字，短句直击核心。只写谁+做了什么+关键数据+时间节点，不铺垫不评价",
          "insight": "80-120字，结合常州产业基础和竞争态势，点明可做什么+怎么做+对接什么资源+涉及的常州政策抓手（三名工程/双高协同/中以常州创新园/科教城等）",
          "source": "来源机构名称",
          "url": "原文URL"
        }
      ]
    }
  ],
  "trend_analysis": "150-250字本周趋势分析，归纳2-3条跨板块的共性趋势，重点分析常州在苏州/无锡/南京/南通等周边万亿城市竞争中的定位与差异化机会"
}
```

记住：只输出 JSON，不要有任何解释、前缀或后缀文字。"""

WEEKLY_USER_PROMPT_TEMPLATE = """今天是{today_cn}。请联网搜索本周（{week_start}至{week_end}）科技创新领域重要动态，生成《创新常州·对标快讯》周报。

## ⛔ 事实准确性自检（每条必过）
1. 机构名称是否准确？（是"市委/省委科技委员会"，不是"科委"）
2. 会议/发布日期是否与原文一致？若原文未明确，标注"近日"
3. 金额、百分比等数据是否与原文严格一致？
4. 是否有 .gov.cn 原文链接？
5. 同一条信息是否用2个以上信源交叉确认？

## 搜索要求

每个维度请使用 site: 限定词优先命中政务官方信源。每个维度搜索3条不同角度。

### 维度1 · 各地科技委动态（至少1条来自 .gov.cn，3条）
注意：搜索"科技委"而非"科委"，全称"省委科技委员会"或"市委科技委员会"。
搜索：
- site:gov.cn "科技委" "会议" OR "全体会议" OR "部署"
- site:most.gov.cn "科技委" OR "科技创新"
- site:jiangsu.gov.cn "科技委" "会议" OR "全体会议"
- site:changzhou.gov.cn "科技委"
- "省委科技委" OR "市委科技委" "全体会议"
- "科技委" "科技创新" "部署"

### 维度2 · 上海（长三角）国创中心资讯（至少1条来自 .gov.cn，3条）
搜索：
- site:most.gov.cn "长三角" "国际科技创新中心"
- site:stcsm.sh.gov.cn "张江" OR "科创中心"
- site:shanghai.gov.cn "国际科技创新中心"
- "长三角" "G60科创走廊" OR "沿沪宁产业创新带"
- "长三角" "科技创新" "协同" "2026"

### 维度3 · 科创政策速览（至少1条来自 .gov.cn，3条）
搜索：
- site:gov.cn "科技创新政策" "2026"
- "万亿城市" "科技创新" "产业政策"
- "AIDC" OR "算力基建" OR "液冷" "产业政策" OR "产业园布局"
- "具身智能" OR "未来能源" OR "未来存储" "政策" OR "产业"
- "算力+硬件+场景+生态" OR "AI产业链创新链"
- site:beijing.gov.cn OR site:shenzhen.gov.cn OR site:nanjing.gov.cn OR site:suzhou.gov.cn "科技创新" "政策"

### 维度4 · 改革举措（至少1条来自 .gov.cn，3条）
搜索：
- site:gov.cn "科技体制改革" OR "科技成果转化"
- site:most.gov.cn "改革"
- "科技成果转化" "先投后股" OR "赋权改革" OR "科技金融"
- "校地合作" OR "新型研发机构" OR "高新区 高水平大学 协同"
- "三名工程" OR "名园名院名企" OR "双高协同"

### 产业交叉搜索（融入以上4个维度，不单独成板块）
每个维度额外追加以下关键词的交叉搜索，确保本周至少覆盖4-5个产业方向：
- "AIDC" OR "智算中心" — 各地AI数据中心建设与补贴
- "具身智能" OR "人形机器人" — 政策、产业园、实训基地
- "未来存储" OR "新型存储" — 技术与产业布局
- "未来能源" OR "氢能" OR "钙钛矿" — 新能源创新链
- "液冷" OR "浸没式冷却" — 数据中心散热技术

## 信息筛选标准
每条结果逐一过：
1. 信源是否权威可信？优先 .gov.cn
2. 日期是否在本周内（{week_start}至{week_end}）？
3. 信息是否充实？必须有具体政策名称/金额/数据/主体/时间节点
4. 对常州是否有对标价值？优先选取可复制的政策工具、可对接的平台资源、周边万亿城市（苏州/无锡/南京/南通）的竞争动态
5. 摘要是否去掉了冗余铺垫，直击核心事实？

## 创新洞察写作自检（每条必查）
1. 是否结合了常州的既有产业基础（新能源、高端装备、新能源汽车等）？
2. 是否分析了常州与苏州/无锡/南京/南通等周边城市的竞争态势与差异化空间？
3. 是否关联了常州"三名工程"（中以常州创新园/科教城/龙头企业）或"双高协同"（高新区+高水平大学）等政策抓手？
4. 是否给出了具体可操作的下一步行动建议？
5. 是否避免了"值得借鉴""有参考价值"等空话套话？
6. 建议中的数字、政策名称是否与搜索到的原文一致？

## 本周趋势分析要求
归纳2-3条跨板块的共性趋势时，重点分析：
- 常州在苏州/无锡/南京/南通等周边万亿城市竞争中的定位
- 常州在 AIDC、具身智能、未来存储、未来能源、液冷等赛道上的差异化机会
- 结合常州市委市政府经济工作会议精神，对常州当前科技创新工作提出综述性建议

请现在开始逐维度搜索并分析，最终只输出 JSON。"""


def get_weekly_data(api_key: str = None, sample: bool = False) -> dict:
    if sample or not api_key:
        return _sample_data()

    from datetime import date, timedelta

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    today = date.today()
    # 本周一到今天
    week_start = today - timedelta(days=today.weekday())
    week_end = today
    today_cn = today.strftime("%Y年%m月%d日")
    week_start_cn = week_start.strftime("%Y年%m月%d日")
    week_end_cn = week_end.strftime("%Y年%m月%d日")

    user_prompt = WEEKLY_USER_PROMPT_TEMPLATE.format(
        today_cn=today_cn,
        week_start=week_start_cn,
        week_end=week_end_cn,
    )

    print(f"[搜索] 周报区间: {week_start_cn} — {week_end_cn}")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": WEEKLY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=16000, temperature=0.3,
        extra_body={"enable_web_search": True},
    )

    text = response.choices[0].message.content or ""
    json_str = text.strip()
    if json_str.startswith("```"):
        lines = json_str.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        json_str = "\n".join(lines).strip()
    return json.loads(json_str)


def _sample_data() -> dict:
    return {
        "weekly_overview": "本周（6月28日—7月5日）长三角国际科技创新中心建设加速推进，各省市科技委密集部署下半年重点任务。武汉光谷、南京、郑州等万亿城市纷纷加码AI与具身智能赛道，政策竞争态势加剧。常州被列为高能级创新型城市建设对象，在沿沪宁产业创新带中的定位进一步明确。",
        "sections": [
            {
                "name": "各地科技委动态",
                "items": [
                    {"title": "江苏省委科技委员会全体会议召开", "date": "2026.7.1",
                     "summary": "省委书记信长星主持，省长刘小涛出席。会议强调高效协同推进上海（长三角）国际科技创新中心建设，南京、苏州扛起关键支点重任，无锡、常州、南通建设高能级创新型城市。会议讨论了《江苏省人工智能驱动科学研究实施方案》，提出推动科技创新与产业创新深度融合。",
                     "insight": "常州被明确列为「高能级创新型城市」建设对象，应趁势主动对接省AI驱动科研方案，争取省级示范项目在常州AIDC落地，加快制定常州版高能级创新型城市建设行动方案，明确在沿沪宁产业创新带中的差异化功能定位。",
                     "source": "江苏省人民政府"},
                    {"title": "广东省委科技委发布脑机接口产业协同发展行动计划", "date": "2026.7.2",
                     "summary": "印发《广东省脑机接口科技与产业协同发展行动计划（2026—2030年）》，目标到2030年核心产业规模达百亿级，辐射上下游达千亿级。这是全国首个由省级科技委直接发布的未来产业行动计划，标志科技委正从协调机构向产业战略策源机构转型。",
                     "insight": "广东科技委直接发布产业行动计划的做法值得关注。常州可参照此模式，由市委科技委发布新能源、合成生物等优势产业的技术创新路线图，提升科技委的战略引领力和产业话语权。",
                     "source": "广东省科技厅"},
                ]
            },
            {
                "name": "上海（长三角）国创中心资讯",
                "items": [
                    {"title": "长三角市场监管一体化发布助力国创中心建设19条举措", "date": "2026.7.3",
                     "summary": "三省一市联合发布《若干举措》，涵盖科技人才「互聘共享」和资质跨区域互认、元宇宙/AI/6G等前沿领域快速获权服务、融入「一中心五支点、一廊两带」主干网等七大板块。长三角经营主体达3828万户，R&D经费占全国约30.55%。",
                     "insight": "「人才互聘共享」和「资质跨区域互认」对常州是直接利好。建议市科技局牵头，依托中以常州创新园、科教城等名园名院，主动对接长三角人才共享平台，柔性引进沪宁领军人才。",
                     "source": "澎湃新闻"},
                    {"title": "学术论坛热议国际科创中心「扩围提质」", "date": "2026.7.2",
                     "summary": "第23届上海市社科界学术年会论坛在同济大学举行。长三角国创中心主任刘庆提出打造「没有围墙的创新中心」。上海全球城市研究院院长阮青提出「前研后转」分工模式——上海做前沿研发，周边城市做产业转化。",
                     "insight": "「前研后转」分工模式对常州定位意义重大。应围绕此定位建强中以常州创新园、科教城等转化载体，梳理与上海高校院所的合作项目，形成「沪研常转」标杆案例。",
                     "source": "网易新闻"},
                ]
            },
            {
                "name": "科创政策速览",
                "items": [
                    {"title": "武汉光谷发布智能体经济「路线图」：三年投10亿、年内万P算力", "date": "2026.7.3",
                     "summary": "光谷未来三年投入超10亿元，培育100家智能体创新企业、落地1000个创新产品。已建成超5000P智能算力，年内提升至10000P，企业租用算力享最高50%补贴。设立智能体场景发布厅，标杆场景最高300万元支持。",
                     "insight": "光谷算力大手笔投入对常州AIDC形成竞争压力。常州应发挥新能源产业场景优势，聚焦「AI+新能源」差异化赛道——智能电网调度、电池健康管理等垂直场景，与光谷形成错位竞争。",
                     "source": "财联社"},
                    {"title": "郑州入局万亿具身智能赛道，与宇树科技共建实训创新中心", "date": "2026.7.3",
                     "summary": "OpenLET郑州工作组揭牌，国内首个国家级具身智能开源数据集社区落地郑州。与宇树科技共建「具身智能实训创新中心」和「具身智能产业学院」。郑州高新区已集聚400余家机器人产业链企业。",
                     "insight": "常州在具身智能领域应加快布局，借助理想、比亚迪等名企在智能制造端的场景优势，联合共建具身智能实训基地，利用科教城职教资源打造长三角具身智能技能人才培训高地。",
                     "source": "网易新闻"},
                ]
            },
            {
                "name": "改革举措",
                "items": [
                    {"title": "海南拟设1亿元「先投后股」资金池支持科技成果转化", "date": "2026.7.3",
                     "summary": "海南发布2026年科技体制改革计划，全省「先投后股」资金池达1亿元，累计支持不少于20个项目。「先投后股」即财政资金先以补助形式投入支持研发，后期按约定转化为企业股权，同步推动省级财政科技专项体系优化改革。",
                     "insight": "「先投后股」是破解成果转化「最初一公里」资金困境的有效模式。常州可在「三名联动」框架下试点——从产业基金中切出专项，以「先投后股」方式支持高校院所成果在常转化，实现财政资金循环增值。",
                     "source": "海南中新网"},
                    {"title": "上海科学技术奖励大会：深化科技评价改革，推进「三评联动」", "date": "2026.7.2",
                     "summary": "上海市委书记陈吉宁为褚君浩、陈赛娟颁发科技功臣奖。核心部署：加强科技计划全过程管理、深化项目经理团队制度建设、推进项目评审/人才评价/机构评估「三评联动」改革、为科研人员赋权增能减负松绑。",
                     "insight": "常州可率先在市级科技计划中试行「分类评价」制度——基础研究看长周期、应用研究看转化效果、企业项目看市场效益，避免「一刀切」扼杀创新活力。",
                     "source": "上海市科委"},
                ]
            },
        ],
        "trend_analysis": "本周呈现三大趋势：一是各省市科技委角色加速从协调议事向产业战略策源转型，广东率先以科技委名义发布产业行动计划；二是万亿城市在AI算力、具身智能等赛道投入力度空前，武汉光谷10亿级别投入和万P算力目标值得常州警惕；三是「先投后股」等成果转化金融工具在多省市落地，常州应抓住政策窗口期推进试点。"
    }


# ── HTML 生成 ──────────────────────────────────────────

def build_html(data: dict, issue_no: int, total_no: int, date_cn: str) -> str:
    """构建编辑级 HTML 报告"""
    overview = data.get("weekly_overview") or data.get("overview") or ""
    sections = data.get("sections", [])
    trend = data.get("trend_analysis") or data.get("trend") or ""

    items_html = ""
    for s in sections:
        sname = s.get("name") or s.get("section_name") or ""
        items_html += f'<h2 class="section-title">{sname}</h2>\n'
        for item in s.get("items", []):
            title = item.get("title", "")
            date_i = item.get("date", "")
            summary = item.get("summary", "")
            insight = item.get("innovation_insight") or item.get("insight") or ""
            source = item.get("source", "")
            items_html += f"""
        <div class="news-item">
          <h3 class="item-title">{title}<span class="item-date">{date_i}</span></h3>
          <p class="item-summary">{summary}</p>
          <div class="item-insight">
            <span class="insight-label">创新洞察</span>
            <p>{insight}</p>
          </div>
          <p class="item-source">{source}</p>
        </div>"""

    trend_html = ""
    if trend:
        trend_html = f"""
      <h2 class="section-title">本周趋势分析</h2>
      <p class="trend-text">{trend}</p>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 22mm 16mm;
    @top-center {{
      content: element(header);
    }}
  }}
  @page:first {{
    margin: 0;
    @top-center {{ content: none; }}
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  :root {{
    --primary: #0a2655;
    --blue: #1e50b4;
    --accent: #8b6914;
    --accent-bg: #fdf8f0;
    --gray: #64748b;
    --light-gray: #e2e8f0;
    --bg: #f8fafc;
    --text: #1e293b;
    --text-secondary: #475569;
  }}

  body {{
    font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", "Microsoft YaHei", sans-serif;
    font-size: 10pt;
    line-height: 1.75;
    color: var(--text);
    counter-reset: page;
  }}

  /* ── Cover ── */
  .cover {{
    width: 210mm; height: 297mm;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(175deg, #eff6ff 0%, #dce8fc 40%, #c5d8f8 100%);
    position: relative; overflow: hidden;
    page: cover;
  }}
  .cover::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 5px;
    background: var(--primary);
  }}
  .cover::after {{
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 5px;
    background: var(--primary);
  }}
  .cover-label {{
    font-size: 9pt; letter-spacing: 5px; text-transform: uppercase;
    color: var(--blue); margin-bottom: 24px;
    font-weight: 500;
  }}
  .cover-title {{
    font-size: 30pt; font-weight: 700; color: var(--primary);
    letter-spacing: 3px; margin-bottom: 8px;
  }}
  .cover-divider {{
    width: 50px; height: 2px; background: var(--blue);
    margin: 16px auto 20px;
  }}
  .cover-sub {{
    font-size: 11pt; color: var(--blue); font-weight: 400;
    letter-spacing: 1px; margin-bottom: 36px;
  }}
  .cover-meta {{
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(59,108,180,0.12);
    border-radius: 6px;
    padding: 16px 32px; text-align: center;
  }}
  .cover-meta p {{
    font-size: 10pt; color: var(--gray); line-height: 2;
  }}

  /* ── Running header ── */
  .running-header {{
    position: running(header);
    font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", sans-serif;
    font-size: 7.5pt; color: var(--blue);
    display: flex; justify-content: space-between;
    border-bottom: 1px solid var(--light-gray);
    padding-bottom: 4px; margin-bottom: 8px;
  }}

  /* ── Content ── */
  .content {{
    padding-top: 8mm;
  }}

  .overview {{
    font-size: 10pt; color: var(--text-secondary);
    line-height: 1.9; margin-bottom: 22px;
    padding: 14px 18px;
    background: var(--bg);
    border-left: 3px solid var(--blue);
    border-radius: 0 4px 4px 0;
  }}

  .section-title {{
    font-size: 13pt; font-weight: 700; color: var(--blue);
    margin: 24px 0 12px 0; padding-bottom: 6px;
    border-bottom: 1.5px solid var(--light-gray);
    letter-spacing: 1px;
  }}

  .news-item {{
    margin-bottom: 16px;
    padding-bottom: 14px;
    border-bottom: 1px dotted var(--light-gray);
  }}
  .news-item:last-child {{ border-bottom: none; }}

  .item-title {{
    font-size: 10.5pt; font-weight: 600; color: var(--blue);
    margin-bottom: 3px; line-height: 1.6;
  }}
  .item-date {{
    font-size: 8pt; font-weight: 400; color: var(--gray);
    margin-left: 6px;
  }}

  .item-summary {{
    font-size: 9.5pt; color: var(--text-secondary);
    line-height: 1.8; margin-bottom: 6px;
    text-align: justify;
  }}

  .item-insight {{
    background: var(--accent-bg);
    border-left: 3px solid var(--accent);
    border-radius: 0 4px 4px 0;
    padding: 8px 14px; margin: 8px 0 6px 0;
  }}
  .item-insight p {{
    font-size: 9pt; color: #6b4f10;
    line-height: 1.8; display: inline;
  }}
  .insight-label {{
    font-size: 8pt; font-weight: 700; color: var(--accent);
    letter-spacing: 2px; margin-right: 6px;
  }}

  .item-source {{
    font-size: 7.5pt; color: #94a3b8; text-align: right;
    margin-top: 4px;
  }}

  .trend-text {{
    font-size: 10pt; color: var(--text-secondary);
    line-height: 1.9; text-align: justify;
    padding: 14px 18px;
    background: var(--bg);
    border-radius: 4px;
  }}

  /* ── Print ── */
  @media print {{
    .cover {{ page-break-after: always; }}
    .news-item {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-label">WEEKLY REPORT</div>
  <h1 class="cover-title">创新常州·对标快讯</h1>
  <div class="cover-divider"></div>
  <p class="cover-sub">Innovation Changzhou · Benchmarking Weekly</p>
  <div class="cover-meta">
    <p>2026年 第{issue_no}期 &nbsp;·&nbsp; 总第{total_no}期</p>
    <p>{date_cn}</p>
  </div>
</div>

<div class="running-header">
  <span>创新常州·对标快讯</span>
  <span>2026年第{issue_no}期</span>
</div>

<div class="content">
  <h2 class="section-title">本周综述</h2>
  <div class="overview">{overview}</div>

  {items_html}

  {trend_html}
</div>

</body>
</html>"""


# ── 共享 PDF 渲染 ──────────────────────────────────────

def html_to_pdf(html: str, pdf_path: Path) -> Path:
    """Chrome headless HTML → PDF"""
    import subprocess, tempfile, os
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(html)
    tmp.close()
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([
        chrome, "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        f"file://{tmp.name}"
    ], check=True, capture_output=True, timeout=30)
    os.unlink(tmp.name)
    return pdf_path


# ── 日报 HTML ──────────────────────────────────────────

def build_daily_html(sections: list[dict], date_cn: str, issue_no: int = 1, total_no: int = 1) -> str:
    """构建日报 HTML"""
    items_html = ""
    for s in sections:
        sname = s.get("name", "")
        items_html += f'<h2 class="section-title">{sname}</h2>\n'
        for item in s.get("items", []):
            title = item.get("title", "")
            date_i = item.get("date", "")
            summary = item.get("summary", "")
            insight = item.get("insight") or item.get("innovation_insight") or ""
            source = item.get("source", "")
            items_html += f"""
        <div class="news-item">
          <h3 class="item-title">{title}<span class="item-date">{date_i}</span></h3>
          <p class="item-summary">{summary}</p>
          <div class="item-insight">
            <span class="insight-label">创新洞察</span>
            <p>{insight}</p>
          </div>
          <p class="item-source">{source}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 22mm 16mm;
    @top-center {{
      content: element(header);
    }}
  }}
  @page:first {{
    margin: 0;
    @top-center {{ content: none; }}
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  :root {{
    --primary: #0a2655;
    --blue: #1e50b4;
    --accent: #8b6914;
    --accent-bg: #fdf8f0;
    --gray: #64748b;
    --light-gray: #e2e8f0;
    --bg: #f8fafc;
    --text: #1e293b;
    --text-secondary: #475569;
  }}

  body {{
    font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", "Microsoft YaHei", sans-serif;
    font-size: 10pt; line-height: 1.75; color: var(--text);
  }}

  /* ── Title block ── */
  .title-block {{
    text-align: center; padding: 20mm 0 8mm 0;
    border-bottom: 2px solid var(--primary);
    margin-bottom: 16px;
  }}
  .title-block h1 {{
    font-size: 20pt; font-weight: 700; color: var(--primary);
    letter-spacing: 2px; margin-bottom: 4px;
  }}
  .title-block .sub {{
    font-size: 9pt; color: var(--gray);
    letter-spacing: 3px; text-transform: uppercase;
  }}
  .title-block .date {{
    font-size: 9pt; color: var(--blue);
    margin-top: 6px;
  }}

  /* ── Running header ── */
  .running-header {{
    position: running(header);
    font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", sans-serif;
    font-size: 7.5pt; color: var(--blue);
    display: flex; justify-content: space-between;
    border-bottom: 1px solid var(--light-gray);
    padding-bottom: 4px; margin-bottom: 8px;
  }}

  .section-title {{
    font-size: 12pt; font-weight: 700; color: var(--blue);
    margin: 20px 0 10px 0; padding-bottom: 5px;
    border-bottom: 1.5px solid var(--light-gray);
    letter-spacing: 1px;
  }}

  /* ── Cover ── */
  .cover {{
    width: 210mm; height: 297mm;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(175deg, #eff6ff 0%, #dce8fc 40%, #c5d8f8 100%);
    position: relative; overflow: hidden;
    page: cover;
  }}
  .cover::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 5px;
    background: var(--primary);
  }}
  .cover::after {{
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 5px;
    background: var(--primary);
  }}
  .cover-label {{
    font-size: 9pt; letter-spacing: 5px; text-transform: uppercase;
    color: var(--blue); margin-bottom: 24px; font-weight: 500;
  }}
  .cover-title {{
    font-size: 30pt; font-weight: 700; color: var(--primary);
    letter-spacing: 3px; margin-bottom: 8px;
  }}
  .cover-divider {{
    width: 50px; height: 2px; background: var(--blue);
    margin: 16px auto 20px;
  }}
  .cover-sub {{
    font-size: 11pt; color: var(--blue); font-weight: 400;
    letter-spacing: 1px; margin-bottom: 36px;
  }}
  .cover-meta {{
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(59,108,180,0.12);
    border-radius: 6px;
    padding: 16px 32px; text-align: center;
  }}
  .cover-meta p {{
    font-size: 10pt; color: var(--gray); line-height: 2;
  }}

  .news-item {{
    margin-bottom: 14px; padding-bottom: 12px;
    border-bottom: 1px dotted var(--light-gray);
  }}
  .news-item:last-child {{ border-bottom: none; }}

  .item-title {{
    font-size: 10.5pt; font-weight: 600; color: var(--blue);
    margin-bottom: 3px; line-height: 1.6;
  }}
  .item-date {{
    font-size: 8pt; font-weight: 400; color: var(--gray);
    margin-left: 6px;
  }}

  .item-summary {{
    font-size: 9.5pt; color: var(--text-secondary);
    line-height: 1.8; margin-bottom: 6px;
    text-align: justify;
  }}

  .item-insight {{
    background: var(--accent-bg);
    border-left: 3px solid var(--accent);
    border-radius: 0 4px 4px 0;
    padding: 8px 14px; margin: 8px 0 6px 0;
  }}
  .item-insight p {{
    font-size: 9pt; color: #6b4f10;
    line-height: 1.8; display: inline;
  }}
  .insight-label {{
    font-size: 8pt; font-weight: 700; color: var(--accent);
    letter-spacing: 2px; margin-right: 6px;
  }}

  .item-source {{
    font-size: 7.5pt; color: #94a3b8; text-align: right;
    margin-top: 4px;
  }}

  @media print {{
    .cover {{ page-break-after: always; }}
    .news-item {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-label">DAILY REPORT</div>
  <h1 class="cover-title">创新常州·对标快讯</h1>
  <div class="cover-divider"></div>
  <p class="cover-sub">Innovation Changzhou · Benchmarking Daily</p>
  <div class="cover-meta">
    <p>2026年 第{issue_no}期 &nbsp;·&nbsp; 总第{total_no}期</p>
    <p>{date_cn}</p>
  </div>
</div>

<div class="running-header">
  <span>创新常州·对标快讯</span>
  <span>2026年第{issue_no}期</span>
</div>

<div class="content">
{items_html}
</div>

</body>
</html>"""


# ── 月报 ──────────────────────────────────────────────

MONTHLY_SYSTEM_PROMPT = """你是一位资深科技创新情报分析师，服务于常州市科技创新决策。请使用联网搜索功能，系统采集本月科技创新领域重要动态，撰写《创新常州·对标快讯》月报。

## ⛔ 事实准确性红线（最高优先级）

1. **所有信息必须来自搜索结果原文**，严禁编造、推测、或基于常识补全。未搜到具体数据的，宁可写"加快推进"也不虚构数字。
2. **每条必须标注发布日期**，日期必须与搜索结果中原文一致。
3. **每条必须有信息来源链接（URL）**，URL 必须是搜索结果中的真实链接。
4. **名称必须准确**：是"市委科技委员会""省委科技委员会"，简称"科技委"，不是"科委"。
5. **会议日期、发布文件名称、金额、数据**等关键信息必须与搜索到的原文严格一致。
6. **自行交叉验证**：对同一事件搜索至少2个不同信源确认。若信源间有矛盾，优先采信 .gov.cn 官方信源，并在摘要中注明"据XX官方发布"。

## 核心原则

1. **时效性**：采集本月内发布的重大信息
2. **信源优先级**：
   - 第一优先：.gov.cn 政务官方（国家级：most.gov.cn, miit.gov.cn, ndrc.gov.cn, cnipa.gov.cn, cgct.cn, service.most.gov.cn；省级：kxjst.jiangsu.gov.cn, stcsm.sh.gov.cn, kjt.zj.gov.cn, gdstc.gd.gov.cn；市级：各市科技局/发改委/工信局官网。重点关注政策发布、项目申报、公示公告、工作动态、规划文件）
   - 第二优先：权威平台（cas.cn, cae.cn, 各行业学会, 省产研院, 各行业技术研究院, 国家级重点实验室, 产业技术创新战略联盟, stdaily.com, cnki.net, wap.chinacos.cn, kczg.org.cn 等）
   - 第三优先：媒体智库（瞭望智库, 赛迪智库, 长城战略咨询, 中国信通院CAICT, 知领, 华信研究院, 甲子光年, 张通社研究院, 上海科技智库, 上海华略智库, 36氪研究院, 投资界研究院, pedaily.cn, thepaper.cn, cls.cn 等）
3. **每板块至少1条来自 .gov.cn 政务官方**
4. **月度视角**：不同于周报的即时性，月报应关注趋势演变、政策连贯性、跨板块关联。每条信息要体现其在月度框架中的位置——是延续性进展还是突破性信号。
5. **信息密度要求**：
   - 摘要充实饱满（100-150字），包含具体政策名称、金额、时间节点、涉及主体
   - 每条必须有独立价值，同一板块内避免选题雷同
   - 优先选取对常州有直接对标价值的信息

## 搜索维度（4维度 + 5产业赛道交叉搜索）

### 维度1：各地科技委动态（3-4条，至少1条来自 .gov.cn）
搜索各省市委科技委员会最新会议、部署、决策。注意：科技委是党委议事协调机构（全称"市委/省委科技委员会"），不是政府部门的"科委"。

### 维度2：上海（长三角）国创中心资讯（3-4条，至少1条来自 .gov.cn）
长三角国际科技创新中心、G60科创走廊、沿沪宁产业创新带

### 维度3：科创政策速览（3-4条，至少1条来自 .gov.cn）
万亿城市科技创新政策、产业扶持政策

### 维度4：改革举措（3-4条，至少1条来自 .gov.cn）
科技体制改革、科技成果转化、科技金融改革

### 产业赛道交叉搜索（融入以上4个维度）
以下5个方向不作为独立板块，交叉融入上述4个维度的搜索中，确保本月每条赛道至少有1条覆盖：
- **AIDC/算力基建**：AI数据中心、智算中心、算力补贴、产业园布局
- **具身智能**：人形机器人、智能体经济、产业政策、实训基地
- **未来存储**：新型存储技术、产业规划、标准制定
- **未来能源**：氢能、新型储能、钙钛矿、虚拟电厂
- **液冷技术**：数据中心液冷、浸没式冷却

以上方向搜索时加入关键词"算力+硬件+场景+生态""AI产业链""创新链"，构建产业链全链条视角。

## 创新洞察写作规范（每条80-120字）

### 必须做到：
1. **对标常州产业基础**：结合常州新能源、高端装备、新能源汽车等既有优势产业
2. **分析竞争态势**：对比苏州/无锡/南京/南通等周边万亿城市的同类布局，指出常州的差异化空间
3. **明确操作路径**：点明牵头部门、对接资源（中以常州创新园/科教城/高新区等名园名院名企）
4. **扣合三名工程/双高协同**：关联常州"名园名院名企"三名工程、高新区与高水平大学协同创新
5. **可落地建议**：给出下一步行动的具体方向

### 严禁出现：
- "值得借鉴""有参考价值""值得关注"等空话套话
- 脱离常州实际的泛泛建议
- 数字/政策名称与原文不符

## 输出格式

```json
{
  "monthly_overview": "200-300字本月综述，梳理本月核心主线、关键节点和重大变化，结合常州产业基础和竞争格局点明启示",
  "sections": [
    {
      "name": "各地科技委动态",
      "items": [
        {
          "title": "信息标题",
          "date": "2026.7.X",
          "summary": "100-150字，月度摘要可略长，用短句直击核心事实，包含具体政策名称/金额/时间/主体",
          "insight": "80-120字，结合常州产业基础和竞争态势，点明可做什么+怎么做+对接什么资源+涉及的常州政策抓手",
          "source": "来源机构名称",
          "url": "原文URL"
        }
      ]
    }
  ],
  "trend_analysis": "200-250字本月趋势分析，归纳2-3条跨板块深层趋势，重点分析常州在周边万亿城市中的定位与差异化机会",
  "strategic_recommendations": ["建议1（30-50字，可操作）", "建议2", "建议3", "建议4"]
}
```

记住：只输出 JSON。"""

MONTHLY_USER_PROMPT_TEMPLATE = """今天是{today_cn}。请联网搜索本月（{month_start}至{month_end}）科技创新领域重要动态，生成《创新常州·对标快讯》月报。

## ⛔ 事实准确性自检（每条必过）
1. 机构名称是否准确？（是"市委/省委科技委员会"，不是"科委"）
2. 会议/发布日期是否与原文一致？
3. 金额、百分比等数据是否与原文严格一致？
4. 是否有 .gov.cn 原文链接？
5. 同一条信息是否用2个以上信源交叉确认？

## 搜索要求

每维度3-4条，使用 site: 限定词优先命中政务官方信源。月报应有更广的覆盖面，各维度搜索至少3轮不同关键词组合。

### 维度1 · 各地科技委动态（至少1条来自 .gov.cn，3-4条）
注意：搜索"科技委"而非"科委"，全称"省委科技委员会"或"市委科技委员会"。
搜索：
- site:gov.cn "科技委" "会议" OR "全体会议" OR "部署"
- site:most.gov.cn "科技委" OR "科技创新"
- site:jiangsu.gov.cn "科技委" "会议" OR "全体会议"
- site:changzhou.gov.cn "科技委"
- "省委科技委" OR "市委科技委" "全体会议" OR "行动方案" OR "行动计划"

### 维度2 · 上海（长三角）国创中心资讯（至少1条来自 .gov.cn，3-4条）
搜索：
- site:most.gov.cn "长三角" "国际科技创新中心"
- site:stcsm.sh.gov.cn "张江" OR "科创中心"
- site:shanghai.gov.cn "国际科技创新中心"
- "长三角" "G60科创走廊" OR "沿沪宁产业创新带"
- "长三角" "科技创新" "协同" OR "一体化"

### 维度3 · 科创政策速览（至少1条来自 .gov.cn，3-4条）
搜索：
- site:gov.cn "科技创新政策"
- "万亿城市" "科技创新" "产业政策"
- "AIDC" OR "算力基建" OR "液冷" "产业政策" OR "产业园布局"
- "具身智能" OR "人工智能" "产业政策" OR "行动计划"
- "未来能源" OR "未来存储" "政策" OR "产业布局"
- "算力+硬件+场景+生态" OR "AI产业链创新链"
- site:beijing.gov.cn OR site:shenzhen.gov.cn OR site:nanjing.gov.cn OR site:suzhou.gov.cn "科技创新" "政策"

### 维度4 · 改革举措（至少1条来自 .gov.cn，3-4条）
搜索：
- site:gov.cn "科技体制改革" OR "科技成果转化"
- site:most.gov.cn "改革"
- "科技成果转化" "先投后股" OR "赋权改革" OR "科技金融"
- "校地合作" OR "新型研发机构" OR "高新区 高水平大学 协同"
- "三名工程" OR "名园名院名企" OR "双高协同"

### 产业交叉搜索（融入以上4个维度，确保全覆盖）
本月每个维度额外追加以下关键词的交叉搜索：
- "AIDC" OR "智算中心" — AI数据中心建设布局与补贴政策
- "具身智能" OR "人形机器人" OR "智能体" — 产业园、实训基地、产业政策
- "未来存储" OR "新型存储" — 存储技术路线与产业布局
- "未来能源" OR "氢能" OR "钙钛矿" OR "新型储能" — 新能源创新链
- "液冷" OR "浸没式冷却" — 数据中心散热技术标准

## 筛选标准
每条结果逐一过：
1. 信源权威可信？优先 .gov.cn
2. 日期是否在本月内（{month_start}至{month_end}）？
3. 信息充实？（具体政策名称/金额/数据/时间节点/涉及主体）
4. 对常州有对标价值？（优先可复制政策工具、可对接平台资源、周边万亿城市竞争动态）
5. 摘要去冗余、直击核心事实？

## 创新洞察自检（每条必查）
1. 是否结合了常州既有产业基础（新能源、高端装备、新能源汽车等）？
2. 是否分析了与苏州/无锡/南京/南通等周边万亿城市的竞争态势与差异化空间？
3. 是否关联了常州"三名工程"（中以常州创新园/科教城/龙头企业）或"双高协同"（高新区+高水平大学）？
4. 是否给出了具体可操作的下一步行动建议？
5. 是否避免了空话套话？
6. 数据、政策名称是否与搜索原文一致？

## 战略建议要求
4条战略建议必须：
- 紧扣常州市委市政府经济工作会议精神
- 针对 AIDC、具身智能、未来存储、未来能源、液冷等产业方向
- 考虑常州在 29 座万亿之城中的差异化定位
- 每条可落地、可量化、有明确责任部门

请逐维度搜索分析，只输出 JSON。"""


def get_monthly_data(api_key: str = None, sample: bool = False) -> dict:
    if sample or not api_key:
        return _monthly_sample_data()

    from datetime import date, timedelta
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    today = date.today()
    month_start = today.replace(day=1)
    today_cn = today.strftime("%Y年%m月%d日")
    month_start_cn = month_start.strftime("%Y年%m月%d日")
    month_end_cn = today.strftime("%Y年%m月%d日")
    year = today.strftime("%Y")
    month = today.strftime("%m")

    user_prompt = MONTHLY_USER_PROMPT_TEMPLATE.format(
        today_cn=today_cn, month_start=month_start_cn, month_end=month_end_cn,
        year=year, month=month,
    )

    print(f"[搜索] 月报区间: {month_start_cn} — {month_end_cn}")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": MONTHLY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=16000, temperature=0.3,
        extra_body={"enable_web_search": True},
    )

    text = response.choices[0].message.content or ""
    json_str = text.strip()
    if json_str.startswith("```"):
        lines = json_str.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        json_str = "\n".join(lines).strip()
    return json.loads(json_str)


def _monthly_sample_data() -> dict:
    return {
        "monthly_overview": "本月，长三角国际科技创新中心建设进入全面加速期。江苏、安徽、广东等省科技委密集召开全体会议，从议事协调机构向产业战略策源机构转型趋势明显。上海科创中心'十四五'收官评估全面超额完成，G60科创走廊和沿沪宁产业创新带建设提速，为常州融入区域创新网络提供新通道。万亿城市在AI算力、具身智能等前沿赛道投入力度空前，常州被明确列为高能级创新型城市建设对象，迎来重大政策窗口期。",
        "sections": [
            {
                "name": "各地科技委动态",
                "items": [
                    {"title": "江苏省委科技委召开第二次全体会议，审议科技招商三年行动计划", "date": "2026.7.2",
                     "summary": "省委科技委第二次全会审议通过《江苏省科技招商三年行动计划（2026-2028）》和《江苏省重大应用场景建设方案》，提出建立'科技+产业+金融'招商新模式，重点围绕第三代半导体、未来网络、氢能等方向招引'链主'企业。将面向全省开放100个重大应用场景。",
                     "insight": "常州应迅速承接省'科技招商'计划，结合新能源、智能制造产业优势，重点对接第三代半导体和氢能领域'链主'企业，并积极申报省级重大应用场景，将常州'智能工厂'作为示范场景争取省级资源。",
                     "source": "江苏省人民政府"},
                    {"title": "安徽省委科技委部署未来产业先导区建设", "date": "2026.7.1",
                     "summary": "安徽省委科技委专题会议明确依托合肥综合性国家科学中心，在量子信息、聚变能源、深空探测三大领域率先建设省级未来产业先导区，计划到2028年集聚相关企业超500家。",
                     "insight": "安徽围绕国家科学中心布局未来产业的做法对常州有借鉴意义。常州可依托中以常州创新园和科教城，在新能源、合成生物等优势领域建设市级未来产业先导区，与合肥形成差异化互补。",
                     "source": "安徽省科技厅"},
                    {"title": "深圳市科技委部署'全域全时'AI应用示范城市方案", "date": "2026.6.30",
                     "summary": "深圳市委科技委审议通过《深圳市加快打造全域全时人工智能应用示范城市行动方案（2026-2028）》，到2028年建成100个以上'AI+'标杆应用场景，建设城市级AI算力调度平台，设立50亿元AI场景应用专项补贴。",
                     "insight": "深圳'全域全时'方案为常州提供了可复制政策工具包。常州应加速AIDC建设，设立市级AI场景应用专项补贴，鼓励理想汽车、中创新航等名企开放生产场景，抢占工业AI应用先机。",
                     "source": "深圳市人民政府"},
                ]
            },
            {
                "name": "上海（长三角）国创中心资讯",
                "items": [
                    {"title": "上海国际科创中心'十四五'收官评估：核心指标全面超额完成", "date": "2026.7.3",
                     "summary": "上海市政府发布收官评估报告：全社会研发经费支出占GDP比重达4.8%，基础研究经费占比达12%，每万人口高价值发明专利拥有量达50件，技术合同成交额突破6000亿元，四项核心指标均超额完成。张江科学城集聚超2万家高新技术企业。",
                     "insight": "上海科创中心溢出效应日益显著，常州应主动承接产业转移和成果转化。建议常州科技局与张江高新区建立定期对接机制，在生物医药和集成电路领域吸引CRO/CMO企业在常设立生产基地，形成'张江研发、常州制造'协同模式。",
                     "source": "上海市人民政府"},
                    {"title": "G60科创走廊发布'科创+产业'深度融合行动方案", "date": "2026.7.2",
                     "summary": "G60科创走廊联席会议办公室发布行动方案，聚焦集成电路、生物医药、人工智能三大先导产业，设立首期规模50亿元的跨区域产业母基金，组建10个跨区域产业联盟，推动创新券在九城市通用。",
                     "insight": "常州作为G60成员城市，应依托新能源产业优势牵头组建跨区域新能源产业联盟，并积极争取跨区域产业母基金支持本地AIDC和未来能源项目，推动常州创新券纳入G60通用体系。",
                     "source": "G60科创走廊联席会议办公室"},
                    {"title": "沿沪宁产业创新带建设提速，常州'创新飞地'模式获推广", "date": "2026.6.29",
                     "summary": "江苏省发改委发布《沿沪宁产业创新带建设2026年工作要点》，明确支持常州等城市在上海设立'创新飞地'，探索'研发孵化在上海、产业化落地在常州'协同模式，计划在常州举办科技成果对接会。",
                     "insight": "常州应将现有上海'创新飞地'从招商窗口升级为'离岸研发+孵化+投资'综合平台，联合上海交大、同济等高校在飞地内设立联合实验室，定向为常州企业输送智能制造和新材料领域原创技术。",
                     "source": "江苏省发展和改革委员会"},
                ]
            },
            {
                "name": "科创政策速览",
                "items": [
                    {"title": "工信部等七部门印发《关于加快推动人工智能赋能新型工业化的实施意见》", "date": "2026.7.1",
                     "summary": "七部门联合发文，到2028年建成30个以上国家AI赋能新型工业化先导区，培育100家以上行业级AI大模型企业。对国家级先导区内AI算力中心建设，中央财政给予不超过总投资20%的补贴。",
                     "insight": "该意见为常州AIDC建设提供直接政策资金支持。常州应积极申报'国家人工智能赋能新型工业化先导区'，加快AIDC项目落地争取中央补贴，鼓励中天钢铁、今创集团等龙头企业与AI企业合作打造行业级大模型。",
                     "source": "工业和信息化部"},
                    {"title": "北京市发布具身智能机器人产业发展行动计划（2026-2030年）", "date": "2026.7.2",
                     "summary": "北京市政府发布行动计划，目标到2030年具身智能机器人核心产业规模达千亿级。提出建设具身智能'数据工厂'和公共训练平台，对购置训练算力的企业给予30%补贴。",
                     "insight": "常州在具身智能领域应发挥制造业场景优势，联合理想汽车、比亚迪在常工厂共建具身智能实训基地，利用科教城职教资源打造长三角具身智能技能人才培训高地，与北京形成'研发在京、实训在常'的分工格局。",
                     "source": "北京市人民政府"},
                    {"title": "浙江省发布未来能源产业培育行动方案，重点发展氢能与储能", "date": "2026.6.30",
                     "summary": "浙江省发布方案，到2028年未来能源产业规模力争达5000亿元，重点发展氢能、新型储能、核能三大方向。对新建氢能基础设施给予不超过投资额30%的补贴。",
                     "insight": "浙江政策对常州新能源之都建设有直接对标意义。常州在氢能和储能领域已有中创新航、蜂巢能源等布局，应进一步对标浙江出台更大力度补贴方案，加快加氢站网络建设，与嘉兴、宁波探索长三角氢能走廊。",
                     "source": "浙江省人民政府"},
                ]
            },
            {
                "name": "改革举措",
                "items": [
                    {"title": "科技部等十部门联合推广'先投后股'科技成果转化改革试点经验", "date": "2026.7.3",
                     "summary": "十部门联合通知在全国推广'先投后股'模式：政府以科技项目资金'先投'给科研团队，项目公司化并引入社会资本后，再将前期投入按约定价格'后股'转为股权。要求各地设立专项资金并建立容错免责机制，允许最高30%的项目失败率。",
                     "insight": "'先投后股'是破解成果转化'死亡之谷'的有效工具。常州应由市科技局牵头，联合财政局设立市级专项资金（首期建议5亿元），重点支持中以常州创新园和科教城内早期硬科技项目，建立容错机制鼓励大胆试错。",
                     "source": "科学技术部"},
                    {"title": "上海市发布新型研发机构备案与管理办法，探索'事业单位+企业'双法人模式", "date": "2026.7.1",
                     "summary": "上海发布新型研发机构管理办法，允许新型研发机构同时登记为事业单位和科技企业，享受事业法人政策支持和企业市场化运营灵活性。对符合条件的机构给予3年运营经费全额补贴。",
                     "insight": "常州应借鉴上海'双法人'模式，在市科教城和中以创新园试点新型研发机构改革，允许入驻机构兼具事业和企业的双重身份，吸引更多高水平研发团队来常落户。",
                     "source": "上海市科学技术委员会"},
                    {"title": "广东省启动'科技金融深度融合'专项行动，试点'科技保险'与'投贷联动'", "date": "2026.6.29",
                     "summary": "广东在8个城市试点'科技保险'（研发失败险、知识产权侵权险等），扩大'投贷联动'试点，设立50亿元省级科技信贷风险补偿资金池。",
                     "insight": "广东科技金融创新为常州提供丰富政策工具箱。常州应联合江南银行等本地金融机构探索'科技保险'产品，引导本地银行与创投机构合作开展'投贷联动'，设立市级科技信贷风险补偿资金池。",
                     "source": "广东省地方金融监督管理局"},
                ]
            },
        ],
        "trend_analysis": "本月呈现三大深层趋势：一是科技委体制从'议事协调'走向'实体化运作'，各地科技委不再停留于宏观部署而是直接审议具体行动方案并配套专项资金，科技创新成为'一把手工程'；二是长三角协同从'物理连接'走向'化学反应'，G60和沿沪宁产业创新带进入实质性项目合作阶段，跨区域产业基金和联盟密集组建；三是政策工具从传统财税补贴全面升级为算力券、场景开放、科技保险、先投后股等新型支撑手段。对常州而言，需紧抓三大机遇：高能级创新型城市定位带来的省级资源倾斜、沿沪宁产业创新带建设带来的'沪研常转'制度通道、以及国家AI赋能新型工业化政策带来的AIDC建设窗口期。",
        "strategic_recommendations": [
            "尽快制定常州版高能级创新型城市建设三年行动方案，明确在沿沪宁产业创新带中的差异化功能定位",
            "积极申报'国家人工智能赋能新型工业化先导区'，加快AIDC项目落地争取中央财政补贴",
            "设立市级'先投后股'专项资金（首期5亿元），在中以创新园和科教城率先试点",
            "将上海'创新飞地'升级为'离岸研发+孵化+投资'综合平台，联合高校设联合实验室",
            "对标浙江出台氢能基础设施补贴方案，牵头组建G60新能源产业联盟"
        ]
    }


def build_monthly_html(data: dict, issue_no: int, total_no: int, date_cn: str) -> str:
    """构建月度 HTML 报告"""
    overview = data.get("monthly_overview") or data.get("overview") or ""
    sections = data.get("sections", [])
    trend = data.get("trend_analysis") or data.get("trend") or ""
    recommendations = data.get("strategic_recommendations") or data.get("recommendations") or []

    items_html = ""
    for s in sections:
        sname = s.get("name") or s.get("section_name") or ""
        items_html += f'<h2 class="section-title">{sname}</h2>\n'
        for item in s.get("items", []):
            title = item.get("title", "")
            date_i = item.get("date", "")
            summary = item.get("summary", "")
            insight = item.get("innovation_insight") or item.get("insight") or ""
            source = item.get("source", "")
            items_html += f"""
        <div class="news-item">
          <h3 class="item-title">{title}<span class="item-date">{date_i}</span></h3>
          <p class="item-summary">{summary}</p>
          <div class="item-insight">
            <span class="insight-label">创新洞察</span>
            <p>{insight}</p>
          </div>
          <p class="item-source">{source}</p>
        </div>"""

    trend_html = ""
    if trend:
        trend_html += f"""
      <h2 class="section-title">本月趋势分析</h2>
      <p class="trend-text">{trend}</p>"""

    recs_html = ""
    if recommendations:
        recs_items = "\n".join(f"<li>{r}</li>" for r in recommendations)
        recs_html = f"""
      <h2 class="section-title">战略建议</h2>
      <ol class="recs-list">{recs_items}</ol>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 22mm 16mm;
    @top-center {{
      content: element(header);
    }}
  }}
  @page:first {{
    margin: 0;
    @top-center {{ content: none; }}
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  :root {{
    --primary: #0a2655;
    --blue: #1e50b4;
    --accent: #8b6914;
    --accent-bg: #fdf8f0;
    --gray: #64748b;
    --light-gray: #e2e8f0;
    --bg: #f8fafc;
    --text: #1e293b;
    --text-secondary: #475569;
  }}

  body {{
    font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", "Microsoft YaHei", sans-serif;
    font-size: 10pt; line-height: 1.75; color: var(--text);
  }}

  /* ── Cover ── */
  .cover {{
    width: 210mm; height: 297mm;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(175deg, #eff6ff 0%, #dce8fc 40%, #c5d8f8 100%);
    position: relative; overflow: hidden;
    page: cover;
  }}
  .cover::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 5px;
    background: var(--primary);
  }}
  .cover::after {{
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 5px;
    background: var(--primary);
  }}
  .cover-label {{
    font-size: 9pt; letter-spacing: 5px; text-transform: uppercase;
    color: var(--blue); margin-bottom: 24px; font-weight: 500;
  }}
  .cover-title {{
    font-size: 30pt; font-weight: 700; color: var(--primary);
    letter-spacing: 3px; margin-bottom: 8px;
  }}
  .cover-divider {{
    width: 50px; height: 2px; background: var(--blue);
    margin: 16px auto 20px;
  }}
  .cover-sub {{
    font-size: 11pt; color: var(--blue); font-weight: 400;
    letter-spacing: 1px; margin-bottom: 36px;
  }}
  .cover-meta {{
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(59,108,180,0.12);
    border-radius: 6px;
    padding: 16px 32px; text-align: center;
  }}
  .cover-meta p {{
    font-size: 10pt; color: var(--gray); line-height: 2;
  }}

  /* ── Running header ── */
  .running-header {{
    position: running(header);
    font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", sans-serif;
    font-size: 7.5pt; color: var(--blue);
    display: flex; justify-content: space-between;
    border-bottom: 1px solid var(--light-gray);
    padding-bottom: 4px; margin-bottom: 8px;
  }}

  /* ── Content ── */
  .content {{ padding-top: 8mm; }}

  .overview {{
    font-size: 10pt; color: var(--text-secondary);
    line-height: 1.9; margin-bottom: 22px;
    padding: 14px 18px;
    background: var(--bg);
    border-left: 3px solid var(--blue);
    border-radius: 0 4px 4px 0;
  }}

  .section-title {{
    font-size: 13pt; font-weight: 700; color: var(--blue);
    margin: 24px 0 12px 0; padding-bottom: 6px;
    border-bottom: 1.5px solid var(--light-gray);
    letter-spacing: 1px;
  }}

  .news-item {{
    margin-bottom: 16px; padding-bottom: 14px;
    border-bottom: 1px dotted var(--light-gray);
  }}
  .news-item:last-child {{ border-bottom: none; }}

  .item-title {{
    font-size: 10.5pt; font-weight: 600; color: var(--blue);
    margin-bottom: 3px; line-height: 1.6;
  }}
  .item-date {{
    font-size: 8pt; font-weight: 400; color: var(--gray);
    margin-left: 6px;
  }}

  .item-summary {{
    font-size: 9.5pt; color: var(--text-secondary);
    line-height: 1.8; margin-bottom: 6px;
    text-align: justify;
  }}

  .item-insight {{
    background: var(--accent-bg);
    border-left: 3px solid var(--accent);
    border-radius: 0 4px 4px 0;
    padding: 8px 14px; margin: 8px 0 6px 0;
  }}
  .item-insight p {{
    font-size: 9pt; color: #6b4f10;
    line-height: 1.8; display: inline;
  }}
  .insight-label {{
    font-size: 8pt; font-weight: 700; color: var(--accent);
    letter-spacing: 2px; margin-right: 6px;
  }}

  .item-source {{
    font-size: 7.5pt; color: #94a3b8; text-align: right;
    margin-top: 4px;
  }}

  .trend-text {{
    font-size: 10pt; color: var(--text-secondary);
    line-height: 1.9; text-align: justify;
    padding: 14px 18px;
    background: var(--bg);
    border-radius: 4px;
  }}

  .recs-list {{
    font-size: 10pt; color: var(--text-secondary);
    line-height: 2; padding-left: 24px;
  }}
  .recs-list li {{ margin-bottom: 6px; }}

  @media print {{
    .cover {{ page-break-after: always; }}
    .news-item {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-label">MONTHLY REPORT</div>
  <h1 class="cover-title">创新常州·对标快讯</h1>
  <div class="cover-divider"></div>
  <p class="cover-sub">Innovation Changzhou · Benchmarking Monthly</p>
  <div class="cover-meta">
    <p>{date_cn[:4]}年 第{issue_no}期 &nbsp;·&nbsp; 总第{total_no}期</p>
    <p>{date_cn}</p>
  </div>
</div>

<div class="running-header">
  <span>创新常州·对标快讯（月报）</span>
  <span>{date_cn[:4]}年第{issue_no}期</span>
</div>

<div class="content">
  <h2 class="section-title">本月综述</h2>
  <div class="overview">{overview}</div>

  {items_html}

  {trend_html}

  {recs_html}
</div>

</body>
</html>"""


def generate_monthly(api_key: str = None, output_path: str = None, sample: bool = False):
    import sys as _sys
    _sys.path.insert(0, str(PROJECT_DIR))

    today = date.today()
    date_cn = today.strftime("%Y年%m月%d日")
    date_fn = today.strftime("%Y%m")

    from generate_docx import get_issue_numbers
    try:
        issue, total = get_issue_numbers()
        if issue <= 0: issue, total = 1, 1
    except Exception:
        issue, total = 1, 1

    print("[数据] 正在获取月报内容...")
    data = get_monthly_data(api_key, sample)

    print("[HTML] 生成页面...")
    html = build_monthly_html(data, issue, total, date_cn)

    html_path = PROJECT_DIR / "monthly" / f"月报_{date_fn}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")

    pdf_path = Path(output_path) if output_path else PROJECT_DIR / "monthly" / f"创新常州·对标快讯_月报_{date_fn}.pdf"
    print("[PDF] 渲染中 (Chrome headless)...")
    html_to_pdf(html, pdf_path)

    # 分发到桌面
    _distribute_report(pdf_path, "monthly")

    print(f"[完成] HTML: {html_path}")
    print(f"[完成] PDF:  {pdf_path}")
    return pdf_path


# ── 桌面同步 ────────────────────────────────────────────

def _distribute_report(pdf_path: Path, report_type: str):
    """将报告分发到桌面对应子目录（日报/周报/月报）"""
    import sys as _sys
    _sys.path.insert(0, str(SCRIPT_DIR))
    from distribute import save_desktop
    save_desktop(str(pdf_path), report_type)


# ── 主入口 ────────────────────────────────────────────

def generate(api_key: str = None, output_path: str = None, sample: bool = False):
    import sys as _sys
    _sys.path.insert(0, str(PROJECT_DIR))

    today = date.today()
    date_cn = today.strftime("%Y年%m月%d日")
    date_fn = today.strftime("%Y%m%d")

    from generate_docx import get_issue_numbers
    try:
        issue, total = get_issue_numbers()
        if issue <= 0: issue, total = 1, 1
    except Exception:
        issue, total = 1, 1

    print("[数据] 正在获取周报内容...")
    data = get_weekly_data(api_key, sample)

    print("[HTML] 生成页面...")
    html = build_html(data, issue, total, date_cn)

    # 保存 HTML
    html_path = PROJECT_DIR / "weekly" / f"周报_{date_fn}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")

    # 转 PDF
    pdf_path = Path(output_path) if output_path else PROJECT_DIR / "weekly" / f"创新常州·对标快讯_周报_{date_fn}.pdf"
    print("[PDF] 渲染中 (Chrome headless)...")
    html_to_pdf(html, pdf_path)

    # 分发到桌面
    _distribute_report(pdf_path, "weekly")

    print(f"[完成] HTML: {html_path}")
    print(f"[完成] PDF:  {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--output", "-o")
    parser.add_argument("--monthly", action="store_true", help="生成月报（默认生成周报）")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key and not args.sample:
        try:
            _sys = __import__("sys"); _sys.path.insert(0, str(PROJECT_DIR))
            from run_daily import load_config
            api_key = load_config().get("deepseek_api_key", "")
        except: pass
    if not api_key and not args.sample:
        print("[提示] 无 API Key，使用示例数据"); args.sample = True

    key = api_key if not args.sample else None
    if args.monthly:
        generate_monthly(api_key=key, output_path=args.output, sample=args.sample)
    else:
        generate(api_key=key, output_path=args.output, sample=args.sample)
