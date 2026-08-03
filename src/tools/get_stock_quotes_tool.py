"""A股实时行情工具集 - 多维度行情数据"""
import json
import os
from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def get_stock_quotes(symbol: str, market: str = "SH", quote_types: str = "实时行情,五档盘口,分时数据,技术指标") -> str:
    """A股实时行情工具集，获取股票多维度行情数据，包括实时行情、五档盘口、分时数据、技术指标等。
    
    Args:
        symbol: 股票代码，如 600519
        market: 市场代码，SH/SZ/BJ(仅支持A股)
        quote_types: 行情类型，逗号分隔，可选: 实时行情,五档盘口,分时数据,技术指标,资金流向,龙虎榜
    """
    ctx = request_context.get() or new_context(method="get_stock_quotes")
    market = market.upper()
    if market not in ("SH", "SZ", "BJ"):
        return json.dumps({"error": "本工具仅支持A股市场(SH/SZ/BJ)"}, ensure_ascii=False)
    
    market_name_map = {"SH": "上海A股", "SZ": "深圳A股", "BJ": "北交所"}
    market_name = market_name_map.get(market, market)
    
    client = SearchClient(ctx=ctx)
    types_list = [t.strip() for t in quote_types.split(",")]
    
    output = {"symbol": symbol, "market": market, "market_name": market_name}
    
    for qtype in types_list:
        if qtype == "实时行情":
            query = f"{symbol} {market_name} 最新价 涨跌幅 成交量 成交额 换手率 量比"
            resp = client.web_search(query=query, count=5)
            items = [{"title": i.title, "snippet": i.snippet, "url": i.url} for i in (resp.web_items or [])]
            output["realtime_quote"] = {"items": items, "summary": resp.summary}
        elif qtype == "五档盘口":
            query = f"{symbol} {market_name} 五档盘口 买一 卖一 委托量 委比"
            resp = client.web_search(query=query, count=5)
            items = [{"title": i.title, "snippet": i.snippet, "url": i.url} for i in (resp.web_items or [])]
            output["order_book"] = {"items": items, "summary": resp.summary}
        elif qtype == "分时数据":
            query = f"{symbol} {market_name} 分时走势 均价线 成交量柱"
            resp = client.web_search(query=query, count=5)
            items = [{"title": i.title, "snippet": i.snippet, "url": i.url} for i in (resp.web_items or [])]
            output["intraday_data"] = {"items": items, "summary": resp.summary}
        elif qtype == "技术指标":
            query = f"{symbol} {market_name} MACD KDJ RSI BOLL 均线 技术形态"
            resp = client.web_search(query=query, count=5)
            items = [{"title": i.title, "snippet": i.snippet, "url": i.url} for i in (resp.web_items or [])]
            output["technical_indicators"] = {"items": items, "summary": resp.summary}
        elif qtype == "资金流向":
            query = f"{symbol} {market_name} 资金流向 主力净流入 大单 超大单"
            resp = client.web_search(query=query, count=5)
            items = [{"title": i.title, "snippet": i.snippet, "url": i.url} for i in (resp.web_items or [])]
            output["fund_flow"] = {"items": items, "summary": resp.summary}
        elif qtype == "龙虎榜":
            query = f"{symbol} {market_name} 龙虎榜 机构席位 游资 营业部"
            resp = client.web_search(query=query, count=5)
            items = [{"title": i.title, "snippet": i.snippet, "url": i.url} for i in (resp.web_items or [])]
            output["dragon_tiger_list"] = {"items": items, "summary": resp.summary}
    
    return json.dumps(output, ensure_ascii=False, indent=2)
