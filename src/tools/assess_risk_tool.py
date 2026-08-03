"""多维度风险评估引擎工具"""
import json
import subprocess
import os
import tempfile
from langchain.tools import tool


@tool
def assess_risk(risk_data: str) -> str:
    """对股票进行多维度风险评估，输出风险评分、风险等级和主要风险点。
    
    评估维度包括: 财务风险、经营风险、市场风险、治理风险、行业风险。
    
    Args:
        risk_data: JSON格式的风险评估数据字符串，需包含:
            - symbol: 股票代码
            - market: 市场代码
            - financials: 财务数据(用于财务风险评估)
            - governance: 治理数据(用于治理风险评估)
            - market_data: 市场数据(用于市场风险评估)
            - industry: 行业数据(用于行业风险评估)
    """
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    script_path = os.path.join(workspace, "scripts", "assess_risk.py")
    
    try:
        data = json.loads(risk_data) if isinstance(risk_data, str) else risk_data
    except (json.JSONDecodeError, TypeError) as e:
        if isinstance(risk_data, str):
            cleaned = risk_data.strip().lstrip('\ufeff')
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                return json.dumps({"error": f"输入数据不是有效的JSON格式: {str(e)[:100]}"}, ensure_ascii=False)
        else:
            return json.dumps({"error": f"输入数据类型错误: {type(risk_data).__name__}"}, ensure_ascii=False)
    
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
