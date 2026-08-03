"""全球多市场股票数据统一采集引擎工具"""
import json
import subprocess
import os
import tempfile
from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


def _search_stock_data(query: str, ctx=None) -> dict:
    """使用联网搜索获取股票相关数据"""
    client = SearchClient(ctx=ctx)
    response = client.web_search(query=query, count=10)
    results = []
    if response.web_items:
        for item in response.web_items:
            results.append({
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "publish_time": item.publish_time,
            })
    summary = response.summary if hasattr(response, 'summary') else None
    return {"web_results": results, "summary": summary}


@tool
def fetch_stock_data(symbol: str, market: str = "SH", data_types: str = "行情,财务,新闻") -> str:
    """获取全球多市场股票数据，支持A股(SH/SZ/BJ)、港股(HK)、美股(US)、日股(JP)、欧股(EU)。
    
    Args:
        symbol: 股票代码，如 600519、00700、AAPL
        market: 市场代码，SH/SZ/BJ(沪深北)、HK(港)、US(美)、JP(日)、EU(欧)
        data_types: 需要获取的数据类型，逗号分隔，可选: 行情,财务,新闻,公告,行业,研报
    """
    ctx = request_context.get() or new_context(method="fetch_stock_data")
    
    market = market.upper()
    if market not in ("SH", "SZ", "BJ", "HK", "US", "JP", "EU"):
        return json.dumps({"error": f"不支持的市场代码: {market}，支持: SH/SZ/BJ/HK/US/JP/EU"}, ensure_ascii=False)
    
    types_list = [t.strip() for t in data_types.split(",")]
    
    # 构建搜索查询
    market_name_map = {"SH": "上海A股", "SZ": "深圳A股", "BJ": "北交所", "HK": "港股", "US": "美股", "JP": "日股", "EU": "欧股"}
    market_name = market_name_map.get(market, market)
    
    all_data = {"symbol": symbol, "market": market, "market_name": market_name, "data_types": types_list}
    
    for dtype in types_list:
        if dtype == "行情":
            query = f"{symbol} {market_name} 股票行情 最新价格 涨跌幅 成交量"
            result = _search_stock_data(query, ctx)
            all_data["realtime_quotes"] = result
        elif dtype == "财务":
            query = f"{symbol} {market_name} 财务数据 营收 净利润 资产负债率 ROE"
            result = _search_stock_data(query, ctx)
            all_data["financials"] = result
        elif dtype == "新闻":
            query = f"{symbol} {market_name} 最新新闻 公告"
            result = _search_stock_data(query, ctx)
            all_data["news_announcements"] = result
        elif dtype == "公告":
            query = f"{symbol} {market_name} 公司公告 重大事项"
            result = _search_stock_data(query, ctx)
            all_data["announcements"] = result
        elif dtype == "行业":
            query = f"{symbol} {market_name} 所属行业 行业对比 竞争格局"
            result = _search_stock_data(query, ctx)
            all_data["industry_data"] = result
        elif dtype == "研报":
            query = f"{symbol} {market_name} 研究报告 券商评级 目标价"
            result = _search_stock_data(query, ctx)
            all_data["research_reports"] = result
    
    # 调用脚本进行数据标准化
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    script_path = os.path.join(workspace, "scripts", "fetch_stock_data.py")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir='/tmp') as f:
        json.dump(all_data, f, ensure_ascii=False)
        input_file = f.name
    
    try:
        proc = subprocess.run(
            ["python3", script_path, "--input", input_file],
            capture_output=True, text=True, timeout=60
        )
        if proc.returncode == 0:
            result = json.loads(proc.stdout)
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            # 脚本执行失败，返回原始搜索数据
            return json.dumps(all_data, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"raw_data": all_data, "script_error": str(e)}, ensure_ascii=False, indent=2)
    finally:
        if os.path.exists(input_file):
            os.unlink(input_file)
