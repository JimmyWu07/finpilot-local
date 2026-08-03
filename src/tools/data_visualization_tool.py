"""
FinPilot 数据对比可视化插件 - LangChain Tool 封装
将各 Skill 产出的报告数据渲染为 6 种图表（饼图/折线图/柱状图/雷达图/树状图/网图）
输出 base64 PNG 拼接 Markdown 图片语法，供 Coze 对话框直接显示
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io, base64, json
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context

COLORS = ['#5470C6', '#91CC75', '#FAC858', '#EE6666', '#73C0DE', '#3BA272', '#FC8452', '#9A60B4']


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def draw_pie(title, data, desc):
    try:
        names = data.get('names', [])
        values = data.get('values', [])
        if not names or not values:
            return None
        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        ax.pie(values, labels=names, autopct='%1.1f%%', startangle=90, colors=COLORS[:len(names)])
        ax.set_title(title, fontsize=12, fontweight='bold')
        b64 = fig_to_base64(fig)
        return f"## {title}\n\n![{title}](data:image/png;base64,{b64})\n\n> {desc}"
    except Exception:
        return None


def draw_line(title, data, desc):
    try:
        x_axis = data.get('x_axis', [])
        series_list = data.get('series', [])
        if not x_axis or not series_list:
            return None
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        for i, s in enumerate(series_list):
            ax.plot(x_axis, s.get('values', []), marker='o', label=s.get('name', ''), color=COLORS[i % len(COLORS)])
        ax.set_xlabel('时间', fontsize=10)
        ax.set_ylabel('数值', fontsize=10)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        b64 = fig_to_base64(fig)
        return f"## {title}\n\n![{title}](data:image/png;base64,{b64})\n\n> {desc}"
    except Exception:
        return None


def draw_bar(title, data, desc):
    try:
        names = data.get('names', [])
        values = data.get('values', [])
        if not names or not values:
            return None
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        x = range(len(names))
        ax.bar(x, values, color=COLORS[:len(names)])
        ax.set_xticks(list(x))
        ax.set_xticklabels(names, rotation=30, ha='right', fontsize=8)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        b64 = fig_to_base64(fig)
        return f"## {title}\n\n![{title}](data:image/png;base64,{b64})\n\n> {desc}"
    except Exception:
        return None


def draw_radar(title, data, desc):
    try:
        indicators = data.get('indicators', [])
        series_list = data.get('series', [])
        if not indicators or not series_list:
            return None
        angles = np.linspace(0, 2 * np.pi, len(indicators), endpoint=False).tolist()
        angles += angles[:1]
        fig = plt.figure(figsize=(6, 6), dpi=100)
        ax = fig.add_subplot(111, polar=True)
        for i, s in enumerate(series_list):
            vals = s.get('values', []) + s.get('values', [])[:1]
            ax.plot(angles, vals, marker='o', label=s.get('name', ''), color=COLORS[i % len(COLORS)])
            ax.fill(angles, vals, alpha=0.15, color=COLORS[i % len(COLORS)])
        ax.set_thetagrids(np.degrees(angles[:-1]), [ind.get('name', '') for ind in indicators], fontsize=9)  # type: ignore
        ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=8)
        b64 = fig_to_base64(fig)
        return f"## {title}\n\n![{title}](data:image/png;base64,{b64})\n\n> {desc}"
    except Exception:
        return None


def draw_tree(title, data, desc):
    try:
        root = data.get('root', {})
        if not root:
            return None

        def _draw(node, x, y, dx, dy, ax):
            ax.text(x, y, node.get('name', ''), ha='center', va='center', fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='#91CC75', alpha=0.8))
            if 'children' in node and node['children']:
                n = len(node['children'])
                for i, child in enumerate(node['children']):
                    cx = x + (i - (n - 1) / 2) * dx
                    cy = y - dy
                    ax.plot([x, cx], [y - 0.15, cy + 0.15], 'k-', lw=1)
                    _draw(child, cx, cy, dx / 1.8, dy, ax)

        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
        _draw(root, 0, 0, 4, 1.5, ax)
        ax.axis('off')
        ax.set_title(title, fontsize=12, fontweight='bold')
        b64 = fig_to_base64(fig)
        return f"## {title}\n\n![{title}](data:image/png;base64,{b64})\n\n> {desc}"
    except Exception:
        return None


def draw_network(title, data, desc):
    try:
        nodes = data.get('nodes', [])
        links = data.get('links', [])
        if not nodes:
            return None
        if len(nodes) > 12:
            keep_ids = {n.get('id', '') for n in nodes[:12]}
            nodes = nodes[:12]
            links = [l for l in links if l.get('source', '') in keep_ids and l.get('target', '') in keep_ids]

        n = len(nodes)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        pos = {node.get('id', i): (np.cos(a) * 3, np.sin(a) * 3) for i, (node, a) in enumerate(zip(nodes, angles))}

        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        for link in links:
            src, tgt = link.get('source', ''), link.get('target', '')
            if src not in pos or tgt not in pos:
                continue
            x = [pos[src][0], pos[tgt][0]]
            y = [pos[src][1], pos[tgt][1]]
            ax.plot(x, y, 'gray', lw=1.5, alpha=0.5)
            mx, my = sum(x) / 2, sum(y) / 2
            ax.text(mx, my, link.get('relation', ''), fontsize=7, color='gray', ha='center')
        color_map = {'核心': '#EE6666', '上游': '#5470C6', '下游': '#91CC75', '同业': '#FAC858'}
        for node in nodes:
            px, py = pos.get(node.get('id', ''), (0, 0))
            c = color_map.get(node.get('category', ''), '#5470C6')
            ax.scatter(px, py, s=400, c=c, zorder=5, edgecolors='black')
            ax.text(px, py, node.get('name', ''), ha='center', va='center', color='white', fontsize=8)
        ax.axis('off')
        ax.set_title(title, fontsize=12, fontweight='bold')
        b64 = fig_to_base64(fig)
        return f"## {title}\n\n![{title}](data:image/png;base64,{b64})\n\n> {desc}"
    except Exception:
        return None


CHART_DRAWERS = {
    'pie': draw_pie, 'line': draw_line, 'bar': draw_bar,
    'radar': draw_radar, 'tree': draw_tree, 'network': draw_network,
}

INTENT_KEYWORDS = {
    'pie': ['占比', '构成', '分布', '比例'],
    'line': ['趋势', '走势', '变化', '预测'],
    'bar': ['对比', '比较', '排名', 'vs'],
    'tree': ['分类', '层级', '结构', '属于'],
    'network': ['关联', '关系', '传导', '概念股'],
    'radar': ['综合', '维度', '评估', '雷达'],
}


def _extract_charts(fin, sen, ind, rsk, pred):
    tasks = []
    # 1. 饼图: 主营业务收入构成（兼容 dict 和 {names, values} 两种格式）
    if fin:
        biz = fin.get('business_segments', {})
        if isinstance(biz, dict) and biz:
            if 'names' in biz and 'values' in biz:
                names, values = biz['names'], biz['values']
            else:
                names = list(biz.keys())
                values = [float(v) for v in biz.values()]
            if names and values:
                tasks.append({'type': 'pie', 'title': '主营业务收入构成',
                              'data': {'names': names, 'values': values},
                              'desc': '各业务板块营收占比分布'})
        quarters = fin.get('quarterly_trend', {})
        if isinstance(quarters, dict) and quarters:
            if 'x_axis' in quarters:
                x_axis = quarters['x_axis']
            else:
                x_axis = list(quarters.keys())
            if 'series' in quarters:
                series = quarters['series']
            elif 'revenue' in quarters or 'profit' in quarters:
                series = []
                if 'revenue' in quarters:
                    series.append({'name': '营收', 'values': quarters['revenue']})
                if 'profit' in quarters:
                    series.append({'name': '净利润', 'values': quarters['profit']})
            else:
                series = [{'name': '数值', 'values': list(quarters.values())}]
            if x_axis and series:
                tasks.append({'type': 'line', 'title': '季度营收与净利润趋势',
                              'data': {'x_axis': x_axis, 'series': series},
                              'desc': '营收与净利润季度变化趋势'})
    # 2. 柱状图: 同行业 ROE 对比
    if ind:
        peers = ind.get('peers', [])
        if peers:
            names = [p.get('name', '') for p in peers]
            values = [p.get('roe', 0) for p in peers]
            tasks.append({'type': 'bar', 'title': '同行业 ROE 对比',
                          'data': {'names': names, 'values': values},
                          'desc': '目标公司与同业 ROE 水平对比'})
    # 3. 雷达图: 五维风险雷达（兼容 dict 和 {indicators, series} 两种格式）
    if rsk:
        radar = rsk.get('radar_chart', {})
        if isinstance(radar, dict) and radar:
            if 'indicators' in radar and 'series' in radar:
                indicators = radar['indicators']
                series_list = radar['series']
            else:
                indicators = [{'name': k} for k in radar.keys()]
                vals = [float(v) for v in radar.values()]
                series_list = [{'name': '风险评估', 'values': vals}]
            if indicators and series_list:
                tasks.append({'type': 'radar', 'title': '五维风险雷达图',
                              'data': {'indicators': indicators, 'series': series_list},
                              'desc': '财务/舆情/行业/跨境/治理五维风险评分'})
    # 4. 树状图: 行业分类树
    if ind:
        tree_data = ind.get('industry_tree', {})
        if tree_data:
            tasks.append({'type': 'tree', 'title': '行业分类层级图',
                          'data': {'root': tree_data},
                          'desc': '目标公司所属行业分类层级结构'})
    # 5. 网图: 概念股/供应链关联
    if ind:
        concept = ind.get('concept_stocks', {})
        if isinstance(concept, dict) and concept.get('nodes'):
            tasks.append({'type': 'network', 'title': '概念股与供应链关联图',
                          'data': {'nodes': concept.get('nodes', []), 'links': concept.get('links', [])},
                          'desc': '核心概念股与上下游供应链关联关系'})
    # 6. 折线图: A股预测曲线
    if pred:
        pred_data = pred.get('prediction_curve', {})
        if isinstance(pred_data, dict) and pred_data.get('x_axis'):
            tasks.append({'type': 'line', 'title': 'A股短中期趋势预测',
                          'data': {'x_axis': pred_data['x_axis'], 'series': pred_data.get('series', [])},
                          'desc': '基于多因子模型的短中期价格预测区间（仅供教学参考）'})
    return tasks


def _filter_by_intent(tasks, intent):
    if not intent:
        return tasks
    matched_types = set()
    for chart_type, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in intent:
                matched_types.add(chart_type)
    if not matched_types:
        return tasks
    return [t for t in tasks if t['type'] in matched_types]


def _render_charts(tasks):
    markdown_parts, chart_types, errors = [], [], []
    for task in tasks:
        drawer = CHART_DRAWERS.get(task['type'])
        if not drawer:
            errors.append(f"未知图表类型: {task['type']}")
            continue
        try:
            result = drawer(task['title'], task['data'], task['desc'])
            if result:
                markdown_parts.append(result)
                chart_types.append(task['type'])
            else:
                errors.append(f"{task['type']} 图表数据不足，已跳过")
        except Exception as e:
            errors.append(f"{task['type']} 生成失败: {str(e)}")
    markdown = "\n\n---\n\n".join(markdown_parts) if markdown_parts else "暂无可用数据"
    return markdown, chart_types, errors


@tool
def generate_charts(
    fin_report: str = "{}",
    sentiment_report: str = "{}",
    industry_report: str = "{}",
    risk_report: str = "{}",
    prediction_report: str = "{}",
    user_intent: str = ""
) -> str:
    """数据对比可视化插件。将财务分析、舆情分析、行业对标、风险评估、趋势预测等报告数据渲染为饼图、折线图、柱状图、雷达图、树状图、网图等PNG图片，以Markdown图片语法输出。

    参数说明:
    - fin_report: 财务分析报告JSON字符串（含business_segments/quarterly_trend字段）
    - sentiment_report: 舆情分析报告JSON字符串
    - industry_report: 行业对标报告JSON字符串（含peers/industry_tree/concept_stocks字段）
    - risk_report: 风险评估报告JSON字符串（含radar_chart字段）
    - prediction_report: 趋势预测报告JSON字符串（含prediction_curve字段）
    - user_intent: 用户意图关键词，用于智能选型（如"占比"生成饼图，"趋势"生成折线图，"对比"生成柱状图等）

    支持的图表类型:
    - pie: 饼图（占比/构成/分布/比例）
    - line: 折线图（趋势/走势/变化/预测）
    - bar: 柱状图（对比/比较/排名/vs）
    - radar: 雷达图（综合/维度/评估）
    - tree: 树状图（分类/层级/结构）
    - network: 网图（关联/关系/传导/概念股）
    """
    ctx = request_context.get() or new_context(method="generate_charts")
    try:
        fin = json.loads(fin_report) if fin_report else {}
    except (json.JSONDecodeError, TypeError):
        fin = {}
    try:
        sen = json.loads(sentiment_report) if sentiment_report else {}
    except (json.JSONDecodeError, TypeError):
        sen = {}
    try:
        ind = json.loads(industry_report) if industry_report else {}
    except (json.JSONDecodeError, TypeError):
        ind = {}
    try:
        rsk = json.loads(risk_report) if risk_report else {}
    except (json.JSONDecodeError, TypeError):
        rsk = {}
    try:
        pred = json.loads(prediction_report) if prediction_report else {}
    except (json.JSONDecodeError, TypeError):
        pred = {}

    tasks = _extract_charts(fin, sen, ind, rsk, pred)
    tasks = _filter_by_intent(tasks, user_intent)

    if not tasks:
        return "暂无可用数据"

    markdown, chart_types, errors = _render_charts(tasks)
    return markdown
