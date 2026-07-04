#!/usr/bin/env python3
"""
《常州创新·对标快讯》周报/月报编译脚本
用法: python3 compile_report.py --type weekly
      python3 compile_report.py --type monthly
"""
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

PROJECT_DIR = Path(__file__).parent.parent
DAILY_DIR = PROJECT_DIR / "daily"
WEEKLY_DIR = PROJECT_DIR / "weekly"
MONTHLY_DIR = PROJECT_DIR / "monthly"


def get_week_range():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


def get_month_range():
    today = datetime.now()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return first_day, last_day


def extract_section(content: str, section_name: str) -> list:
    """从日报中提取指定板块的所有条目"""
    pattern = rf'## 【{section_name}】(.*?)(?=## \[|$)'
    matches = re.findall(pattern, content, re.DOTALL)
    items = []
    for match in matches:
        entries = re.findall(r'► \*\*(.+?)\*\*\n(.+?)\n｜创新洞察：(.*?)\n｜信息来源：(.*?)(?:\n|$)', match, re.DOTALL)
        for title, summary, insight, source in entries:
            items.append({
                'title': title.strip(),
                'summary': summary.strip(),
                'insight': insight.strip(),
                'source': source.strip(),
            })
    return items


def extract_all_entries(daily_files: list) -> dict:
    """从所有日报文件中提取四个维度的条目"""
    all_entries = {
        '各地科技委动态': [],
        '上海（长三角）国创中心资讯': [],
        '科创政策速览': [],
        '改革举措': [],
    }
    for f in sorted(daily_files):
        try:
            content = f.read_text(encoding='utf-8')
            for section in all_entries:
                all_entries[section].extend(extract_section(content, section))
        except Exception as e:
            print(f'[警告] 读取 {f} 失败: {e}')
    return all_entries


def extract_keywords(text: str, top_n: int = 15) -> list:
    words = re.findall(r'[一-鿿]{2,4}', text)
    counter = Counter(words)
    stopwords = {'可以', '一个', '这个', '我们', '他们', '什么', '没有', '就是', '不是',
                 '进行', '通过', '对于', '以及', '这些', '那些', '为了', '因为', '所以',
                 '因此', '如果', '目前', '已经', '其中', '关于', '同时', '主要'}
    for sw in stopwords:
        counter.pop(sw, None)
    return [word for word, _ in counter.most_common(top_n)]


def compile_weekly():
    monday, friday = get_week_range()
    today = datetime.now()
    end_date = min(friday, today)

    daily_files = list(DAILY_DIR.glob('*.md'))
    daily_files = [f for f in daily_files
                   if monday.strftime('%Y-%m-%d') <= f.stem[-10:] <= end_date.strftime('%Y-%m-%d')]

    if not daily_files:
        print(f'[警告] 本周未找到日报，无法生成周报')
        return None

    all_entries = extract_all_entries(daily_files)
    total_items = sum(len(v) for v in all_entries.values())

    # 收集全文用于关键词提取
    full_text = ''
    for f in sorted(daily_files):
        try:
            full_text += f.read_text(encoding='utf-8') + '\n'
        except:
            pass
    hot_keywords = extract_keywords(full_text)

    week_str = f'{monday.strftime("%Y.%m.%d")} - {end_date.strftime("%Y.%m.%d")}'
    today_str = today.strftime('%Y年%m月%d日')

    # 取每个板块最重要的条目（去重，每板块最多5条）
    report_sections = ''
    for section_name in ['各地科技委动态', '上海（长三角）国创中心资讯', '科创政策速览', '改革举措']:
        items = all_entries[section_name]
        seen = set()
        unique_items = []
        for item in items:
            if item['title'] not in seen:
                seen.add(item['title'])
                unique_items.append(item)
        top_items = unique_items[:5]

        report_sections += f'\n## 【{section_name}】\n\n'
        for item in top_items:
            report_sections += f'► **{item["title"]}**\n{item["summary"]}\n'
            report_sections += f'｜创新洞察：{item["insight"]}\n'
            report_sections += f'｜信息来源：{item["source"]}\n\n'
        if not top_items:
            report_sections += '（本周暂无）\n\n'

    report = f'''# 常州创新·对标快讯 周报
**2026年第X期·总第X期**
**{week_str}**
**生成时间：{today_str}**

---

## 本周热点关键词
{', '.join([f'**{kw}**' for kw in hot_keywords])}

---

## 本周综述

本周共收录情报 **{total_items}** 条，覆盖京津冀、长三角、粤港澳大湾区等城市群及29座GDP万亿城市。以下为各板块关键动态：

{report_sections}

---

## 本周重点关注

本周值得常州特别关注的3-5个要点（根据情报频次和战略相关性筛选）：

1. **（重点1）**
2. **（重点2）**
3. **（重点3）**

---

## 趋势研判

基于本周情报，初步研判：

- **政策方向**：
- **产业动向**：
- **改革信号**：

---

> 本快讯由AI自动采集生成 | 数据来源：anysearch 实时搜索
> 重点关注城市群：京津冀 · 长三角 · 粤港澳大湾区 | 29座GDP万亿城市
'''
    weekly_file = WEEKLY_DIR / f'常州创新·对标快讯_周报_{week_str}.md'
    weekly_file.parent.mkdir(parents=True, exist_ok=True)
    weekly_file.write_text(report, encoding='utf-8')
    print(f'[完成] 周报已生成: {weekly_file} (共{total_items}条情报)')
    return weekly_file


def compile_monthly():
    first_day, last_day = get_month_range()
    today = datetime.now()
    end_date = min(last_day, today)

    weekly_files = list(WEEKLY_DIR.glob('*.md'))
    weekly_files = [f for f in weekly_files
                    if first_day.strftime('%Y-%m') in f.stem or first_day.strftime('%Y') in f.stem]

    if not weekly_files:
        print(f'[警告] 本月未找到周报，无法生成月报')
        return None

    all_content = ''
    all_entries = {'各地科技委动态': [], '上海（长三角）国创中心资讯': [],
                   '科创政策速览': [], '改革举措': []}

    for f in sorted(weekly_files):
        try:
            content = f.read_text(encoding='utf-8')
            all_content += content + '\n'
            for section in all_entries:
                all_entries[section].extend(extract_section(content, section))
        except:
            pass

    hot_keywords = extract_keywords(all_content, top_n=20)
    total_items = sum(len(v) for v in all_entries.values())

    month_str = f'{first_day.strftime("%Y年%m月")}'

    # 每个板块取TOP3趋势
    trends = ''
    for section_name in ['各地科技委动态', '上海（长三角）国创中心资讯', '科创政策速览', '改革举措']:
        items = all_entries[section_name]
        insights = [item['insight'] for item in items]
        combined = ' '.join(insights)
        section_keywords = extract_keywords(combined, top_n=5)

        trends += f'\n### {section_name}\n'
        trends += f'本月共收录 {len(items)} 条 | 关键词：{", ".join(section_keywords)}\n'
        trends += f'主要趋势：（待填充）\n'

    report = f'''# 常州创新·对标快讯 月报
**{month_str}**
**生成时间：{today.strftime("%Y年%m月%d日")}**

---

## 月度关键词云
{', '.join([f'**{kw}**' for kw in hot_keywords])}

---

## 月度态势总览

本月累计收录情报 **{total_items}** 条，覆盖四大维度。
周报数量：{len(weekly_files)} 份。

---

## 各板块趋势

{trends}

---

## 月度战略建议

基于本月情报整体态势分析：

### 机遇窗口
1. （本月出现的政策机遇、合作机会）
2.
3.

### 风险提示
1. （需关注的政策变化、竞争态势）
2.

### 建议行动
1. （面向常州的可行建议）
2.
3.

---

## 各周报摘要

'''
    for f in sorted(weekly_files):
        try:
            content = f.read_text(encoding='utf-8')
            # 只取摘要部分
            first_part = content[:1500]
            report += f'### {f.stem}\n\n{first_part}\n\n---\n\n'
        except:
            pass

    report += '''
> 本快讯由AI自动采集生成 | 数据来源：anysearch 实时搜索
> 重点关注城市群：京津冀 · 长三角 · 粤港澳大湾区 | 29座GDP万亿城市
'''
    monthly_file = MONTHLY_DIR / f'常州创新·对标快讯_月报_{month_str}.md'
    monthly_file.parent.mkdir(parents=True, exist_ok=True)
    monthly_file.write_text(report, encoding='utf-8')
    print(f'[完成] 月报已生成: {monthly_file} (共{total_items}条情报, {len(weekly_files)}份周报)')
    return monthly_file


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='编译《常州创新·对标快讯》周报/月报')
    parser.add_argument('--type', choices=['weekly', 'monthly'], required=True)
    args = parser.parse_args()

    if args.type == 'weekly':
        report_file = compile_weekly()
    else:
        report_file = compile_monthly()

    if report_file:
        # 自动分发
        sys.path.insert(0, str(SCRIPT_DIR))
        from distribute import distribute
        distribute(str(report_file), args.type)
