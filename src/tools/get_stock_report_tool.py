"""获取个股研报工具 - 券商研究报告与评级"""
import json
import os
from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def get_stock_report(symbol: str, market: str = "SH", report_type: str = "综合") -> str:
    """获取个股研报，包括券商研究报告、投资评级、目标价、盈利预测等。
    
    Args:
        symbol: 股票代码，如 600519、00700、AAPL
        market: 市场代码，SH/SZ/BJ(沪深北)、HK(港)、US(美)、JP(日)、EU(欧)
        report_type: 研报类型，可选: 综合、深度报告、点评报告、盈利预测、行业对比
    """
    ctx = request_context.get() or new_context(method="get_stock_report")
    market = market.upper()
    market_name_map = {"SH": "上海A股", "SZ": "深圳A股", "BJ": "北交所", "HK": "港股", "US": "美股", "JP": "日股", "EU": "欧股"}
    market_name = market_name_map.get(market, market)
    
    client = SearchClient(ctx=ctx)
    
    # 搜索研报和评级
    query = f"{symbol} {market_name} 券商研报 投资评级 目标价 盈利预测 {report_type}"
    response = client.web_search(query=query, count=10)
    
    reports = []
    if response.web_items:
        for item in response.web_items:
            reports.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
                "publish_time": item.publish_time,
            })
    
    # 搜索评级汇总
    query2 = f"{symbol} {market_name} 分析师评级 买入 增持 中性 减持 一致预期 目标价"
    response2 = client.web_search(query=query2, count=5)
    rating_summary_items = []
    if response2.web_items:
        for item in response2.web_items:
            rating_summary_items.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
            })
    
    summary = response.summary if hasattr(response, 'summary') else None
    
    output = {
        "symbol": symbol,
        "market": market,
        "market_name": market_name,
        "report_type": report_type,
        "research_reports": reports,
        "rating_summary": rating_summary_items,
        "ai_summary": summary,
        "key_metrics_hint": "关注: 一致评级(买入/增持/中性/减持比例)、平均目标价及较当前价涨跌幅、盈利预测(营收/净利润预测值及增速)、核心投资逻辑",
        "data_source": "数据来源于联网搜索，研报观点仅供参考，不构成投资建议"
    }
    
    return json.dumps(output, ensure_ascii=False, indent=2)
