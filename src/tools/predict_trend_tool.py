"""A股量化趋势预测引擎工具"""
import json
import subprocess
import os
import tempfile
from langchain.tools import tool


@tool
def predict_trend(prediction_data: str) -> str:
    """对A股进行量化趋势预测，基于多因子加权评分输出短中期预测和压力测试。
    
    仅支持A股市场(SH/SZ/BJ)，其他市场将返回跳过提示。
    
    Args:
        prediction_data: JSON格式的预测数据字符串，需包含:
            - symbol: 股票代码
            - market: 市场代码(仅SH/SZ/BJ有效)
            - market_data: 行情数据(含daily_prices列表)
            - financial_data: 财务分析结果(含fin_metrics列表)
            - sentiment_data: 舆情分析结果(含composite对象)
            - risk_data: 风险评估结果(含composite_risk_score)
    """
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    script_path = os.path.join(workspace, "scripts", "predict_trend.py")
    
    try:
        data = json.loads(prediction_data) if isinstance(prediction_data, str) else prediction_data
    except (json.JSONDecodeError, TypeError) as e:
        if isinstance(prediction_data, str):
            cleaned = prediction_data.strip().lstrip('\ufeff')
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                return json.dumps({"error": f"输入数据不是有效的JSON格式: {str(e)[:100]}"}, ensure_ascii=False)
        else:
            return json.dumps({"error": f"输入数据类型错误: {type(prediction_data).__name__}"}, ensure_ascii=False)
    
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
