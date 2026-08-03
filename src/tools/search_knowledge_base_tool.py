"""金融知识库检索工具 - 支持搜索KB1/KB2/KB3及参考文档"""
import json
import os
import re
from langchain.tools import tool


# 知识库文件索引
KB_FILES = {
    "KB1": "assets/KB1_合并版.md",       # A股预测模型、风险模型、财务指标阈值、舆情配置
    "KB2": "assets/KB2_合并版.md",       # A股龙头财报、全球龙头财报、产业政策、研报框架
    "KB3": "assets/KB3_合并版.md",       # 跨境投资基础、财务教学指南、量化方法论、风险案例
}

REFERENCE_FILES = {
    "financial_standards": "references/financial_standards.md",   # 财务评级阈值、会计准则差异
    "sentiment_dictionary": "references/sentiment_dictionary.md", # 情感词典、分类关键词
    "teaching_cases": "references/teaching_cases.md",             # 金融知识点、经典案例
}


def _load_kb_content(file_path: str) -> str:
    """加载知识库文件内容"""
    workspace = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    full_path = os.path.join(workspace, file_path)
    if not os.path.exists(full_path):
        return ""
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def _search_in_text(text: str, keywords: list, context_lines: int = 3) -> list:
    """在文本中搜索关键词，返回匹配段落"""
    lines = text.split("\n")
    matches = []
    for i, line in enumerate(lines):
        for kw in keywords:
            if kw.lower() in line.lower():
                # 获取上下文
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = "\n".join(lines[start:end])
                matches.append({
                    "line": i + 1,
                    "keyword": kw,
                    "matched_line": line.strip()[:200],
                    "context": context.strip()[:500]
                })
                break  # 同一行只记录一次
    return matches


def _extract_section(text: str, section_title: str) -> str:
    """提取指定章节内容"""
    pattern = rf"##?\s+.*{re.escape(section_title)}.*?\n(.*?)(?=##?\s+|$)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()[:2000]
    return ""


@tool
def search_knowledge_base(query: str, kb_scope: str = "all") -> str:
    """搜索金融知识库，获取A股预测模型、龙头财报数据、财务指标阈值、情感词典、教学案例等参考信息。
    
    Args:
        query: 搜索关键词，如 "贵州茅台财报"、"ROE评级阈值"、"情感词典"、"跨境投资"、"杜邦分析"
        kb_scope: 搜索范围，可选:
            - all: 搜索全部知识库
            - KB1: 仅搜索A股预测模型、风险模型、财务指标阈值、舆情配置
            - KB2: 仅搜索龙头财报、产业政策、研报框架
            - KB3: 仅搜索跨境投资、财务教学、量化方法论、风险案例
            - references: 仅搜索参考文档(财务标准/情感词典/教学案例)
    """
    results = {"query": query, "kb_scope": kb_scope, "matches": []}
    
    # 解析关键词
    keywords = [kw.strip() for kw in query.replace("，", " ").replace(",", " ").split() if len(kw.strip()) >= 2]
    if not keywords:
        keywords = [query.strip()]
    
    # 确定搜索范围
    search_files = {}
    if kb_scope == "all":
        search_files.update({f"KB1({KB_FILES['KB1']})": KB_FILES["KB1"]})
        search_files.update({f"KB2({KB_FILES['KB2']})": KB_FILES["KB2"]})
        search_files.update({f"KB3({KB_FILES['KB3']})": KB_FILES["KB3"]})
        for name, path in REFERENCE_FILES.items():
            search_files.update({f"{name}({path})": path})
    elif kb_scope in KB_FILES:
        search_files.update({f"{kb_scope}({KB_FILES[kb_scope]})": KB_FILES[kb_scope]})
    elif kb_scope == "references":
        for name, path in REFERENCE_FILES.items():
            search_files.update({f"{name}({path})": path})
    else:
        # 尝试模糊匹配
        for name, path in {**KB_FILES, **REFERENCE_FILES}.items():
            if name.lower() in kb_scope.lower():
                search_files.update({f"{name}({path})": path})
        if not search_files:
            search_files.update({f"KB1({KB_FILES['KB1']})": KB_FILES["KB1"]})
            search_files.update({f"KB2({KB_FILES['KB2']})": KB_FILES["KB2"]})
            search_files.update({f"KB3({KB_FILES['KB3']})": KB_FILES["KB3"]})
    
    # 搜索每个文件
    for file_label, file_path in search_files.items():
        content = _load_kb_content(file_path)
        if not content:
            continue
        
        matches = _search_in_text(content, keywords, context_lines=2)
        if matches:
            results["matches"].append({
                "file": file_label,
                "match_count": len(matches),
                "top_matches": matches[:5]  # 最多返回5条匹配
            })
    
    # 如果没有精确匹配，尝试章节提取
    if not results["matches"]:
        for file_label, file_path in search_files.items():
            content = _load_kb_content(file_path)
            if not content:
                continue
            section = _extract_section(content, query)
            if section:
                results["matches"].append({
                    "file": file_label,
                    "match_type": "section_extract",
                    "section_title": query,
                    "content": section
                })
    
    # 统计
    total_matches = sum(m.get("match_count", 1) for m in results["matches"])
    results["summary"] = f"在 {len(results['matches'])} 个文件中找到 {total_matches} 条相关结果"
    
    return json.dumps(results, ensure_ascii=False, indent=2)
