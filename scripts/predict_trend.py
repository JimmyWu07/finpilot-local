# requires: 无额外依赖（纯计算模块）
# A股量化趋势预测引擎 - 多因子加权评分 + 压力测试
import argparse
import json
import sys
import math

# ============================================================
# 免责声明
# ============================================================
DISCLAIMER = "⚠️ 本预测基于历史数据的量化模型，仅供教学实训参考，不构成任何形式的投资建议。股市有风险，投资须谨慎。过去的表现不代表未来的结果。"

# 趋势判断阈值
TREND_THRESHOLDS = [
    (65, "📈 偏多", "看涨"),
    (45, "➡️ 震荡", "震荡"),
    (0, "📉 偏空", "看跌"),
]


def safe_float(val, default=0.0):
    """安全转换为浮点数"""
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def calculate_technical_score(market_data):
    """计算技术面得分 (0-100)"""
    prices = market_data.get("daily_prices", [])
    if len(prices) < 20:
        return 50  # 数据不足默认中性
    closes = [p.get("close", 0) for p in prices if p.get("close")]
    volumes = [p.get("volume", 0) for p in prices if p.get("volume")]
    if len(closes) < 20:
        return 50
    latest = closes[-1]
    # 均线计算
    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else latest
    ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else latest
    ma20 = sum(closes[-20:]) / 20
    score = 0
    # 价格位于20日均线上方: +20分
    if latest > ma20:
        score += 20
    # 5日线上穿20日线(金叉): +15分
    if ma5 > ma20:
        score += 15
    # RSI简化计算
    gains, losses = 0, 0
    for i in range(-14, 0):
        if i >= -len(closes):
            diff = closes[i] - closes[i-1]
            if diff > 0:
                gains += diff
            else:
                losses += abs(diff)
    rs = gains / losses if losses > 0 else 1
    rsi = 100 - (100 / (1 + rs))
    if 30 <= rsi <= 70:
        score += 10
    # MACD简化(正负判断)
    if ma5 > ma10:
        score += 15
    # 成交量温和放大
    avg_vol = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 1
    recent_vol = volumes[-1] if volumes else 0
    if avg_vol * 1.2 <= recent_vol <= avg_vol * 2:
        score += 10
    # 满分70分，按比例转换到0-100
    return min(100, round(score / 70 * 100, 1))


def calculate_fundamental_score(financial_data):
    """计算基本面得分 (0-100)"""
    metrics = financial_data.get("fin_metrics", [])
    if not metrics:
        return 50
    metric_map = {m.get("key"): m.get("value", 0) for m in metrics}
    score = 0
    # ROE评分
    roe = metric_map.get("roe", 0)
    if roe > 15:
        score += 30
    elif roe > 8:
        score += 20
    elif roe > 3:
        score += 10
    # 营收增速
    rev_growth = metric_map.get("revenue_growth", 0)
    if rev_growth > 20:
        score += 25
    elif rev_growth > 5:
        score += 15
    # 净利增速
    profit_growth = metric_map.get("profit_growth", 0)
    if profit_growth > 20:
        score += 25
    elif profit_growth > 5:
        score += 15
    # 满分80分，按比例转换到0-100
    return min(100, round(score / 80 * 100, 1))


def calculate_sentiment_score(sentiment_data):
    """计算情绪面得分 (0-100)"""
    if not sentiment_data:
        return 50
    composite = sentiment_data.get("composite", {})
    weighted_score = safe_float(composite.get("weighted_score", 0))
    # 情绪值 -100~100 转为 0~100
    return round((weighted_score + 100) / 2, 1)


def calculate_risk_score(risk_data):
    """计算风险面得分 (0-100, 风险越高分越低)"""
    if not risk_data:
        return 50
    composite_risk = safe_float(risk_data.get("composite_risk_score", 50))
    # 风险分 0-100 转为得分 100-0
    return round(100 - composite_risk, 1)


def predict_short_term(tech_score, fund_score, sent_score, risk_score):
    """短期预测(1个月)"""
    # 权重: 技术40% + 基本面30% + 情绪20% + 风险10%
    composite = (tech_score * 0.4 + fund_score * 0.3 +
                 sent_score * 0.2 + risk_score * 0.1)
    composite = round(composite, 1)
    direction = "➡️ 震荡"
    for threshold, label, _ in TREND_THRESHOLDS:
        if composite >= threshold:
            direction = label
            break
    key_factors = []
    if tech_score >= 70:
        key_factors.append("技术面偏强")
    if fund_score >= 70:
        key_factors.append("基本面支撑")
    if sent_score >= 60:
        key_factors.append("舆情偏正面")
    return {
        "score": composite,
        "direction": direction,
        "confidence_interval": "±8%",
        "period": "1个月",
        "key_factors": key_factors or ["各因子均衡"]
    }


def predict_mid_term(tech_score, fund_score, sent_score, risk_score):
    """中期预测(3-6个月)"""
    # 权重: 基本面50% + 技术20% + 情绪10% + 风险20%
    composite = (fund_score * 0.5 + tech_score * 0.2 +
                 sent_score * 0.1 + risk_score * 0.2)
    composite = round(composite, 1)
    direction = "➡️ 震荡"
    for threshold, label, _ in TREND_THRESHOLDS:
        if composite >= threshold:
            direction = label
            break
    key_factors = []
    if fund_score >= 70:
        key_factors.append("盈利增长确定性强")
    if risk_score >= 60:
        key_factors.append("风险可控")
    if tech_score >= 60:
        key_factors.append("技术面中性偏强")
    return {
        "score": composite,
        "direction": direction,
        "confidence_interval": "±15%",
        "period": "3-6个月",
        "key_factors": key_factors or ["各因子均衡"]
    }


def generate_stress_tests(latest_price):
    """生成压力测试"""
    if not latest_price or latest_price <= 0:
        latest_price = 100  # 默认基准
    return [
        {"scenario": "市场系统性下跌20%", "estimated_drawdown": "-18% ~ -25%",
         "estimated_price_range": f"{latest_price*0.75:.2f} ~ {latest_price*0.82:.2f}"},
        {"scenario": "行业政策利空", "estimated_drawdown": "-12% ~ -18%",
         "estimated_price_range": f"{latest_price*0.82:.2f} ~ {latest_price*0.88:.2f}"},
        {"scenario": "盈利低于预期20%", "estimated_drawdown": "-15% ~ -22%",
         "estimated_price_range": f"{latest_price*0.78:.2f} ~ {latest_price*0.85:.2f}"},
    ]


def generate_teaching_reference(latest_price, short_prediction, mid_prediction):
    """生成实训参考位"""
    if not latest_price or latest_price <= 0:
        latest_price = 100
    short_score = short_prediction.get("score", 50)
    mid_score = mid_prediction.get("score", 50)
    # 基于预测分数估算支撑/压力位
    short_support = latest_price * (1 - (100 - short_score) / 200)
    short_resistance = latest_price * (1 + (short_score - 50) / 200)
    mid_support = latest_price * (1 - (100 - mid_score) / 150)
    mid_resistance = latest_price * (1 + (mid_score - 50) / 150)
    return {
        "short_term_support": round(short_support, 2),
        "short_term_resistance": round(short_resistance, 2),
        "mid_term_support": round(mid_support, 2),
        "mid_term_resistance": round(mid_resistance, 2),
        "stop_loss_reference": "短期支撑位下方3%",
        "take_profit_reference": "短期压力位附近",
        "disclaimer": "⚠️ 以上参考位仅供教学实训使用，绝不构成投资建议。实际交易请咨询持牌投资顾问。"
    }


def predict(data):
    """主预测函数"""
    market = data.get("market", "SH")
    stock_code = data.get("stock_code", "")
    company_name = data.get("company_name", "")
    # 仅A股触发
    if market not in ("SH", "SZ", "BJ"):
        return {"skip": True, "reason": f"非A股市场({market})，跳过预测", "disclaimer": DISCLAIMER}
    market_data = data.get("market_data", {})
    financial_data = data.get("financial_analysis", {})
    sentiment_data = data.get("sentiment_analysis", {})
    risk_data = data.get("risk_assessment", {})
    # 计算四维度得分
    tech_score = calculate_technical_score(market_data)
    fund_score = calculate_fundamental_score(financial_data)
    sent_score = calculate_sentiment_score(sentiment_data)
    risk_score = calculate_risk_score(risk_data)
    # 短中期预测
    short_prediction = predict_short_term(tech_score, fund_score, sent_score, risk_score)
    mid_prediction = predict_mid_term(tech_score, fund_score, sent_score, risk_score)
    # 最新价格
    prices = market_data.get("daily_prices", [])
    latest_price = prices[-1].get("close", 0) if prices else 0
    # 压力测试
    stress_tests = generate_stress_tests(latest_price)
    # 实训参考位
    teaching_reference = generate_teaching_reference(latest_price, short_prediction, mid_prediction)
    return {
        "market": market,
        "stock_code": stock_code,
        "company_name": company_name,
        "disclaimer": DISCLAIMER,
        "factor_scores": {
            "technical": tech_score,
            "fundamental": fund_score,
            "sentiment": sent_score,
            "risk": risk_score
        },
        "short_term_prediction": short_prediction,
        "mid_term_prediction": mid_prediction,
        "stress_tests": stress_tests,
        "teaching_reference": teaching_reference,
        "model_limitations": [
            "历史数据不代表未来表现",
            "无法预测黑天鹅事件(政策突变、重大灾害等)",
            "模型未考虑内幕信息、市场操纵等非公开因素",
            "置信区间随预测周期拉长而扩大",
            "本模型为教学简化版本，实际量化模型需更多维度和更复杂的算法"
        ]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A股量化趋势预测引擎")
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
    result = predict(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
