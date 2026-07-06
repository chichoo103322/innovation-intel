#!/usr/bin/env python3
"""Update weekly JSON: move 科技保险 to 科创政策速览, add user's text."""
import json
from pathlib import Path

json_path = Path("/Users/jzxzhou/innovation-intel/weekly/report_weekly_20260706.json")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# ---- 1. Add the user's item to 科创政策速览 ----
new_policy_item = {
    "title": "广东省印发《广东省科技保险后奖补管理办法（试行）》",
    "date": "近日",
    "summary": "广东省科技厅等四部门联合印发《广东省科技保险后奖补管理办法（试行）》，对科技企业购买研发中断险、科技成果转化险等给予事后奖补，降低企业创新风险，引导保险机构开发更多定制化科技保险产品，促进科技、产业、金融良性循环。",
    "insight": [
        "建议常州由市科技局与金融监管局联合出台科技保险奖补细则，重点覆盖新能源与智能装备领域的中试和首台套应用风险。可联合天合光能、恒立液压等链主企业，与太平洋产险合作开发“钙钛矿组件户外实证险”“协作机器人应用责任险”，利用奖补资金降低保费门槛，扣合龙城金谷科技金融定位。",
        "相比广东的广谱性补贴，常州应聚焦未来能源、具身智能等主导赛道差异化发力。苏州侧重知识产权质押融资、南京侧重科技信贷——常州可将保险工具嵌入常州高新区、武进高新区的新技术应用保险示范区试点，形成“保险支持中试—中试加速产业化—产业反哺保险”的闭环，在29座万亿城市中树立科技保险服务实体制造的标杆。",
        "科技保险是未来3-5年科技金融的核心增长极。随着硬科技投资风险加大、中试环节成为成果转化最大断点，保险资金作为长期资本进入科技创新领域是必然趋势。常州应提前布局科技保险精算基础设施，在科教城设立科技风险评估实验室，联合高校开发技术成熟度评估模型，为钙钛矿、液冷、氢能等五大产业方向的保险产品定价提供数据支撑，抢占科技保险蓝海。"
    ],
    "source": "广东省科技厅",
    "url": "http://gdstc.gd.gov.cn/zwgk_n/tzgg/content/post_4917547.html"
}

for sec in data["sections"]:
    if "科创政策" in sec["name"]:
        sec["items"].insert(0, new_policy_item)
        sec["overview"] = "本周万亿城市及省级科技创新政策聚焦具身智能和科技金融两大主题。广东率先出台全国首个省级科技保险后奖补管理办法，为科技保险提供制度范本；深圳正式印发具身智能机器人产业发展行动计划，目标2028年产业规模突破1000亿元；苏州审议通过科创与产业融合三年行动方案，锁定4个万亿级产业集群。三项政策均体现“硬目标+强投入+全链条”的特征。"
        sec["highlights"].insert(0, "广东省科技厅等四部门联合印发《广东省科技保险后奖补管理办法（试行）》，系全国首个省级科技保险专项奖补政策，覆盖研发中断险、成果转化险等")
        break

# ---- 2. Remove from 改革举措 ----
for sec in data["sections"]:
    if "改革举措" in sec["name"]:
        sec["items"] = [it for it in sec["items"] if "科技保险" not in it.get("title", "")]
        sec["overview"] = "本周科技成果转化和科技金融改革多点突破。“先投后股”模式在全国至少10城推开，海南1亿元资金池、成都单个最高2000万元、洛阳转股让利50%。华中科大科技金融研究院揭牌，全国首个科技金融研究联盟在武汉成立。江苏科技成果拍卖季和挑战季加力，“科技专家进企业”走进常州。"
        sec["highlights"] = [h for h in sec["highlights"] if "科技保险" not in h]
        break

# ---- 3. Update weekly_overview ----
data["weekly_overview"] = "本周（6.30—7.6）科技创新领域聚焦三大主线：一是长三角国际科创中心建设从战略框架进入政策落地阶段，三省一市联合发布19条举措，江苏省委科技委全体会议明确常州为高能级创新型城市建设对象；二是具身智能和科技保险成为万亿城市政策竞赛新焦点，深圳发布千亿级产业行动计划，广东率先出台科技保险后奖补办法；三是科技金融制度创新加速——华中科大成立全国首个科技金融研究联盟，“先投后股”改革在全国至少10城铺开。对常州而言，本周被明确列入高能级创新型城市建设名单是最大政策利好，深圳具身智能千亿目标和广东科技保险制度创新提供了对标参照，常州应聚焦“新能源+AI”差异化赛道，尽快出台配套行动方案。"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

total = sum(len(s.get("items", [])) for s in data["sections"])
print(f"[完成] JSON 已更新: {total} 条信息")
for s in data["sections"]:
    print(f"  {s['name']}: {len(s['items'])} 条")
    for it in s["items"]:
        n = len(it.get("insight", []))
        has_book = "《" in it.get("title", "")
        ok = f"  ✓" if n == 3 else f"  ⚠ insight={n}"
        if "科创政策" in s["name"] and not has_book:
            ok += " ⚠缺《》"
        print(f"    {ok} {it['title'][:60]}")
