"""股票综合分析工具 - 消息面/资金面/技术面/基本面四维分析"""
import json
import os
from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


def _web_search(query: str, ctx=None, count: int = 5) -> list:
    """通用联网搜索"""
    client = SearchClient(ctx=ctx)
    response = client.web_search(query=query, count=count)
    results = []
    if response.web_items:
        for item in response.web_items:
            results.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
                "publish_time": item.publish_time,
            })
    return results


@tool
def stock_comprehensive_analysis(symbol: str, market: str = "SH", analysis_dimensions: str = "消息面,资金面,技术面,基本面") -> str:
    """根据股票简称/代码，提供股票相关的消息面分析、资金面分析、技术面分析、基本面分析。
    
    Args:
        symbol: 股票代码，如 600519、00700、AAPL
        market: 市场代码，SH/SZ/BJ(沪深北)、HK(港)、US(美)、JP(日)、EU(欧)
        analysis_dimensions: 分析维度，逗号分隔，可选: 消息面,资金面,技术面,基本面
    """
    ctx = request_context.get() or new_context(method="stock_comprehensive_analysis")
    market = market.upper()
    market_name_map = {"SH": "上海A股", "SZ": "深圳A股", "BJ": "北交所", "HK": "港股", "US": "美股", "JP": "日股", "EU": "欧股"}
    market_name = market_name_map.get(market, market)
    dims = [d.strip() for d in analysis_dimensions.split(",")]
    
    result = {"symbol": symbol, "market": market, "market_name": market_name}
    
    for dim in dims:
        if dim == "消息面":
            query = f"{symbol} {market_name} 最新消息 重大事件 公告 新闻"
            items = _web_search(query, ctx, count=8)
            result["news_analysis"] = {
                "summary": "基于最新新闻和公告的消息面分析",
                "items": items,
                "sentiment_hint": "请结合舆情分析工具进一步判断情感倾向"
            }
        elif dim == "资金面":
            query = f"{symbol} {market_name} 资金流向 主力资金 北向资金 融资融券 大单"
            items = _web_search(query, ctx, count=8)
            result["fund_flow_analysis"] = {
                "summary": "基于资金流向数据的资金面分析",
                "items": items,
                "key_metrics_hint": "关注主力资金净流入/流出、北向资金持仓变化、融资融券余额变动"
            }
        elif dim == "技术面":
            query = f"{symbol} {market_name} 技术分析 K线 均线 MACD RSI 支撑位 压力位"
            items = _web_search(query, ctx, count=8)
            result["technical_analysis"] = {
                "summary": "基于技术指标的技术面分析",
                "items": items,
                "key_metrics_hint": "关注均线排列、MACD金叉/死叉、RSI超买超卖、成交量变化"
            }
        elif dim == "基本面":
            query = f"{symbol} {market_name} 基本面分析 营收 净利润 ROE 估值 PE PB"
            items = _web_search(query, ctx, count=8)
            result["fundamental_analysis"] = {
                "summary": "基于财务数据的基本面分析",
                "items": items,
                "key_metrics_hint": "关注营收增速、净利润增速、ROE、估值水平(PE/PB)与行业对比"
            }
    
    return json.dumps(result, ensure_ascii=False, indent=2)
