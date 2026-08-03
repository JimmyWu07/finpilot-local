# requires: 无额外依赖（纯计算模块）
# 全球同行业对标分析引擎 - GICS分类 + 三维度对比
import argparse
import json
import sys

# ============================================================
# GICS行业分类与对标公司库
# ============================================================
GICS_INDUSTRIES = {
    "白酒": {
        "code": "2510", "name": "可选消费-饮料",
        "domestic_peers": [
            {"code": "000858", "name": "五粮液", "market_cap": 5800},
            {"code": "000568", "name": "泸州老窖", "market_cap": 2800},
            {"code": "002304", "name": "洋河股份", "market_cap": 2200},
            {"code": "603369", "name": "今世缘", "market_cap": 580},
        ],
        "global_peers": [
            {"code": "DGE.DI", "name": "帝亚吉欧", "market_cap": 650, "currency": "GBP"},
            {"code": "RI.PA", "name": "保乐力加", "market_cap": 420, "currency": "EUR"},
            {"code": "BF.B", "name": "百富门", "market_cap": 110, "currency": "USD"},
        ],
        "key_metrics": ["毛利率", "净利率", "ROE", "营收增速", "品牌价值"]
    },
    "银行": {
        "code": "4010", "name": "金融-银行",
        "domestic_peers": [
            {"code": "600036", "name": "招商银行", "market_cap": 9500},
            {"code": "601398", "name": "工商银行", "market_cap": 18000},
            {"code": "601939", "name": "建设银行", "market_cap": 16000},
            {"code": "600000", "name": "浦发银行", "market_cap": 3200},
        ],
        "global_peers": [
            {"code": "JPM", "name": "摩根大通", "market_cap": 5800, "currency": "USD"},
            {"code": "HSBA.L", "name": "汇丰控股", "market_cap": 1600, "currency": "GBP"},
            {"code": "BAC", "name": "美国银行", "market_cap": 3200, "currency": "USD"},
        ],
        "key_metrics": ["净息差", "不良率", "ROE", "资本充足率", "成本收入比"]
    },
    "科技硬件": {
        "code": "4510", "name": "信息技术-技术硬件",
        "domestic_peers": [
            {"code": "002475", "name": "立讯精密", "market_cap": 3200},
            {"code": "600183", "name": "生益科技", "market_cap": 520},
            {"code": "002241", "name": "歌尔股份", "market_cap": 850},
        ],
        "global_peers": [
            {"code": "AAPL", "name": "苹果", "market_cap": 28000, "currency": "USD"},
            {"code": "MSFT", "name": "微软", "market_cap": 25000, "currency": "USD"},
            {"code": "005930.KS", "name": "三星电子", "market_cap": 3800, "currency": "KRW"},
        ],
        "key_metrics": ["研发投入比", "毛利率", "营收增速", "市场份额", "专利数量"]
    },
    "房地产": {
        "code": "6010", "name": "房地产",
        "domestic_peers": [
            {"code": "001979", "name": "招商蛇口", "market_cap": 1200},
            {"code": "600048", "name": "保利发展", "market_cap": 1800},
            {"code": "000002", "name": "万科A", "market_cap": 1500},
        ],
        "global_peers": [
            {"code": "DHI", "name": "霍顿房屋", "market_cap": 450, "currency": "USD"},
            {"code": "LEN", "name": "莱纳建筑", "market_cap": 380, "currency": "USD"},
        ],
        "key_metrics": ["净负债率", "土储面积", "销售增速", "毛利率", "融资成本"]
    },
}

# 默认行业映射(按股票代码前缀)
DEFAULT_INDUSTRY_MAP = {
    "600519": "白酒", "000858": "白酒", "000568": "白酒",
    "600036": "银行", "000001": "银行", "601398": "银行",
    "002475": "科技硬件", "002236": "科技硬件",
    "001979": "房地产", "600048": "房地产", "000002": "房地产",
}


def detect_industry(stock_code, company_name=""):
    """检测所属行业"""
    if stock_code in DEFAULT_INDUSTRY_MAP:
        return DEFAULT_INDUSTRY_MAP[stock_code]
    name_lower = company_name.lower()
    if any(kw in name_lower for kw in ["银行", "bank"]):
        return "银行"
    if any(kw in name_lower for kw in ["茅台", "五粮液", "酒"]):
        return "白酒"
    if any(kw in name_lower for kw in ["科技", "电子", "芯片"]):
        return "科技硬件"
    if any(kw in name_lower for kw in ["地产", "置业", "万科"]):
        return "房地产"
    return "白酒"  # 默认


def build_comparison_table(target, peers, metrics):
    """构建对比表"""
    table = []
    # 目标公司
    target_row = {"name": target.get("name", target.get("stock_code", "")),
                  "code": target.get("stock_code", ""),
                  "is_target": True}
    for m in metrics:
        target_row[m] = target.get("metrics", {}).get(m, "N/A")
    table.append(target_row)
    # 对标公司
    for peer in peers:
        row = {"name": peer["name"], "code": peer["code"], "is_target": False,
               "market_cap": peer.get("market_cap", 0)}
        for m in metrics:
            row[m] = "参考值"  # 实际应对标数据
        table.append(row)
    return table


def analyze(data):
    """主分析函数"""
    stock_code = data.get("stock_code", "")
    company_name = data.get("company_name", "")
    financials = data.get("financials", {})
    market = data.get("market", "SH")
    # 检测行业
    industry = detect_industry(stock_code, company_name)
    industry_info = GICS_INDUSTRIES.get(industry, GICS_INDUSTRIES["白酒"])
    # 构建目标公司数据
    target = {
        "stock_code": stock_code,
        "name": company_name,
        "market": market,
        "metrics": {}
    }
    # 从财务数据提取指标
    annual = financials.get("annual_reports", [])
    if annual:
        latest = annual[0]
        revenue = latest.get("revenue", 0)
        net_profit = latest.get("net_profit", 0)
        target["metrics"]["营收"] = f"{revenue/1e8:.0f}亿" if revenue else "N/A"
        target["metrics"]["净利润"] = f"{net_profit/1e8:.0f}亿" if net_profit else "N/A"
        if revenue:
            target["metrics"]["净利率"] = f"{net_profit/revenue*100:.1f}%"
        target["metrics"]["ROE"] = f"{latest.get('roe', 0)*100:.1f}%" if latest.get('roe') else "N/A"
    # 国内对标
    domestic_peers = industry_info["domestic_peers"]
    domestic_table = build_comparison_table(target, domestic_peers, industry_info["key_metrics"])
    # 全球对标
    global_peers = industry_info["global_peers"]
    global_table = build_comparison_table(target, global_peers, industry_info["key_metrics"])
    return {
        "stock_code": stock_code,
        "company_name": company_name,
        "industry_position": {
            "gics_code": industry_info["code"],
            "gics_name": industry_info["name"],
            "industry": industry,
            "key_metrics": industry_info["key_metrics"]
        },
        "domestic_peers": {
            "peer_count": len(domestic_peers),
            "peers": domestic_peers,
            "comparison_table": domestic_table
        },
        "global_peers": {
            "peer_count": len(global_peers),
            "peers": global_peers,
            "comparison_table": global_table
        },
        "analysis_summary": f"{company_name}属于{industry}行业(GICS {industry_info['code']})，"
                           f"国内对标{len(domestic_peers)}家，全球对标{len(global_peers)}家。"
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="全球同行业对标分析引擎")
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
