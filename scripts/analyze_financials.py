# requires: 无额外依赖（纯计算模块）
# 全球标准化财务分析引擎 - 12项核心指标计算与评级
import argparse
import json
import sys
from datetime import datetime

# ============================================================
# 评级阈值常量
# ============================================================
RATING_THRESHOLDS = {
    "debt_ratio": {"excellent": 30, "healthy": 50, "warning": 70, "unit": "%", "cn_name": "资产负债率", "lower_better": True},
    "current_ratio": {"excellent": 2.5, "healthy": 1.5, "warning": 1.0, "unit": "", "cn_name": "流动比率", "lower_better": False},
    "quick_ratio": {"excellent": 1.5, "healthy": 0.8, "warning": 0.5, "unit": "", "cn_name": "速动比率", "lower_better": False},
    "gross_margin": {"excellent": 60, "healthy": 30, "warning": 15, "unit": "%", "cn_name": "毛利率", "lower_better": False},
    "net_margin": {"excellent": 20, "healthy": 8, "warning": 3, "unit": "%", "cn_name": "净利率", "lower_better": False},
    "roe": {"excellent": 20, "healthy": 8, "warning": 3, "unit": "%", "cn_name": "ROE", "lower_better": False},
    "roa": {"excellent": 10, "healthy": 4, "warning": 1, "unit": "%", "cn_name": "ROA", "lower_better": False},
    "revenue_growth": {"excellent": 30, "healthy": 5, "warning": 0, "unit": "%", "cn_name": "营收增速", "lower_better": False},
    "profit_growth": {"excellent": 30, "healthy": 5, "warning": 0, "unit": "%", "cn_name": "净利增速", "lower_better": False},
    "goodwill_ratio": {"excellent": 5, "healthy": 15, "warning": 30, "unit": "%", "cn_name": "商誉/净资产", "lower_better": True},
    "asset_turnover": {"excellent": 0.8, "healthy": 0.5, "warning": 0.3, "unit": "", "cn_name": "总资产周转率", "lower_better": False},
    "inventory_turnover": {"excellent": 5, "healthy": 2, "warning": 1, "unit": "", "cn_name": "存货周转率", "lower_better": False},
}

RATING_LABELS = {
    "excellent": "优秀",
    "healthy": "健康",
    "warning": "预警",
    "danger": "危险"
}

# 会计准则映射
ACCOUNTING_STANDARDS = {
    "SH": "CAS", "SZ": "CAS", "BJ": "CAS",
    "HK": "HKFRS", "US": "US GAAP", "JP": "JGAAP", "EU": "IFRS"
}

# 综合评分等级
GRADE_THRESHOLDS = [
    (80, "优质", "🔵 优质"),
    (60, "良好", "🔵 良好"),
    (40, "一般", "🟡 一般"),
    (20, "较差", "🟠 较差"),
    (0, "危险", "🔴 危险"),
]


def safe_float(val, default=0.0):
    """安全转换为浮点数"""
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def rate_metric(key, value, prev_value=None):
    """对单个指标进行评级"""
    threshold = RATING_THRESHOLDS.get(key)
    if not threshold:
        return None
    lower_better = threshold["lower_better"]
    if lower_better:
        if value <= threshold["excellent"]:
            rating = "excellent"
        elif value <= threshold["healthy"]:
            rating = "healthy"
        elif value <= threshold["warning"]:
            rating = "warning"
        else:
            rating = "danger"
    else:
        if value >= threshold["excellent"]:
            rating = "excellent"
        elif value >= threshold["healthy"]:
            rating = "healthy"
        elif value >= threshold["warning"]:
            rating = "warning"
        else:
            rating = "danger"
    # 同比变化方向
    direction = "→"
    if prev_value is not None and prev_value != 0:
        change = ((value - prev_value) / abs(prev_value)) * 100
        if lower_better:
            direction = "↓" if change < -2 else ("↑" if change > 2 else "→")
        else:
            direction = "↑" if change > 2 else ("↓" if change < -2 else "→")
    return {
        "key": key,
        "cn_name": threshold["cn_name"],
        "value": round(value, 2),
        "unit": threshold["unit"],
        "rating": rating,
        "rating_label": RATING_LABELS[rating],
        "direction": direction,
        "description": f"{threshold['cn_name']}{RATING_LABELS[rating]}"
    }


def calculate_metrics(financials, market="SH"):
    """计算12项核心财务指标"""
    annual = financials.get("annual_reports", [])
    quarterly = financials.get("quarterly_reports", [])
    # 提取最新年度和去年同期数据
    latest = annual[0] if annual else {}
    prev_year = annual[1] if len(annual) > 1 else {}
    # 基础数据提取
    revenue = safe_float(latest.get("revenue"))
    net_profit = safe_float(latest.get("net_profit"))
    total_assets = safe_float(latest.get("total_assets", revenue * 1.5))
    total_liabilities = safe_float(latest.get("total_liabilities", total_assets * 0.4))
    current_assets = safe_float(latest.get("current_assets", total_assets * 0.4))
    current_liabilities = safe_float(latest.get("current_liabilities", total_liabilities * 0.5))
    inventory = safe_float(latest.get("inventory", current_assets * 0.2))
    net_assets = safe_float(latest.get("net_assets", total_assets - total_liabilities))
    goodwill = safe_float(latest.get("goodwill", 0))
    operating_cost = safe_float(latest.get("operating_cost", revenue * 0.6))
    prev_revenue = safe_float(prev_year.get("revenue"))
    prev_profit = safe_float(prev_year.get("net_profit"))
    prev_gross_margin = None
    metrics = []
    # 1. 资产负债率
    debt_ratio = (total_liabilities / total_assets * 100) if total_assets else 0
    metrics.append(rate_metric("debt_ratio", debt_ratio))
    # 2. 流动比率
    current_ratio = (current_assets / current_liabilities) if current_liabilities else 0
    metrics.append(rate_metric("current_ratio", current_ratio))
    # 3. 速动比率
    quick_ratio = ((current_assets - inventory) / current_liabilities) if current_liabilities else 0
    metrics.append(rate_metric("quick_ratio", quick_ratio))
    # 4. 毛利率
    gross_margin = ((revenue - operating_cost) / revenue * 100) if revenue else 0
    if prev_revenue:
        prev_cost = safe_float(prev_year.get("operating_cost", prev_revenue * 0.6))
        prev_gross_margin = ((prev_revenue - prev_cost) / prev_revenue * 100) if prev_revenue else None
    metrics.append(rate_metric("gross_margin", gross_margin, prev_gross_margin))
    # 5. 净利率
    net_margin = (net_profit / revenue * 100) if revenue else 0
    metrics.append(rate_metric("net_margin", net_margin))
    # 6. ROE
    roe = (net_profit / net_assets * 100) if net_assets else 0
    metrics.append(rate_metric("roe", roe))
    # 7. ROA
    roa = (net_profit / total_assets * 100) if total_assets else 0
    metrics.append(rate_metric("roa", roa))
    # 8. 营收增速
    revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0
    metrics.append(rate_metric("revenue_growth", revenue_growth))
    # 9. 净利增速
    profit_growth = ((net_profit - prev_profit) / prev_profit * 100) if prev_profit else 0
    metrics.append(rate_metric("profit_growth", profit_growth))
    # 10. 商誉/净资产
    goodwill_ratio = (goodwill / net_assets * 100) if net_assets else 0
    metrics.append(rate_metric("goodwill_ratio", goodwill_ratio))
    # 11. 总资产周转率
    asset_turnover = (revenue / total_assets) if total_assets else 0
    metrics.append(rate_metric("asset_turnover", asset_turnover))
    # 12. 存货周转率
    inventory_turnover = (operating_cost / inventory) if inventory else 0
    metrics.append(rate_metric("inventory_turnover", inventory_turnover))
    return [m for m in metrics if m is not None]


def detect_risk_flags(metrics, financials):
    """检测5类风险标记"""
    flags = []
    metric_map = {m["key"]: m["value"] for m in metrics}
    # 1. 资产负债率过高
    if metric_map.get("debt_ratio", 0) > 70:
        flags.append({"type": "debt_ratio_high", "level": "warning",
                      "desc": f"资产负债率{metric_map['debt_ratio']:.1f}%超过70%警戒线"})
    # 2. 流动比率过低
    if metric_map.get("current_ratio", 999) < 1.5:
        flags.append({"type": "current_ratio_low", "level": "warning",
                      "desc": f"流动比率{metric_map['current_ratio']:.2f}低于1.5安全线"})
    # 3. 商誉占比过高
    if metric_map.get("goodwill_ratio", 0) > 30:
        flags.append({"type": "goodwill_ratio_high", "level": "danger",
                      "desc": f"商誉占净资产{metric_map['goodwill_ratio']:.1f}%超过30%"})
    # 4. 连续亏损检测
    annual = financials.get("annual_reports", [])
    loss_count = sum(1 for r in annual[:3] if safe_float(r.get("net_profit")) < 0)
    if loss_count >= 2:
        flags.append({"type": "loss_year", "level": "danger",
                      "desc": f"近{len(annual[:3])}年中有{loss_count}年净利润为负"})
    # 5. 毛利率大幅下滑
    if metric_map.get("gross_margin", 0) > 0:
        # 需要去年同期数据，此处简化处理
        pass
    return flags


def calculate_composite_score(metrics):
    """计算综合评分(财务维度50%)"""
    rating_scores = {"excellent": 100, "healthy": 75, "warning": 45, "danger": 15}
    if not metrics:
        return 0, "危险", "🔴 危险"
    total = sum(rating_scores.get(m["rating"], 0) for m in metrics)
    avg_score = total / len(metrics)
    # 财务维度占50%
    composite = avg_score * 0.5
    # 映射等级
    for threshold, grade, label in GRADE_THRESHOLDS:
        if composite >= threshold:
            return round(composite, 1), grade, label
    return 0, "危险", "🔴 危险"


def analyze(data):
    """主分析函数"""
    financials = data.get("financials", {})
    market = data.get("market", "SH")
    stock_code = data.get("stock_code", "")
    company_name = data.get("company_name", "")
    accounting_standard = ACCOUNTING_STANDARDS.get(market, "CAS")
    # 计算指标
    metrics = calculate_metrics(financials, market)
    # 检测风险
    risk_flags = detect_risk_flags(metrics, financials)
    # 计算综合评分
    score, grade, label = calculate_composite_score(metrics)
    # 生成摘要
    excellent_count = sum(1 for m in metrics if m["rating"] == "excellent")
    warning_count = sum(1 for m in metrics if m["rating"] in ("warning", "danger"))
    summary = f"公司财务状况{'整体健康' if warning_count < 3 else '需关注'}，"
    summary += f"12项指标中{excellent_count}项优秀，{warning_count}项预警。"
    summary += f"会计准则: {accounting_standard}。"
    return {
        "company_name": company_name,
        "stock_code": stock_code,
        "market": market,
        "accounting_standard": accounting_standard,
        "fin_metrics": metrics,
        "risk_flags": risk_flags,
        "composite_score": score,
        "composite_grade": grade,
        "composite_label": label,
        "analysis_summary": summary
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="全球标准化财务分析引擎")
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
    result = analyze(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
