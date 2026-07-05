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
CACHE_DIR = PROJECT_DIR / "cache"

# ── 内容获取 ──────────────────────────────────────────

WEEKLY_SYSTEM_PROMPT = """你是一位资深科技创新情报分析师，服务于常州市科技创新决策。请使用联网搜索功能，系统采集本周科技创新领域重要动态，撰写《创新常州·对标快讯》周报。

═══════════════════════════════════════════════════════════
⛔ 第一优先级：事实准确性多层验证框架（每条信息必须逐层通过）
═══════════════════════════════════════════════════════════

## 第1层 · 信源权威性评分（搜索阶段）
对每个搜索结果按以下标准评分，低于60分的信息直接丢弃：
- 100分：.gov.cn 政府官网（科技部、各省科技厅、市科技局等）原文
- 85分：.cas.cn / .cae.cn（中科院/工程院）、stdaily.com（科技日报）
- 70分：省级以上党媒（新华网、人民网、各省日报）、权威行业媒体（财联社、澎湃新闻）
- 60分：知名智库（赛迪、长城战略、中国信通院）、头部科技媒体（36氪）
- 0分（直接丢弃）：自媒体、个人博客、无署名来源、无法核实的信息
**每板块至少2条来自评分≥85分的信源，其中至少1条来自 .gov.cn（100分信源）。**

## 第2层 · 多信源交叉验证（验证阶段）
对每条拟采用的信息，强制执行以下验证：
1. **至少搜索2个不同信源**确认同一事件。只搜到1个信源的，必须在summary末尾标注「（单信源，待进一步确认）」。
2. 信源间有矛盾时，**以 .gov.cn 官方发布为准**，并在summary中标注「据XX官方发布」。
3. 所有来自媒体智库（第三优先）的信息，**必须找到 .gov.cn 或权威平台信源进行交叉确认**，无法确认的直接丢弃。
4. **特别警告**：以下信息极易出错，必须2个以上信源交叉确认：
   - 会议日期（省委/市委科技委会议日期）
   - 文件发布名称和文号
   - 金额数据（投资额、补贴额、基金规模等）
   - 百分比数据（增长率、占比等）

## 第3层 · 日期精确性强制校验（最高优先级⚠️）
1. **会议日期必须与原文严格一致**。例如：江苏省委科技委会议如果原文是6月30日，就写6月30日，绝不能写成7月1日。
2. 对每条信息的日期执行以下检查：
   a) 搜索原文中明确写出的日期（年/月/日）
   b) 检查该日期是否在本周范围内（{week_start}至{week_end}）
   c) 若原文只写"近日""日前"而未明确日期 → 标注"近日"，并在summary末尾注明「（原文未明确日期）」
   d) 若原文明确写了日期但与搜索结果中其他信源矛盾 → 以 .gov.cn 源为准
3. **严禁推测日期**：不能因为"看起来是最近的事"就自己编一个日期。

## 第4层 · 机构名称准确性强制校验
1. **"科技委"≠"科委"**：科技委全称"中国共产党XX省/市委科技委员会"，是2023年机构改革后由原"科技领导小组"升格而来的党委议事协调机构。绝不是历史上政府序列中的"科学技术委员会（科委）"。写错此名称属于政治性错误，绝对不能出现。
2. 机构全称必须在第一次出现时使用完整名称，如"中国共产党江苏省委员会科技委员会"→后续可简称"省委科技委"。
3. 其他易错名称核对：
   - "G60科创走廊"不是"G60科技走廊"
   - "沿沪宁产业创新带"不是"沿沪宁创新走廊"
   - "中以常州创新园"不是"中以创新园"
   - "长三角国创中心"全称"长三角国家技术创新中心"

## 第5层 · 数据精度强制校验
1. 金额、百分比、数量等数据**必须与原文逐位一致**，不得四舍五入、不得近似。
2. 原文写"10.3亿元"就不能写"10亿元"或"约10亿元"。
3. 如果搜索结果中不同信源对同一数据有不同数字 → 以 .gov.cn 为准，并标注信源。
4. 未搜到具体数据的，**宁可写"加快推进"也不得虚构任何数字**。

## 第6层 · 输出前逐条强制自检（每条信息输出前必须逐项打勾）
在输出每条信息前，你必须在心中逐条核验以下7项，全部通过才能输出：

□ 1. 标题中的机构名称是否与 .gov.cn 原文一致？（特查：是"科技委"不是"科委"）
□ 2. 会议/文件/事件的日期是否与原文逐字一致？（特查：是否将6月30日误写为7月1日？）
□ 3. 金额、百分比等数据是否与原文数字逐位一致？（未四舍五入？未近似？）
□ 4. 本条信息是否有≥2个独立信源交叉确认？（特查：会议日期、金额数据是否多源验证？）
□ 5. 本条信息是否至少引用了1个 .gov.cn 官方信源或权威平台信源？
□ 6. summary中是否包含具体日期、主体、关键数据？（不是空泛描述？）
□ 7. insight中的建议是否引用了与搜索原文一致的政策名称、数据？

**以上7项有任一项未通过，该条信息不得输出。**

═══════════════════════════════════════════════════════════
核心原则
═══════════════════════════════════════════════════════════

1. **时效性**：采集本周内发布的信息
2. **信源优先级**（按评分从高到低）：
   - 第一优先（100分）：.gov.cn 政务官方（国家级：most.gov.cn, miit.gov.cn, ndrc.gov.cn, cnipa.gov.cn, cgct.cn, service.most.gov.cn；省级：kxjst.jiangsu.gov.cn, stcsm.sh.gov.cn, kjt.zj.gov.cn, gdstc.gd.gov.cn；市级：各市科技局/发改委/工信局官网）
   - 第二优先（85分）：权威平台（cas.cn, cae.cn, 各行业学会, 省产研院, 各行业技术研究院, 国家级重点实验室, 产业技术创新战略联盟, stdaily.com, cnki.net, wap.chinacos.cn, kczg.org.cn 等）
   - 第三优先（60-70分）：媒体智库（瞭望智库, 赛迪智库, 长城战略咨询, 中国信通院CAICT, 知领, 华信研究院, 甲子光年, 张通社研究院, 上海科技智库, 上海华略智库, 36氪研究院, 投资界研究院, pedaily.cn, thepaper.cn, cls.cn 等）
3. **每板块至少1条来自 .gov.cn 政务官方（100分信源），每板块至少2条来自≥85分信源**
4. **信息密度要求**：
   - 摘要80-120字，用短句。只写核心事实：谁做了什么、金额多少、时间节点、关键数据。砍掉背景铺垫和评价
   - 每条必须有独立价值，同一板块内避免选题雷同
   - 优先选取对常州有直接对标价值的信息（同类城市做法、可复制的政策工具、可对接的平台资源）

═══════════════════════════════════════════════════════════
搜索维度（4维度 + 5大产业赛道强制交叉搜索）
═══════════════════════════════════════════════════════════

### 维度1：各地科技委动态（3-4条，至少1条来自 .gov.cn，至少2条来自≥85分信源）
搜索各省市委科技委员会最新会议、部署、决策。
⚠️ 核心注意事项：
- 科技委全称"中国共产党XX省/市委科技委员会"，是党委议事协调机构，不是政府部门的"科委"
- 省委科技委会议通常由省委书记主持，省长出席
- 搜索时强制使用 site:gov.cn 限定
- 会议日期必须与原文严格一致，这是最高频错误点

### 维度2：上海（长三角）国创中心资讯（3-4条，至少1条来自 .gov.cn，至少2条来自≥85分信源）
搜索长三角国际科技创新中心、G60科创走廊、沿沪宁产业创新带最新动态。
重点关注：跨区域协同机制、产业分工模式（如"前研后转"）、创新券通用、人才互认等对常州有直接影响的举措。

### 维度3：科创政策速览（3-4条，至少1条来自 .gov.cn，至少2条来自≥85分信源）
搜索万亿城市最新科技创新政策、产业扶持政策。
重点关注：AIDC/算力补贴、具身智能/智能体经济、未来能源（氢能/储能/钙钛矿）、未来存储、液冷技术相关产业政策。

### 维度4：改革举措（3-4条，至少1条来自 .gov.cn，至少2条来自≥85分信源）
搜索科技体制改革、科技成果转化、科技金融改革最新进展。
重点关注："先投后股"成果转化模式、新型研发机构改革、科技金融工具创新（科技保险、投贷联动等）。

### ⚠️ 五大产业赛道强制交叉搜索（每条赛道在周报中至少被1条信息覆盖）
以下5个方向**不作为独立板块**，而是**强制交叉融入**上述4个维度的搜索中。本周周报中，每条赛道至少要有1条相关信息覆盖：

1. **AIDC/算力基建** ★ 最高优先级
   搜索词：site:gov.cn "AI数据中心" OR "智算中心" OR "算力补贴" OR "算力基建"；"算力券" "补贴"；"AI产业园" "布局"
   常州关联：常州AIDC建设进度、算力规模规划、与武汉光谷/南京等城市的算力竞赛

2. **具身智能** ★ 最高优先级
   搜索词："具身智能" OR "人形机器人" "产业政策" OR "实训基地" OR "产业园"；"智能体经济" "行动计划"
   常州关联：常州在智能制造端的场景优势（理想汽车、比亚迪工厂）、科教城职教资源

3. **未来存储**
   搜索词："新型存储" OR "存储技术" "产业规划" OR "标准"
   常州关联：常州在存储产业链中的潜在切入点

4. **未来能源** ★ 最高优先级
   搜索词："氢能" OR "新型储能" OR "钙钛矿" OR "虚拟电厂" "政策" OR "产业布局" OR "补贴"
   常州关联：常州新能源之都建设、中创新航/蜂巢能源等龙头企业、氢能基础设施布局

5. **液冷技术**
   搜索词："液冷" OR "浸没式冷却" "数据中心" "标准" OR "产业布局"
   常州关联：常州在液冷产业链（泵、换热器等精密制造）中的潜在优势

以上5个方向搜索时额外加入关键词"算力+硬件+场景+生态""AI产业链""创新链""全链条"，构建完整产业链视野。

═══════════════════════════════════════════════════════════
创新洞察深度要求（每条80-150字，精炼简洁、直击要点）
═══════════════════════════════════════════════════════════

每条 insight 必须做到以下9个维度中至少5个（★为必选项，篇幅精简切忌冗长）：

### ★ 1. 对标常州五大未来产业方向（必选）
必须指明该信息与常州 AIDC/具身智能/未来存储/未来能源/液冷 五大产业方向中至少一个的关联：
- 该政策/事件对常州相关产业是机遇还是威胁？
- 常州在该赛道上的现有基础和差距是什么？
- 如何在"算力+硬件+场景+生态"全链条中找到常州的卡位点？

### ★ 2. 嫁接常州既有产业基础（必选）
结合常州新能源（比亚迪/理想/中创新航/蜂巢能源）、高端装备（智能制造/数控机床）、新能源汽车及零部件等既有优势产业，指出如何借此基础切入新赛道。

### ★ 3. 周边万亿城市竞争态势分析（必选）
必须对比苏州/无锡/南京/南通中至少2个城市的同类布局，明确指出：
- 这些城市在同一赛道上已做了什么？（具体政策名/金额/时间）
- 常州的差异化空间在哪里？（不是follow，而是找到独特切入点）
- 如果周边城市已大幅领先，常州的紧迫性是什么？

### 4. 29座万亿之城差异化定位
分析常州在29座GDP万亿城市中的独特定位——常州是"新能源之都"+"国际化智造名城"，如何在新能源与智能制造的交叉点上找到不可替代的位置？

### ★ 5. 紧扣常州政策抓手（必选）
至少关联以下政策工具中的1-2个，**不强制特定园区，只要是常州本地的产业载体即可**：
- **三名工程**：名园（科教城/高新区/中以常州创新园/各省级开发区等）+ 名院（与高水平大学合作）+ 名企（理想/比亚迪/中创新航/蜂巢能源等龙头企业）
- **双高协同**：高新区与高水平大学协同创新
- 常州本地产业园区/创新载体：科教城、高新区、中以常州创新园、各省级开发区、特色产业园等
- 科技创新政策：算力券、研发补贴、人才引进等

### ★ 6. 对接市委市政府经济工作会议精神和企业调研关注点（必选）
每条 insight 必须与以下至少一个方向建立关联：
- **经济工作会议精神**：常州市委市政府近期经济工作会议部署的科技创新重点任务、产业发展主攻方向、年度攻坚目标
- **企业调研关注点**：市领导调研重点企业时关注的痛点（如技术卡脖子环节、产业链配套短板、人才缺口、融资需求等）
- 将外部情报转化为回应上述关注点的具体建议

### 7. "算力+硬件+场景+生态"全链条分析
分析该信息如何嵌入"算力+硬件+场景+生态"的AI产业链创新链框架——常州的优势在"硬件"（智能制造）和"场景"（新能源/工业AI），短板在"算力"和"生态"，如何补短板拉长板？

### 8. 具体可操作建议（精简，1-2句即可）
给出下一步行动的具体方向：
- 由哪个部门牵头？对接什么资源？

### 9. 严格禁止的写法
- ✕ "值得借鉴""有参考价值""值得关注"——空洞无物
- ✕ "常州也应......""建议常州......"——只有结论没有路径
- ✕ 脱离常州实际的泛泛建议
- ✕ 照搬原文不做本地化转化
- ✕ 数字/政策名称与原文不符

═══════════════════════════════════════════════════════════
输出格式
═══════════════════════════════════════════════════════════

完成搜索和分析后，你必须以如下 JSON 格式输出（不要包含任何其他文字，只输出 JSON）：

```json
{
  "weekly_overview": "200-250字本周综述。概括本周最重要的3-4条动态主线，明确对常州的整体启示。必须结合常州五大产业方向和周边竞争格局，点明本周出现的机遇窗口和竞争威胁。",
  "sections": [
    {
      "name": "各地科技委动态",
      "items": [
        {
          "title": "信息标题（机构全称准确，如'江苏省委科技委员会第X次全体会议'）",
          "date": "YYYY.M.D（🔴只能填正文事件实际发生日期，严禁填网页发布日期。素材中区分'事件日期'与'网页发布'，只取事件日期。事件日期缺失填'近日'）",
          "summary": "80-120字，短句直击核心。格式：主体+事件+关键数据+时间节点。信源标注：如有多源验证写'据XX官方发布'；单信源写'（单信源，待进一步确认）'",
          "insight": "80-150字（精炼简洁）。必须包含：①五大产业方向关联 ②常州产业基础嫁接点 ③至少2个周边城市竞争对比 ④政策抓手（三名工程/双高协同/本地产业园区）⑤对接经济工作会议精神/企业调研关注点 ⑥可操作建议+牵头部门",
          "source": "来源机构名称（全称）",
          "url": "原文URL（真实链接）"
        }
      ]
    }
  ],
  "trend_analysis": "200-300字本周趋势分析。归纳2-3条跨板块的共性趋势，重点分析：①常州在苏州/无锡/南京/南通竞争中的差异化空间 ②常州在AIDC/具身智能/未来能源等赛道上的本周最新态势 ③结合常州市委市政府科技创新工作部署，提出下一步行动的优先级建议"
}
```

记住：只输出 JSON，不要有任何解释、前缀或后缀文字。输出前必须逐条通过第6层自检清单的7项检查。"""

WEEKLY_USER_PROMPT_TEMPLATE = """今天是{today_cn}。请联网搜索本周（{week_start}至{week_end}）科技创新领域重要动态，生成《创新常州·对标快讯》周报。

═══════════════════════════════════════════════════════════
⛔ 搜索前必读：最高频错误警示
═══════════════════════════════════════════════════════════
1. ⚠️ 江苏省委科技委最近一次全体会议于**2026年6月30日**召开。如果搜索结果中有关于此会议的信息，日期**必须**写6月30日，绝不能写成7月1日或其他日期！
2. ⚠️ "科技委"≠"科委"：科技委全称"中国共产党XX省/市委科技委员会"，是党委议事协调机构。写错此名称属于政治性错误。
3. ⚠️ 所有日期、金额、百分比等关键数据必须与 .gov.cn 原文逐位一致。
	4. 🔴 日期致命错误：date字段只能填正文中事件实际发生日期，严禁填网页发布日期！每个素材都标注了"事件日期"和"网页发布"两个日期——只取"事件日期"。若事件日期缺失，填"近日"（不是填网页发布日期）。此条为硬性约束，出错即错误。

═══════════════════════════════════════════════════════════
搜索要求（每维度必须使用 site: 限定词优先命中政务官方信源）
═══════════════════════════════════════════════════════════

### 维度1 · 各地科技委动态（至少2条来自 .gov.cn，3-4条）
⚠️ 搜索"科技委"而非"科委"。全称"省委科技委员会"或"市委科技委员会"。

第一轮（政务官方强制）：
- site:gov.cn "科技委" "会议" OR "全体会议" OR "部署"
- site:most.gov.cn "科技委" OR "科技创新"
- site:jiangsu.gov.cn "科技委" "全体会议" OR "会议"
- site:changzhou.gov.cn "科技委"

第二轮（补充搜索）：
- "省委科技委" OR "市委科技委" "全体会议" "2026年7月"
- "科技委" "科技创新" "部署" "2026年7月"

第三轮（交叉验证）：
- 对第一轮命中的关键会议，用不同关键词组合重新搜索以确认日期和细节
- 搜索具体会议名称（如"江苏省委科技委员会 全体会议 2026"）进行二次确认

### 维度2 · 上海（长三角）国创中心资讯（至少1条来自 .gov.cn，3-4条）
第一轮（政务官方强制）：
- site:most.gov.cn "长三角" "国际科技创新中心"
- site:stcsm.sh.gov.cn "张江" OR "科创中心" OR "长三角"
- site:shanghai.gov.cn "国际科技创新中心" OR "长三角"

第二轮（扩充搜索）：
- "长三角" "G60科创走廊" OR "沿沪宁产业创新带" "2026年7月"
- "长三角" "科技创新" "协同" OR "一体化" "2026"
- "长三角国创中心" OR "长三角国家技术创新中心" "2026"

### 维度3 · 科创政策速览（至少1条来自 .gov.cn，3-4条）
⚠️ 重点搜索五大产业方向相关政策

第一轮（政务官方强制）：
- site:gov.cn "科技创新政策" "2026"
- site:beijing.gov.cn OR site:shenzhen.gov.cn OR site:nanjing.gov.cn OR site:suzhou.gov.cn OR site:wuhan.gov.cn "科技创新" "政策"

第二轮（五大产业方向政策搜索，每项至少搜一轮）：
- site:gov.cn "AI数据中心" OR "智算中心" OR "算力补贴" OR "算力基建" "2026"
- site:gov.cn "具身智能" OR "人形机器人" OR "智能体经济" "政策" OR "行动计划"
- site:gov.cn "氢能" OR "新型储能" OR "钙钛矿" OR "未来能源" "政策" OR "补贴"
- site:gov.cn "液冷" OR "浸没式冷却" "数据中心" "标准"
- site:gov.cn "新型存储" OR "存储技术" "产业"

第三轮（常州本地+周边城市）：
- site:changzhou.gov.cn "AIDC" OR "算力" OR "人工智能" OR "新能源"
- "苏州" OR "无锡" OR "南京" OR "南通" "算力" OR "AI" OR "具身智能" OR "氢能" "产业政策" "2026"

第四轮（全链条搜索）：
- "算力+硬件+场景+生态" "AI产业链" "创新链"
- "AI产业园" OR "算力产业园" OR "人工智能产业园" "布局" "2026"

### 维度4 · 改革举措（至少1条来自 .gov.cn，3-4条）
第一轮（政务官方强制）：
- site:gov.cn "科技体制改革" OR "科技成果转化" "2026"
- site:most.gov.cn "改革" "2026"

第二轮（专题搜索）：
- "科技成果转化" "先投后股" OR "赋权改革" OR "科技金融" "2026年7月"
- "校地合作" OR "新型研发机构" OR "高新区 高水平大学 协同"
- "三名工程" OR "名园名院名企" OR "双高协同"
- "科技保险" OR "投贷联动" OR "科技信贷" "2026"

### ⚠️ 常州本地对标搜索（每期必搜，作为创新洞察的本地化依据）
以下搜索用于确保每条 insight 紧扣常州实际，不能脱离：

**常州市委市政府经济工作部署**：
- site:changzhou.gov.cn "经济工作会议" OR "市委全会" OR "市政府常务会议" "2026"
- site:changzhou.gov.cn "科技创新" OR "产业发展" "部署" OR "攻坚"
- "常州" "新能源之都" OR "国际化智造名城" "2026"

**市领导调研企业关注点**：
- site:changzhou.gov.cn "调研" "企业" OR "产业" "2026"
- "常州" "市委书记" OR "市长" "调研" "新能源" OR "智能制造" OR "AI"
- 重点关注：技术卡脖子环节、产业链配套短板、人才缺口、融资需求、园区配套等

### ⚠️ 五大产业赛道强制交叉搜索（每条赛道本周至少覆盖1次）
在搜索以上4个维度时，每个维度额外追加以下产业关键词的交叉搜索。本周周报中5条赛道必须全部覆盖，不能遗漏：

**AIDC/算力基建** ★（最高优先级）：
- "AIDC" OR "智算中心" OR "算力券" OR "算力补贴" — 各地AI数据中心建设与补贴政策
- 重点关注对常州AIDC建设有直接对标价值的城市（武汉光谷、南京、深圳等）

**具身智能** ★（最高优先级）：
- "具身智能" OR "人形机器人" OR "智能体经济" — 政策、产业园、实训基地
- 重点关注制造业场景应用（与常州智能制造优势结合）

**未来能源** ★（最高优先级）：
- "氢能" OR "新型储能" OR "钙钛矿" OR "虚拟电厂" — 新能源创新链
- 重点关注浙江、广东、江苏等省份的未来能源产业政策

**未来存储**：
- "新型存储" OR "存储技术" OR "存储产业" — 技术与产业布局

**液冷技术**：
- "液冷" OR "浸没式冷却" — 数据中心散热技术与标准

═══════════════════════════════════════════════════════════
信息筛选标准（每条结果必须逐一通过）
═══════════════════════════════════════════════════════════
□ 1. 信源评分≥60分？（.gov.cn=100分，权威平台≥85分，媒体智库≥60分）
□ 2. 日期是否在本周内（{week_start}至{week_end}）？是否与原文逐位一致？
□ 3. 信息是否充实？（必须有具体政策名称/金额/数据/主体/时间节点，缺一项即跳过）
□ 4. 对常州是否有直接对标价值？（优先：可复制的政策工具、可对接的平台资源、周边万亿城市的竞争动态）
□ 5. 是否有≥2个独立信源交叉确认？（重点数据：会议日期、金额、政策名称）
□ 6. 标题中的机构名称是否准确？（科技委≠科委！）

═══════════════════════════════════════════════════════════
创新洞察自检（每条必查，输出前逐项打勾）
═══════════════════════════════════════════════════════════
□ 1. 是否关联了常州AIDC/具身智能/未来存储/未来能源/液冷五大产业中至少一个？
□ 2. 是否结合了常州既有产业基础（新能源/高端装备/新能源汽车等）？
□ 3. 是否对比了苏州/无锡/南京/南通中至少2个城市的同类布局？
□ 4. 是否在29座万亿之城中明确了常州的差异化定位？
□ 5. 是否扣合了"三名工程"（本地园区/名院/名企）或"双高协同"（高新区+大学）等政策抓手？
□ 6. 是否对接了市委市政府经济工作会议精神或企业调研关注点？（技术卡脖子/产业链短板/人才缺口/融资需求等）
□ 7. 是否从"算力+硬件+场景+生态"全链条视角做了分析？
□ 8. 是否给出了具体可操作的行动建议（含牵头部门+对接资源）？
□ 9. 是否避免了"值得借鉴""有参考价值"等空话套话？
□ 10. 建议中引用的数据/政策名称是否与搜索结果原文逐位一致？

═══════════════════════════════════════════════════════════
本周趋势分析要求
═══════════════════════════════════════════════════════════
归纳2-3条跨板块的共性趋势时，必须包含：
1. 常州在苏州/无锡/南京/南通等周边万亿城市竞争中的最新定位变化
2. 常州在 AIDC、具身智能、未来存储、未来能源、液冷五大产业赛道上的本周最新态势（每条赛道至少一句话）
3. 结合常州市委市政府经济工作会议部署和企业调研反馈，提出本周最紧迫的1-2项行动建议
4. 分析本周出现的对常州而言是"机遇窗口"还是"竞争威胁"的信号

请现在开始逐维度搜索。每条信息输出前必须通过6层验证框架的全部检查。最终只输出 JSON。"""


def _get_supplementary_urls(report_type: str = "weekly") -> list[dict]:
    """
    返回从指定信息渠道（WebSearch验证）的补充文章URL列表。
    覆盖爬虫CSS选择器无法触及的信源，定期更新保持时效性。
    """
    base_urls = [
        # ── 长三角（重点补充）──
        {
            "url": "http://www.js.gov.cn/art/2026/7/4/art_60095_11798950.html",
            "source": "江苏省人民政府",
            "score": 100,
            "dimension": "上海（长三角）国创中心资讯",
        },
        {
            "url": "https://www.zgjssw.gov.cn/yaowen/202607/t20260704_8581695.shtml",
            "source": "中共江苏省委新闻网",
            "score": 100,
            "dimension": "上海（长三角）国创中心资讯",
        },
        {
            "url": "https://news.cctv.com/2026/07/01/ARTI7r5vchk6ZLHbdkJUwXI1260701.shtml",
            "source": "央视网",
            "score": 70,
            "dimension": "上海（长三角）国创中心资讯",
        },
        {
            "url": "https://www.sh.chinanews.com.cn/qxdt/2026-07-04/147549.shtml",
            "source": "中新社上海",
            "score": 70,
            "dimension": "上海（长三角）国创中心资讯",
        },
        # ── 科技日报 ──
        {
            "url": "https://www.stdaily.com/web/gdxw/2026-07/04/content_542088.html",
            "source": "科技日报",
            "score": 85,
            "dimension": "科创政策速览",
        },
        # ── 常州本地 ──
        {
            "url": "https://kjj.changzhou.gov.cn/html/kjj/2026/MIHPIKKP_0703/49603.html",
            "source": "常州市科技局",
            "score": 100,
            "dimension": "各地科技委动态",
        },
        {
            "url": "https://www.cznd.gov.cn/html/cznd/2026/EFBJILJD_0703/574891.html",
            "source": "常州高新区",
            "score": 100,
            "dimension": "科创政策速览",
        },
        {
            "url": "https://www.changzhou.gov.cn/ns_news/442178312987266",
            "source": "常州市人民政府",
            "score": 100,
            "dimension": "各地科技委动态",
        },
        # ── 其他省市科技委 ──
        {
            "url": "http://rf.jiangxi.gov.cn/jxsgfdybgs/szfyw123/list/content/content_2072814374501392384.html",
            "source": "江西省人民政府",
            "score": 100,
            "dimension": "各地科技委动态",
        },
        {
            "url": "https://kjt.ah.gov.cn/kjzx/jckj/123425511.html",
            "source": "安徽省科技厅",
            "score": 100,
            "dimension": "各地科技委动态",
        },
    ]

    if report_type == "monthly":
        base_urls.extend([
            {
                "url": "https://www.cls.cn/detail/2287605",
                "source": "财联社",
                "score": 70,
                "dimension": "上海（长三角）国创中心资讯",
            },
        ])

    return base_urls


def get_weekly_data(api_key: str = None, sample: bool = False) -> dict:
    """新管线：真实信源采集 → AI 摘要+洞察"""
    if sample or not api_key:
        return _sample_data()

    from datetime import date, timedelta
    sys.path.insert(0, str(SCRIPT_DIR))

    today = date.today()
    today_cn = today.strftime("%Y年%m月%d日")
    week_start_cn = (today - timedelta(days=today.weekday())).strftime("%Y年%m月%d日")
    week_end_cn = today.strftime("%Y年%m月%d日")

    # ── 阶段1: 真实信源采集 ──
    print(f"\n{'='*65}")
    print(f"  阶段1: 真实信源采集（近7天 .gov.cn 等权威网站）")
    print(f"{'='*65}")
    from crawler import crawl_all, SourceItem, fetch_supplementary_articles, merge_sources
    crawled = crawl_all(days_back=7, max_per_source=8)

    # ── 阶段1b: 补充 WebSearch 验证过的文章 ──
    supplementary_urls = _get_supplementary_urls("weekly")
    if supplementary_urls:
        print(f"\n  补充采集: 从指定渠道获取 {len(supplementary_urls)} 篇验证文章...")
        supp_items = fetch_supplementary_articles(supplementary_urls)
        crawled = merge_sources(crawled, supp_items)
        for dim, items in crawled.items():
            print(f"    [{dim}]: {len(items)} 条（合并后）")

    # 构建真实素材上下文
    context_parts = []
    total_articles = 0
    for dim, items in crawled.items():
        context_parts.append(f"\n### {dim}（共{len(items)}条真实素材）")
        for i, it in enumerate(items):
            context_parts.append(
                f"[{i+1}] 标题: {it.title}\n"
                f"    🔴事件日期（必须用于报告date字段）: {it.event_date or '未知'}\n"
                f"    网页发布日期（仅供参考，严禁用作报告date字段）: {it.date_str}\n"
                f"    来源: {it.source} ({it.domain}, 评分{it.score})\n"
                f"    链接: {it.url}\n"
                f"    摘要: {it.summary[:150]}"
            )
            total_articles += 1

    if total_articles < 4:
        print(f"[警告] 仅采集到 {total_articles} 条真实素材，不足生成报告。使用示例数据。")
        return _sample_data()

    # 缓存原始采集素材供事实核查使用
    crawled_for_cache = {}
    for dim, items in crawled.items():
        crawled_for_cache[dim] = [it.to_dict() for it in items]
    cache_file = CACHE_DIR / "crawled_sources.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(crawled_for_cache, f, ensure_ascii=False, indent=2)

    crawled_context = "\n".join(context_parts)

    # ── 阶段2: AI 基于真实素材进行摘要和洞察 ──
    print(f"\n{'='*65}")
    print(f"  阶段2: AI 基于 {total_articles} 条真实素材生成摘要+洞察")
    print(f"{'='*65}")

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    curation_prompt = f"""你是常州科技创新情报分析师，专责为常州市委市政府提供决策参考。以下是从 .gov.cn 等权威网站真实采集的本周最新信息。

请基于这些**真实素材**完成以下工作：
1. 从素材中筛选最有价值的12-16条信息，严格归入以下4个板块（板块名称不可更改）：
   - 各地科技委动态
   - 上海（长三角）国创中心资讯
   - 科创政策速览
   - 改革举措
2. 为每条信息撰写80-120字摘要（基于原文事实，不得编造原文没有的数据）
3. 为每条信息撰写120-160字创新洞察（精炼简洁，直击要点，下文有详细要求）
4. 撰写200-250字本周综述和200-300字趋势分析

⛔ 关键约束：
- **只能使用素材中提供的信息**，不得编造素材中不存在的会议、政策、数据
- **时效性强制要求**：素材标注的事件日期必须在近2周内（{week_start_cn}至{week_end_cn}），超出范围或日期不明确的素材直接丢弃不用
- **日期使用规则**：素材中标注了"事件日期"和"网页发布"两个日期，你必须使用**事件日期**（格式YYYY.M.D，如2026.6.30）。如果事件日期为空，则以网页发布日期为准。summary 中如需标注信源报道日期，写在摘要正文末尾，**绝对不要写在 date 字段里**。date 字段只能是纯日期格式（YYYY.M.D 或 近日）。
- **机构名称强制**：素材中已有的机构名称必须原样使用，不得改动。"长三角国家技术创新中心"绝不能简写为"长三角国创中心"，必须使用全称。
- 如果某板块素材不足2条，宁可少写，不要编造

═══════════════════════════════════════════════════════════
创新洞察撰写规范（每条120-160字，核心：常州如何差异化突围）
═══════════════════════════════════════════════════════════

## 战略定位框架（每条洞察必须体现以下视角）：
常州是长三角27座万亿城市之一，正在建设"长三角产业科技创新中心"。当前重点布局五大未来产业赛道：
- **AIDC（人工智能数据中心）**：算力基础设施，构建"算力+硬件+场景+生态"AI产业链创新链
- **具身智能**：人形机器人、协作机器人、智能体，重点在核心零部件（力触觉传感器、灵巧手）
- **未来存储**：新型存储技术、存算一体芯片、磁光电融合存储
- **未来能源**：氢能、新型储能、钙钛矿、虚拟电厂
- **液冷技术**：浸没式冷却、液冷散热方案，配套算力中心建设

## 每条洞察必须同时满足以下6个维度（缺一不可）：
★1. **产业赛道锚定**：明确本条关联五大产业中哪1-2个，点出具体技术/产品方向（不要空说"未来能源"，要写"钙钛矿中试线"或"氢能储运装备"）
★2. **产业基础嫁接**：点出常州现有优势产业/企业（新能源：天合光能、中创新航、蜂巢能源、理想汽车、比亚迪常州；高端装备：恒立液压、安川机器人、纳博特斯克），说清如何嫁接
★3. **万亿城市对标**（必须对比至少2个城市）：明确写出常州vs苏州/无锡/南京/南通的具体差异——苏州强在XX，无锡深耕XX，南京依托XX，南通发力XX，因此常州应差异化走XX路线。最终落脚到常州如何在29座万亿之城中建立不可替代地位
★4. **产业园区承载**：点出常州具体承载园区（科教城、常州高新区、武进高新区、西太湖科技产业园、常州经开区、溧阳高新区、金坛华罗庚高新区、中以常州创新园），说明应在哪个园区布局什么
★5. **政策工具扣合**：对接常州政策抓手——三名工程（名园名院名企）、双高协同（高校+高新园区）、龙城金谷（科技金融）、科技创新政策（创新券、研发费用补贴、人才引进）
★6. **行动建议+牵头部门**：给出1-2句可执行建议，指明牵头部门（市科技局/市工信局/市发改委/市市场监管局/市金融监管局/市大数据局/市人才办/科教城管委会等）

## 企业调研关注点（涉及企业时必须考虑以下真实痛点）：
- 卡脖子技术瓶颈（产业链短板在哪）
- 人才缺口（缺什么类型人才，数量级）
- 融资需求（天使/VC/产业基金缺口）
- 园区配套（中试场地、检测认证、算力券等）
- 链主企业带动效应、专精特新企业培育

## 禁止事项：
禁止：空话套话（"值得借鉴""有参考价值""有借鉴意义""值得关注""值得学习""应该加强""应该重视""进一步加大""不断深化""大力推进""意义重大""影响深远"等绝对禁止）
禁止：啰嗦冗长、空洞无物、不点具体企业/园区/部门名称
禁止：使用"长三角国创中心"简称——必须写全称"长三角国家技术创新中心"

### 以下是本周从权威网站采集的真实素材

{crawled_context}

### 请以 JSON 格式输出（只输出 JSON，不要其他文字）：

```json
{{
  "weekly_overview": "200-250字本周综述",
  "sections": [
    {{
      "name": "各地科技委动态",
      "items": [
        {{
          "title": "标题",
          "date": "YYYY.M.D（🔴只能填正文事件实际发生日期，严禁填网页发布日期。素材中区分'事件日期'与'网页发布'，只取事件日期。事件日期缺失填'近日'）",
          "summary": "80-120字摘要（仅基于原文事实）",
          "insight": "120-160字创新洞察（严格遵循6维度规范）",
          "source": "来源机构",
          "url": "原文链接（素材中的真实URL）"
        }}
      ]
    }}
  ],
  "trend_analysis": "200-300字趋势分析"
}}
```

记住：基于真实素材，不要编造。只输出 JSON。"""

    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": curation_prompt}],
        max_tokens=16000, temperature=0.1,
    )

    text = response.choices[0].message.content or ""
    json_str = text.strip()
    if json_str.startswith("```"):
        lines = json_str.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        json_str = "\n".join(lines).strip()
    return json.loads(json_str)


def get_daily_data(api_key: str = None, sample: bool = False) -> dict:
    """日报新管线：真实信源采集 → AI 摘要+洞察（3天窗口）"""
    if sample or not api_key:
        return _sample_data()

    from datetime import date, timedelta
    sys.path.insert(0, str(SCRIPT_DIR))

    today = date.today()
    today_cn = today.strftime("%Y年%m月%d日")

    # ── 阶段1: 真实信源采集 ──
    print(f"\n{'='*65}")
    print(f"  阶段1: 真实信源采集（近3天 .gov.cn 等权威网站）")
    print(f"{'='*65}")
    from crawler import crawl_all, fetch_supplementary_articles, merge_sources
    crawled = crawl_all(days_back=3, max_per_source=5)

    # 补充 WebSearch 验证过的文章
    supplementary_urls = _get_supplementary_urls("daily")
    if supplementary_urls:
        print(f"\n  补充采集: 从指定渠道获取 {len(supplementary_urls)} 篇验证文章...")
        supp_items = fetch_supplementary_articles(supplementary_urls)
        crawled = merge_sources(crawled, supp_items)

    context_parts = []
    total_articles = 0
    for dim, items in crawled.items():
        context_parts.append(f"\n### {dim}（共{len(items)}条真实素材）")
        for i, it in enumerate(items):
            context_parts.append(
                f"[{i+1}] 标题: {it.title}\n"
                f"    🔴事件日期（必须用于报告date字段）: {it.event_date or '未知'}\n"
                f"    网页发布日期（仅供参考，严禁用作报告date字段）: {it.date_str}\n"
                f"    来源: {it.source} ({it.domain}, 评分{it.score})\n"
                f"    链接: {it.url}\n"
                f"    摘要: {it.summary[:150]}"
            )
            total_articles += 1

    if total_articles < 3:
        print(f"[警告] 仅采集到 {total_articles} 条真实素材，不足生成日报。使用示例数据。")
        return _sample_data()

    # 缓存原始采集素材供事实核查使用
    crawled_for_cache = {}
    for dim, items in crawled.items():
        crawled_for_cache[dim] = [it.to_dict() for it in items]
    cache_file = CACHE_DIR / "crawled_sources_daily.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(crawled_for_cache, f, ensure_ascii=False, indent=2)

    crawled_context = "\n".join(context_parts)

    # ── 阶段2: AI 基于真实素材进行摘要和洞察 ──
    print(f"\n{'='*65}")
    print(f"  阶段2: AI 基于 {total_articles} 条真实素材生成日报摘要+洞察")
    print(f"{'='*65}")

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    curation_prompt = f"""你是常州科技创新情报分析师，专责为常州市委市政府提供决策参考。以下是从 .gov.cn 等权威网站真实采集的近3天最新信息。

请基于这些**真实素材**完成以下工作：
1. 从素材中筛选最有价值的8-12条信息，严格归入以下4个板块（板块名称不可更改）：
   - 各地科技委动态
   - 上海（长三角）国创中心资讯
   - 科创政策速览
   - 改革举措
2. 为每条信息撰写80-120字摘要（基于原文事实，不得编造原文没有的数据）
3. 为每条信息撰写120-160字创新洞察（精炼简洁，直击要点，下文有详细要求）

⛔ 关键约束：
- **只能使用素材中提供的信息**，不得编造素材中不存在的会议、政策、数据
- **时效性强制要求**：素材标注的事件日期必须在近3天内，超出范围或日期不明确的素材直接丢弃不用
- **日期使用规则**：素材中标注了"事件日期"和"网页发布"两个日期，你必须使用**事件日期**（格式YYYY.M.D，如2026.6.30）。如果事件日期为空，则以网页发布日期为准。summary 中如需标注信源报道日期，写在摘要正文末尾，**绝对不要写在 date 字段里**。date 字段只能是纯日期格式（YYYY.M.D 或 近日）。
- **机构名称强制**：素材中已有的机构名称必须原样使用，不得改动。"长三角国家技术创新中心"绝不能简写为"长三角国创中心"，必须使用全称。
- 如果某板块素材不足，宁可少写，不要编造

═══════════════════════════════════════════════════════════
创新洞察撰写规范（每条120-160字，核心：常州如何差异化突围）
═══════════════════════════════════════════════════════════

## 战略定位：常州是长三角27座万亿城市之一，正在建设"长三角产业科技创新中心"。重点布局五大未来产业：
- AIDC（算力基础设施，构建"算力+硬件+场景+生态"AI产业链创新链）
- 具身智能（力触觉传感器、灵巧手、协作机器人等核心零部件）
- 未来存储（新型存储技术、存算一体芯片）
- 未来能源（氢能、新型储能、钙钛矿、虚拟电厂）
- 液冷技术（浸没式冷却、液冷散热方案）

## 每条洞察必须同时满足6个维度：
★1. **产业赛道锚定**：明确关联五大产业中哪1-2个，点出具体技术/产品方向（不空谈，写"钙钛矿中试线"而非"未来能源"）
★2. **产业基础嫁接**：点出常州企业（天合光能、中创新航、蜂巢能源、理想汽车、比亚迪常州、恒立液压等），说清如何嫁接现有优势
★3. **万亿城市对标**（至少2城）：苏州强在XX，无锡深耕XX，南京依托XX，南通发力XX → 常州应差异化走XX路线，在29座万亿之城中建立不可替代地位
★4. **产业园区承载**：点出具体园区（科教城、常州高新区、武进高新区、西太湖科技产业园、常州经开区、中以常州创新园等），说明在哪个园区布局什么
★5. **政策工具扣合**：对接三名工程（名园名院名企）、双高协同（高校+高新园区）、龙城金谷（科技金融）、科技创新政策
★6. **行动建议+牵头部门**：1-2句可执行建议，指明牵头部门（市科技局/市工信局/市发改委/市市场监管局/市金融监管局/市大数据局/市人才办/科教城管委会等）

## 企业调研关注点（涉及企业时须考虑真实痛点）：
卡脖子技术瓶颈、产业链短板、人才缺口、融资需求、园区配套（中试场地、检测认证、算力券）、链主企业带动、专精特新培育

## 禁止：
空话套话（"值得借鉴""有参考价值""有借鉴意义""值得关注""值得学习""应该加强""进一步加大""大力推进"等绝对禁止）
啰嗦冗长、空洞无具体企业/园区/部门名称
使用"长三角国创中心"简称——必须写全称"长三角国家技术创新中心"

### 以下是近3天从权威网站采集的真实素材

{crawled_context}

### 请以 JSON 格式输出（只输出 JSON，不要其他文字）：

```json
{{
  "sections": [
    {{
      "name": "各地科技委动态",
      "items": [
        {{
          "title": "标题",
          "date": "YYYY.M.D（🔴只能填正文事件实际发生日期，严禁填网页发布日期。素材中区分'事件日期'与'网页发布'，只取事件日期。事件日期缺失填'近日'）",
          "summary": "80-120字摘要（仅基于原文事实）",
          "insight": "120-160字创新洞察（严格遵循6维度规范）",
          "source": "来源机构",
          "url": "原文链接（素材中的真实URL）"
        }}
      ]
    }}
  ]
}}
```

记住：基于真实素材，不要编造。只输出 JSON。"""

    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": curation_prompt}],
        max_tokens=12000, temperature=0.1,
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
            url = item.get("url", "")
            source_link_html = ""
            if url:
                source_link_html = f'<p class="item-source-link">信息来源：<a href="{url}">{url}</a></p>'
            items_html += f"""
        <div class="news-item">
          <h3 class="item-title">{title}<span class="item-date">{date_i}</span></h3>
          <p class="item-summary">{summary}</p>
          <div class="item-insight">
            <span class="insight-label">创新洞察</span>
            <p>{insight}</p>
          </div>
          <p class="item-source">{source}</p>
          {source_link_html}
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
    margin: 10mm 12mm 16mm 12mm;
    @top-center {{
      content: element(header);
    }}
    @bottom-center {{
      content: "— " counter(page) " —";
      font-size: 7pt;
      color: #94a3b8;
      font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", "Microsoft YaHei", sans-serif;
    }}
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
    font-size: 9pt;
    line-height: 1.6;
    color: var(--text);
  }}

  /* ── Cover: compact blue header block ── */
  .cover {{
    background: linear-gradient(135deg, #0a2655 0%, #1e50b4 100%);
    padding: 14px 20px 12px 20px;
    margin-bottom: 12px;
    border-radius: 3px;
    color: #fff;
  }}
  .cover-inner {{
    display: flex; align-items: center; justify-content: space-between;
  }}
  .cover-left h1 {{
    font-size: 16pt; font-weight: 700; letter-spacing: 2px; color: #fff;
  }}
  .cover-left .cover-sub {{
    font-size: 7pt; color: rgba(255,255,255,0.65); letter-spacing: 1px; margin-top: 1px;
  }}
  .cover-right {{
    text-align: right; font-size: 7.5pt; color: rgba(255,255,255,0.8); line-height: 1.5;
  }}

  /* ── Running header ── */
  .running-header {{
    position: running(header);
    font-size: 7pt; color: var(--blue);
    display: flex; justify-content: space-between;
    border-bottom: 0.5px solid var(--light-gray);
    padding-bottom: 3px; margin-bottom: 4px;
  }}

  /* ── Content ── */
  .content {{ padding-top: 0; }}

  .overview {{
    font-size: 9pt; color: var(--text-secondary);
    line-height: 1.55; margin-bottom: 6px;
    padding: 6px 10px;
    background: var(--bg);
    border-left: 3px solid var(--blue);
    border-radius: 0 3px 3px 0;
  }}

  .section-title {{
    font-size: 10.5pt; font-weight: 700; color: var(--blue);
    margin: 10px 0 4px 0; padding-bottom: 0;
    border-bottom: none;
  }}
  .section-title::before {{
    content: '●'; color: var(--blue); margin-right: 5px; font-size: 9pt;
  }}

  .news-item {{
    margin-bottom: 5px; padding-bottom: 3px;
    border-bottom: none;
  }}

  .item-title {{
    font-size: 9.5pt; font-weight: 600; color: var(--blue);
    margin-bottom: 1px; line-height: 1.45;
  }}
  .item-title::before {{
    content: '▸'; color: var(--accent); margin-right: 4px; font-size: 8pt;
  }}
  .item-date {{
    font-size: 7pt; font-weight: 400; color: var(--gray);
    margin-left: 4px;
  }}

  .item-summary {{
    font-size: 8.5pt; color: var(--text-secondary);
    line-height: 1.6; margin-bottom: 3px;
    text-align: justify;
  }}

  .item-insight {{
    background: var(--accent-bg);
    border-left: 2px solid var(--accent);
    border-radius: 0 3px 3px 0;
    padding: 5px 10px; margin: 4px 0 3px 0;
  }}
  .item-insight p {{
    font-size: 8pt; color: #6b4f10;
    line-height: 1.6; display: inline;
  }}
  .insight-label {{
    font-size: 7pt; font-weight: 700; color: var(--accent);
    letter-spacing: 1px; margin-right: 4px;
  }}

  .item-source {{
    font-size: 6.5pt; color: #94a3b8; text-align: right;
    margin-top: 2px;
  }}
  .item-source-link {{
    font-size: 6.5pt; color: #94a3b8; margin-top: 1px;
    word-break: break-all;
  }}
  .item-source-link a {{
    color: #64748b; text-decoration: none;
  }}

  .trend-text {{
    font-size: 9pt; color: var(--text-secondary);
    line-height: 1.7; text-align: justify;
    padding: 8px 12px;
    background: var(--bg);
    border-radius: 3px;
  }}

  /* ── Print ── */
  @media print {{
    .news-item {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-inner">
    <div class="cover-left">
      <h1>创新常州·对标快讯</h1>
      <p class="cover-sub">Innovation Changzhou · Benchmarking Weekly</p>
    </div>
    <div class="cover-right">
      <p>2026年 第{issue_no}期 &nbsp;·&nbsp; 总第{total_no}期</p>
      <p>{date_cn}</p>
    </div>
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

def build_daily_html(data, date_cn: str, issue_no: int = 1, total_no: int = 1) -> str:
    """构建日报 HTML。data 可以是 dict（含 sections）或 list[dict]"""
    if isinstance(data, list):
        sections, overview = data, ""
    else:
        sections = data.get("sections", [])
        overview = data.get("daily_overview") or data.get("weekly_overview") or ""

    items_html = ""
    if overview:
        items_html += f'<p class="overview">{overview}</p>\n'

    for s in sections:
        sname = s.get("name", "")
        items_html += f'<h2 class="section-title">{sname}</h2>\n'
        for item in s.get("items", []):
            title = item.get("title", "")
            date_i = item.get("date", "")
            summary = item.get("summary", "")
            insight = item.get("insight") or item.get("innovation_insight") or ""
            source = item.get("source", "")
            url = item.get("url", "")
            source_html = f'<p class="item-source">信息来源：<a href="{url}">{url}</a></p>' if url else f'<p class="item-source">{source}</p>'
            items_html += f"""
        <div class="news-item">
          <h3 class="item-title">{title}<span class="item-date">{date_i}</span></h3>
          <p class="item-summary">{summary}</p>
          <div class="item-insight">
            <span class="insight-label">创新洞察</span>
            <p>{insight}</p>
          </div>
          {source_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 10mm 12mm 16mm 12mm;
    @top-center {{
      content: element(header);
    }}
    @bottom-center {{
      content: "— " counter(page) " —";
      font-size: 7pt;
      color: #94a3b8;
      font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", "Microsoft YaHei", sans-serif;
    }}
  }}
  @page:first {{
    margin: 0;
    @top-center {{ content: none; }}
    @bottom-center {{ content: none; }}
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
  .item-title::before {{
    content: '▸'; color: var(--accent); margin-right: 4px; font-size: 9pt;
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
    margin-top: 4px; word-break: break-all;
  }}
  .item-source a {{
    color: #64748b; text-decoration: none;
  }}

  .overview {{
    font-size: 9.5pt; color: #475569;
    line-height: 1.8; margin-bottom: 16px;
    text-align: justify; padding: 8px 12px;
    background: #f1f5f9; border-radius: 4px;
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

═══════════════════════════════════════════════════════════
⛔ 第一优先级：事实准确性多层验证框架（每条信息必须逐层通过）
═══════════════════════════════════════════════════════════

## 第1层 · 信源权威性评分
- 100分：.gov.cn 政府官网原文
- 85分：.cas.cn / .cae.cn / stdaily.com
- 70分：省级以上党媒、权威行业媒体
- 60分：知名智库、头部科技媒体
- 0分（丢弃）：自媒体、无署名来源
**每板块至少2条来自≥85分信源，其中至少1条来自 .gov.cn（100分信源）。**

## 第2层 · 多信源交叉验证
1. 至少2个不同信源确认同一事件。仅1个信源的须标注「（单信源，待进一步确认）」。
2. 信源矛盾以 .gov.cn 为准。
3. 以下数据必须2个以上信源确认：会议日期、文件名称和文号、金额数据、百分比数据。

## 第3层 · 日期精确性强制校验（⚠️最高频错误）
1. ⚠️ **会议日期必须与原文严格一致**。如江苏省委科技委会议原文为6月30日，必须写6月30日，绝不能写成7月1日。
2. 原文仅"近日"则标注"近日"并注明「（原文未明确日期）」。
3. 严禁推测日期。

## 第4层 · 机构名称准确性强制校验
1. **"科技委"≠"科委"**：全称"中国共产党XX省/市委科技委员会"，2023年机构改革后设立的党委议事协调机构。写错属政治性错误。
2. 易错名核查："G60科创走廊"非"G60科技走廊"、"沿沪宁产业创新带"非"沿沪宁创新走廊"、"中以常州创新园"非"中以创新园"。

## 第5层 · 数据精度强制校验
1. 金额、百分比必须与原文逐位一致，不得四舍五入。
2. 未搜到具体数据宁写"加快推进"不虚构数字。

## 第6层 · 输出前逐条强制自检（7项全通过才输出）
□ 1. 机构名称准确？（科技委≠科委！）
□ 2. 会议/事件日期与原文逐字一致？（6月30日≠7月1日！）
□ 3. 金额/百分比与原文逐位一致？
□ 4. ≥2个独立信源交叉确认？
□ 5. 至少1个 .gov.cn 或权威平台信源？
□ 6. summary含具体日期、主体、关键数据？
□ 7. insight中数据/政策名称与搜索结果原文一致？

═══════════════════════════════════════════════════════════
核心原则
═══════════════════════════════════════════════════════════

1. **时效性**：采集本月内发布的重大信息
2. **信源优先级**：.gov.cn（100分）> 权威平台（85分）> 媒体智库（60-70分）
3. **每板块至少1条来自 .gov.cn，至少2条来自≥85分信源**
4. **月度视角**：关注趋势演变、政策连贯性、跨板块关联。每条信息要体现其在月度框架中的位置——是延续性进展还是突破性信号
5. **信息密度**：摘要100-150字，包含具体政策名称、金额、时间节点、涉及主体

═══════════════════════════════════════════════════════════
搜索维度（4维度 + 5大产业赛道强制交叉搜索）
═══════════════════════════════════════════════════════════

### 维度1：各地科技委动态（3-4条，至少1条 .gov.cn）
⚠️ 搜索"科技委"而非"科委"。科技委是党委议事协调机构（全称"市委/省委科技委员会"）。会议日期必须与原文严格一致。

### 维度2：上海（长三角）国创中心资讯（3-4条，至少1条 .gov.cn）
长三角国际科技创新中心、G60科创走廊、沿沪宁产业创新带

### 维度3：科创政策速览（3-4条，至少1条 .gov.cn）
万亿城市科技创新政策、产业扶持政策。重点搜索五大产业方向。

### 维度4：改革举措（3-4条，至少1条 .gov.cn）
科技体制改革、科技成果转化、科技金融改革

### ⚠️ 五大产业赛道强制交叉搜索（本月每条赛道至少覆盖2条信息）
1. **AIDC/算力基建** ★：AI数据中心、智算中心、算力补贴/算力券、"算力+硬件+场景+生态"
2. **具身智能** ★：人形机器人、智能体经济、产业政策、实训基地
3. **未来存储**：新型存储技术、产业规划、标准制定
4. **未来能源** ★：氢能、新型储能、钙钛矿、虚拟电厂
5. **液冷技术**：数据中心液冷、浸没式冷却

═══════════════════════════════════════════════════════════
创新洞察深度要求（每条80-150字，精炼简洁、直击要点，★为必选项）
═══════════════════════════════════════════════════════════

★ 1. **对标五大产业方向**：关联AIDC/具身智能/未来存储/未来能源/液冷至少一个
★ 2. **嫁接常州产业基础**：结合新能源（比亚迪/理想/中创新航/蜂巢能源）、高端装备、新能源汽车等
★ 3. **竞争态势分析**：对比苏州/无锡/南京/南通中至少2个城市，指出差异化空间
4. **29座万亿之城定位**：分析常州"新能源之都"+"国际化智造名城"的独特定位
★ 5. **扣合政策抓手**：关联三名工程（本地园区/名院/名企）、双高协同（高新区+高水平大学），不强制特定园区
★ 6. **对接经济工作会议精神和企业调研关注点**：结合常州市委市政府经济工作会议部署的重点任务、市领导调研企业时关注的痛点（技术卡脖子/产业链短板/人才缺口/融资需求等）
7. **全链条视角**："算力+硬件+场景+生态"分析常州卡位点
8. **可操作建议**（精简，1-2句）：给出牵头部门+对接资源

### 严禁出现：
- "值得借鉴""有参考价值""值得关注"等空话套话
- 脱离常州实际的泛泛建议
- 照搬原文不做本地化转化的分析
- 数字/政策名称与原文不符
- 篇幅冗长，超过150字

## 输出格式

```json
{
  "monthly_overview": "250-350字本月综述，梳理核心主线和重大变化，结合常州五大产业方向和竞争格局点明启示。必须覆盖AIDC/具身智能/未来能源等关键赛道的月度动态。",
  "sections": [
    {
      "name": "各地科技委动态",
      "items": [
        {
          "title": "信息标题（机构全称准确）",
          "date": "2026.7.X（🔴只能填正文事件实际发生日期，严禁填网页发布日期）",
          "summary": "100-150字，包含具体政策名称/金额/时间/主体。信源标注：多源验证写'据XX官方发布'",
          "insight": "80-150字（精炼简洁）。必须包含：①五大产业方向关联 ②常州产业基础嫁接点 ③至少2个周边城市竞争对比 ④政策抓手 ⑤经济工作会议精神/企业调研关注点 ⑥可操作建议+牵头部门",
          "source": "来源机构名称（全称）",
          "url": "原文URL"
        }
      ]
    }
  ],
  "trend_analysis": "250-350字月度趋势分析，归纳2-3条跨板块深层趋势。必须分析常州在苏州/无锡/南京/南通竞争中的差异化空间和29座万亿之城中的定位。",
  "strategic_recommendations": ["建议1（可操作+责任部门+政策抓手）", "建议2", "建议3", "建议4", "建议5"]
}
```

记住：只输出 JSON。输出前必须逐条通过第6层自检清单的7项检查。"""

MONTHLY_USER_PROMPT_TEMPLATE = """今天是{today_cn}。请联网搜索本月（{month_start}至{month_end}）科技创新领域重要动态，生成《创新常州·对标快讯》月报。

═══════════════════════════════════════════════════════════
⛔ 搜索前必读：最高频错误警示
═══════════════════════════════════════════════════════════
1. ⚠️ 江苏省委科技委最近一次全体会议于**2026年6月30日**召开。若搜索结果涉及此会议，日期**必须**写6月30日！
2. ⚠️ "科技委"≠"科委"：全称"中国共产党XX省/市委科技委员会"，党委议事协调机构。此错误属于政治性错误。
3. ⚠️ 所有日期、金额、百分比必须与 .gov.cn 原文逐位一致。

═══════════════════════════════════════════════════════════
搜索要求（每维度使用 site: 限定词优先命中政务官方信源。月报应有更广的覆盖面）
═══════════════════════════════════════════════════════════

### 维度1 · 各地科技委动态（至少1条 .gov.cn，3-4条）
⚠️ 搜索"科技委"而非"科委"。全称"省委科技委员会"或"市委科技委员会"。
第一轮（政务官方）：
- site:gov.cn "科技委" "会议" OR "全体会议" OR "部署"
- site:most.gov.cn "科技委" OR "科技创新"
- site:jiangsu.gov.cn "科技委" "全体会议" OR "会议"
第二轮（补充）：
- "省委科技委" OR "市委科技委" "全体会议" OR "行动方案" OR "行动计划"
第三轮（交叉验证）：
- 对关键会议用不同关键词二次搜索确认日期和细节

### 维度2 · 上海（长三角）国创中心资讯（至少1条 .gov.cn，3-4条）
- site:most.gov.cn "长三角" "国际科技创新中心"
- site:stcsm.sh.gov.cn "张江" OR "科创中心" OR "长三角"
- site:shanghai.gov.cn "国际科技创新中心"
- "长三角" "G60科创走廊" OR "沿沪宁产业创新带"
- "长三角" "科技创新" "协同" OR "一体化"

### 维度3 · 科创政策速览（至少1条 .gov.cn，3-4条）
⚠️ 重点搜索五大产业方向政策
政务官方：
- site:gov.cn "科技创新政策"
- site:gov.cn "AI数据中心" OR "智算中心" OR "算力补贴" "2026"
- site:gov.cn "具身智能" OR "人形机器人" "政策" OR "行动计划"
- site:gov.cn "氢能" OR "新型储能" OR "钙钛矿" "政策" OR "补贴"
- site:gov.cn "液冷" OR "浸没式冷却" "数据中心"
- site:gov.cn "新型存储" OR "存储技术" "产业"
万亿城市+周边：
- site:beijing.gov.cn OR site:shenzhen.gov.cn OR site:nanjing.gov.cn OR site:suzhou.gov.cn OR site:wuhan.gov.cn "科技创新" "政策"
- "苏州" OR "无锡" OR "南京" OR "南通" "算力" OR "AI" OR "氢能" "产业政策" "2026"
全链条：
- "算力+硬件+场景+生态" OR "AI产业链创新链"

### 维度4 · 改革举措（至少1条 .gov.cn，3-4条）
- site:gov.cn "科技体制改革" OR "科技成果转化"
- site:most.gov.cn "改革"
- "科技成果转化" "先投后股" OR "赋权改革" OR "科技金融"
- "校地合作" OR "新型研发机构" OR "高新区 高水平大学 协同"
- "三名工程" OR "名园名院名企" OR "双高协同"
- "科技保险" OR "投贷联动"

### ⚠️ 常州本地对标搜索（每期必搜，作为创新洞察的本地化依据）
- site:changzhou.gov.cn "经济工作会议" OR "市委全会" OR "市政府常务会议"
- site:changzhou.gov.cn "调研" "企业" OR "产业"
- "常州" "市委书记" OR "市长" "调研" "新能源" OR "智能制造" OR "AI"
- 重点关注：技术卡脖子、产业链配套短板、人才缺口、融资需求、园区配套

### ⚠️ 五大产业赛道强制交叉搜索（本月每条赛道至少覆盖2条）
- "AIDC" OR "智算中心" — AI数据中心建设布局与补贴政策
- "具身智能" OR "人形机器人" OR "智能体" — 产业园、实训基地、产业政策
- "未来存储" OR "新型存储" — 存储技术路线与产业布局
- "未来能源" OR "氢能" OR "钙钛矿" OR "新型储能" — 新能源创新链
- "液冷" OR "浸没式冷却" — 数据中心散热技术标准

═══════════════════════════════════════════════════════════
筛选标准（每条逐一过）
═══════════════════════════════════════════════════════════
□ 1. 信源评分≥60分？
□ 2. 日期在本月内（{month_start}至{month_end}）？与原文逐位一致？
□ 3. 信息充实？（具体政策名称/金额/数据/时间节点/涉及主体）
□ 4. 对常州有对标价值？（优先可复制政策工具、可对接平台资源、周边万亿城市竞争动态）
□ 5. 摘要去冗余、直击核心事实？
□ 6. 机构名称准确？（科技委≠科委！）

═══════════════════════════════════════════════════════════
创新洞察自检（每条必查，输出前逐项打勾）
═══════════════════════════════════════════════════════════
□ 1. 关联了常州AIDC/具身智能/未来存储/未来能源/液冷五大产业中至少一个？
□ 2. 结合了常州既有产业基础（新能源/高端装备/新能源汽车等）？
□ 3. 对比了苏州/无锡/南京/南通中至少2个城市的同类布局？
□ 4. 在29座万亿之城中明确了常州差异化定位？
□ 5. 扣合了"三名工程"（本地园区/名院/名企）或"双高协同"（高新区+大学）？
□ 6. 对接了市委市政府经济工作会议精神或企业调研关注点？（技术卡脖子/产业链短板/人才缺口/融资需求等）
□ 7. 从"算力+硬件+场景+生态"全链条视角做了分析？
□ 8. 给出了具体可操作的行动建议（含牵头部门+对接资源）？
□ 9. 避免了"值得借鉴""有参考价值"等空话套话？
□ 10. 数据、政策名称与搜索结果原文逐位一致？

═══════════════════════════════════════════════════════════
战略建议要求（5条）
═══════════════════════════════════════════════════════════
- 紧扣常州市委市政府当前科技创新工作部署
- 针对 AIDC、具身智能、未来存储、未来能源、液冷等产业方向
- 考虑常州在 29 座万亿之城中的差异化定位
- 每条可落地、可量化、有明确责任部门
- 从"算力+硬件+场景+生态"全链条给出系统建议

请逐维度搜索分析。每条信息输出前必须通过6层验证框架的全部检查。只输出 JSON。"""


def get_monthly_data(api_key: str = None, sample: bool = False) -> dict:
    """月报新管线：真实信源采集 → AI 摘要+洞察（30天窗口）"""
    if sample or not api_key:
        return _monthly_sample_data()

    from datetime import date, timedelta
    sys.path.insert(0, str(SCRIPT_DIR))

    today = date.today()
    today_cn = today.strftime("%Y年%m月%d日")
    month_start_cn = today.replace(day=1).strftime("%Y年%m月%d日")
    month_end_cn = today.strftime("%Y年%m月%d日")

    # ── 阶段1: 真实信源采集（30天窗口）──
    print(f"\n{'='*65}")
    print(f"  阶段1: 真实信源采集（近30天）")
    print(f"{'='*65}")
    from crawler import crawl_all, fetch_supplementary_articles, merge_sources
    crawled = crawl_all(days_back=30, max_per_source=12)

    # 补充 WebSearch 验证过的文章
    supplementary_urls = _get_supplementary_urls("monthly")
    if supplementary_urls:
        print(f"\n  补充采集: 从指定渠道获取 {len(supplementary_urls)} 篇验证文章...")
        supp_items = fetch_supplementary_articles(supplementary_urls)
        crawled = merge_sources(crawled, supp_items)

    context_parts = []
    total_articles = 0
    for dim, items in crawled.items():
        context_parts.append(f"\n### {dim}（共{len(items)}条真实素材）")
        for i, it in enumerate(items):
            context_parts.append(
                f"[{i+1}] 标题: {it.title}\n"
                f"    🔴事件日期（必须用于报告date字段）: {it.event_date or '未知'}\n"
                f"    网页发布日期（仅供参考，严禁用作报告date字段）: {it.date_str}\n"
                f"    来源: {it.source} ({it.domain}, 评分{it.score})\n"
                f"    链接: {it.url}\n"
                f"    摘要: {it.summary[:150]}"
            )
            total_articles += 1

    if total_articles < 4:
        print(f"[警告] 仅采集到 {total_articles} 条真实素材，使用示例数据。")
        return _monthly_sample_data()

    # 缓存原始采集素材
    crawled_for_cache = {}
    for dim, items in crawled.items():
        crawled_for_cache[dim] = [it.to_dict() for it in items]
    cache_file = CACHE_DIR / "crawled_sources_monthly.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(crawled_for_cache, f, ensure_ascii=False, indent=2)

    crawled_context = "\n".join(context_parts)

    # ── 阶段2: AI 基于真实素材生成月报 ──
    print(f"\n{'='*65}")
    print(f"  阶段2: AI 基于 {total_articles} 条真实素材生成月报")
    print(f"{'='*65}")

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    curation_prompt = f"""你是常州科技创新情报分析师，专责为常州市委市政府提供决策参考。以下是从 .gov.cn 等权威网站真实采集的本月最新信息。

请基于这些**真实素材**完成以下工作：
1. 从素材中筛选最有价值的12-16条信息，严格归入以下4个板块：
   - 各地科技委动态
   - 上海（长三角）国创中心资讯
   - 科创政策速览
   - 改革举措
2. 为每条信息撰写100-150字摘要（基于原文事实）
3. 为每条信息撰写120-160字创新洞察（精炼简洁，直击要点，下文有详细要求）
4. 撰写250-350字本月综述和250-350字趋势分析
5. 提出5条战略建议

⛔ 只能使用素材中的信息，不得编造。
- **时效性强制要求**：素材标注的事件日期必须在本月内（{month_start_cn}至{month_end_cn}），超出范围或日期不明确的素材直接丢弃不用
- **日期使用规则**：素材中标注了"事件日期"和"网页发布"两个日期，你必须使用**事件日期**（格式YYYY.M.D，如2026.6.30）。如果事件日期为空，则以网页发布日期为准。summary 中如需标注信源报道日期，写在摘要正文末尾，**绝对不要写在 date 字段里**。date 字段只能是纯日期格式（YYYY.M.D 或 近日）。
- **机构名称强制**：素材中已有的机构名称必须原样使用，不得改动。"长三角国家技术创新中心"绝不能简写为"长三角国创中心"，必须使用全称。

═══════════════════════════════════════════════════════════
创新洞察撰写规范（每条120-160字，核心：常州如何差异化突围）
═══════════════════════════════════════════════════════════

## 战略定位：常州是长三角万亿城市之一，正在建设"长三角产业科技创新中心"。重点布局五大未来产业：
- AIDC（算力基础设施，构建"算力+硬件+场景+生态"AI产业链创新链）
- 具身智能（力触觉传感器、灵巧手、协作机器人等核心零部件）
- 未来存储（新型存储技术、存算一体芯片）
- 未来能源（氢能、新型储能、钙钛矿、虚拟电厂）
- 液冷技术（浸没式冷却、液冷散热方案）

## 每条洞察必须同时满足6个维度：
★1. **产业赛道锚定**：明确关联五大产业中哪1-2个，点出具体技术/产品方向
★2. **产业基础嫁接**：点出常州企业（天合光能、中创新航、蜂巢能源、理想汽车、比亚迪常州、恒立液压等），说清如何嫁接
★3. **万亿城市对标**（至少2城）：苏州强XX/无锡深耕XX/南京依托XX/南通发力XX → 常州应差异化走XX路线，在29座万亿之城中建立不可替代地位
★4. **产业园区承载**：点出具体园区（科教城、常州高新区、武进高新区、西太湖科技产业园、常州经开区、中以常州创新园等），说明在哪个园区布局什么
★5. **政策工具扣合**：对接三名工程（名园名院名企）、双高协同（高校+高新园区）、龙城金谷（科技金融）、科技创新政策
★6. **行动建议+牵头部门**：可执行建议+牵头部门

## 企业调研关注点：卡脖子技术瓶颈、产业链短板、人才缺口、融资需求、园区配套、链主带动、专精特新培育

## 禁止：
空话套话（"值得借鉴""有参考价值""有借鉴意义""值得关注""值得学习""应该加强""进一步加大""大力推进"等绝对禁止）
使用"长三角国创中心"简称——必须写全称"长三角国家技术创新中心"

### 真实素材
{crawled_context}

### 输出 JSON（只输出 JSON）：
```json
{{
  "monthly_overview": "250-350字本月综述",
  "sections": [
    {{
      "name": "各地科技委动态",
      "items": [
        {{
          "title": "标题",
          "date": "YYYY.M.D（必填，优先使用事件日期；若无则用网页发布日期并注明'据XX网站X月X日报道'；素材无日期填'近日'）",
          "summary": "100-150字摘要",
          "insight": "120-160字创新洞察（严格遵循6维度规范）",
          "source": "来源机构",
          "url": "原文链接（素材中的真实URL）"
        }}
      ]
    }}
  ],
  "trend_analysis": "250-350字趋势分析",
  "strategic_recommendations": ["建议1", "建议2", "建议3", "建议4", "建议5"]
}}
```
只输出 JSON。"""

    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": curation_prompt}],
        max_tokens=16000, temperature=0.1,
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
            url = item.get("url", "")
            source_link_html = ""
            if url:
                source_link_html = f'<p class="item-source-link">信息来源：<a href="{url}">{url}</a></p>'
            items_html += f"""
        <div class="news-item">
          <h3 class="item-title">{title}<span class="item-date">{date_i}</span></h3>
          <p class="item-summary">{summary}</p>
          <div class="item-insight">
            <span class="insight-label">创新洞察</span>
            <p>{insight}</p>
          </div>
          <p class="item-source">{source}</p>
          {source_link_html}
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
    margin: 10mm 12mm 16mm 12mm;
    @top-center {{
      content: element(header);
    }}
    @bottom-center {{
      content: "— " counter(page) " —";
      font-size: 7pt;
      color: #94a3b8;
      font-family: "PingFang SC", "STHeiti", "Noto Sans SC", "Heiti SC", "Microsoft YaHei", sans-serif;
    }}
  }}
  @page:first {{
    margin: 0;
    @top-center {{ content: none; }}
    @bottom-center {{ content: none; }}
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
  .item-title::before {{
    content: '▸'; color: var(--accent); margin-right: 4px; font-size: 9pt;
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
    _sys.path.insert(0, str(SCRIPT_DIR))

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

    # ── 后处理校验管道 ──
    if not sample and api_key:
        print("\n" + "=" * 65)
        print("  启动后处理校验管道（月报）")
        print("=" * 65)

        from validate_report import validate_report, print_validation_report
        errors, warnings = validate_report(data, "monthly")
        print_validation_report(errors, warnings)

        if errors:
            print("\n⚠️  校验发现错误，但仍继续生成 PDF")

        from fact_check import fact_check_against_sources, print_fact_check_report
        crawled_cache = CACHE_DIR / "crawled_sources_monthly.json"
        if crawled_cache.exists():
            with open(crawled_cache, "r", encoding="utf-8") as f:
                crawled_data = json.load(f)
            fc_result = fact_check_against_sources(data, crawled_data)
            print_fact_check_report(fc_result)

    print("\n[HTML] 生成页面...")
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


def _inject_editorial_content(data: dict, date_cn: str):
    """注入编辑定稿内容并过滤冗余条目。只注入编辑分析(综述/趋势),不注入任何事实性条目。"""

    # 1. 替换本周综述（编辑定稿分析版，不包含未经验证的事实主张）
    data["weekly_overview"] = (
        '本周（2026年6月28日至7月5日），科技创新领域聚焦于人工智能与算力基础设施的深化布局、'
        '长三角区域协同创新机制的加速落地，以及科技金融与成果转化政策的密集出台。各地科技委强调以AI赋能产业升级，'
        '长三角国家技术创新中心推动跨区域技术转移与产业孵化，万亿城市竞相出台算力补贴与未来产业扶持政策。'
        '科技体制改革方面，职务科技成果赋权改革与科技金融试点成为热点，为常州在AIDC、具身智能及未来能源等方向'
        '提供了政策窗口与对标样本。'
    )

    # 2. 替换本周趋势分析（编辑定稿分析版）
    data["trend_analysis"] = (
        '本周趋势信号显示，科技创新正呈现三大主线：一是算力基础设施从"建设"转向"运营"，'
        '各地通过补贴、试点等模式降低使用门槛，常州需加快AIDC与液冷技术的商业化应用；'
        '二是未来产业布局加速，具身智能、未来存储、未来能源成为万亿城市竞争焦点，'
        '常州应依托"三名工程"与"双高协同"，在细分领域形成差异化优势；'
        '三是科技金融与成果转化改革深化，赋权、投贷联动、先使用后付费等模式为创新松绑，'
        '常州可借鉴上海、浙江经验，构建更灵活的成果转化生态。'
        '整体看，长三角区域协同创新网络日益紧密，常州需主动融入沿沪宁产业创新带与G60走廊，借势提升产业能级。'
    )

    # 3. 从科创政策速览中移除"周伟调研光电子信息产业"（与其他条目信息重叠，且验证后保留其他条）
    sections = data.get("sections", [])
    for section in sections:
        if '科创政策' in section.get('name', ''):
            section['items'] = [
                it for it in section.get('items', [])
                if '光电子信息' not in it.get('title', '')
            ]
            break


# ── 主入口 ────────────────────────────────────────────

def generate(api_key: str = None, output_path: str = None, sample: bool = False):
    import sys as _sys
    _sys.path.insert(0, str(PROJECT_DIR))
    _sys.path.insert(0, str(SCRIPT_DIR))

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

    # ── 注入编辑定稿内容（本周综述/趋势分析 + 长三角预写条目）──
    _inject_editorial_content(data, date_cn)

    # ── 后处理校验管道 ──
    if not sample and api_key:
        print("\n" + "=" * 65)
        print("  启动后处理校验管道")
        print("=" * 65)

        # 第1层：正则后处理校验
        from validate_report import validate_report, print_validation_report
        errors, warnings = validate_report(data, "weekly")
        print_validation_report(errors, warnings)

        if errors:
            print("\n⚠️  校验发现严重错误，但仍继续生成 PDF（错误已标记在日志中）")

        # 第2层：事实核查（基于采集素材比对，不再依赖联网搜索）
        from fact_check import fact_check_against_sources, print_fact_check_report
        # 从缓存加载原始采集素材
        crawled_cache = CACHE_DIR / "crawled_sources.json"
        if crawled_cache.exists():
            with open(crawled_cache, "r", encoding="utf-8") as f:
                crawled_data = json.load(f)
            fc_result = fact_check_against_sources(data, crawled_data)
            fc_passed = print_fact_check_report(fc_result)
            if not fc_passed:
                print("\n⚠️  事实核查发现疑点，请人工复核")
        else:
            print("\n  ⚠️  无采集素材缓存，跳过事实核查")

    print("\n[HTML] 生成页面...")
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
