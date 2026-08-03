# requires: 无额外依赖（纯文本处理）
# 多维度舆情情感分析引擎 - 词典匹配 + 三维度分类
import argparse
import json
import sys
import re

# ============================================================
# 情感词典
# ============================================================
NEGATIVE_WORDS = [
    "不及预期", "暴雷", "亏损", "减持", "处罚", "诉讼", "下滑",
    "暴跌", "下跌", "下降", "负面", "利空", "缩水", "坏账",
    "违约", "违规", "调查", "退市", "警告", "风险", "危机",
    "倒闭", "破产", "裁员", "造假", "欺诈", "虚增", "减值", "计提",
    "资金链断裂", "债务违约", "质押爆仓", "商誉减值", "跌停", "套现"
]

POSITIVE_WORDS = [
    "利好", "增持", "回购", "扩产", "降息", "业绩大增", "订单饱满",
    "上涨", "上升", "增长", "大涨", "暴涨", "创新高", "突破",
    "反弹", "回暖", "复苏", "景气", "强劲", "稳健", "盈利增长",
    "分红", "送股", "战略合作", "签约", "中标", "获批", "募资",
    "营收增长", "毛利率提升", "净利润大增", "涨停", "超预期"
]

# 三维度分类关键词
POLICY_KEYWORDS = ["央行", "降息", "加息", "国务院", "发改委", "证监会",
                   "财政部", "货币政策", "财政政策", "产业规划", "监管", "银保监"]

INDUSTRY_KEYWORDS = ["景气度", "产能", "竞争格局", "市场份额", "技术路线",
                     "行业标准", "产业链", "供需", "价格战", "行业"]

STOCK_KEYWORDS = ["财报", "季报", "年报", "公告", "增减持", "分红", "并购",
                  "重组", "停牌", "复牌", "业绩预告", "问询函"]


def classify_dimension(title, content=""):
    """三维度分类器"""
    text = title + content
    policy_hits = sum(1 for kw in POLICY_KEYWORDS if kw in text)
    industry_hits = sum(1 for kw in INDUSTRY_KEYWORDS if kw in text)
    stock_hits = sum(1 for kw in STOCK_KEYWORDS if kw in text)
    if policy_hits >= industry_hits and policy_hits >= stock_hits and policy_hits > 0:
        return "policy"
    elif stock_hits >= industry_hits and stock_hits > 0:
        return "stock"
    else:
        return "industry"  # 默认归为行业动态


def calculate_sentiment(title, content=""):
    """情感打分算法"""
    text = title + " " + content
    pos_hits = sum(1 for word in POSITIVE_WORDS if word in text)
    neg_hits = sum(1 for word in NEGATIVE_WORDS if word in text)
    total_words = max(len(text), 1)
    # 情绪值 = (正面命中 - 负面命中×1.2) / (总词数+1) × 100
    score = (pos_hits - neg_hits * 1.2) / (total_words + 1) * 100
    # 归一化到 -100 ~ 100
    score = max(-100, min(100, score * 10))
    # 情感分类
    if score > 20:
        sentiment = "positive"
    elif score < -20:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    # 置信度
    confidence = min(1.0, (pos_hits + neg_hits) / 5)
    return {
        "score": round(score, 2),
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "pos_hits": pos_hits,
        "neg_hits": neg_hits
    }


def analyze_news_item(item):
    """分析单条新闻"""
    title = item.get("title", "")
    content = item.get("content", "")
    dimension = classify_dimension(title, content)
    sentiment_result = calculate_sentiment(title, content)
    result = {
        "title": title,
        "dimension": dimension,
        "score": sentiment_result["score"],
        "sentiment": sentiment_result["sentiment"],
        "confidence": sentiment_result["confidence"],
        "is_low_confidence": sentiment_result["confidence"] < 0.7
    }
    return result


def aggregate_dimension(items, dimension_name, weight):
    """汇总单个维度"""
    if not items:
        return {
            "score": 0, "sentiment": "neutral", "article_count": 0,
            "key_topics": [], "weight": weight
        }
    scores = [item["score"] for item in items]
    avg_score = sum(scores) / len(scores)
    if avg_score > 20:
        sentiment = "positive"
    elif avg_score < -20:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    # 提取关键主题(简化: 取标题中出现频率高的词)
    topics = []
    for item in items[:5]:
        title = item.get("title", "")
        if len(title) > 5:
            topics.append(title[:15])
    return {
        "score": round(avg_score, 2),
        "sentiment": sentiment,
        "article_count": len(items),
        "key_topics": topics[:3],
        "weight": weight
    }


def analyze(data):
    """主分析函数"""
    news_data = data.get("news_announcements", data.get("news", {}))
    # 收集所有新闻
    all_items = []
    for category in ["policy_news", "industry_news", "stock_news", "announcements"]:
        for item in news_data.get(category, []):
            item["_category"] = category
            all_items.append(item)
    # 逐条分析
    analyzed_items = [analyze_news_item(item) for item in all_items]
    # 按维度分组
    policy_items = [i for i in analyzed_items if i["dimension"] == "policy"]
    industry_items = [i for i in analyzed_items if i["dimension"] == "industry"]
    stock_items = [i for i in analyzed_items if i["dimension"] == "stock"]
    # 三维度汇总
    policy_dim = aggregate_dimension(policy_items, "policy", 0.40)
    industry_dim = aggregate_dimension(industry_items, "industry", 0.35)
    stock_dim = aggregate_dimension(stock_items, "stock", 0.25)
    # 加权综合
    weighted_score = (
        policy_dim["score"] * policy_dim["weight"] +
        industry_dim["score"] * industry_dim["weight"] +
        stock_dim["score"] * stock_dim["weight"]
    )
    if weighted_score > 20:
        overall_sentiment = "positive"
    elif weighted_score < -20:
        overall_sentiment = "negative"
    else:
        overall_sentiment = "neutral"
    # 低置信度条目
    low_confidence = [
        {"title": item["title"], "score": item["score"],
         "sentiment": item["sentiment"], "reason": "词典命中数不足"}
        for item in analyzed_items if item["is_low_confidence"]
    ]
    return {
        "policy_dimension": policy_dim,
        "industry_dimension": industry_dim,
        "stock_dimension": stock_dim,
        "composite": {
            "weighted_score": round(weighted_score, 2),
            "overall_sentiment": overall_sentiment,
            "total_articles": len(analyzed_items)
        },
        "low_confidence_items": low_confidence,
        "analyzed_items": analyzed_items
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="多维度舆情情感分析引擎")
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
