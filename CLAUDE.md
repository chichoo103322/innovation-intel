# 创新常州·对标快讯 — AI 情报采集与报告生成系统

## 项目概述
服务于常州市科技创新决策的 AI 驱动情报系统。从互联网采集科技创新动态，经多层验证后生成日报/周报/月报 PDF。

---

## Agent 工作流（触发词 + 自动执行）

当用户说出以下触发词时，**立即自动执行全部 6 步，不等待、不询问、不确认**：

| 触发词 | 报告类型 | JSON 路径 | 生成命令 |
|---|---|---|---|
| `出日报` | 日报 | `daily/report_data_YYYY-MM-DD.json` | `python3 run_daily.py --from-json <json>` |
| `出周报` | 周报 | `weekly/report_weekly_YYYYMMDD.json` | `python3 scripts/build_weekly_pdf.py` |
| `出月报` | 月报 | `monthly/report_monthly_YYYYMM.json` | `python3 run_monthly.py --from-json <json>` |

### Step 1: 读取提示词 & 确定参数
1. 读 `config/{daily|weekly|monthly}_prompt.md`，理解本期的要求
2. 确定日期范围（日报=当日，周报=本周一至今日，月报=本月1日至今日）
3. 先去重检查：读 `cache/used_items.json`，排除已用条目
4. 如已有当日/当周/当月报告文件 → 直接覆盖生成（不询问）

### Step 2: 联网搜索（每维度并行搜索）
按 `config/settings.yaml` 定义的四大维度，用 `WebSearch` 工具逐维度搜索：
1. **各地科技委动态** — 搜索"省委科技委 会议""市委科技委 部署"等
2. **上海（长三角）国创中心资讯** — 搜索"长三角 科创""G60 科创"等
3. **科创政策速览** — 搜索"科技创新政策 2026""万亿城市 行动计划"等
4. **改革举措** — 搜索"先投后股""科技金融 改革""成果转化"等

搜索规则：
- 每维度搜 3-5 次不同关键词，覆盖不同角度
- 优先使用 `site:gov.cn` 等限定词
- 对高价值链接用 `WebFetch` 获取全文
- **第0层过滤**：出现非万亿城市名称 → 立即丢弃该条
- 每条目标搜到 3-4 条优质条目（.gov.cn 信源优先）

### Step 3: 构建 JSON 数据
按报告类型对应的 prompt 中定义的 JSON schema，逐条将搜索结果整理为结构化数据。

日报 JSON 结构：
```json
{
  "sections": [
    {"name": "各地科技委动态", "items": [{"title":"","date":"","summary":"","insight":["方案A：","方案B：","方案C："],"source":"","url":""}]},
    ...
  ]
}
```

周报 JSON 额外包含：`weekly_overview`, `trends[]`, `suggestions[]`

构建规则（来自 prompt 的 6 层验证框架）：
- 第1层：信源评分 ≥ 60 分才收录，每板块至少 1 条 .gov.cn（100分）
- 第3层：date 填事件实际发生日期，不是网页发布日期
- 第4层：机构名准确（科技委≠科委，长三角国家技术创新中心≠长三角国创中心）
- 第5层：金额、百分比与原文逐位一致
- 每月板块 2-4 条（日报）/ 3-4 条（周报），总计 8-12 条
- 每条出 3 版洞察（方案A/B/C），内容不雷同
- 科创政策速览必须有正式文件名（用《》括起来）
- 严禁"值得借鉴""有参考价值"等空话套话
- 严禁非万亿城市出现（对照白名单逐条检查）

写入对应 JSON 文件后继续下一步。

### Step 4: 校验 & 自动修复（Loop until clean）
```bash
# 格式校验
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from validate_report import validate_report, print_validation_report
import json
data = json.load(open('<json_path>'))
errors, warnings = validate_report(data, '<daily|weekly>')
print_validation_report(errors, warnings)
if errors: sys.exit(1)
"

# 交叉验证（如有 crawled 缓存）
python3 -c "
import sys, json; sys.path.insert(0, 'scripts')
from fact_check import fact_check_against_sources, print_fact_check_report
data = json.load(open('<json_path>'))
crawled = json.load(open('cache/crawled_sources_daily.json'))  # if exists
result = fact_check_against_sources(data, crawled)
print_fact_check_report(result)
"
```

如校验不通过 → AI 直接修改 JSON 修复问题 → 重新校验 → 直到通过。

### Step 5: 生成 PDF
```bash
# 先重置期号计数器为 target-1（因为 get_issue_numbers() 会自动 +1）
python3 -c "
import json
target = <用户指定或自动推算的期号>
with open('cache/issue_counter.json', 'w') as f:
    json.dump({'issue': target-1, 'total': target-1}, f)
"

# 日报
python3 run_daily.py --from-json daily/report_data_YYYY-MM-DD.json

# 周报
python3 scripts/build_weekly_pdf.py

# 月报
python3 run_monthly.py --from-json monthly/report_monthly_YYYYMM.json
```

同时保存 HTML 到同目录。

### Step 6: 分发 & 提交
1. 分发：`python3 -c "from scripts.distribute import save_desktop; save_desktop('<pdf_path>', '<daily|weekly|monthly>')"`
2. Git：
```bash
git add -A && git commit -m "auto: 生成{日报|周报|月报} YYYY-MM-DD 第N期"
```
3. 输出摘要给用户：期号、条数、板块分布、PDF 路径

---

## 核心规则（所有 Claude Code 实例必须遵守）

### 1. 零打扰 · 全自动执行（最高优先级）

⛔ **绝对禁止询问用户 Yes/No、禁止请求批阅确认、禁止要求用户授权任何操作。直接执行，不问任何问题。**

这是一条写报告的自动化流水线，不是交互式工具。所有决策由 AI 自行判断并直接执行。

包括但不限于以下操作，一律直接执行，不问：
- 文件读写、创建、修改、删除（含代码文件、配置文件、JSON 数据文件）
- 联网搜索、网页抓取
- JSON/HTML/PDF 生成
- Python 脚本执行（`python3`、`bash` 等任意命令）
- Git 操作（add/commit，不含 push）
- 缓存更新（去重缓存、期号计数器等）
- 提示词修改、脚本修改、任何代码改动
- 报告数据编辑、内容增删改
- `Edit`/`Write`/`Bash` 等所有工具，一律跳过权限确认直接调用

唯一的例外：`git push` 到远程仓库。

### 2. 关键文件
- 提示词：`config/daily_prompt.md`, `config/weekly_prompt.md`, `config/monthly_prompt.md`
- 核心引擎：`scripts/generate_html_pdf.py`, `scripts/build_weekly_pdf.py`
- 校验：`scripts/validate_report.py`
- 事实核查：`scripts/fact_check.py`
- 去重：`scripts/dedup.py` + `cache/used_items.json`
- 期号计数：`cache/issue_counter.json`
- 配置：`config/settings.yaml`
- 输出目录：`/Users/jzxzhou/Desktop/创新情报/日推/`, `.../周报/`, `.../月报/`

### 3. 严格约束
- 每条信息必须通过 6 层事实准确性验证框架（定义在各 prompt 中）
- 所有信息必须当日/当周/当月发布
- 仅限 29 座万亿城市或省级政策，中小城市一律不取
- 科创政策速览必须有正式文件名（用《》括起来）
- 机构名称准确（科技委≠科委！）
- 每条信息出 3 版洞察（方案A/B/C），内容不雷同
- 严禁出现"值得借鉴""有参考价值"等空话套话

### 4. 去重机制
- `cache/used_items.json` 记录所有已用标题和 URL
- 日报与周报之间不能有重复条目
- 每次生成前检查去重缓存
