"""FinPilot_Agent - 全球金融分析智能体"""
import os
import json
from typing import Annotated
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, ToolMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver

# 原始7大工具
from tools.fetch_stock_data_tool import fetch_stock_data
from tools.analyze_financials_tool import analyze_financials
from tools.analyze_sentiment_tool import analyze_sentiment
from tools.assess_risk_tool import assess_risk
from tools.benchmark_industry_tool import benchmark_industry
from tools.predict_trend_tool import predict_trend
from tools.export_report_tool import export_report

# 新增6大插件工具
from tools.stock_comprehensive_analysis_tool import stock_comprehensive_analysis
from tools.get_key_financials_tool import get_key_financials
from tools.get_cashflow_data_tool import get_cashflow_data
from tools.get_realtime_quote_tool import get_realtime_quote
from tools.get_stock_quotes_tool import get_stock_quotes
from tools.get_stock_report_tool import get_stock_report

# 知识库检索工具
from tools.search_knowledge_base_tool import search_knowledge_base

# 数据可视化插件
from tools.data_visualization_tool import generate_charts

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40


def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]


@wrap_tool_call
def handle_tool_errors(request, handler):
    """Handle tool execution errors with custom messages."""
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"工具执行出错: {str(e)}，请检查输入参数后重试。",
            tool_call_id=request.tool_call["id"]
        )


def build_agent(ctx=None):
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )

    all_tools = [
        # 原始7大工具
        fetch_stock_data,
        analyze_financials,
        analyze_sentiment,
        assess_risk,
        benchmark_industry,
        predict_trend,
        export_report,
        # 新增6大插件工具
        stock_comprehensive_analysis,
        get_key_financials,
        get_cashflow_data,
        get_realtime_quote,
        get_stock_quotes,
        get_stock_report,
        # 知识库检索工具
        search_knowledge_base,
        # 数据可视化插件
        generate_charts,
    ]

    return create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=all_tools,
        middleware=[handle_tool_errors],
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
