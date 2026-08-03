"""tushare上市公司现金流获取工具 - 三大表现金流数据"""
import json
import os
from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def get_cashflow_data(symbol: str, market: str = "SH", report_period: str = "latest") -> str:
    """获取上市公司三大表(资产负债表、利润表、现金流量表)金融数据，重点关注现金流相关指标。
    
    Args:
        symbol: 股票代码，如 600519、00700、AAPL
        market: 市场代码，SH/SZ/BJ(沪深北)、HK(港)、US(美)、JP(日)、EU(欧)
        report_period: 报告期，如 2026Q1、2025年报，默认 latest(最新)
    """
    ctx = request_context.get() or new_context(method="get_cashflow_data")
    market = market.upper()
    market_name_map = {"SH": "上海A股", "SZ": "深圳A股", "BJ": "北交所", "HK": "港股", "US": "美股", "JP": "日股", "EU": "欧股"}
    market_name = market_name_map.get(market, market)
    
    client = SearchClient(ctx=ctx)
    
    # 搜索现金流量表数据
    query_cf = f"{symbol} {market_name} 现金流量表 经营活动现金流 投资活动现金流 筹资活动现金流 {report_period}"
    response_cf = client.web_search(query=query_cf, count=8)
    cashflow_items = []
    if response_cf.web_items:
        for item in response_cf.web_items:
            cashflow_items.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
            })
    
    # 搜索资产负债表数据
    query_bs = f"{symbol} {market_name} 资产负债表 总资产 总负债 净资产 流动资产 {report_period}"
    response_bs = client.web_search(query=query_bs, count=5)
    balance_sheet_items = []
    if response_bs.web_items:
        for item in response_bs.web_items:
            balance_sheet_items.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
            })
    
    # 搜索利润表数据
    query_is = f"{symbol} {market_name} 利润表 营业收入 营业成本 净利润 毛利率 {report_period}"
    response_is = client.web_search(query=query_is, count=5)
    income_statement_items = []
    if response_is.web_items:
        for item in response_is.web_items:
            income_statement_items.append({
                "title": item.title,
                "snippet": item.snippet,
                "url": item.url,
            })
    
    output = {
        "symbol": symbol,
        "market": market,
        "report_period": report_period,
        "cash_flow_statement": cashflow_items,
        "balance_sheet": balance_sheet_items,
        "income_statement": income_statement_items,
        "key_cashflow_metrics_hint": "重点关注: 经营活动现金流净额、经营现金流/净利润比值(>1为优)、自由现金流(经营现金流-资本支出)、现金及现金等价物余额",
        "data_source": "数据来源于联网搜索，建议与财报原文交叉验证"
    }
    
    return json.dumps(output, ensure_ascii=False, indent=2)
