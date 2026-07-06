# 创新常州·对标快讯 — AI 情报采集与报告生成系统

## 项目概述
服务于常州市科技创新决策的 AI 驱动情报系统。从互联网采集科技创新动态，经多层验证后生成日报/周报/月报 PDF。

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

### 2. 报告生成流程
- 日报：`config/daily_prompt.md` → 搜索 → `daily/report_data_YYYY-MM-DD.json` → `scripts/generate_html_pdf.py` → PDF
- 周报：`config/weekly_prompt.md` → 搜索 → `weekly/report_weekly_YYYYMMDD.json` → `scripts/build_weekly_pdf.py` → PDF
- 月报：`config/monthly_prompt.md` → 搜索 → JSON → `scripts/generate_html_pdf.py` → PDF

### 3. 关键文件
- 提示词：`config/daily_prompt.md`, `config/weekly_prompt.md`, `config/monthly_prompt.md`
- 核心引擎：`scripts/generate_html_pdf.py`, `scripts/build_weekly_pdf.py`
- 校验：`scripts/validate_report.py`
- 去重缓存：`cache/used_items.json`
- 期号计数：`cache/issue_counter.json`
- 输出目录：`/Users/jzxzhou/Desktop/创新情报/日推/`, `.../周报/`, `.../月报/`

### 4. 严格约束
- 每条信息必须通过 6 层事实准确性验证框架
- 所有信息必须当日发布（日报）/ 当周发布（周报）/ 当月发布（月报）
- 仅限 29 座万亿城市或省级政策，中小城市一律不取
- 科创政策速览必须有正式文件名（用《》括起来）
- 机构名称准确（科技委≠科委！）
- 每条信息出 3 版洞察（方案A/B/C），内容不雷同
- 严禁出现"值得借鉴""有参考价值"等空话套话

### 5. 去重机制
- `cache/used_items.json` 记录所有已用标题和 URL
- 日报与周报之间不能有重复条目
- 每次生成前检查去重缓存
