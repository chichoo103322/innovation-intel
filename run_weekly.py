#!/usr/bin/env python3
"""
《创新常州·对标快讯》周报自动生成（每周五执行）
汇总本周日报 → Claude 趋势分析 → 生成 Word → 分发
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).parent
SCRIPT_DIR = PROJECT_DIR / "scripts"
DAILY_DIR = PROJECT_DIR / "daily"

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


def find_this_week_dailies():
    """找到本周一到今天的日报文件"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    files = []
    for i in range(7):
        d = monday + timedelta(days=i)
        if d > today:
            break
        fn = DAILY_DIR / f'创新常州·对标快讯_{d.strftime("%Y-%m-%d")}.docx'
        if fn.exists():
            files.append((d, fn))
    return files


def extract_docx_text(filepath):
    """提取 docx 文本"""
    from zipfile import ZipFile
    from xml.etree import ElementTree
    try:
        with ZipFile(filepath, 'r') as z:
            xml_content = z.read('word/document.xml')
            tree = ElementTree.fromstring(xml_content)
            paragraphs = []
            for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                texts = []
                for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if t.text:
                        texts.append(t.text)
                if texts:
                    paragraphs.append(''.join(texts))
            return '\n'.join(paragraphs)
    except Exception as e:
        return f"[读取失败: {e}]"


def call_deepseek_for_weekly(api_key, model, daily_texts, today_cn):
    """调用 DeepSeek 进行周度趋势分析"""
    from openai import OpenAI

    system = """你是资深科技创新情报分析师，服务于常州市科技创新决策。请根据本周日报内容，生成一份周报。

═══════════════════════════════════════════════════════════
内容要求
═══════════════════════════════════════════════════════════

1. **本周综述（200-300字）**：归纳本周核心主线和关键信号，必须结合常州五大产业方向（AIDC/具身智能/未来存储/未来能源/液冷）和周边万亿城市（苏州/无锡/南京/南通）竞争格局进行分析。

2. **每周维度分述**：各维度本周要点总结，highlights 每条50-80字，必须包含具体数据和日期。

3. **趋势研判（3-4条）**：基于本周信息发现的跨板块新趋势，每条趋势分析必须：
   - 点明对常州五大产业方向的影响
   - 对比周边万亿城市的同类动向
   - 指出常州的机遇窗口或竞争威胁

4. **对常州的建议（3-4条）**：每条建议必须：
   - 关联常州具体产业基础（新能源/高端装备/新能源汽车等）
   - 扣合三名工程/双高协同/中以常州创新园/科教城等政策抓手
   - 从"算力+硬件+场景+生态"全链条视角分析
   - 给出可操作的方向+可能的牵头部门
   - 严禁出现"值得借鉴""值得关注"等空话套话

输出纯 JSON（不要其他文字）：
{
  "weekly_overview": "200-300字综述。结合五大产业和周边竞争格局，点明机遇窗口和竞争威胁。",
  "trends": ["趋势1（含对常州影响分析）", "趋势2", "趋势3"],
  "suggestions": ["建议1（具体可操作+责任部门+政策抓手）", "建议2", "建议3"],
  "sections": [
    {"name": "各地科技委动态", "overview": "80-120字本维度本周要点总结", "highlights": ["要点1（含具体数据和日期）", "要点2"]},
    {"name": "上海（长三角）国创中心资讯", "overview": "...", "highlights": ["要点1"]},
    {"name": "科创政策速览", "overview": "...", "highlights": ["要点1"]},
    {"name": "改革举措", "overview": "...", "highlights": ["要点1"]}
  ]
}"""

    user = f"""今天是{today_cn}。以下是本周（周一至今天）所有日报的汇总内容，请进行趋势分析并生成周报。

═══════════════════════════════════════════════════════════
分析要求
═══════════════════════════════════════════════════════════
1. 趋势研判必须跨板块分析，不能只是各维度的简单堆砌
2. 建议必须有常州针对性——要能落实到常州的具体园区（中以园/科教城/高新区）、具体企业（理想/比亚迪/中创新航等）、具体政策（三名工程/双高协同）
3. 必须覆盖五大产业方向（AIDC/具身智能/未来存储/未来能源/液冷）中本周出现的关键信号
4. 必须对比分析苏州/无锡/南京/南通等周边城市的本周动向
5. 严格核查日报中的日期、金额、机构名称——如发现"科委"（应为"科技委"）、日期错误等问题必须先修正再使用

{daily_texts}

请输出 JSON（不要其他文字）："""

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=8000,
        temperature=0.3,
    )

    text = response.choices[0].message.content or ""
    json_str = text.strip()
    if json_str.startswith("```"):
        lines = [l for l in json_str.split("\n") if not l.startswith("```")]
        json_str = "\n".join(lines).strip()
    return json.loads(json_str)


def generate_weekly_docx(data, output_path):
    """生成周报 Word 文档"""
    from generate_docx import create_doc, add_header_block, add_section_title, set_run_font, BODY_SIZE, INDENT_2CHAR

    today = datetime.now()
    date_cn = today.strftime('%Y年%m月%d日')
    doc = create_doc()
    add_header_block(doc, '创新常州·对标快讯（周报）', 0, 0, date_cn)

    # 综述
    add_section_title(doc, '【本周综述】')
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = INDENT_2CHAR
    run = p.add_run(data.get("weekly_overview", ""))
    set_run_font(run, '仿宋_GB2312')

    # 各板块
    for sec in data.get("sections", []):
        add_section_title(doc, f'【{sec["name"]} · 本周要点】')
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = INDENT_2CHAR
        run = p.add_run(sec.get("overview", ""))
        set_run_font(run, '仿宋_GB2312')
        for hl in sec.get("highlights", []):
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = INDENT_2CHAR
            run = p.add_run(f'• {hl}')
            set_run_font(run, '仿宋_GB2312')

    # 趋势研判
    add_section_title(doc, '【本周趋势研判】')
    for t in data.get("trends", []):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = INDENT_2CHAR
        run = p.add_run(f'• {t}')
        set_run_font(run, '仿宋_GB2312')

    # 建议
    add_section_title(doc, '【对常州建议】')
    for s in data.get("suggestions", []):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = INDENT_2CHAR
        run = p.add_run(f'• {s}')
        set_run_font(run, '仿宋_GB2312')

    doc.save(str(output_path))
    print(f'[完成] 周报已生成: {output_path}')


def main():
    print("=" * 60)
    print("  创新常州·对标快讯 — 周报自动生成")
    print("=" * 60)

    # --sample 模式：使用示例数据生成，不调 API
    if "--sample" in sys.argv:
        sample_data = {
            "weekly_overview": "本周核心主线为长三角国际科技创新中心建设加速推进，上海联合苏浙皖三省发布协同创新协议，沿线城市争相布局高能级创新平台。北京、深圳等先行城市在人工智能立法和未来产业培育上动作频频，常州被明确列入高能级创新型城市建设对象，迎来政策窗口期。",
            "trends": [
                "长三角科创协同从「框架协议」进入「项目落地」阶段，各地密集发布建设方案和行动计划",
                "AI+产业融合加速，多个万亿城市将智能体、具身智能列入重点赛道，竞争日趋激烈",
                "科技成果转化「先投后股」模式被多地采纳，财政资金支持方式正在发生结构性转变"
            ],
            "suggestions": [
                "建议加快制定常州版高能级创新型城市建设行动方案，明确在沿沪宁产业创新带中的差异化功能定位",
                "依托新能源产业优势，率先布局「AI+新能源」特色场景，抢占智能体经济赛道先机",
                "在中以常州创新园试点「先投后股」成果转化机制，形成可复制推广的常州经验"
            ],
            "sections": [
                {"name": "各地科技委动态", "overview": "本周多个省级科技委密集召开会议，围绕「十五五」科技创新规划、未来产业布局展开部署。江苏省委科技委全体会议明确常州为高能级创新型城市建设对象，广东省发布全国首个脑机接口产业行动计划。", "highlights": ["江苏省委科技委全会在南京召开，常州被列入高能级创新型城市建设名单", "广东省科技委发布脑机接口产业协同发展行动计划，目标2030年核心产业百亿级", "江西省部署「2030启航计划」，推动AI重构科研范式"]},
                {"name": "上海（长三角）国创中心资讯", "overview": "长三角市场监管一体化19条举措发布，涉及人才互聘、资质互认等实质性突破。「前研后转」分工模式被热议——上海做前沿研发、周边城市做产业转化。", "highlights": ["三省一市联合发布19条举措，涵盖人才互聘共享、资质跨区域互认", "刘庆提出「没有围墙的创新中心」，推动跨域规则共识", "阮青提出「前研后转」分工模式，常州定位为产业转化和中试放大"]},
                {"name": "科创政策速览", "overview": "多个万亿城市加码科技创新投入。武汉光谷三年投入超10亿元发展智能体经济，南京推进AI立法并设立「算力券」补贴机制，郑州入局万亿具身智能赛道。", "highlights": ["武汉光谷三年投入超10亿培育智能体创新企业，年内算力达万P", "南京审议AI产业发展条例，大模型备案奖励20万元，AI项目最高补助200万", "郑州与宇树科技共建具身智能实训创新中心，400余家机器人企业集聚高新区"]},
                {"name": "改革举措", "overview": "科技成果转化成为本周改革焦点。海南设1亿元「先投后股」资金池，郑东新区构建全链条资金支持体系，上海深化「三评联动」科技评价改革。", "highlights": ["海南拟设1亿元「先投后股」资金池，已支持20余个项目", "郑东新区形成从概念验证到产业引导基金的全周期资金支持链条", "上海推进项目评审、人才评价、机构评估「三评联动」，为科研人员减负松绑"]}
            ]
        }
        date_fn = datetime.now().strftime('%Y%m%d')
        output = PROJECT_DIR / 'weekly' / f'创新常州·对标快讯_周报_{date_fn}.docx'
        output.parent.mkdir(parents=True, exist_ok=True)
        generate_weekly_docx(sample_data, output)
        from distribute import save_desktop
        save_desktop(str(output), "weekly")
        return

    api_key = get_api_key()
    if not api_key:
        print("[错误] 未找到 DEEPSEEK_API_KEY。请设置环境变量或在 settings.yaml 中配置")
        sys.exit(1)

    today = datetime.now()
    today_cn = today.strftime("%Y年%m月%d日")

    # 检查是否是周五
    if today.weekday() != 4:
        print(f"[提示] 今天是周{today.weekday()+1}，非周五。周报仅在周五生成。")
        print("如需强制生成，请使用 --force 参数")
        # 检查是否有 --force
        if "--force" not in sys.argv:
            return

    # 找本周日报
    dailies = find_this_week_dailies()
    if not dailies:
        print("[错误] 本周尚无日报，无法生成周报")
        sys.exit(1)

    print(f"本周已有 {len(dailies)} 期日报:")
    for d, f in dailies:
        print(f"  {d.strftime('%m/%d')} — {f.name}")

    # 提取日报文本
    all_texts = []
    for d, f in dailies:
        text = extract_docx_text(str(f))
        all_texts.append(f"=== {d.strftime('%Y年%m月%d日')} ===\n{text}")
    combined = "\n\n".join(all_texts)

    # Claude 分析
    print("\n[分析] 正在通过 DeepSeek 进行周度趋势分析...")
    data = call_deepseek_for_weekly(api_key, get_model(), combined, today_cn)

    # 生成 Word
    date_fn = today.strftime('%Y%m%d')
    output = PROJECT_DIR / 'weekly' / f'创新常州·对标快讯_周报_{date_fn}.docx'
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_weekly_docx(data, output)

    # 分发
    from distribute import save_desktop
    print("\n=== 分发周报 ===")
    save_desktop(str(output), "weekly")
    print("=== 完成 ===")


if __name__ == "__main__":
    main()
