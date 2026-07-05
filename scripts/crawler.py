#!/usr/bin/env python3
"""
创新常州·对标快讯 —— 真实信源采集模块
直接从 .gov.cn 等权威网站抓取最新政务信息，杜绝 AI 虚构内容。

采集策略：
  1. 抓取各大部委/省市 .gov.cn 官网的新闻列表页
  2. 提取标题、日期、摘要、链接
  3. 按4大维度分类归档（关键词匹配）
  4. 去重、时效过滤

🆕 搜索经验固化（2026.7.5）：
  - 政府网站信息按"业务实义词"组织，不按抽象分类标签。搜"概念验证中心"
    比搜"管理办法"命中率高得多。
  - 必须按"城市名 × 业务实义词"逐个交叉搜索，不得笼统搜"万亿城市"。
  - 业务实义词轮换清单（每次 crawl 至少覆盖6个）：
    成果转化平台、概念验证中心、赋权改革、职务科技成果、算力创新券、
    科技保险、先投后股、揭榜挂帅、AI科研、科学智能、研发计划
  - 上海信息来源不能只靠 stcsm.sh.gov.cn，必须同时爬 shanghai.gov.cn
    新闻页、js.gov.cn 长三角专题。

用法:
    from crawler import crawl_all, SourceItem
    items = crawl_all(days_back=7)
"""

import re
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import OrderedDict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

PROJECT_DIR = Path(__file__).parent.parent
CACHE_DIR = PROJECT_DIR / "cache" / "crawler"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ══════════════════════════════════════════════════════════════
# 信源配置：每个信源的列表页 URL 和解析规则
# ══════════════════════════════════════════════════════════════

SOURCE_CONFIGS = [
    # ── 国家级 ──
    {
        "name": "科技部",
        "domain": "most.gov.cn",
        "score": 100,
        "urls": [
            "https://www.most.gov.cn/kjbgz/",  # 科技部工作
            "https://www.most.gov.cn/tpxw/",    # 图片新闻（通常含重要政策）
        ],
        "list_selector": "ul.list li, div.news_list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time, em",
        "date_format": None,  # auto-detect
    },
    {
        "name": "工信部",
        "domain": "miit.gov.cn",
        "score": 100,
        "urls": [
            "https://www.miit.gov.cn/xwdt/gxdt/",
            "https://www.miit.gov.cn/zwgk/zcwj/",
        ],
        "list_selector": "ul.list li, .news-list li, .clist li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "发改委",
        "domain": "ndrc.gov.cn",
        "score": 100,
        "urls": [
            "https://www.ndrc.gov.cn/xwdt/xwfb/",
            "https://www.ndrc.gov.cn/fzggw/jgsj/jgdw/",
        ],
        "list_selector": "ul.list li, .u-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    # ── 省级 ──
    {
        "name": "江苏省科技厅",
        "domain": "kxjst.jiangsu.gov.cn",
        "score": 100,
        "urls": [
            "http://kxjst.jiangsu.gov.cn/col/col82535/index.html",  # 通知公告
            "http://kxjst.jiangsu.gov.cn/col/col82536/index.html",  # 科技动态
        ],
        "list_selector": "ul.list li, .news_list li, .default_pgContainer li",
        "title_selector": "a",
        "date_selector": "span.date, span.time, span.right",
        "date_format": None,
    },
    {
        "name": "上海市科委",
        "domain": "stcsm.sh.gov.cn",
        "score": 100,
        "urls": [
            "https://stcsm.sh.gov.cn/zwgk/kjzj/",
            "https://stcsm.sh.gov.cn/zwgk/gsgg/",
            "https://stcsm.sh.gov.cn/zwgk/kjzc/",     # 🆕 科技政策
        ],
        "list_selector": "ul.list li, .news-list li, .zwgk_list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "浙江省科技厅",
        "domain": "kjt.zj.gov.cn",
        "score": 100,
        "urls": [
            "https://kjt.zj.gov.cn/col/col1228971339/index.html",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "广东省科技厅",
        "domain": "gdstc.gd.gov.cn",
        "score": 100,
        "urls": [
            "http://gdstc.gd.gov.cn/zwgk_n/tzgg/",
            "http://gdstc.gd.gov.cn/kjzx_n/kjyw/",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    # ── 市级 ──
    {
        "name": "常州市人民政府",
        "domain": "changzhou.gov.cn",
        "score": 100,
        "urls": [
            "http://www.changzhou.gov.cn/ns_class/zxzx",
            "http://www.changzhou.gov.cn/ns_class/bmdt",
        ],
        "list_selector": "ul.list li, .news_list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "苏州市人民政府",
        "domain": "suzhou.gov.cn",
        "score": 100,
        "urls": [
            "https://www.suzhou.gov.cn/szxxgk/",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "上海市人民政府",
        "domain": "shanghai.gov.cn",
        "score": 100,
        "urls": [
            "https://www.shanghai.gov.cn/nw12344/index.html",
        ],
        "list_selector": "ul.list li, .news-list li, .list_right li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "北京市人民政府",
        "domain": "beijing.gov.cn",
        "score": 100,
        "urls": [
            "https://www.beijing.gov.cn/xwzx_20031/bmdt/",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "深圳市人民政府",
        "domain": "shenzhen.gov.cn",
        "score": 100,
        "urls": [
            "https://www.shenzhen.gov.cn/zwgk/zfxxgk/zfxxgkml/",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    # ── 更多国家级 ──
    {
        "name": "国家知识产权局",
        "domain": "cnipa.gov.cn",
        "score": 100,
        "urls": [
            "https://www.cnipa.gov.cn/col/col74/index.html",
            "https://www.cnipa.gov.cn/col/col75/index.html",
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    # ── 更多市级（万亿城市）──
    {
        "name": "南京市人民政府",
        "domain": "nanjing.gov.cn",
        "score": 100,
        "urls": [
            "https://www.nanjing.gov.cn/xxgk/bmxt/",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "武汉市人民政府",
        "domain": "wuhan.gov.cn",
        "score": 100,
        "urls": [
            "https://www.wuhan.gov.cn/sy/whyw/",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "武汉市科技局",
        "domain": "wuhan.gov.cn",
        "score": 100,
        "urls": [
            "http://kjj.wuhan.gov.cn/zwgk/tzgg/",  # 通知公告（科技政策集中发布）
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "合肥市人民政府",
        "domain": "hefei.gov.cn",
        "score": 100,
        "urls": [
            "https://www.hefei.gov.cn/xwzx/",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "无锡市人民政府",
        "domain": "wuxi.gov.cn",
        "score": 100,
        "urls": [
            "https://www.wuxi.gov.cn/doc/2022/01/04/index.shtml",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "南通市人民政府",
        "domain": "nantong.gov.cn",
        "score": 100,
        "urls": [
            "https://www.nantong.gov.cn/ntsrmzf/xxgk/xxgk.html",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    # ── 权威平台（85分）─
    {
        "name": "中科院",
        "domain": "cas.cn",
        "score": 85,
        "urls": [
            "https://www.cas.cn/yw/",
            "https://www.cas.cn/ky/",
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "中国工程院",
        "domain": "cae.cn",
        "score": 85,
        "urls": [
            "https://www.cae.cn/cae/html/main/col1/column_1_1.html",
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "科技日报",
        "domain": "stdaily.com",
        "score": 85,
        "urls": [
            "http://www.stdaily.com/index/hotlist/index.html",
        ],
        "list_selector": "ul.list li, .news-list li, .item",
        "title_selector": "a",
        "date_selector": "span.date, span.time, .time",
        "date_format": None,
    },
    {
        "name": "中国科技网",
        "domain": "wokeji.com",
        "score": 85,
        "urls": [
            "https://www.wokeji.com/xwzx/",
        ],
        "list_selector": "ul.list li, .news-list li, .item",
        "title_selector": "a",
        "date_selector": "span.date, span.time, .time",
        "date_format": None,
    },
    # ── 万亿城市·科技局/科创委政策页（100分，核心政策来源）──
    {
        "name": "苏州市科技局",
        "domain": "suzhou.gov.cn",
        "score": 100,
        "urls": [
            "http://kjj.suzhou.gov.cn/col/col16205/index.html",  # 通知公告
            "http://kjj.suzhou.gov.cn/col/col16206/index.html",  # 政策文件
        ],
        "list_selector": "ul.list li, .news_list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "深圳市科创局",
        "domain": "sz.gov.cn",
        "score": 100,
        "urls": [
            "https://stic.sz.gov.cn/xxgk/tzgg/",  # 通知公告
            "https://stic.sz.gov.cn/xxgk/zcfgj/",  # 政策文件
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "杭州市科技局",
        "domain": "hangzhou.gov.cn",
        "score": 100,
        "urls": [
            "https://kj.hangzhou.gov.cn/col/col1229558583/index.html",  # 通知公告
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "成都市科技局",
        "domain": "chengdu.gov.cn",
        "score": 100,
        "urls": [
            "https://cdst.chengdu.gov.cn/cdst/zwgg/zwgg.shtml",  # 政务公告
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "宁波市科技局",
        "domain": "ningbo.gov.cn",
        "score": 100,
        "urls": [
            "https://kjj.ningbo.gov.cn/col/col1229906766/index.html",  # 通知公告
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "安徽省科技厅",
        "domain": "ah.gov.cn",
        "score": 100,
        "urls": [
            "https://kjt.ah.gov.cn/kjzx/tzgg/",  # 通知公告（覆盖合肥等安徽城市）
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "山东省科技厅",
        "domain": "shandong.gov.cn",
        "score": 100,
        "urls": [
            "http://kjt.shandong.gov.cn/col/col94187/index.html",  # 通知公告（覆盖济南/青岛等）
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "陕西省科技厅",
        "domain": "shaanxi.gov.cn",
        "score": 100,
        "urls": [
            "https://kjt.shaanxi.gov.cn/col/col261184/index.html",  # 通知公告（覆盖西安）
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    # ── 省级发改委/工信厅（100分，政策发布主渠道）──
    {
        "name": "江苏省发改委",
        "domain": "jiangsu.gov.cn",
        "score": 100,
        "urls": [
            "http://fzggw.jiangsu.gov.cn/col/col83748/index.html",  # 通知公告
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    {
        "name": "江苏省工信厅",
        "domain": "jiangsu.gov.cn",
        "score": 100,
        "urls": [
            "http://gxt.jiangsu.gov.cn/col/col6279/index.html",  # 通知公告
        ],
        "list_selector": "ul.list li, .news-list li, .list_main li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
    # ── 权威平台补充（85分）──
    {
        "name": "科技日报·政策解读",
        "domain": "stdaily.com",
        "score": 85,
        "urls": [
            "http://www.stdaily.com/index/keji/keji.shtml",  # 科技频道
        ],
        "list_selector": "ul.list li, .news-list li, .item, .list_con li",
        "title_selector": "a",
        "date_selector": "span.date, span.time, .time",
        "date_format": None,
    },
    {
        "name": "经济参考报",
        "domain": "jjckb.cn",
        "score": 70,
        "urls": [
            "https://www.jjckb.cn/",  # 科技财经政策报道
        ],
        "list_selector": "ul.list li, .news-list li, .item",
        "title_selector": "a",
        "date_selector": "span.date, span.time, .time",
        "date_format": None,
    },
    # ── 媒体智库（70分）──
    {
        "name": "新华网",
        "domain": "xinhuanet.com",
        "score": 70,
        "urls": [
            "https://www.xinhuanet.com/tech/",
        ],
        "list_selector": "ul.list li, .news-list li, .item",
        "title_selector": "a",
        "date_selector": "span.date, span.time, .time",
        "date_format": None,
    },
    {
        "name": "中国信通院",
        "domain": "caict.ac.cn",
        "score": 70,
        "urls": [
            "http://www.caict.ac.cn/xwdt/",
        ],
        "list_selector": "ul.list li, .news-list li",
        "title_selector": "a",
        "date_selector": "span.date, span.time",
        "date_format": None,
    },
]


class SourceItem:
    """标准化情报条目"""
    def __init__(self, title="", url="", date_str="", summary="",
                 source="", domain="", score=0, dimension=None,
                 event_date=""):
        self.title = title
        self.url = url
        self.date_str = date_str        # 网页发布日期
        self.summary = summary
        self.source = source
        self.domain = domain
        self.score = score
        self.dimension = dimension
        self.content = ""               # 全文（可选，抓取后填充）
        self.event_date = event_date    # 活动/事件实际日期（从正文提取）

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "date": self.date_str,
            "event_date": self.event_date,
            "summary": self.summary,
            "source": self.source,
            "domain": self.domain,
            "score": self.score,
            "dimension": self.dimension,
        }

    def fingerprint(self):
        """去重指纹"""
        return hashlib.md5(f"{self.title}{self.url}".encode()).hexdigest()


def _fetch_page(url: str, timeout: int = 15) -> tuple[str, str]:
    """抓取页面，返回 (html, final_url)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout,
                          allow_redirects=True, verify=False)
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text, resp.url
    except requests.RequestException as e:
        print(f"  [抓取失败] {url}: {e}")
        return "", url


def _parse_date(text: str, default: str = "") -> str:
    """从文本中提取日期"""
    if not text:
        return default
    text = text.strip()
    # 常见格式：2026-07-05, 2026/07/05, 2026.07.05, 2026年7月5日
    patterns = [
        r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})",
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                dt = datetime(y, mo, d)
                return dt.strftime("%Y.%m.%d")
            except ValueError:
                pass
    return default


def _parse_list_page(html: str, base_url: str, config: dict,
                     days_back: int) -> list[SourceItem]:
    """解析列表页，提取条目"""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    cutoff = datetime.now() - timedelta(days=days_back)

    # 尝试多种选择器
    selectors = [
        config.get("list_selector", ""),
        "ul.list li", "ul.news_list li", ".list_main li",
        "ul li:has(a)", ".news-item", ".item", "tr:has(td a)",
        "div:has(> a) > span", "li",
    ]

    candidates = []
    for sel in selectors:
        if not sel:
            continue
        try:
            candidates = soup.select(sel)
            if len(candidates) >= 3:
                break
        except Exception:
            continue

    for cand in candidates[:50]:  # 每页最多50条
        try:
            # 提取链接和标题
            link = cand.select_one("a")
            if not link:
                continue
            href = link.get("href", "")
            if not href:
                continue
            title = link.get_text(strip=True)
            if not title or len(title) < 8:
                continue

            # 构造完整 URL
            full_url = urljoin(base_url, href)
            domain = urlparse(full_url).netloc

            # 提取摘要（先提取，后续用于事件日期解析）
            summary_el = cand.select_one("p, .summary, .des, .intro")
            summary = summary_el.get_text(strip=True)[:200] if summary_el else ""

            # 提取日期（从 date 元素 + URL + 摘要中多源提取）
            date_el = None
            for dsel in ["span.date", "span.time", "span.right", "em", ".date", ".time"]:
                try:
                    date_el = cand.select_one(dsel)
                    if date_el:
                        break
                except Exception:
                    continue
            date_text = date_el.get_text(strip=True) if date_el else ""
            date_str = _parse_date(date_text)

            # 若 date 元素无日期，尝试从 URL 路径中提取
            if not date_str:
                # 模式1: /202607/t20260705_xxx 或 /20260705/xxx
                url_m = re.search(r"/(\d{4})(\d{2})/(?:t)?(\d{4})(\d{2})(\d{2})[_.]", full_url)
                if url_m:
                    try:
                        d = datetime(int(url_m.group(1)), int(url_m.group(2)), int(url_m.group(5)))
                        date_str = d.strftime("%Y.%m.%d")
                    except ValueError:
                        pass
                # 模式2: /art/2026/7/2/xxx (江苏省科技厅等)
                if not date_str:
                    url_m = re.search(r"/art/(\d{4})/(\d{1,2})/(\d{1,2})/", full_url)
                    if url_m:
                        try:
                            d = datetime(int(url_m.group(1)), int(url_m.group(2)), int(url_m.group(3)))
                            date_str = d.strftime("%Y.%m.%d")
                        except ValueError:
                            pass
                # 模式3: /2026-07/05/xxx 或 /2026/07/05/xxx
                if not date_str:
                    url_m = re.search(r"/(\d{4})[/-](\d{1,2})[/-](\d{1,2})/", full_url)
                    if url_m:
                        try:
                            d = datetime(int(url_m.group(1)), int(url_m.group(2)), int(url_m.group(3)))
                            date_str = d.strftime("%Y.%m.%d")
                        except ValueError:
                            pass

            # 若仍无日期，尝试从摘要中提取（如"6月30日，省委科技委..."）
            if not date_str and summary:
                date_str = _parse_date(summary)

            # 若仍无日期，尝试从标题中提取
            if not date_str:
                date_str = _parse_date(title)

            # ⛔ 时效过滤：无日期或超出窗口的直接丢弃
            if not date_str:
                continue
            try:
                d = datetime.strptime(date_str, "%Y.%m.%d")
                if d < cutoff:
                    continue
            except ValueError:
                continue  # 无法解析则丢弃

            # 尝试从摘要中提取事件实际日期（不同于网页发布日期）
            event_date = ""
            event_patterns = [
                r"(\d{1,2})月(\d{1,2})日[，,]\s*(?:省委|市委|区委|县委|会议|召开|发布|印发|启动|成立|揭牌|签约|开幕)",
                r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?[，,]\s*(?:省委|市委|会议|召开|发布|印发|启动)",
                r"已于(\d{1,2})月(\d{1,2})日",
                r"于(\d{1,2})月(\d{1,2})日",
                r"(\d{1,2})月(\d{1,2})日",
            ]
            for pat in event_patterns:
                m = re.search(pat, summary) or re.search(pat, title)
                if m:
                    groups = m.groups()
                    if len(groups) == 2:
                        mo, day = int(groups[0]), int(groups[1])
                        year = d.year  # 使用发布日期的年份
                        # 若月份大于当前月份（如当前7月，事件写12月），用上一年
                        if mo > datetime.now().month:
                            year -= 1
                        try:
                            event_dt = datetime(year, mo, day)
                            event_date = event_dt.strftime("%Y.%m.%d")
                        except ValueError:
                            pass
                    elif len(groups) == 3:
                        try:
                            event_dt = datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                            event_date = event_dt.strftime("%Y.%m.%d")
                        except ValueError:
                            pass
                    break

            item = SourceItem(
                title=title,
                url=full_url,
                date_str=date_str,
                summary=summary,
                source=config["name"],
                domain=domain or config.get("domain", ""),
                score=config.get("score", 0),
                event_date=event_date,
            )
            items.append(item)
        except Exception:
            continue

    return items


def _crawl_source(config: dict, days_back: int) -> list[SourceItem]:
    """抓取单个信源"""
    all_items = []
    for url in config.get("urls", []):
        print(f"  [{config['name']}] 抓取: {url}")
        html, final_url = _fetch_page(url)
        if not html:
            continue
        items = _parse_list_page(html, final_url, config, days_back)
        print(f"    → 获取 {len(items)} 条")
        all_items.extend(items)
        time.sleep(0.5)  # 礼貌间隔
    return all_items


def _classify_dimension(item: SourceItem):
    """根据标题/摘要自动归类到4大维度"""
    text = f"{item.title} {item.summary}"

    dim_keywords = {
        "各地科技委动态": ["科技委", "省委科技", "市委科技", "科创委", "科技委员会"],
        "上海（长三角）国创中心资讯": [
            # 机构名/平台名
            "长三角", "G60", "张江", "国创中心", "沿沪宁",
            "国际科技创新中心", "长三角国家技术创新中心",
            # 业务实义词（上海及长三角科创实际高频用语）
            "长三角市场监管", "联合发文", "科创19条", "标准互认",
            "知识产权协同", "人才互通", "跨区域", "一体化",
            "长三角国际标准", "高价值专利", "统一大市场",
            # 对接上海动态
            "对接上海", "融入长三角", "沪苏", "沪浙",
        ],
        "科创政策速览": [
            # 政策类型词
            "政策", "行动计划", "方案", "意见", "措施", "补贴",
            "管理办法", "实施意见", "若干措施", "试点办法",
            # 产业实义词
            "算力", "AIDC", "具身智能", "人形机器人", "氢能",
            "储能", "钙钛矿", "液冷", "AI数据中心", "智算中心",
            "先导产业", "未来产业", "产业规划", "扶持",
            "低空经济", "商业航天", "工业母机",
            # 业务实义词（政策文本中实际出现的高频词）
            "科学智能", "算力创新券", "概念验证", "成果转化平台",
            "赋权改革", "职务科技成果", "先投后股", "揭榜挂帅",
            "研发计划", "孵化器", "创新联合体", "科技型企业",
            # 产业赛道
            "人工智能", "AI赋能", "大模型", "工业软件",
        ],
        "改革举措": [
            # 传统改革关键词
            "改革", "科技成果转化", "先投后股", "科技金融",
            "新型研发机构", "校地合作", "三名工程", "双高协同",
            "科技保险", "投贷联动", "揭榜挂帅", "赋权改革",
            # 新增业务实义词
            "概念验证中心", "中试平台", "职务科技成果",
            "创新券", "算力券", "先使用后付费", "拨投结合",
            "拨改投", "技术托管", "赋权", "成果赋权",
            "科技金融研究", "科技信贷", "知识产权证券化",
        ],
    }

    best_dim = None
    best_score = 0
    for dim, keywords in dim_keywords.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_dim = dim

    item.dimension = best_dim or "科创政策速览"  # 默认归入政策
    return item


def crawl_all(days_back: int = 7, max_per_source: int = 10) -> dict[str, list[SourceItem]]:
    """
    从所有配置的信源抓取最新信息。

    返回: {"各地科技委动态": [...], "上海（长三角）...": [...], ...}
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print(f"[采集] 抓取近 {days_back} 天内信息...")
    print(f"[采集] 共 {len(SOURCE_CONFIGS)} 个信源\n")

    all_items = []
    seen_fps = set()

    for config in SOURCE_CONFIGS:
        items = _crawl_source(config, days_back)
        for item in items:
            fp = item.fingerprint()
            if fp not in seen_fps:
                seen_fps.add(fp)
                _classify_dimension(item)
                all_items.append(item)
        print()

    # 按维度分组
    grouped: dict[str, list[SourceItem]] = OrderedDict()
    dimensions = ["各地科技委动态", "上海（长三角）国创中心资讯", "科创政策速览", "改革举措"]
    for dim in dimensions:
        grouped[dim] = []

    for item in all_items:
        dim = item.dimension or "科创政策速览"
        if dim in grouped:
            grouped[dim].append(item)

    # 每维度按评分排序，限制数量
    for dim in grouped:
        grouped[dim].sort(key=lambda x: (x.score, x.date_str), reverse=True)
        grouped[dim] = grouped[dim][:max_per_source]

    # 统计
    total = sum(len(v) for v in grouped.values())
    print(f"[采集] 完成！共 {total} 条有效信息")
    for dim, items in grouped.items():
        gov_count = sum(1 for it in items if ".gov.cn" in (it.domain or ""))
        print(f"  [{dim}]: {len(items)} 条 (其中 .gov.cn: {gov_count})")

    return grouped


def crawl_to_json(days_back: int = 7) -> dict:
    """抓取并输出为标准化 JSON，供后续 AI 处理"""
    grouped = crawl_all(days_back=days_back)

    sections = []
    for dim_name, items in grouped.items():
        sections.append({
            "name": dim_name,
            "items": [it.to_dict() for it in items],
            "source_count": len(items),
            "gov_count": sum(1 for it in items if ".gov.cn" in (it.domain or "")),
        })

    return {
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "days_back": days_back,
        "total_items": sum(len(v) for v in grouped.values()),
        "sections": sections,
    }


def fetch_supplementary_articles(urls: list[dict]) -> list[SourceItem]:
    """
    从指定 URL 列表抓取文章详情页，补充爬虫无法覆盖的信源。
    用于整合 WebSearch 验证过的真实文章。

    参数:
        urls: [{"url": "...", "source": "科技日报", "score": 85, "dimension": "科创政策速览"}, ...]

    返回: SourceItem 列表
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    items = []
    for entry in urls:
        url = entry.get("url", "")
        if not url:
            continue
        try:
            print(f"  [补充] 抓取: {url[:80]}...")
            html, final_url = _fetch_page(url, timeout=10)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            # 提取标题
            title = ""
            for sel in ["h1", ".article-title", ".news-title", ".content-title", "title"]:
                el = soup.select_one(sel)
                if el:
                    title = el.get_text(strip=True)
                    if len(title) > 5:
                        break

            # 提取日期（从文章正文）
            date_str = ""
            for sel in [".article-date", ".news-date", ".info-date", ".time", ".pub-date",
                       "meta[name='pubdate']", "meta[name='publishdate']"]:
                el = soup.select_one(sel)
                if el:
                    text = el.get("content", "") or el.get_text(strip=True)
                    date_str = _parse_date(text)
                    if date_str:
                        break

            # 从正文提取摘要和事件日期
            body_text = ""
            for sel in ["#content", ".article-content", ".news-content", ".content",
                       "article", ".article", ".TRS_Editor", ".Custom_UnionStyle"]:
                el = soup.select_one(sel)
                if el:
                    body_text = el.get_text(separator="\n", strip=True)[:1000]
                    break
            if not body_text:
                body_text = soup.get_text(separator="\n", strip=True)[:1000]

            summary = body_text[:200] if body_text else ""

            # 提取事件日期
            event_date = ""
            event_patterns = [
                r"(\d{1,2})月(\d{1,2})日[，,、]\s*(?:省委|市委|区委|会议|召开|发布|印发|启动|成立|揭牌|签约|开幕)",
                r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?[，,、]",
                r"已于(\d{1,2})月(\d{1,2})日",
                r"于(\d{1,2})月(\d{1,2})日",
            ]
            now = datetime.now()
            for pat in event_patterns:
                m = re.search(pat, body_text)
                if m:
                    groups = m.groups()
                    if len(groups) == 2:
                        mo, day = int(groups[0]), int(groups[1])
                        year = now.year
                        if mo > now.month:
                            year -= 1
                        try:
                            event_dt = datetime(year, mo, day)
                            event_date = event_dt.strftime("%Y.%m.%d")
                        except ValueError:
                            pass
                    elif len(groups) == 3:
                        try:
                            event_dt = datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                            event_date = event_dt.strftime("%Y.%m.%d")
                        except ValueError:
                            pass
                    break

            if not date_str and event_date:
                date_str = event_date  # 用事件日期作为发布日期
            if not date_str:
                # 从URL提取
                url_m = re.search(r"/(\d{4})(\d{2})/(?:t)?(\d{4})(\d{2})(\d{2})[_.]", url)
                if url_m:
                    try:
                        d = datetime(int(url_m.group(1)), int(url_m.group(2)), int(url_m.group(5)))
                        date_str = d.strftime("%Y.%m.%d")
                    except ValueError:
                        pass
                if not date_str:
                    url_m = re.search(r"/art/(\d{4})/(\d{1,2})/(\d{1,2})/", url)
                    if url_m:
                        try:
                            d = datetime(int(url_m.group(1)), int(url_m.group(2)), int(url_m.group(3)))
                            date_str = d.strftime("%Y.%m.%d")
                        except ValueError:
                            pass
                if not date_str:
                    url_m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
                    if url_m:
                        try:
                            d = datetime(int(url_m.group(1)), int(url_m.group(2)), int(url_m.group(3)))
                            date_str = d.strftime("%Y.%m.%d")
                        except ValueError:
                            pass

            domain = urlparse(url).netloc
            item = SourceItem(
                title=title or entry.get("title", ""),
                url=url,
                date_str=date_str,
                event_date=event_date,
                summary=summary,
                source=entry.get("source", ""),
                domain=domain,
                score=entry.get("score", 70),
                dimension=entry.get("dimension", ""),
            )
            if item.dimension:
                _classify_dimension(item)
            items.append(item)
            time.sleep(0.3)
        except Exception as e:
            print(f"  [补充失败] {url}: {e}")
            continue

    return items


def merge_sources(crawled: dict[str, list[SourceItem]],
                  supplementary: list[SourceItem]) -> dict[str, list[SourceItem]]:
    """合并爬虫结果和补充文章，去重后返回"""
    seen_urls = set()
    for items in crawled.values():
        for it in items:
            seen_urls.add(it.url)

    for item in supplementary:
        if item.url not in seen_urls:
            seen_urls.add(item.url)
            dim = item.dimension or "科创政策速览"
            if dim not in crawled:
                crawled[dim] = []
            crawled[dim].append(item)

    # 按评分排序
    for dim in crawled:
        crawled[dim].sort(key=lambda x: (x.score, x.date_str), reverse=True)

    return crawled


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="政府信源采集")
    parser.add_argument("--days", type=int, default=7, help="采集天数")
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径")
    parser.add_argument("--max", type=int, default=10, help="每维度最大条数")
    args = parser.parse_args()

    result = crawl_to_json(days_back=args.days)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[输出] {out_path}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
