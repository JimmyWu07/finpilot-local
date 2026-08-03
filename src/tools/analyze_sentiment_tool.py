"""多维度舆情情感分析引擎工具"""
import json
import subprocess
import os
import tempfile
from langchain.tools import tool


@tool
def analyze_sentiment(news_data: str) -> str:
    """对股票相关新闻进行三维度(宏观政策/行业动态/个股新闻)情感分析。
    
    使用情感词典匹配打分，输出各维度情感评分、综合情绪值及低置信度条目。
    
    Args:
        news_data: JSON格式的新闻数据字符串，需包含:
            - news_announcements 或 news: 新闻数据对象，包含:
                - policy_news: 宏观政策新闻列表，每条含title和content
                - industry_news: 行业新闻列表，每条含title和content
                - stock_news: 个股新闻列表，每条含title和content
                - announcements: 公告列表，每条含title和content
    """
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    script_path = os.path.join(workspace, "scripts", "analyze_sentiment.py")
    
    try:
        data = json.loads(news_data) if isinstance(news_data, str) else news_data
    except json.JSONDecodeError:
        return json.dumps({"error": "输入数据不是有效的JSON格式"}, ensure_ascii=False)
    
    # 数据格式适配：确保 news_announcements 是 dict 格式
    news = data.get("news_announcements", data.get("news", {}))
    if isinstance(news, list):
        # 如果是列表，自动分类到 industry_news
        data["news_announcements"] = {
            "policy_news": [],
            "industry_news": news,
            "stock_news": [],
            "announcements": []
        }
    elif isinstance(news, dict):
        data["news_announcements"] = news
    
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
