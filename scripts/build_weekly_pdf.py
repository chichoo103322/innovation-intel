#!/usr/bin/env python3
"""生成周报 PDF，使用项目已有的美化样式"""
import sys, json
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from generate_html_pdf import html_to_pdf, get_issue_numbers


def build_weekly_html_v2(data, date_cn, issue_no, total_no):
    """构建周报 HTML V2，简化版2页模板：仅科技创新政策列表"""
    items = data.get("items", [])
    stats = data.get("stats", f"共 {len(items)} 条政策")

    items_html = ""
    for item in items:
        title = item.get("title", "")
        date_i = item.get("date", "")
        summary = item.get("summary", "")
        insight = item.get("insight", "")
        source = item.get("source", "")
        url = item.get("url", "")

        insight_block = ""
        if insight:
            insight_block = f"""<div class="item-insight">
            <span class="insight-label">创新洞察：</span>
            <p>{insight}</p>
          </div>"""

        source_html = f'<p class="item-source">{source}</p>' if source else ""
        url_html = f'<p class="item-source-link">信息来源：<a href="{url}">{url}</a></p>' if url else ""

        items_html += f"""<div class="news-item">
          <h3 class="item-title">{title}<span class="item-date">　{date_i}</span></h3>
          <p class="item-summary">{summary}</p>
          {insight_block}
          {source_html}
          {url_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
      @page {{
        size: A4;
        margin: 4mm 6mm 4mm 6mm;
        @top-center {{
          content: element(header);
        }}
        @bottom-center {{
          content: "— " counter(page) " —";
          font-size: 6pt;
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
        font-size: 10.5pt; line-height: 1.4; color: var(--text);
      }}

      .cover {{
        background: linear-gradient(135deg, #0a2655 0%, #1e50b4 100%);
        padding: 4px 12px 2px 12px;
        margin-bottom: 3px;
        border-radius: 2px;
        color: #fff;
      }}
      .cover-inner {{
        display: flex; align-items: stretch; justify-content: space-between;
      }}
      .cover-left h1 {{
        font-size: 16pt; font-weight: 700; letter-spacing: 2px; color: #fff;
      }}
      .cover-left .cover-sub {{
        font-size: 8.5pt; color: rgba(255,255,255,0.6); letter-spacing: 1px; margin-top: 0;
      }}
      .cover-right {{
        text-align: right; font-size: 9pt; color: rgba(255,255,255,0.75); line-height: 1.3;
      }}

      .running-header {{
        position: running(header);
        font-size: 8pt; color: var(--blue);
        display: flex; justify-content: space-between;
        border-bottom: 0.5px solid var(--light-gray);
        padding-bottom: 1px; margin-bottom: 2px;
      }}

      .stats-line {{
        font-size: 9.5pt; color: var(--text-secondary);
        margin-bottom: 3px;
        padding: 2px 6px;
        background: var(--bg);
        border-radius: 2px;
        text-align: center;
      }}

      .section-title {{
        font-size: 11pt; font-weight: 700; color: var(--blue);
        margin: 0 0 0 0; padding-bottom: 0;
      }}
      .section-title::before {{
        content: '●'; color: var(--blue); margin-right: 4px; font-size: 11pt;
      }}

      .news-item {{
        margin-bottom: 0; padding-bottom: 0;
      }}

      .item-title {{
        font-size: 10pt; font-weight: 600; color: var(--blue);
        margin-bottom: 0; line-height: 1.4;
      }}
      .item-title::before {{
        content: '▸'; color: var(--accent); margin-right: 3px; font-size: 10pt;
      }}
      .item-date {{
        font-size: 8pt; font-weight: 400; color: var(--gray);
      }}

      .item-summary {{
        font-size: 9pt; color: var(--text-secondary);
        line-height: 1.4; margin-bottom: 0;
        text-align: justify;
      }}

      .item-insight {{
        background: var(--accent-bg);
        border-radius: 1px;
        padding: 1px 5px; margin: 0;
      }}
      .item-insight p {{
        font-size: 9.5pt; color: #6b4f10;
        line-height: 1.4; display: inline;
      }}
      .insight-label {{
        font-size: 10pt; font-weight: 700; color: var(--accent);
        letter-spacing: 0.5px; margin-right: 2px;
      }}

      .item-source {{
        font-size: 7.5pt; color: #94a3b8; text-align: right; margin-top: 0;
      }}
      .item-source-link {{
        font-size: 7pt; color: #94a3b8; margin-top: 0;
        word-break: break-all;
      }}
      .item-source-link a {{
        color: #64748b; text-decoration: none;
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
      <h1>创新政策·对标快讯</h1>
      <p class="cover-sub">Innovation Changzhou · Weekly Policy Watch</p>
    </div>
    <div class="cover-right">
      <p>2026年 第{issue_no}期 &nbsp;·&nbsp; 总第{total_no}期</p>
      <p>{date_cn}</p>
    </div>
  </div>
</div>

<div class="running-header">
  <span>创新政策·对标快讯</span>
  <span>2026年第{issue_no}期</span>
</div>

<div class="stats-line">📋 {stats}</div>

<h2 class="section-title">本周科技创新政策</h2>

{items_html}

</body></html>"""


def build_weekly_html(data, date_cn, issue_no, total_no):
    """构建周报 HTML，支持V1（四板块）和V2（政策列表）两种格式"""
    # V2 格式检测：有 items 无 sections → 使用简化版
    if data.get("items") and not data.get("sections"):
        return build_weekly_html_v2(data, date_cn, issue_no, total_no)

    # ── V1 格式：传统四板块模板 ──
    overview_text = data.get("weekly_overview", "") or data.get("summary", "")

    # ── 板块固定排序 ──
    SECTION_ORDER = ["各地科技委动态", "上海（长三角）国创中心资讯", "科创政策速览", "改革举措"]
    raw_sections = data.get("sections", [])
    ordered_sections = []
    for name in SECTION_ORDER:
        for sec in raw_sections:
            if sec.get("name", "") == name:
                ordered_sections.append(sec)
                break
    # 兜底：未匹配的板块追加到末尾
    for sec in raw_sections:
        if sec not in ordered_sections:
            ordered_sections.append(sec)

    # ── 各板块内容 ──
    sections_html = ""
    for sec in ordered_sections:
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
            labels = ["A", "B", "C"]
            insight_blocks = ""
            for i, ins in enumerate(insights):
                label = f"创新洞察{labels[i]}：" if len(insights) > 1 else "创新洞察："
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
            if isinstance(t, dict):
                txt = f"<b>{t.get('title', '')}</b><br>{t.get('content', '')}"
            else:
                txt = str(t)
            trends_html += f'<p class="trend-item">{i+1}. {txt}</p>\n'

    # ── 建议 ──
    suggestions = data.get("suggestions", [])
    suggestions_html = ""
    if suggestions:
        suggestions_html = '<h2 class="section-title">对常州建议</h2>\n'
        for i, s in enumerate(suggestions):
            if isinstance(s, dict):
                txt = f"<b>{s.get('title', '')}</b><br>{s.get('content', '')}"
            else:
                txt = str(s)
            suggestions_html += f'<p class="suggestion-item">{i+1}. {txt}</p>\n'

    # ── 条件区块：无内容不渲染 ──
    overview_block = f'<h2 class="section-title">本周综述</h2>\n  <div class="overview">{overview_text}</div>' if overview_text.strip() else ""
    has_pre_content = bool(overview_block or trends_html or suggestions_html)
    page_break = '<div style="page-break-before: always;"></div>' if has_pre_content else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
	  @page {{
	    size: A4;
	    margin: 4mm 6mm 4mm 6mm;
	    @top-center {{
	      content: element(header);
	    }}
	    @bottom-center {{
	      content: "— " counter(page) " —";
	      font-size: 6pt;
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
	    font-size: 7.5pt; line-height: 1.25; color: var(--text);
	  }}

	  .cover {{
	    background: linear-gradient(135deg, #0a2655 0%, #1e50b4 100%);
	    padding: 4px 12px 2px 12px;
	    margin-bottom: 2px;
	    border-radius: 2px;
	    color: #fff;
	  }}
	  .cover-inner {{
	    display: flex; align-items: stretch; justify-content: space-between;
	  }}
	  .cover-left {{
	    display: flex; flex-direction: column; justify-content: flex-end;
	  }}
	  .cover-left h1 {{
	    font-size: 13pt; font-weight: 700; letter-spacing: 2px; color: #fff;
	  }}
	  .cover-left .cover-sub {{
	    font-size: 6pt; color: rgba(255,255,255,0.6); letter-spacing: 1px; margin-top: 0;
	  }}
	  .cover-right {{
	    display: flex; flex-direction: column; justify-content: flex-end;
	    text-align: right; font-size: 6.5pt; color: rgba(255,255,255,0.75); line-height: 1.3;
	  }}

	  .running-header {{
	    position: running(header);
	    font-size: 6pt; color: var(--blue);
	    display: flex; justify-content: space-between;
	    border-bottom: 0.5px solid var(--light-gray);
	    padding-bottom: 1px; margin-bottom: 1px;
	  }}

	  .overview {{
	    font-size: 7.5pt; color: var(--text-secondary);
	    line-height: 1.25; margin-bottom: 2px;
	    padding: 1px 5px;
	    background: var(--bg);
	    border-radius: 1px;
	    text-align: justify;
	  }}

	  .section-title {{
	    font-size: 8pt; font-weight: 700; color: var(--blue);
	    margin: 3px 0 0 0; padding-bottom: 0;
	  }}
	  .section-title::before {{
	    content: '●'; color: var(--blue); margin-right: 4px; font-size: 8pt;
	  }}

	  .news-item {{
	    margin-bottom: 0; padding-bottom: 0;
	  }}

	  .item-title {{
	    font-size: 7.5pt; font-weight: 600; color: var(--blue);
	    margin-bottom: 0; line-height: 1.25;
	  }}
	  .item-title::before {{
	    content: '▸'; color: var(--accent); margin-right: 3px; font-size: 7.5pt;
	  }}
	  .item-date {{
	    font-size: 6pt; font-weight: 400; color: var(--gray);
	    margin-left: 2px;
	  }}

	  .item-summary {{
	    font-size: 6.5pt; color: var(--text-secondary);
	    line-height: 1.25; margin-bottom: 0;
	    text-align: justify;
	  }}

	  .item-insight {{
	    background: var(--accent-bg);
	    border-radius: 1px;
	    padding: 1px 5px; margin: 0;
	  }}
	  .item-insight p {{
	    font-size: 8pt; color: #6b4f10;
	    line-height: 1.3; display: inline;
	  }}
	  .insight-label {{
	    font-size: 9pt; font-weight: 700; color: var(--accent);
	    letter-spacing: 0.5px; margin-right: 2px;
	  }}

	  .item-source {{
	    font-size: 5.5pt; color: #94a3b8; text-align: right;
	    margin-top: 0;
	  }}
	  .item-source-link {{
	    font-size: 5.5pt; color: #94a3b8; margin-top: 0;
	    word-break: break-all;
	  }}
	  .item-source-link a {{
	    color: #64748b; text-decoration: none;
	  }}

	  .trend-item {{
	    font-size: 7.5pt; color: var(--text-secondary);
	    line-height: 1.25; margin: 1px 2px;
	    text-align: justify;
	    padding: 1px 3px;
	    background: var(--bg);
	    border-radius: 1px;
	  }}

	  .suggestion-item {{
	    font-size: 7.5pt; color: var(--text-secondary);
	    line-height: 1.25; margin: 1px 2px;
	    text-align: justify;
	    padding: 1px 5px;
	    background: #f0f4ff;
	    border-radius: 1px;
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
      <h1>创新政策·对标快讯</h1>
      <p class="cover-sub">Innovation Changzhou · Benchmarking Weekly</p>
    </div>
    <div class="cover-right">
      <p>2026年 第{issue_no}期 &nbsp;·&nbsp; 总第{total_no}期</p>
      <p>{date_cn}</p>
    </div>
  </div>
</div>

<div class="running-header">
  <span>创新政策·对标快讯</span>
  <span>2026年第{issue_no}期</span>
</div>

<div class="content">
  {overview_block}

  {trends_html}

  {suggestions_html}

  {page_break}

  {sections_html}
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

    output_pdf = Path.home() / "Desktop/创新情报/周报/创新政策·对标快讯_周报_20260706.pdf"
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    result = html_to_pdf(html, output_pdf)
    print(f"PDF 已生成: {result}")
    print(f"期号: 2026年第{issue}期 / 总第{total}期")


if __name__ == "__main__":
    main()
