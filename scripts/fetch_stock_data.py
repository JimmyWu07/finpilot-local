# requires: akshare, yfinance
# 全球股票数据采集引擎 - 支持A/港/美/日/欧股多市场数据采集
# 所有A股数据通过akshare采集，确保数据最新
import argparse
import json
import os
import sys
import re
from datetime import datetime, timedelta

# 优先使用coze_workload_identity(Coze运行时), 否则回退标准requests
if os.getenv("COZE_OUTBOUND_AUTH_PROXY"):
    from coze_workload_identity import requests
else:
    import requests

# ============================================================
# Mock 兜底数据
# ============================================================
MOCK_DATA = {
    "600519": {
        "meta": {"stock_code": "600519", "market": "SH", "company_name": "贵州茅台",
                 "fetch_time": "", "data_source": "mock", "is_mock": True},
        "market_data": {
            "daily_prices": [
                {"date": "2025-07-{:02d}".format(d), "open": 1680 + d * 2, "high": 1695 + d * 2,
                 "low": 1670 + d * 2, "close": 1685 + d * 2, "volume": 2500000 + d * 10000}
                for d in range(1, 31)
            ],
            "latest_price": 1745.0, "change_pct": 1.25
        },
        "financials": {
            "annual_reports": [
                {"year": 2024, "revenue": 150500000000, "net_profit": 74700000000,
                 "eps": 59.5, "roe": 0.34, "mock_data_approximate": True},
                {"year": 2023, "revenue": 139400000000, "net_profit": 69300000000,
                 "eps": 55.2, "roe": 0.33, "mock_data_approximate": True},
                {"year": 2022, "revenue": 124100000000, "net_profit": 61700000000,
                 "eps": 49.1, "roe": 0.31, "mock_data_approximate": True}
            ],
            "quarterly_reports": [
                {"quarter": "2025Q1", "revenue": 43500000000, "net_profit": 21800000000,
                 "eps": 17.3, "mock_data_approximate": True},
                {"quarter": "2024Q4", "revenue": 42000000000, "net_profit": 20500000000,
                 "eps": 16.3, "mock_data_approximate": True},
                {"quarter": "2024Q3", "revenue": 33700000000, "net_profit": 16500000000,
                 "eps": 13.1, "mock_data_approximate": True},
                {"quarter": "2024Q2", "revenue": 31800000000, "net_profit": 15700000000,
                 "eps": 12.5, "mock_data_approximate": True}
            ]
        },
        "news_announcements": {
            "policy_news": [
                {"title": "白酒行业消费税政策保持稳定", "source": "新华社",
                 "date": "2025-07-28", "sentiment": "neutral"},
                {"title": "证监会发布上市公司分红新规", "source": "证监会官网",
                 "date": "2025-07-25", "sentiment": "positive"}
            ],
            "industry_news": [
                {"title": "高端白酒市场持续回暖，茅台批价回升", "source": "财新网",
                 "date": "2025-07-29", "sentiment": "positive"},
                {"title": "白酒行业上半年产量同比下降3%", "source": "国家统计局",
                 "date": "2025-07-20", "sentiment": "negative"}
            ],
            "stock_news": [
                {"title": "贵州茅台上半年净利润同比增长8.5%", "source": "公司公告",
                 "date": "2025-07-27", "sentiment": "positive"},
                {"title": "茅台集团加大海外市场布局", "source": "上海证券报",
                 "date": "2025-07-22", "sentiment": "positive"},
                {"title": "贵州茅台获北向资金净买入5.2亿元", "source": "东方财富",
                 "date": "2025-07-18", "sentiment": "positive"}
            ],
            "announcements": [
                {"title": "贵州茅台2024年年度利润分配方案", "source": "上交所",
                 "date": "2025-07-15", "sentiment": "positive"},
                {"title": "贵州茅台关于回购股份进展公告", "source": "上交所",
                 "date": "2025-07-10", "sentiment": "neutral"}
            ]
        }
    },
    "000001": {
        "meta": {"stock_code": "000001", "market": "SZ", "company_name": "平安银行",
                 "fetch_time": "", "data_source": "mock", "is_mock": True},
        "market_data": {
            "daily_prices": [
                {"date": "2025-07-{:02d}".format(d), "open": 11.5 + d * 0.02,
                 "high": 11.7 + d * 0.02, "low": 11.4 + d * 0.02,
                 "close": 11.6 + d * 0.02, "volume": 45000000 + d * 500000}
                for d in range(1, 31)
            ],
            "latest_price": 12.2, "change_pct": 0.82
        },
        "financials": {
            "annual_reports": [
                {"year": 2024, "revenue": 165000000000, "net_profit": 46200000000,
                 "eps": 2.18, "roe": 0.12, "mock_data_approximate": True},
                {"year": 2023, "revenue": 160500000000, "net_profit": 44800000000,
                 "eps": 2.11, "roe": 0.11, "mock_data_approximate": True},
                {"year": 2022, "revenue": 158200000000, "net_profit": 42700000000,
                 "eps": 2.01, "roe": 0.11, "mock_data_approximate": True}
            ],
            "quarterly_reports": [
                {"quarter": "2025Q1", "revenue": 42800000000, "net_profit": 12500000000,
                 "eps": 0.59, "mock_data_approximate": True},
                {"quarter": "2024Q4", "revenue": 41000000000, "net_profit": 11200000000,
                 "eps": 0.53, "mock_data_approximate": True},
                {"quarter": "2024Q3", "revenue": 40500000000, "net_profit": 11800000000,
                 "eps": 0.56, "mock_data_approximate": True},
                {"quarter": "2024Q2", "revenue": 40700000000, "net_profit": 11500000000,
                 "eps": 0.54, "mock_data_approximate": True}
            ]
        },
        "news_announcements": {
            "policy_news": [
                {"title": "央行下调LPR利率10个基点", "source": "中国人民银行",
                 "date": "2025-07-28", "sentiment": "positive"},
                {"title": "银保监会加强银行业风险管理", "source": "银保监会",
                 "date": "2025-07-22", "sentiment": "neutral"}
            ],
            "industry_news": [
                {"title": "银行业上半年净利润同比增长3.2%", "source": "银保监会",
                 "date": "2025-07-26", "sentiment": "positive"},
                {"title": "商业银行不良贷款率降至1.56%", "source": "金融时报",
                 "date": "2025-07-20", "sentiment": "positive"}
            ],
            "stock_news": [
                {"title": "平安银行零售转型成效显著", "source": "证券时报",
                 "date": "2025-07-27", "sentiment": "positive"},
                {"title": "平安银行发行500亿元金融债", "source": "上交所",
                 "date": "2025-07-23", "sentiment": "neutral"},
                {"title": "平安银行获外资机构上调评级", "source": "路透社",
                 "date": "2025-07-19", "sentiment": "positive"}
            ],
            "announcements": [
                {"title": "平安银行2024年度利润分配预案", "source": "深交所",
                 "date": "2025-07-14", "sentiment": "positive"},
                {"title": "平安银行关于关联交易公告", "source": "深交所",
                 "date": "2025-07-08", "sentiment": "neutral"}
            ]
        }
    },
    "000858": {
        "meta": {"stock_code": "000858", "market": "SZ", "company_name": "五粮液",
                 "fetch_time": "", "data_source": "mock", "is_mock": True},
        "market_data": {
            "daily_prices": [
                {"date": "2025-07-{:02d}".format(d), "open": 138 + d * 0.5,
                 "high": 140 + d * 0.5, "low": 136 + d * 0.5,
                 "close": 139 + d * 0.5, "volume": 8000000 + d * 100000}
                for d in range(1, 31)
            ],
            "latest_price": 154.0, "change_pct": 1.05
        },
        "financials": {
            "annual_reports": [
                {"year": 2024, "revenue": 84200000000, "net_profit": 31800000000,
                 "eps": 8.2, "roe": 0.25, "mock_data_approximate": True},
                {"year": 2023, "revenue": 78900000000, "net_profit": 29500000000,
                 "eps": 7.6, "roe": 0.24, "mock_data_approximate": True},
                {"year": 2022, "revenue": 71400000000, "net_profit": 26700000000,
                 "eps": 6.9, "roe": 0.22, "mock_data_approximate": True}
            ],
            "quarterly_reports": [
                {"quarter": "2025Q1", "revenue": 23500000000, "net_profit": 9200000000,
                 "eps": 2.37, "mock_data_approximate": True},
                {"quarter": "2024Q4", "revenue": 21000000000, "net_profit": 7800000000,
                 "eps": 2.01, "mock_data_approximate": True},
                {"quarter": "2024Q3", "revenue": 19800000000, "net_profit": 7400000000,
                 "eps": 1.91, "mock_data_approximate": True},
                {"quarter": "2024Q2", "revenue": 18500000000, "net_profit": 7000000000,
                 "eps": 1.81, "mock_data_approximate": True}
            ]
        },
        "news_announcements": {
            "policy_news": [
                {"title": "白酒行业消费税改革方案征求意见", "source": "财政部",
                 "date": "2025-07-27", "sentiment": "neutral"},
                {"title": "消费促进政策持续加码", "source": "国务院",
                 "date": "2025-07-21", "sentiment": "positive"}
            ],
            "industry_news": [
                {"title": "浓香型白酒市场份额稳步提升", "source": "中国酒业协会",
                 "date": "2025-07-25", "sentiment": "positive"},
                {"title": "白酒出口额同比增长15%", "source": "海关总署",
                 "date": "2025-07-19", "sentiment": "positive"}
            ],
            "stock_news": [
                {"title": "五粮液经典第八代升级版上市", "source": "公司官网",
                 "date": "2025-07-26", "sentiment": "positive"},
                {"title": "五粮液上半年营收同比增长12%", "source": "四川日报",
                 "date": "2025-07-22", "sentiment": "positive"},
                {"title": "五粮液渠道改革持续推进", "source": "每日经济新闻",
                 "date": "2025-07-17", "sentiment": "neutral"}
            ],
            "announcements": [
                {"title": "五粮液2024年度利润分配实施公告", "source": "深交所",
                 "date": "2025-07-13", "sentiment": "positive"},
                {"title": "五粮液关于控股股东增持计划公告", "source": "深交所",
                 "date": "2025-07-07", "sentiment": "positive"}
            ]
        }
    }
}


# ============================================================
# 市场自动识别
# ============================================================
def detect_market(stock_code):
    """根据股票代码前缀判断所属市场"""
    code = stock_code.strip().upper()
    if code.endswith(".T"):
        return "JP"
    if code.isdigit():
        first = code[0] if code else ""
        if first in ("6", "9"):
            return "SH"
        if first in ("0", "3"):
            return "SZ"
        if first == "8":
            return "BJ"
        if len(code) <= 5:
            return "HK"
        return "SH"
    if code.isalpha() and len(code) <= 5:
        return "US"
    return "EU"


def get_yf_ticker(stock_code, market):
    """转换为yfinance可用的ticker代码"""
    if market == "HK":
        return stock_code.zfill(4) + ".HK"
    if market == "JP":
        return stock_code
    if market in ("US", "EU"):
        return stock_code
    return stock_code


# ============================================================
# A股数据采集 (akshare) - 全部使用akshare确保数据最新
# ============================================================
def fetch_a_share_price(stock_code):
    """采集A股日线行情 - akshare stock_zh_a_hist"""
    try:
        import akshare as ak
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                start_date=start, end_date=end, adjust="qfq")
        if df is None or df.empty:
            print(f"[WARN] akshare行情返回空数据({stock_code})")
            return None
        prices = []
        for _, row in df.tail(30).iterrows():
            prices.append({
                "date": str(row.get("日期", "")),
                "open": float(row.get("开盘", 0)),
                "high": float(row.get("最高", 0)),
                "low": float(row.get("最低", 0)),
                "close": float(row.get("收盘", 0)),
                "volume": int(row.get("成交量", 0))
            })
        if not prices:
            return None
        latest = prices[-1]
        prev_close = prices[-2]["close"] if len(prices) >= 2 else latest.get("close", 0)
        change_pct = ((latest.get("close", 0) - prev_close) / prev_close * 100) if prev_close else 0
        print(f"[INFO] akshare行情采集成功({stock_code}): {len(prices)}条, 最新{latest.get('date')} 收盘{latest.get('close')}")
        return {"daily_prices": prices, "latest_price": latest.get("close", 0),
                "change_pct": round(change_pct, 2)}
    except Exception as e:
        print(f"[WARN] akshare行情采集失败({stock_code}): {e}")
        return None


def fetch_a_share_financials(stock_code):
    """采集A股财务摘要 - akshare stock_financial_abstract"""
    try:
        import akshare as ak
        df = ak.stock_financial_abstract(symbol=stock_code)
        if df is None or df.empty:
            print(f"[WARN] akshare财务返回空数据({stock_code})")
            return None
        # 提取日期列(格式如20251231)
        date_cols = [c for c in df.columns if str(c).isdigit() and len(str(c)) == 8]
        date_cols.sort(reverse=True)
        if not date_cols:
            return None
        # 构建指标映射
        indicator_map = {}
        for _, row in df.iterrows():
            name = str(row.get("指标", ""))
            if name in ("归母净利润", "营业总收入", "基本每股收益"):
                indicator_map[name] = {c: row.get(c, 0) for c in date_cols}
        annual, quarterly = [], []
        for col in date_cols[:12]:
            year_str, month_str = col[:4], col[4:6]
            revenue = float(indicator_map.get("营业总收入", {}).get(col, 0) or 0)
            net_profit = float(indicator_map.get("归母净利润", {}).get(col, 0) or 0)
            eps = float(indicator_map.get("基本每股收益", {}).get(col, 0) or 0)
            report = {"revenue": revenue, "net_profit": net_profit, "eps": eps}
            if month_str == "12":
                report["year"] = int(year_str)
                annual.append(report)
            else:
                q = {"03": "Q1", "06": "Q2", "09": "Q3"}.get(month_str, "")
                report["quarter"] = f"{year_str}{q}"
                quarterly.append(report)
        print(f"[INFO] akshare财务采集成功({stock_code}): 年报{len(annual)}份, 季报{len(quarterly)}份, 最新{date_cols[0]}")
        return {"annual_reports": annual[:3], "quarterly_reports": quarterly[:4]}
    except Exception as e:
        print(f"[WARN] akshare财务采集失败({stock_code}): {e}")
        return None


def fetch_a_share_announcements(stock_code):
    """采集A股公告 - akshare stock_notice_report
    遍历最近7天确保获取到公告数据
    """
    try:
        import akshare as ak
        announcements = []
        # 遍历最近7天，确保获取到公告
        for days_ago in range(7):
            target_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
            try:
                df = ak.stock_notice_report(symbol="全部", date=target_date)
                if df is not None and not df.empty:
                    filtered = df[df["代码"].astype(str).str.strip() == stock_code]
                    for _, row in filtered.iterrows():
                        announcements.append({
                            "title": str(row.get("公告标题", "")),
                            "source": str(row.get("名称", "交易所")),
                            "date": str(row.get("公告日期", target_date)),
                            "sentiment": "neutral"
                        })
                    if announcements:
                        break
            except Exception:
                continue
        # 去重
        seen = set()
        unique_announcements = []
        for a in announcements:
            key = a["title"] + a["date"]
            if key not in seen:
                seen.add(key)
                unique_announcements.append(a)
        print(f"[INFO] akshare公告采集成功({stock_code}): {len(unique_announcements)}条")
        return unique_announcements[:15]
    except Exception as e:
        print(f"[WARN] akshare公告采集失败({stock_code}): {e}")
        return []


def fetch_a_share_news(stock_code, company_name=""):
    """采集个股新闻 - akshare stock_news_em (东方财富个股新闻)"""
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol=stock_code)
        if df is None or df.empty:
            print(f"[WARN] akshare个股新闻返回空({stock_code})")
            return []
        news_list = []
        for _, row in df.head(20).iterrows():
            news_list.append({
                "title": str(row.get("新闻标题", "")),
                "content": str(row.get("新闻内容", ""))[:200],
                "source": str(row.get("文章来源", "东方财富")),
                "date": str(row.get("发布时间", "")),
                "url": str(row.get("新闻链接", "")),
                "sentiment": "neutral"
            })
        print(f"[INFO] akshare个股新闻采集成功({stock_code}): {len(news_list)}条")
        return news_list
    except Exception as e:
        print(f"[WARN] akshare个股新闻采集失败({stock_code}): {e}")
        return []


def fetch_policy_news():
    """采集宏观政策新闻 - akshare news_cctv (央视新闻)"""
    try:
        import akshare as ak
        today = datetime.now().strftime("%Y%m%d")
        df = ak.news_cctv(date=today)
        if df is None or df.empty:
            # 尝试前一天
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            df = ak.news_cctv(date=yesterday)
        if df is None or df.empty:
            return []
        news_list = []
        for _, row in df.head(10).iterrows():
            news_list.append({
                "title": str(row.get("title", "")),
                "content": str(row.get("content", ""))[:200],
                "source": "央视新闻",
                "date": str(row.get("date", "")),
                "sentiment": "neutral"
            })
        print(f"[INFO] akshare政策新闻采集成功: {len(news_list)}条")
        return news_list
    except Exception as e:
        print(f"[WARN] akshare政策新闻采集失败: {e}")
        return []


def fetch_global_news():
    """采集全球财经快讯 - akshare stock_info_global_em"""
    try:
        import akshare as ak
        df = ak.stock_info_global_em()
        if df is None or df.empty:
            return []
        news_list = []
        for _, row in df.head(15).iterrows():
            title = str(row.get("标题", row.get("title", "")))
            content = str(row.get("内容", row.get("content", "")))
            news_list.append({
                "title": title,
                "content": content[:200] if content else "",
                "source": "东方财富全球快讯",
                "date": str(row.get("发布时间", row.get("date", ""))),
                "sentiment": "neutral"
            })
        print(f"[INFO] akshare全球快讯采集成功: {len(news_list)}条")
        return news_list
    except Exception as e:
        print(f"[WARN] akshare全球快讯采集失败: {e}")
        return []


# ============================================================
# 港美股数据采集 (yfinance)
# ============================================================
def fetch_yf_data(stock_code, market):
    """采集港美股行情 - yfinance"""
    try:
        import yfinance as yf
        ticker = get_yf_ticker(stock_code, market)
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1mo")
        if hist is None or hist.empty:
            return None
        prices = []
        for date, row in hist.iterrows():
            prices.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row.get("Open", 0)), 2),
                "high": round(float(row.get("High", 0)), 2),
                "low": round(float(row.get("Low", 0)), 2),
                "close": round(float(row.get("Close", 0)), 2),
                "volume": int(row.get("Volume", 0))
            })
        latest = prices[-1] if prices else {}
        prev_close = prices[-2]["close"] if len(prices) >= 2 else latest.get("close", 0)
        change_pct = ((latest.get("close", 0) - prev_close) / prev_close * 100) if prev_close else 0
        market_data = {"daily_prices": prices, "latest_price": latest.get("close", 0),
                       "change_pct": round(change_pct, 2)}
        financials = {"annual_reports": [], "quarterly_reports": []}
        try:
            inc = tk.financials
            if inc is not None and not inc.empty:
                for col in inc.columns[:3]:
                    financials["annual_reports"].append({
                        "year": col.year if hasattr(col, "year") else str(col),
                        "revenue": float(inc.loc["Total Revenue", col] if "Total Revenue" in inc.index else 0),
                        "net_profit": float(inc.loc["Net Income", col] if "Net Income" in inc.index else 0),
                    })
        except Exception:
            pass
        print(f"[INFO] yfinance采集成功({stock_code}): {len(prices)}条行情")
        return {"market_data": market_data, "financials": financials}
    except Exception as e:
        print(f"[WARN] yfinance采集失败({stock_code}): {e}")
        return None


# ============================================================
# Mock 数据获取
# ============================================================
def get_mock_data(stock_code):
    """返回Mock兜底数据"""
    mock = MOCK_DATA.get(stock_code)
    if mock:
        result = json.loads(json.dumps(mock))
        result["meta"]["fetch_time"] = datetime.now().isoformat(timespec="seconds")
        return result
    return {
        "meta": {"stock_code": stock_code, "market": detect_market(stock_code),
                 "company_name": stock_code, "fetch_time": datetime.now().isoformat(timespec="seconds"),
                 "data_source": "mock", "is_mock": True},
        "market_data": {"daily_prices": [], "latest_price": 0.0, "change_pct": 0.0},
        "financials": {"annual_reports": [], "quarterly_reports": []},
        "news_announcements": {"policy_news": [], "industry_news": [], "stock_news": [], "announcements": []}
    }


# ============================================================
# 主采集逻辑
# ============================================================
def collect(stock_code, force_refresh=False):
    """统一采集入口，全部使用akshare确保数据最新"""
    market = detect_market(stock_code)
    print(f"[INFO] 股票代码: {stock_code}, 识别市场: {market}")
    sources_used = []
    market_data = None
    financials = None
    announcements = []
    stock_news = []
    policy_news = []
    industry_news = []

    # A股市场: 全部使用akshare
    if market in ("SH", "SZ", "BJ"):
        # 1. 行情数据
        market_data = fetch_a_share_price(stock_code)
        if market_data:
            sources_used.append("akshare")
        else:
            market_data = get_mock_data(stock_code).get("market_data")
            sources_used.append("mock")
        # 2. 财务数据
        financials = fetch_a_share_financials(stock_code)
        if not financials:
            financials = get_mock_data(stock_code).get("financials")
        # 3. 公告数据
        announcements = fetch_a_share_announcements(stock_code)
        # 4. 个股新闻
        stock_news = fetch_a_share_news(stock_code)
        # 5. 政策新闻
        policy_news = fetch_policy_news()
        # 6. 行业/全球新闻
        global_news = fetch_global_news()
        # 简单分类：包含行业关键词的归为industry_news
        industry_keywords = ["行业", "产业", "市场", "景气", "产能", "竞争", "供需", "产业链"]
        for item in global_news:
            title = item.get("title", "")
            if any(kw in title for kw in industry_keywords):
                industry_news.append(item)

    # 港美股: yfinance
    elif market in ("HK", "US", "JP", "EU"):
        yf_result = fetch_yf_data(stock_code, market)
        if yf_result:
            market_data = yf_result["market_data"]
            financials = yf_result["financials"]
            sources_used.append("yfinance")
        else:
            mock = get_mock_data(stock_code)
            market_data = mock["market_data"]
            financials = mock["financials"]
            sources_used.append("mock")

    # 全部失败则使用Mock兜底
    is_mock = not sources_used or all(s == "mock" for s in sources_used)
    if is_mock and market_data is None:
        mock = get_mock_data(stock_code)
        market_data = mock["market_data"]
        financials = mock["financials"]
        sources_used = ["mock"]

    company_name = stock_code
    if stock_code in MOCK_DATA:
        company_name = MOCK_DATA[stock_code]["meta"]["company_name"]

    result = {
        "meta": {
            "stock_code": stock_code,
            "market": market,
            "company_name": company_name,
            "fetch_time": datetime.now().isoformat(timespec="seconds"),
            "data_source": "+".join(sources_used) if sources_used else "mock",
        },
        "market_data": market_data or {"daily_prices": [], "latest_price": 0.0, "change_pct": 0.0},
        "financials": financials or {"annual_reports": [], "quarterly_reports": []},
        "news_announcements": {
            "policy_news": policy_news,
            "industry_news": industry_news,
            "stock_news": stock_news,
            "announcements": announcements
        }
    }
    if is_mock:
        result["meta"]["is_mock"] = True
    return result


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="全球股票数据采集引擎")
    parser.add_argument("--stock_code", required=True, help="股票代码，如600519、AAPL、00700")
    parser.add_argument("--force_refresh", action="store_true", default=False, help="强制刷新数据")
    args = parser.parse_args()
    result = collect(args.stock_code, args.force_refresh)
    print(json.dumps(result, ensure_ascii=False, indent=2))
