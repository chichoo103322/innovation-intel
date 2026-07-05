#!/usr/bin/env python3
"""
《创新常州·对标快讯》PDF 报告生成器（美化版）
现代专业报告设计，蓝金配色，封面+连续内容排版
"""
import sys
from pathlib import Path
from datetime import datetime, date
from fpdf import FPDF

PROJECT_DIR = Path(__file__).parent.parent

# ── 字体查找 ──────────────────────────────────────────────

def _find_font(base_names: list[str]) -> str | None:
    font_dirs = [
        Path.home() / "Library/Fonts",
        "/Library/Fonts",
        "/System/Library/Fonts",
        "/System/Library/Fonts/Supplemental",
    ]
    for d in font_dirs:
        p = Path(d)
        if not p.exists():
            continue
        for name in base_names:
            for ext in (".ttf", ".ttc", ".otf"):
                candidate = p / f"{name}{ext}"
                if candidate.exists():
                    return str(candidate)
    return None


FONT_BOLD = _find_font([
    "NotoSansSC-Bold", "NotoSans-Bold",
    "PingFang-SC-Semibold", "PingFang-SC-Medium",
    "STHeiti-Medium", "STHeiti Medium",
    "Heiti-SC-Medium", "Heiti SC Medium",
])
FONT_REGULAR = _find_font([
    "NotoSansSC-Regular", "NotoSans-Regular",
    "PingFang-SC-Regular", "PingFang-SC-Light",
    "STHeiti-Light", "STHeiti Light",
    "Heiti-SC-Light", "Heiti SC Light",
])
FONT_LIGHT = _find_font([
    "NotoSansSC-Light", "NotoSans-Light",
    "PingFang-SC-Ultralight", "PingFang-SC-Thin",
    "STHeiti-Light", "STHeiti Light",
    "Heiti-SC-Light", "Heiti SC Light",
]) or FONT_REGULAR
FONT_BOLD = FONT_BOLD or FONT_REGULAR
FONT_REGULAR = FONT_REGULAR or FONT_BOLD
assert FONT_REGULAR, "找不到任何中文字体，请安装 Noto Sans SC 或 PingFang"

print(f"[字体] Bold: {FONT_BOLD}")
print(f"[字体] Regular: {FONT_REGULAR}")

# ── 设计常量 ──────────────────────────────────────────────
C_DARK_BLUE  = (26,  82,  118)   # #1a5276
C_MID_BLUE   = (41,  128, 185)   # #2980b9
C_LIGHT_BLUE = (133, 193, 233)   # 装饰线
C_GOLD       = (125, 102, 8)     # #7d6608
C_GRAY       = (85,  85,  85)    # #555555
C_LIGHT_GRAY = (180, 180, 180)
C_BG         = (245, 248, 252)   # 封面背景浅蓝
C_BLACK      = (0,   0,   0)
C_WHITE      = (255, 255, 255)

S_COVER_TITLE  = 34
S_COVER_SUB    = 14
S_COVER_ISSUE  = 12
S_COVER_DATE   = 11
S_SECTION      = 13
S_ITEM_TITLE   = 10.5
S_BODY         = 9.5
S_SOURCE       = 7.5
S_HEADER       = 7.5
S_FOOTER       = 7.5

M_LEFT   = 14
M_RIGHT  = 14
M_TOP    = 14
M_INSIGHT_LEFT = 20

PAGE_W = 210
PAGE_H = 297
BODY_W = PAGE_W - M_LEFT - M_RIGHT


class InnovationPDF(FPDF):
    """创新常州·对标快讯 PDF 报告"""

    def __init__(self, issue_no: int = 1, total_no: int = 1, date_cn: str = ""):
        super().__init__("P", "mm", "A4")
        self.issue_no = issue_no
        self.total_no = total_no
        self.date_cn = date_cn
        self._in_cover = False

        self.add_font("NB", "", FONT_BOLD)
        self.add_font("NR", "", FONT_REGULAR)
        self.add_font("NL", "", FONT_LIGHT)

        self.set_auto_page_break(True, 18)

    # ── 封面 ───────────────────────────────────────────

    def cover_page(self, report_type: str = "weekly"):
        self._in_cover = True
        self.add_page()
        self._in_cover = False

        # 顶部装饰条
        self.set_fill_color(*C_DARK_BLUE)
        self.rect(0, 0, PAGE_W, 3, "F")

        # 中部内容区
        center_y = 95
        self.set_y(center_y)

        # 英文小标签
        self.set_font("NR", "", 10)
        self.set_text_color(*C_MID_BLUE)
        type_label = {"weekly": "WEEKLY REPORT", "monthly": "MONTHLY REPORT", "daily": "DAILY BRIEFING"}
        self.cell(0, 5, type_label.get(report_type, "REPORT"), align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(8)

        # 主标题
        self.set_font("NB", "", S_COVER_TITLE)
        self.set_text_color(*C_DARK_BLUE)
        self.cell(0, 13, "创新常州·对标快讯", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        # 细线分隔
        self.set_draw_color(*C_LIGHT_BLUE)
        self.set_line_width(0.3)
        line_w = 60
        line_x = (PAGE_W - line_w) / 2
        self.line(line_x, self.get_y() + 2, line_x + line_w, self.get_y() + 2)
        self.ln(6)

        # 英文副标题
        self.set_font("NL", "", S_COVER_SUB)
        self.set_text_color(*C_MID_BLUE)
        en_title = {"weekly": "Innovation Changzhou · Benchmarking Weekly",
                    "monthly": "Innovation Changzhou · Benchmarking Monthly",
                    "daily": "Innovation Changzhou · Benchmarking Daily"}
        self.cell(0, 7, en_title.get(report_type, ""), align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(16)

        # 期号 & 日期卡片
        card_w = 70
        card_h = 24
        card_x = (PAGE_W - card_w) / 2
        card_y = self.get_y()

        self.set_fill_color(*C_BG)
        self.set_draw_color(*C_LIGHT_BLUE)
        self.set_line_width(0.2)
        self.rect(card_x, card_y, card_w, card_h, "DF")

        self.set_xy(card_x, card_y + 3)
        self.set_font("NR", "", S_COVER_ISSUE)
        self.set_text_color(*C_GRAY)
        issue_text = f"2026年 第{self.issue_no}期  总第{self.total_no}期"
        self.cell(card_w, 6, issue_text, align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_x(card_x)
        self.set_font("NR", "", S_COVER_DATE)
        self.set_text_color(*C_GRAY)
        self.cell(card_w, 6, self.date_cn, align="C")

        # 底部装饰条
        self.set_fill_color(*C_DARK_BLUE)
        self.rect(0, PAGE_H - 4, PAGE_W, 4, "F")

    # ── 页眉页脚 ──────────────────────────────────────

    def header(self):
        if self._in_cover:
            return
        # 文字
        self.set_font("NR", "", S_HEADER)
        self.set_text_color(*C_MID_BLUE)
        self.set_y(7)
        self.cell(0, 4, "创新常州·对标快讯", align="L")
        self.set_xy(-50, 7)
        self.cell(0, 4, f"2026年第{self.issue_no}期", align="R")
        # 文字下方细线
        self.set_draw_color(*C_MID_BLUE)
        self.set_line_width(0.3)
        self.line(M_LEFT, 13, PAGE_W - M_RIGHT, 13)
        self.set_y(16)

    def footer(self):
        if self._in_cover:
            return
        self.set_y(-15)
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.2)
        self.line(M_LEFT, self.get_y(), PAGE_W - M_RIGHT, self.get_y())
        self.ln(2)
        self.set_font("NR", "", S_FOOTER)
        self.set_text_color(*C_GRAY)
        self.cell(0, 5, f"— {self.page_no()} —", align="C")

    # ── 内容组件 ───────────────────────────────────────

    def section_title(self, text: str):
        """板块标题"""
        self.ln(2)
        # 左侧小色块
        self.set_fill_color(*C_DARK_BLUE)
        x0 = self.get_x()
        y0 = self.get_y() + 2
        self.rect(x0, y0, 3, 6, "F")
        self.set_x(x0 + 5)
        self.set_font("NB", "", S_SECTION)
        self.set_text_color(*C_DARK_BLUE)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def news_item(self, title: str, date_info: str, summary: str,
                  insight: str, source: str = ""):
        """一条新闻"""
        # 检查剩余空间：如果剩余不到 30mm，换页
        if self.get_y() > PAGE_H - 40:
            self.add_page()

        # 标题
        self.set_font("NB", "", S_ITEM_TITLE)
        self.set_text_color(*C_MID_BLUE)
        title_full = f"● {title}"
        if date_info:
            title_full += f"（{date_info}）"
        self.multi_cell(BODY_W, 5.8, title_full, align="L")
        self.ln(0.5)

        # 正文
        self.set_font("NR", "", S_BODY)
        self.set_text_color(*C_BLACK)
        self.multi_cell(BODY_W, 5, summary, align="L")
        self.ln(0.5)

        # 创新洞察（缩进 + 金色）
        self.set_font("NR", "", S_BODY)
        self.set_text_color(*C_GOLD)
        self.set_x(M_INSIGHT_LEFT)
        self.multi_cell(PAGE_W - M_INSIGHT_LEFT - M_RIGHT, 5,
                        f"创新洞察：{insight}", align="L")
        self.ln(0.5)

        # 来源
        if source:
            self.set_font("NR", "", S_SOURCE)
            self.set_text_color(*C_GRAY)
            self.cell(0, 3.5, f"（来源：{source}）", align="R",
                      new_x="LMARGIN", new_y="NEXT")
        self.ln(3)


# ── 内容生成 ──────────────────────────────────────────

def generate_weekly_content(api_key: str) -> dict:
    week_start = "2026年6月28日"
    week_end = "2026年7月5日"

    system = f"""你是资深科技创新情报分析师。请生成本周（{week_start}至{week_end}）的《创新常州·对标快讯》周报。

## 板块结构

严格按以下4个板块，每板块2-3条：

1. 各地科技委动态 — 各省市科技委最新会议、部署、决策
2. 上海（长三角）国创中心资讯 — 长三角国创中心、G60科创走廊、沿沪宁产业创新带动态
3. 科创政策速览 — 万亿城市科技创新政策、产业扶持政策
4. 改革举措 — 科技体制改革、科技成果转化、科技金融改革

## 内容要求

- weekly_overview：150-200字，概述本周核心主线
- 每条含：title、date、summary（100-150字，直击核心要点，删冗余铺垫）、innovation_insight（80-120字，结合常州实际，可关联常州AIDC/算力、具身智能、未来存储/能源、液冷、三名工程、双高协同等方向，但不强求每条都覆盖）、source
- trend_analysis：200-300字，本周趋势信号

只输出 JSON。"""

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"本周：{week_start} 至 {week_end}。请联网搜索，按4个标准板块生成周报JSON。创新洞察可自然结合常州重点方向（AIDC、具身智能、液冷、未来能源/存储、三名工程、双高协同），但不需每条强行关联。"},
        ],
        max_tokens=12000,
        temperature=0.3,
        extra_body={"enable_web_search": True},
    )

    text = response.choices[0].message.content or ""
    json_str = text.strip()
    if json_str.startswith("```"):
        lines = json_str.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        json_str = "\n".join(lines).strip()

    import json
    return json.loads(json_str)


# ── 主入口 ────────────────────────────────────────────

def generate_weekly_pdf(api_key: str = None, output_path: str = None,
                        sample: bool = False):
    import sys as _sys
    _sys.path.insert(0, str(PROJECT_DIR))

    today = date.today()
    date_cn = today.strftime("%Y年%m月%d日")
    date_fn = today.strftime("%Y%m%d")

    from generate_docx import get_issue_numbers
    try:
        issue, total = get_issue_numbers()
        if issue <= 0:
            issue, total = 1, 1
    except Exception:
        issue, total = 1, 1

    if sample:
        data = _sample_weekly_data()
    elif api_key:
        data = generate_weekly_content(api_key)
    else:
        data = _sample_weekly_data()

    pdf = InnovationPDF(issue_no=issue, total_no=total, date_cn=date_cn)
    pdf.cover_page("weekly")

    # ── 第一页开始内容，连续排版 ──
    first_page = True

    # 本周综述
    overview = data.get("weekly_overview") or data.get("overview") or ""
    if overview:
        pdf.add_page()
        first_page = False
        pdf.section_title("本周综述")
        pdf.set_font("NR", "", S_BODY)
        pdf.set_text_color(*C_BLACK)
        pdf.multi_cell(BODY_W, 5, overview, align="L")
        pdf.ln(4)

    # 四个板块 — 连续排版，不分页
    sections = data.get("sections", [])
    for section in sections:
        section_name = section.get("name") or section.get("section_name") or ""
        if section_name:
            pdf.section_title(section_name)
        for item in section.get("items", []):
            pdf.news_item(
                title=item.get("title", ""),
                date_info=item.get("date", ""),
                summary=item.get("summary", ""),
                insight=item.get("innovation_insight") or item.get("insight") or "",
                source=item.get("source", ""),
            )

    # 周度趋势
    trend = data.get("trend_analysis") or data.get("trend") or ""
    if trend:
        pdf.section_title("本周趋势分析")
        pdf.set_font("NR", "", S_BODY)
        pdf.set_text_color(*C_BLACK)
        pdf.multi_cell(BODY_W, 5, trend, align="L")

    if output_path is None:
        output_path = PROJECT_DIR / "weekly" / f"创新常州·对标快讯_周报_{date_fn}.pdf"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"[完成] 周报 PDF 已生成: {output_path}")
    return output_path


def _sample_weekly_data() -> dict:
    return {
        "weekly_overview": "本周（6月28日—7月5日）长三角国际科技创新中心建设加速推进，各省市科技委密集召开全体会议部署下半年重点任务。武汉光谷、南京、郑州等万亿城市纷纷加码AI与具身智能赛道，政策竞争态势加剧。常州被列为高能级创新型城市建设对象，在沿沪宁产业创新带中的定位进一步明确。",
        "sections": [
            {
                "name": "各地科技委动态",
                "items": [
                    {
                        "title": "江苏省委科技委员会全体会议召开",
                        "date": "2026.7.1",
                        "summary": "省委书记信长星主持，省长刘小涛出席。会议强调高效协同推进上海（长三角）国际科技创新中心建设，南京、苏州扛起关键支点重任，无锡、常州、南通建设高能级创新型城市。会议讨论了《江苏省人工智能驱动科学研究实施方案》。",
                        "insight": "常州被明确列为「高能级创新型城市」建设对象，应趁势主动对接省AI驱动科研方案，争取省级示范项目在常州AIDC落地，同时加快制定常州版高能级创新型城市建设行动方案，明确在沿沪宁产业创新带中的差异化功能定位。",
                        "source": "江苏省人民政府"
                    },
                    {
                        "title": "广东省委科技委发布脑机接口产业协同发展行动计划",
                        "date": "2026.7.2",
                        "summary": "印发《广东省脑机接口科技与产业协同发展行动计划（2026—2030年）》，目标到2030年核心产业规模达百亿级，辐射上下游达千亿级。这是全国首个由省级科技委直接发布的未来产业行动计划，标志科技委正从协调机构向产业战略策源机构转型。",
                        "insight": "广东科技委直接发布产业行动计划的做法值得关注。常州可参照此模式，由市委科技委发布新能源、合成生物等优势产业的技术创新路线图，提升科技委的战略引领力和产业话语权。",
                        "source": "广东省科技厅"
                    },
                    {
                        "title": "江西省委科技委第七次全体会议召开",
                        "date": "2026.7.2",
                        "summary": "省长叶建春主持，部署加快推进「十五五」科技创新规划编制，实施「2030启航计划」和「2030先锋工程」，推动人工智能重构科研范式，构建多元化科技投入格局。",
                        "insight": "江西「靶向攻坚」方法论和多元化科技投入格局值得借鉴。常州可在「三名联动」框架下探索「财政引导+企业主导+社会资本跟投」三级投入模式，集中资源突破新能源、合成生物等优势领域的关键瓶颈。",
                        "source": "江西新闻网"
                    },
                ]
            },
            {
                "name": "上海（长三角）国创中心资讯",
                "items": [
                    {
                        "title": "长三角市场监管一体化发布助力国创中心建设19条举措",
                        "date": "2026.7.3",
                        "summary": "三省一市联合发布《若干举措》，涵盖科技人才「互聘共享」和资质跨区域互认、元宇宙/AI/6G等前沿领域快速获权服务等七大板块。长三角经营主体达3828万户，R&D经费占全国约30.55%。",
                        "insight": "「人才互聘共享」和「资质跨区域互认」对常州是直接利好。建议市科技局牵头，依托中以常州创新园、科教城等名园名院，主动对接长三角人才共享平台，柔性引进沪宁领军人才，降低人才流动制度壁垒。",
                        "source": "澎湃新闻"
                    },
                    {
                        "title": "学术论坛热议国际科创中心「扩围提质」：刘庆提「没有围墙的创新中心」",
                        "date": "2026.7.2",
                        "summary": "第23届上海市社科界学术年会论坛在同济大学举行。长三角国创中心主任刘庆提出打造「没有围墙的创新中心」。上海全球城市研究院院长阮青提出「前研后转」分工模式——上海做前沿研发，周边城市做产业转化。",
                        "insight": "「前研后转」分工模式对常州定位意义重大。应围绕此定位建强中以常州创新园、科教城等转化载体，梳理与上海高校院所的合作项目，形成「沪研常转」标杆案例。",
                        "source": "网易新闻"
                    },
                ]
            },
            {
                "name": "科创政策速览",
                "items": [
                    {
                        "title": "武汉光谷发布智能体经济「路线图」：三年投10亿、年内万P算力",
                        "date": "2026.7.3",
                        "summary": "光谷未来三年投入超10亿元，培育100家智能体创新企业。已建成超5000P智能算力，年内提升至10000P，企业租用算力享最高50%补贴。设立智能体场景发布厅，标杆场景最高300万元支持。",
                        "insight": "光谷在算力基建的大手笔投入对常州AIDC形成竞争压力。常州应发挥新能源产业场景优势，聚焦「AI+新能源」差异化赛道——如智能电网调度智能体、电池健康管理智能体等垂直场景，与光谷形成错位竞争。",
                        "source": "财联社"
                    },
                    {
                        "title": "郑州入局万亿具身智能赛道，与宇树科技共建实训创新中心",
                        "date": "2026.7.3",
                        "summary": "OpenLET郑州工作组揭牌，国内首个国家级具身智能开源数据集社区落地郑州。与宇树科技共建「具身智能实训创新中心」和「具身智能产业学院」。郑州高新区已集聚400余家机器人产业链企业。",
                        "insight": "常州在具身智能领域应加快布局，借助理想、比亚迪等名企在智能制造端的场景优势，联合共建具身智能实训基地。同时可利用常州科教城职教资源，打造长三角具身智能技能人才培训高地。",
                        "source": "网易新闻"
                    },
                ]
            },
            {
                "name": "改革举措",
                "items": [
                    {
                        "title": "海南拟设1亿元「先投后股」资金池支持科技成果转化",
                        "date": "2026.7.3",
                        "summary": "海南发布2026年科技体制改革计划，全省「先投后股」资金池达1亿元，累计支持不少于20个项目。同步推动省级财政科技专项体系优化改革。",
                        "insight": "「先投后股」是破解成果转化「最初一公里」资金困境的有效模式。常州可在「三名联动」框架下试点——从产业基金中切出专项，以「先投后股」方式支持高校院所成果在常转化，实现财政资金循环使用和增值退出。",
                        "source": "海南中新网"
                    },
                    {
                        "title": "上海科学技术奖励大会：深化科技评价改革，推进「三评联动」",
                        "date": "2026.7.2",
                        "summary": "上海市委书记陈吉宁为褚君浩、陈赛娟颁发科技功臣奖。核心部署：加强科技计划全过程管理、深化项目经理团队制度建设、推进项目评审/人才评价/机构评估「三评联动」改革、为科研人员赋权增能减负松绑。",
                        "insight": "常州可率先在市级科技计划中试行「分类评价」制度——基础研究看长周期、应用研究看转化效果、企业项目看市场效益，避免「一刀切」扼杀创新活力。",
                        "source": "上海市科委"
                    },
                ]
            },
        ],
        "trend_analysis": "本周呈现三大趋势：一是各省市科技委角色加速从协调议事向产业战略策源转型，广东率先以科技委名义发布产业行动计划；二是万亿城市在AI算力、具身智能等赛道投入力度空前，武汉光谷10亿级别投入和万P算力目标值得常州警惕；三是「先投后股」等成果转化金融工具在多省市落地，常州应抓住政策窗口期推进试点。"
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="生成《创新常州·对标快讯》美化版 PDF")
    parser.add_argument("--type", choices=["weekly", "monthly", "daily"], default="weekly")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    api_key = None
    if not args.sample:
        import os as _os
        _sys = __import__("sys")
        _sys.path.insert(0, str(PROJECT_DIR))
        from run_daily import load_config
        cfg = load_config()
        api_key = _os.environ.get("DEEPSEEK_API_KEY", "") or cfg.get("deepseek_api_key", "")
        if not api_key:
            print("[提示] 未配置 API Key，使用示例数据。")
            args.sample = True

    generate_weekly_pdf(api_key=api_key if not args.sample else None,
                        output_path=args.output,
                        sample=args.sample)
