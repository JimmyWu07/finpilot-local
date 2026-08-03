"""全球标准化财务分析引擎工具"""
import json
import subprocess
import os
import tempfile
from langchain.tools import tool


@tool
def analyze_financials(financial_data: str) -> str:
    """对股票财务数据进行标准化分析，计算12项核心财务指标并评级。
    
    支持CAS/HKFRS/US-GAAP/JGAAP/IFRS多会计准则，自动识别并标注差异。
    
    Args:
        financial_data: JSON格式的财务数据字符串，需包含以下字段:
            - symbol: 股票代码
            - market: 市场代码(SH/SZ/BJ/HK/US/JP/EU)
            - accounting_standard: 会计准则(CAS/HKFRS/US_GAAP/JGAAP/IFRS)
            - financials: 财务数据对象，包含:
                - revenue: 营收
                - net_profit: 净利润
                - total_assets: 总资产
                - total_liabilities: 总负债
                - current_assets: 流动资产
                - current_liabilities: 流动负债
                - inventory: 存货
                - goodwill: 商誉
                - equity: 净资产/股东权益
                - operating_cash_flow: 经营现金流
                - revenue_growth: 营收同比增速(%)
                - profit_growth: 净利润同比增速(%)
                - gross_margin: 毛利率(%)
                - net_margin: 净利率(%)
                - roe: ROE(%)
                - roa: ROA(%)
    """
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    script_path = os.path.join(workspace, "scripts", "analyze_financials.py")
    
    try:
        data = json.loads(financial_data) if isinstance(financial_data, str) else financial_data
    except json.JSONDecodeError:
        return json.dumps({"error": "输入数据不是有效的JSON格式"}, ensure_ascii=False)
    
    # 数据格式适配：将扁平字段转换为脚本期望的 annual_reports 格式
    fin = data.get("financials", {})
    if "annual_reports" not in fin and "revenue" in fin:
        data["financials"] = {
            "annual_reports": [fin],
            "quarterly_reports": []
        }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir='/tmp') as f:
        json.dump(data, f, ensure_ascii=False)
        input_file = f.name
    
    try:
        proc = subprocess.run(
            ["python3", script_path, "--input", input_file],
            capture_output=True, text=True, timeout=60
        )
        if proc.returncode == 0:
            return proc.stdout
        else:
            return json.dumps({"error": "脚本执行失败", "stderr": proc.stderr}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if os.path.exists(input_file):
            os.unlink(input_file)
