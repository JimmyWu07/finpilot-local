"""教学级分析报告生成引擎工具"""
import json
import subprocess
import os
import tempfile
from langchain.tools import tool


@tool
def export_report(report_data: str) -> str:
    """生成教学级分析报告，输出为Word文档(.docx)。
    
    将Markdown格式的分析报告内容转换为专业Word文档。
    
    Args:
        report_data: JSON格式的报告数据字符串，需包含:
            - markdown_content: Markdown格式的报告正文内容
            - stock_code: 股票代码(可选)
            - company_name: 公司名称(可选)
    """
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    script_path = os.path.join(workspace, "scripts", "export_word.py")
    
    try:
        data = json.loads(report_data) if isinstance(report_data, str) else report_data
    except (json.JSONDecodeError, TypeError) as e:
        if isinstance(report_data, str):
            cleaned = report_data.strip().lstrip('\ufeff')
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                return json.dumps({"error": f"输入数据不是有效的JSON格式: {str(e)[:100]}"}, ensure_ascii=False)
        else:
            return json.dumps({"error": f"输入数据类型错误: {type(report_data).__name__}"}, ensure_ascii=False)
    
    markdown_content = data.get("markdown_content", "")
    if not markdown_content:
        return json.dumps({"error": "缺少markdown_content字段，请提供Markdown格式的报告内容"}, ensure_ascii=False)
    
    stock_code = data.get("stock_code", "")
    company_name = data.get("company_name", "")
    
    # 写入临时Markdown文件
    md_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, dir='/tmp', encoding='utf-8')
    md_file.write(markdown_content)
    md_file.close()
    
    # 输出Word文件路径
    output_filename = f"{company_name or 'report'}({stock_code or 'code'})_分析报告.docx"
    output_filename = output_filename.replace(" ", "_")
    output_path = os.path.join("/tmp", output_filename)
    
    try:
        proc = subprocess.run(
            ["python3", script_path, "--input", md_file.name, "--output", output_path,
             "--stock_code", stock_code, "--company_name", company_name],
            capture_output=True, text=True, timeout=120
        )
        if proc.returncode == 0:
            result = json.loads(proc.stdout)
            # 将文件路径告知调用方
            result["output_path"] = output_path
            result["download_hint"] = f"报告已生成，文件路径: {output_path}"
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            return json.dumps({"error": "脚本执行失败", "stderr": proc.stderr}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if os.path.exists(md_file.name):
            os.unlink(md_file.name)
