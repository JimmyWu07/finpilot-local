"""股票实时行情查询工具"""
import json
import os
from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def get_realtime_quote(symbol: str, market: str = "SH") -> str:
    """获取股票实时最新行情数据，包括当前价格、涨跌幅、成交量、成交额、换手率、市盈率、市净率等。
    
    Args:
        symbol: 股票代码，如 600519、00700、AAPL
        market: 市场代码，SH/SZ/BJ(沪深北)、HK(港)、US(美)、JP(日)、EU(欧)
    """
    ctx = request_context.get() or new_context(method="get_realtime_quote")
    market = market.upper()
    market_name_map = {"SH": "上海A股", "SZ": "深圳A股", "BJ": "北交所", "HK": "港股", "US": "美股", "JP": "日股", "EU": "欧股"}
    market_name = market_name_map.get(market, market)
    
    client = SearchClient(ctx=ctx)
    
    # 搜索实时行情
    query = f"{symbol} {market_name} 实时行情 最新价格 涨跌幅 成交量 成交额 换手率 市盈率 市净率"
    response = client.web_search(query=query, count=8)
    
    results = []
    if response.web_items:
        for item in response.web_items:
            results.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
                "publish_time": item.publish_time,
            })
    
    # 提取AI摘要
    summary = response.summary if hasattr(response, 'summary') else None
    
    output = {
        "symbol": symbol,
        "market": market,
        "market_name": market_name,
        "realtime_data": results,
        "ai_summary": summary,
        "key_metrics_hint": "关注: 当前价格、涨跌幅、成交量与均量对比、换手率(>3%为活跃)、市盈率(PE)与行业对比、市净率(PB)",
        "data_source": "数据来源于联网搜索，行情数据有延迟，以交易所实时数据为准"
    }
    
    return json.dumps(output, ensure_ascii=False, indent=2)
