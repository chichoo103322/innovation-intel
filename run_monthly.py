#!/usr/bin/env python3
"""
《创新常州·对标快讯》月报自动生成（每月最后一天执行）
汇总本月周报 → Claude 战略分析 → 生成 Word → 分发
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).parent
SCRIPT_DIR = PROJECT_DIR / "scripts"
WEEKLY_DIR = PROJECT_DIR / "weekly"

sys.path.insert(0, str(SCRIPT_DIR))


def get_api_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    from run_daily import load_config, get_api_key as gk
    return gk(load_config())


def get_model():
    from run_daily import load_config
    return load_config().get("deepseek_model", "deepseek-chat")


def is_last_day_of_month():
    """判断今天是否是本月最后一天"""
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.day == 1


def find_this_month_weeklies():
    """找到本月周报文件"""
    today = datetime.now()
    files = []
    for item in WEEKLY_DIR.glob("*.docx"):
        mtime = datetime.fromtimestamp(item.stat().st_mtime)
        if mtime.year == today.year and mtime.month == today.month:
            files.append((mtime, item))
    files.sort(key=lambda x: x[0])
    return files


def extract_docx_text(filepath):
    from zipfile import ZipFile
    from xml.etree import ElementTree
    try:
        with ZipFile(filepath, 'r') as z:
            xml_content = z.read('word/document.xml')
            tree = ElementTree.fromstring(xml_content)
            paragraphs = []
            for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                texts = [t.text for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text]
                if texts:
                    paragraphs.append(''.join(texts))
            return '\n'.join(paragraphs)
    except Exception as e:
        return f"[读取失败: {e}]"


def call_deepseek_for_monthly(api_key, model, weekly_texts, month_cn):
    """DeepSeek 月度战略分析"""
    from openai import OpenAI

    system = """你是资深科技创新情报分析师和战略顾问，服务于常州市科技创新决策。
请根据本月所有周报内容，生成月度战略报告。你需要：

1. 月度综述（300-500字）：本月总体态势、核心主题演进
2. 四个维度的月度全景分析（每维度2-3个关键要点）
3. 重大信号识别（2-3条）：可能影响常州科技创新的重要信号
4. 战略建议（3-5条）：面向未来的行动建议，结合常州实际

输出纯 JSON：
{
  "monthly_overview": "月度综述...",
  "major_signals": ["信号1", "信号2"],
  "strategic_advice": ["建议1", "建议2", "建议3"],
  "sections": [
    {"name": "各地科技委动态", "analysis": "...", "key_points": ["要点1"]},
    {"name": "上海（长三角）国创中心资讯", "analysis": "...", "key_points": ["要点1"]},
    {"name": "科创政策速览", "analysis": "...", "key_points": ["要点1"]},
    {"name": "改革举措", "analysis": "...", "key_points": ["要点1"]}
  ]
}"""

    user = f"""本月是{month_cn}。以下是本月所有周报内容，请进行战略分析并生成月报。

{weekly_texts}

请输出 JSON（不要其他文字）："""

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=12000,
        temperature=0.3,
    )

    text = response.choices[0].message.content or ""
    json_str = text.strip()
    if json_str.startswith("```"):
        lines = [l for l in json_str.split("\n") if not l.startswith("```")]
        json_str = "\n".join(lines).strip()
    return json.loads(json_str)


def generate_monthly_docx(data, output_path):
    from generate_docx import create_doc, add_header_block, add_section_title, set_run_font, BODY_SIZE, INDENT_2CHAR

    today = datetime.now()
    date_cn = today.strftime('%Y年%m月%d日')
    doc = create_doc()
    add_header_block(doc, '创新常州·对标快讯（月报）', 0, 0, date_cn)

    add_section_title(doc, '【月度综述】')
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = INDENT_2CHAR
    run = p.add_run(data.get("monthly_overview", ""))
    set_run_font(run, '仿宋_GB2312')

    for sec in data.get("sections", []):
        add_section_title(doc, f'【{sec["name"]} · 月度全景】')
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = INDENT_2CHAR
        run = p.add_run(sec.get("analysis", ""))
        set_run_font(run, '仿宋_GB2312')
        for kp in sec.get("key_points", []):
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = INDENT_2CHAR
            run = p.add_run(f'• {kp}')
            set_run_font(run, '仿宋_GB2312')

    add_section_title(doc, '【重大信号识别】')
    for sig in data.get("major_signals", []):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = INDENT_2CHAR
        run = p.add_run(f'• {sig}')
        set_run_font(run, '仿宋_GB2312', bold=True)

    add_section_title(doc, '【战略建议】')
    for i, adv in enumerate(data.get("strategic_advice", []), 1):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = INDENT_2CHAR
        run = p.add_run(f'{i}. {adv}')
        set_run_font(run, '仿宋_GB2312')

    doc.save(str(output_path))
    print(f'[完成] 月报已生成: {output_path}')


def main():
    print("=" * 60)
    print("  创新常州·对标快讯 — 月报自动生成")
    print("=" * 60)

    # --sample 模式
    if "--sample" in sys.argv:
        sample = {
            "monthly_overview": "6月份，长三角国际科技创新中心建设进入全面加速期。上海联合苏浙皖三省发布协同创新协议，沿线城市密集出台科技创新政策。常州被明确列入高能级创新型城市建设对象，迎来重大政策机遇期。总体来看，科技创新已从单点突破转向体系化、协同化发展新阶段，长三角各城市在竞合中加速形成差异化定位。",
            "major_signals": [
                "长三角科创协同从「框架协议」进入「项目落地」阶段，沿线城市竞争加剧，常州需尽快锁定差异化定位",
                "AI+产业融合成为万亿城市标配，智能体、具身智能赛道进入爆发前夜，常州新能源场景优势突出",
                "科技成果转化「先投后股」模式被中央和地方多层面采纳，财政科技投入方式面临结构性转变"
            ],
            "strategic_advice": [
                "尽快制定常州版高能级创新型城市建设三年行动方案，明确重点突破方向和阶段性目标",
                "依托新能源产业优势，打造「AI+新能源」全国标杆场景，与武汉光谷、郑州形成差异化竞争",
                "在中以常州创新园率先试点「先投后股+概念验证」双轨机制，形成可推广的常州模式",
                "主动对接长三角人才共享平台，建立「沪研常转」常态化合作机制",
                "关注南京AI立法进展，提前储备政策工具，为常州未来AI产业规范化发展打好制度基础"
            ],
            "sections": [
                {"name": "各地科技委动态", "analysis": "6月份，省级科技委作为区域科技创新最高议事协调机构的角色进一步凸显。江苏、广东、江西等省科技委密集召开全体会议，从单纯协调机构向产业战略策源机构转型趋势明显。", "key_points": ["省级科技委角色升级，从协调机构向产业战略策源机构转型", "多个省份将「十五五」科技创新规划编制提上日程", "常州被列入高能级创新型城市建设对象，战略地位提升"]},
                {"name": "上海（长三角）国创中心资讯", "analysis": "长三角国际科技创新中心建设本月实现多项制度性突破。19条市场监管一体化举措标志着从基础设施互联互通向制度规则深度对接升级。「前研后转」分工模式得到广泛认可。", "key_points": ["19条举措实现人才互聘、资质互认等制度性突破", "「前研后转」分工模式明确，常州定位为产业转化和中试放大", "长三角R&D经费占全国约30.55%，创新密度持续领先"]},
                {"name": "科创政策速览", "analysis": "万亿城市在科技创新领域的竞争白热化。武汉、南京、郑州等城市在智能体、AI立法、具身智能等前沿赛道集中发力，政策工具从传统财税补贴升级为算力券、场景开放等新型支撑手段。", "key_points": ["多个万亿城市布局智能体、具身智能等同一赛道，同质化竞争风险显现", "政策工具从财税补贴升级为算力券、场景开放、立法保障等新形态", "龙头企业共建产业学院模式值得常州借鉴"]},
                {"name": "改革举措", "analysis": "本月科技体制改革聚焦科技成果转化全链条。「先投后股」模式被海南、郑东新区等多地采纳，标志财政科技投入从「无偿补助」向「循环增值」转型。科技评价「三评联动」改革在上海深化推进。", "key_points": ["「先投后股」模式在多个省市落地，财政科技资金循环使用机制日趋成熟", "全链条资金支持体系（概念验证-研发基金-种子-天使-产业基金）成为标配", "科技评价改革从「破四唯」进入「立新标」阶段，分类评价制度逐步建立"]}
            ]
        }
        output = PROJECT_DIR / 'monthly' / '创新常州·对标快讯_月报_202606.docx'
        output.parent.mkdir(parents=True, exist_ok=True)
        generate_monthly_docx(sample, output)
        from distribute import save_desktop
        save_desktop(str(output), "monthly")
        return

    if not is_last_day_of_month() and "--force" not in sys.argv:
        print("[提示] 今天不是本月最后一天。月报仅在月末生成。")
        print("如需强制生成，请使用 --force")
        return

    api_key = get_api_key()
    if not api_key:
        print("[错误] 未找到 DEEPSEEK_API_KEY")
        sys.exit(1)

    today = datetime.now()
    month_cn = today.strftime('%Y年%m月')

    weeklies = find_this_month_weeklies()
    if not weeklies:
        print("[错误] 本月尚无周报，无法生成月报")
        sys.exit(1)

    print(f"本月已有 {len(weeklies)} 期周报:")
    for d, f in weeklies:
        print(f"  {d.strftime('%m/%d')} — {f.name}")

    all_texts = []
    for d, f in weeklies:
        text = extract_docx_text(str(f))
        all_texts.append(f"=== {d.strftime('%Y年%m月%d日')} ===\n{text}")
    combined = "\n\n".join(all_texts)

    print("\n[分析] 正在通过 DeepSeek 进行月度战略分析...")
    data = call_deepseek_for_monthly(api_key, get_model(), combined, month_cn)

    output = PROJECT_DIR / 'monthly' / f'创新常州·对标快讯_月报_{today.strftime("%Y%m")}.docx'
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_monthly_docx(data, output)

    from distribute import save_desktop
    print("\n=== 分发月报 ===")
    save_desktop(str(output), "monthly")
    print("=== 完成 ===")


if __name__ == "__main__":
    main()
