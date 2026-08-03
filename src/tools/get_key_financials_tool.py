"""上市公司重要财务数据查询工具"""
import json
import os
from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def get_key_financials(symbol: str, market: str = "SH") -> str:
    """返回上市公司的重要财务指标数据，包括营收、净利润、ROE、资产负债率、毛利率、净利率、现金流等核心指标。
    
    Args:
        symbol: 股票代码，如 600519、00700、AAPL
        market: 市场代码，SH/SZ/BJ(沪深北)、HK(港)、US(美)、JP(日)、EU(欧)
    """
    ctx = request_context.get() or new_context(method="get_key_financials")
    market = market.upper()
    market_name_map = {"SH": "上海A股", "SZ": "深圳A股", "BJ": "北交所", "HK": "港股", "US": "美股", "JP": "日股", "EU": "欧股"}
    market_name = market_name_map.get(market, market)
    
    # 搜索最新财务数据
    query = f"{symbol} {market_name} 最新财务数据 营收 净利润 ROE 资产负债率 毛利率 现金流 2026"
    client = SearchClient(ctx=ctx)
    response = client.web_search(query=query, count=10)
    
    results = []
    if response.web_items:
        for item in response.web_items:
            results.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
                "publish_time": item.publish_time,
            })
    
    # 搜索关键指标
    query2 = f"{symbol} {market_name} 每股收益EPS 每股净资产 市盈率PE 市净率PB 股息率"
    response2 = client.web_search(query=query2, count=5)
    valuation_results = []
    if response2.web_items:
        for item in response2.web_items:
            valuation_results.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
            })
    
    output = {
        "symbol": symbol,
        "market": market,
        "market_name": market_name,
        "financial_data": results,
        "valuation_metrics": valuation_results,
        "key_indicators_hint": "重点关注: 营收同比增速、净利润同比增速、ROE(TTM)、资产负债率、毛利率、经营现金流/净利润比值",
        "data_source": "数据来源于联网搜索，建议交叉验证"
    }
    
    return json.dumps(output, ensure_ascii=False, indent=2)
