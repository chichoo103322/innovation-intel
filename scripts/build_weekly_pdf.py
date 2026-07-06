#!/usr/bin/env python3
"""生成周报 PDF，使用项目已有的美化样式"""
import sys, json
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path("/Users/jzxzhou/innovation-intel")
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from generate_html_pdf import html_to_pdf, get_issue_numbers


def build_weekly_html(data, date_cn, issue_no, total_no):
    """构建周报 HTML，完全复用项目已有 CSS 样式"""
    overview_text = data.get("weekly_overview", "")

    # ── 各板块内容 ──
    sections_html = ""
    for sec in data.get("sections", []):
        sname = sec.get("name", "")
        sections_html += f'<h2 class="section-title">{sname}</h2>\n'

        # 板块概述
        sec_overview = sec.get("overview", "")
        if sec_overview:
            sections_html += f'<div class="overview">{sec_overview}</div>\n'

        # 详细条目
        for item in sec.get("items", []):
            title = item.get("title", "")
            date_i = item.get("date", "")
            summary = item.get("summary", "")
            source = item.get("source", "")
            url = item.get("url", "")

            # 多条洞察
            insights = item.get("insight", "")
            if isinstance(insights, str):
                insights = [insights]
            labels = ["方案A", "方案B", "方案C"]
            insight_blocks = ""
            for i, ins in enumerate(insights):
                label = f"创新洞察 · {labels[i]}：" if len(insights) > 1 else "创新洞察："
                insight_blocks += f"""
          <div class="item-insight">
            <span class="insight-label">{label}</span>
            <p>{ins}</p>
          </div>"""

            source_html = f'<p class="item-source">{source}</p>' if source else ""
            url_html = f'<p class="item-source-link">信息来源：<a href="{url}">{url}</a></p>' if url else ""

            sections_html += f"""
        <div class="news-item">
          <h3 class="item-title">{title}<span class="item-date">{date_i}</span></h3>
          <p class="item-summary">{summary}</p>
          {insight_blocks}
          {source_html}
          {url_html}
        </div>"""

    # ── 趋势研判 ──
    trends = data.get("trends", [])
    trends_html = ""
    if trends:
        trends_html = '<h2 class="section-title">本周趋势研判</h2>\n'
        for i, t in enumerate(trends):
            trends_html += f'<p class="trend-item">{i+1}. {t}</p>\n'

    # ── 建议 ──
    suggestions = data.get("suggestions", [])
    suggestions_html = ""
    if suggestions:
        suggestions_html = '<h2 class="section-title">对常州建议</h2>\n'
        for i, s in enumerate(suggestions):
            suggestions_html += f'<p class="suggestion-item">{i+1}. {s}</p>\n'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 8mm 10mm 10mm 10mm;
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
    font-size: 8pt; line-height: 1.45; color: var(--text);
  }}

  /* ── Cover: compact blue header block ── */
  .cover {{
    background: linear-gradient(135deg, #0a2655 0%, #1e50b4 100%);
    padding: 10px 18px 8px 18px;
    margin-bottom: 8px;
    border-radius: 3px;
    color: #fff;
  }}
  .cover-inner {{
    display: flex; align-items: stretch; justify-content: space-between;
  }}
  .cover-left {{
    display: flex; flex-direction: column; justify-content: flex-end;
  }}
  .cover-left h1 {{
    font-size: 14pt; font-weight: 700; letter-spacing: 2px; color: #fff;
  }}
  .cover-left .cover-sub {{
    font-size: 6.5pt; color: rgba(255,255,255,0.65); letter-spacing: 1px; margin-top: 0;
  }}
  .cover-right {{
    display: flex; flex-direction: column; justify-content: flex-end;
    text-align: right; font-size: 7pt; color: rgba(255,255,255,0.8); line-height: 1.4;
  }}

  /* ── Running header ── */
  .running-header {{
    position: running(header);
    font-size: 6.5pt; color: var(--blue);
    display: flex; justify-content: space-between;
    border-bottom: 0.5px solid var(--light-gray);
    padding-bottom: 2px; margin-bottom: 2px;
  }}

  /* ── Overview ── */
  .overview {{
    font-size: 8pt; color: var(--text-secondary);
    line-height: 1.45; margin-bottom: 4px;
    padding: 4px 8px;
    background: var(--bg);
    border-radius: 2px;
    text-align: justify;
  }}

  /* ── Section titles ── */
  .section-title {{
    font-size: 9pt; font-weight: 700; color: var(--blue);
    margin: 6px 0 2px 0; padding-bottom: 0;
  }}
  .section-title::before {{
    content: '●'; color: var(--blue); margin-right: 5px; font-size: 9pt;
  }}

  /* ── News items ── */
  .news-item {{
    margin-bottom: 3px; padding-bottom: 2px;
  }}

  .item-title {{
    font-size: 8.5pt; font-weight: 600; color: var(--blue);
    margin-bottom: 1px; line-height: 1.35;
  }}
  .item-title::before {{
    content: '▸'; color: var(--accent); margin-right: 4px; font-size: 8pt;
  }}
  .item-date {{
    font-size: 6.5pt; font-weight: 400; color: var(--gray);
    margin-left: 3px;
  }}

  .item-summary {{
    font-size: 7.5pt; color: var(--text-secondary);
    line-height: 1.45; margin-bottom: 2px;
    text-align: justify;
  }}

  .item-insight {{
    background: var(--accent-bg);
    border-radius: 2px;
    padding: 3px 8px; margin: 2px 0 2px 0;
  }}
  .item-insight p {{
    font-size: 8.5pt; color: #6b4f10;
    line-height: 1.55; display: inline;
  }}
  .insight-label {{
    font-size: 9.5pt; font-weight: 700; color: var(--accent);
    letter-spacing: 0.5px; margin-right: 3px;
  }}

  .item-source {{
    font-size: 6pt; color: #94a3b8; text-align: right;
    margin-top: 1px;
  }}
  .item-source-link {{
    font-size: 6pt; color: #94a3b8; margin-top: 0;
    word-break: break-all;
  }}
  .item-source-link a {{
    color: #64748b; text-decoration: none;
  }}

  /* ── Trends ── */
  .trend-item {{
    font-size: 8pt; color: var(--text-secondary);
    line-height: 1.5; margin: 3px 6px;
    text-align: justify;
    padding: 3px 6px;
    background: var(--bg);
    border-radius: 2px;
  }}

  /* ── Suggestions ── */
  .suggestion-item {{
    font-size: 8pt; color: var(--text-secondary);
    line-height: 1.5; margin: 3px 6px;
    text-align: justify;
    padding: 3px 8px;
    background: #f0f4ff;
    border-radius: 2px;
  }}

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
      <p class="cover-sub">Innovation Changzhou · Weekly</p>
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
  <div class="overview">{overview_text}</div>

  {sections_html}

  {trends_html}

  {suggestions_html}
</div>

</body></html>"""


def main():
    json_path = PROJECT_DIR / "weekly" / "report_weekly_20260706.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now()
    date_cn = today.strftime("%Y年%m月%d日")
    issue, total = get_issue_numbers()

    html = build_weekly_html(data, date_cn, issue, total)

    output_pdf = Path("/Users/jzxzhou/Desktop/创新情报/周报/创新常州·对标快讯_周报_20260706.pdf")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    result = html_to_pdf(html, output_pdf)
    print(f"PDF 已生成: {result}")
    print(f"期号: 2026年第{issue}期 / 总第{total}期")


if __name__ == "__main__":
    main()
