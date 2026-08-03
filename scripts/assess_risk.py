# requires: 无额外依赖（纯计算模块）
# 多维度综合风险研判引擎 - 四维度风险评分 + 雷达图数据
import argparse
import json
import sys
import math

# ============================================================
# 风险等级常量
# ============================================================
RISK_LEVELS = [
    (20, "低风险", "🟢 低风险"),
    (40, "较低风险", "🔵 较低风险"),
    (60, "中等风险", "🟡 中等风险"),
    (80, "较高风险", "🟠 较高风险"),
    (100, "高风险", "🔴 高风险"),
]

# 四维度权重
DIMENSION_WEIGHTS = {
    "financial": 0.35,
    "sentiment": 0.25,
    "industry": 0.25,
    "cross_border": 0.15,
}


def safe_float(val, default=0.0):
    """安全转换为浮点数"""
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def assess_financial_risk(financial_data):
    """评估财务风险 (0-100, 越高越危险)"""
    if not financial_data:
        return 50  # 无数据默认中等风险
    metrics = financial_data.get("fin_metrics", [])
    risk_flags = financial_data.get("risk_flags", [])
    # 基于评级计算风险
    rating_risk = {"excellent": 10, "healthy": 25, "warning": 60, "danger": 90}
    if metrics:
        total_risk = sum(rating_risk.get(m.get("rating", "warning"), 50) for m in metrics)
        base_risk = total_risk / len(metrics)
    else:
        base_risk = 50
    # 风险标记加分
    flag_bonus = len(risk_flags) * 10
    # 综合财务风险
    financial_risk = min(100, base_risk + flag_bonus)
    return round(financial_risk, 1)


def assess_sentiment_risk(sentiment_data):
    """评估舆情风险 (0-100, 越高越危险)"""
    if not sentiment_data:
        return 50
    composite = sentiment_data.get("composite", {})
    weighted_score = safe_float(composite.get("weighted_score", 0))
    # 情绪值 -100~100 转为风险 0~100
    # 正面情绪(高score) = 低风险，负面情绪(低score) = 高风险
    sentiment_risk = (100 - weighted_score) / 2
    # 低置信度条目数量影响
    low_conf_count = len(sentiment_data.get("low_confidence_items", []))
    conf_bonus = min(20, low_conf_count * 3)
    return round(min(100, sentiment_risk + conf_bonus), 1)


def assess_industry_risk(industry_data):
    """评估行业风险 (0-100, 越高越危险)"""
    if not industry_data:
        return 50
    # 基于行业对标数据
    domestic = industry_data.get("domestic_peers", {})
    global_p = industry_data.get("global_peers", {})
    peer_count = domestic.get("peer_count", 0) + global_p.get("peer_count", 0)
    # 对标公司数量越多，行业透明度越高，风险越低
    transparency_bonus = min(20, peer_count * 2)
    base_risk = 50 - transparency_bonus
    return round(max(10, min(90, base_risk)), 1)


def assess_cross_border_risk(market):
    """评估跨境风险 (0-100, 越高越危险)"""
    # A股无跨境风险
    if market in ("SH", "SZ", "BJ"):
        return 10
    # 港股较低风险
    if market == "HK":
        return 25
    # 美股/日股中等风险
    if market in ("US", "JP"):
        return 40
    # 欧股较高风险
    return 55


def generate_radar_data(dimensions):
    """生成雷达图数据(兼容ECharts/Chart.js)"""
    labels = ["财务风险", "舆情风险", "行业风险", "跨境风险"]
    values = [
        dimensions.get("financial", 50),
        dimensions.get("sentiment", 50),
        dimensions.get("industry", 50),
        dimensions.get("cross_border", 50),
    ]
    return {
        "labels": labels,
        "values": values,
        "max_value": 100,
        "chart_type": "radar",
        "series": [{
            "name": "风险评估",
            "data": values,
            "areaStyle": {"opacity": 0.3}
        }]
    }


def get_risk_level(score):
    """获取风险等级"""
    for threshold, level, label in RISK_LEVELS:
        if score <= threshold:
            return level, label
    return "高风险", "🔴 高风险"


def assess(data):
    """主评估函数"""
    market = data.get("market", "SH")
    stock_code = data.get("stock_code", "")
    company_name = data.get("company_name", "")
    # 四维度评估
    financial_risk = assess_financial_risk(data.get("financial_analysis"))
    sentiment_risk = assess_sentiment_risk(data.get("sentiment_analysis"))
    industry_risk = assess_industry_risk(data.get("industry_comparison"))
    cross_border_risk = assess_cross_border_risk(market)
    # 维度详情
    dimensions = {
        "financial": financial_risk,
        "sentiment": sentiment_risk,
        "industry": industry_risk,
        "cross_border": cross_border_risk,
    }
    # 加权综合评分
    composite_score = sum(
        dimensions[dim] * weight
        for dim, weight in DIMENSION_WEIGHTS.items()
    )
    composite_score = round(composite_score, 1)
    risk_level, risk_label = get_risk_level(composite_score)
    # 雷达图数据
    radar_data = generate_radar_data(dimensions)
    # 风险摘要
    risk_summary = f"{company_name}综合风险评分{composite_score}分，属于{risk_level}。"
    max_dim = max(dimensions, key=dimensions.get)
    dim_names = {"financial": "财务", "sentiment": "舆情", "industry": "行业", "cross_border": "跨境"}
    risk_summary += f"其中{dim_names[max_dim]}风险最高({dimensions[max_dim]}分)。"
    return {
        "stock_code": stock_code,
        "company_name": company_name,
        "market": market,
        "risk_dimensions": {
            "financial": {"score": financial_risk, "weight": DIMENSION_WEIGHTS["financial"],
                         "desc": "基于财务指标评级与风险标记"},
            "sentiment": {"score": sentiment_risk, "weight": DIMENSION_WEIGHTS["sentiment"],
                         "desc": "基于舆情情绪值与置信度"},
            "industry": {"score": industry_risk, "weight": DIMENSION_WEIGHTS["industry"],
                        "desc": "基于行业对标透明度"},
            "cross_border": {"score": cross_border_risk, "weight": DIMENSION_WEIGHTS["cross_border"],
                            "desc": "基于市场类型与监管环境"},
        },
        "composite_risk_score": composite_score,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "radar_data": radar_data,
        "risk_summary": risk_summary
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="多维度综合风险研判引擎")
    parser.add_argument("--input", help="输入JSON文件路径")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取")
    args = parser.parse_args()
    if args.stdin:
        data = json.load(sys.stdin)
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        parser.print_help()
        sys.exit(1)
    result = assess(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
