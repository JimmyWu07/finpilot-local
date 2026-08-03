"""行业对标分析引擎工具"""
import json
import subprocess
import os
import tempfile
from langchain.tools import tool


@tool
def benchmark_industry(benchmark_data: str) -> str:
    """对股票进行行业对标分析，输出各指标的行业排名、分位值和行业对比。
    
    支持A股证监会行业分类和港股GICS行业分类。
    
    Args:
        benchmark_data: JSON格式的对标数据字符串，需包含:
            - symbol: 股票代码
            - market: 市场代码
            - industry_code: 行业代码(证监会行业代码或GICS代码)
            - metrics: 指标数据对象，包含各财务指标值
    """
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    script_path = os.path.join(workspace, "scripts", "benchmark_industry.py")
    
    try:
        data = json.loads(benchmark_data) if isinstance(benchmark_data, str) else benchmark_data
    except (json.JSONDecodeError, TypeError) as e:
        # 尝试修复常见的JSON格式问题
        if isinstance(benchmark_data, str):
            # 移除可能的BOM或不可见字符
            cleaned = benchmark_data.strip().lstrip('\ufeff')
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                return json.dumps({"error": f"输入数据不是有效的JSON格式: {str(e)[:100]}"}, ensure_ascii=False)
        else:
            return json.dumps({"error": f"输入数据类型错误: {type(benchmark_data).__name__}"}, ensure_ascii=False)
    
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
