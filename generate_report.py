import pandas as pd
import re
from pyecharts import options as opts
from pyecharts.charts import Bar, Map, Pie, HeatMap, Line, TreeMap, Page, Timeline , Grid
from pyecharts.globals import ThemeType
import os

# ================= 1. 数据清洗与预处理 =================

# 建立区域名称映射字典（解决房管局特有经济区在标准地图上无法识别的问题）
REGION_MAPPING = {
    "东湖高新": "洪山区",
    "东湖高新区": "洪山区",
    "武汉经开": "汉南区",
    "经济开发区": "汉南区",
    "经开区": "汉南区",
    "东湖风景区": "武昌区",
    "化工区": "青山区",
    "武汉开发区": "汉南区"
}

def clean_region_name(name):
    """清洗并标准化区域名称"""
    name = str(name).strip()
    # 去除多余的后缀，但保留'区'
    for k, v in REGION_MAPPING.items():
        if k in name:
            return v
    if not name.endswith("区") and len(name) > 1:
        name += "区"
    return name

def load_and_clean_data(file_path="武汉市新建商品房成交统计-全量.xlsx"):
    print("正在加载并清洗数据，请稍候...")
    excel_data = pd.read_excel(file_path, sheet_name=None, header=None)

    all_data = []

    for sheet_name, df in excel_data.items():
        match = re.search(r'(\d{4})年(\d{1,2})月', sheet_name)
        if not match:
            continue
        year_month = f"{match.group(1)}-{match.group(2).zfill(2)}"

        start_idx = df[df[0] == '江岸区'].index
        if len(start_idx) == 0:
            continue
        start_idx = start_idx[0]

        for i in range(start_idx, len(df)):
            raw_region = str(df.iloc[i, 0]).strip()
            if raw_region in ['nan', 'None', '总计', '合计'] or '计' in raw_region:
                break

            region = clean_region_name(raw_region)

            try:
                volume = float(df.iloc[i, 1])
                all_data.append({'Month': year_month, 'Region': region, 'Volume': volume})
            except (ValueError, TypeError):
                continue

    df_clean = pd.DataFrame(all_data)
    # 因为我们合并了某些区域（如东湖高新并入洪山），需要按月和区域重新求和汇总
    df_grouped = df_clean.groupby(['Month', 'Region'], as_index=False)['Volume'].sum()
    df_grouped = df_grouped.sort_values(by='Month')
    print(f"数据清洗完毕！共提取 {len(df_grouped['Month'].unique())} 个月的数据。")
    return df_grouped

# ================= 2. 图表生成函数 (增大尺寸 + 留白) =================
# 统一初始化配置：宽度95视口宽度，高度700px
COMMON_INIT_OPTS = opts.InitOpts(width="95vw", height="700px", theme=ThemeType.MACARONS)

def draw_bar_timeline(df):
    tl = Timeline(init_opts=COMMON_INIT_OPTS)
    months = sorted(df['Month'].unique().tolist())
    for month in months:
        df_month = df[df['Month'] == month].sort_values(by='Volume', ascending=True)
        bar = (
            Bar()
            .add_xaxis(df_month['Region'].tolist())
            .add_yaxis("成交套数", df_month['Volume'].tolist(), label_opts=opts.LabelOpts(position="right"))
            .reversal_axis()
            .set_global_opts(title_opts=opts.TitleOpts(title=f"{month} 武汉各区商品住房成交排名"))
        )
        tl.add(bar, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_map_timeline(df):
    tl = Timeline(init_opts=opts.InitOpts(width="95vw", height="800px", theme=ThemeType.LIGHT))
    months = sorted(df['Month'].unique().tolist())
    global_max = df['Volume'].max() if not df.empty else 1000

    for month in months:
        df_month = df[df['Month'] == month]
        data_pair = [list(z) for z in zip(df_month['Region'], df_month['Volume'])]
        m = (
            Map()
            .add("成交套数", data_pair, maptype="武汉")
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f"{month} 武汉商品住房成交真实行政区热力图"),
                visualmap_opts=opts.VisualMapOpts(max_=global_max, is_piecewise=False, range_color=["#E0ECF8", "#045FB4"]),
            )
        )
        tl.add(m, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_pie_timeline(df):
    tl = Timeline(init_opts=COMMON_INIT_OPTS)
    months = sorted(df['Month'].unique().tolist())
    for month in months:
        df_month = df[df['Month'] == month].sort_values(by='Volume', ascending=False)
        data_pair = [list(z) for z in zip(df_month['Region'], df_month['Volume'])]
        pie = (
            Pie()
            .add("成交套数", data_pair, radius=["30%", "65%"], center=["50%", "50%"], rosetype="radius",
                 label_opts=opts.LabelOpts(is_show=True, formatter="{b}: {c}套"))
            .set_global_opts(title_opts=opts.TitleOpts(title=f"{month} 各区成交结构对比"), legend_opts=opts.LegendOpts(is_show=False))
        )
        tl.add(pie, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_treemap_timeline(df):
    tl = Timeline(init_opts=COMMON_INIT_OPTS)
    months = sorted(df['Month'].unique().tolist())
    for month in months:
        df_month = df[df['Month'] == month]
        tree_data = [{"value": val, "name": reg} for reg, val in zip(df_month['Region'], df_month['Volume'])]
        treemap = (
            TreeMap()
            .add("成交占比", tree_data, label_opts=opts.LabelOpts(position="inside"))
            .set_global_opts(title_opts=opts.TitleOpts(title=f"{month} 武汉商品住房成交占比结构"), legend_opts=opts.LegendOpts(is_show=False))
        )
        tl.add(treemap, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_trend_line(df):
    # 增加高度为 700px，宽度95vw
    line = Line(init_opts=opts.InitOpts(width="95vw", height="700px", theme=ThemeType.WALDEN))
    months = sorted(df['Month'].unique().tolist())
    regions = df['Region'].unique().tolist()

    line.add_xaxis(months)
    for region in regions:
        region_data = [df[(df['Month'] == m) & (df['Region'] == region)]['Volume'].sum() for m in months]
        line.add_yaxis(series_name=region, y_axis=region_data, is_smooth=True, label_opts=opts.LabelOpts(is_show=False))

    line.set_global_opts(
        title_opts=opts.TitleOpts(title="武汉各区域月度成交趋势 (支持底部滑动缩放)"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        yaxis_opts=opts.AxisOpts(name="套数"),
        # 重点：加入范围缩放滑块，默认只显示最后 20% 的时间范围，避免拥挤
        datazoom_opts=[
            opts.DataZoomOpts(is_show=True, type_="slider", range_start=80, range_end=100),
            opts.DataZoomOpts(type_="inside") # 支持鼠标滚轮缩放
        ],
        # 重点：图例设置为可滚动，防止挤占主图空间
        legend_opts=opts.LegendOpts(type_="scroll", pos_top="5%", pos_left="center")
    )
    return line

def draw_heatmap(df):
    # 1. 先创建 HeatMap 实例（注意：这里的 init_opts 建议移交给外层的 Grid）
    hm = HeatMap(init_opts=opts.InitOpts(theme=ThemeType.ESSOS))

    months = sorted(df['Month'].unique().tolist())
    regions = df['Region'].unique().tolist()

    heat_data = [[i, j, df[(df['Month'] == m) & (df['Region'] == r)]['Volume'].sum()]
                 for i, m in enumerate(months) for j, r in enumerate(regions)]

    hm.add_xaxis(months)
    hm.add_yaxis(
        "成交套数",
        regions,
        heat_data,
        label_opts=opts.LabelOpts(is_show=False)
    )

    # 2. set_global_opts 中删掉 grid_opts
    hm.set_global_opts(
        title_opts=opts.TitleOpts(title="武汉各区历月成交热力矩阵", subtitle="点击方块查看数值，下方滑块可缩放"),
        visualmap_opts=opts.VisualMapOpts(
            max_=df['Volume'].max(),
            orient="horizontal",
            pos_left="center",
            pos_top="10%"
        ),
        xaxis_opts=opts.AxisOpts(
            axislabel_opts=opts.LabelOpts(rotate=90, font_size=10),
            interval=0
        ),
        datazoom_opts=[
            opts.DataZoomOpts(is_show=True, type_="slider", range_start=80, range_end=100),
            opts.DataZoomOpts(is_show=True, type_="inside")
        ],
        tooltip_opts=opts.TooltipOpts(is_show=True)
    )

    # 3. 【核心修复】使用 Grid 容器来承载热力图并设置边距
    grid = (
        Grid(init_opts=opts.InitOpts(width="95vw", height="600px", theme=ThemeType.ESSOS))
        .add(
            hm,
            # 这里的 grid_opts 是有效的，用于解决移动端标签截断问题
            grid_opts=opts.GridOpts(pos_left="15%", pos_bottom="15%", pos_top="25%")
        )
    )
    return grid

# ================= 3. 整合渲染 HTML (注入 CSS 间距) =================
def generate_dashboard():
    df = load_and_clean_data()
    if df.empty:
        print("提取数据为空，请检查Excel文件格式。")
        return

    print("数据准备完毕，正在生成超大屏可视化报表...")

    page = Page(layout=Page.SimplePageLayout)
    page.add(
        draw_bar_timeline(df),
        draw_map_timeline(df),
        draw_pie_timeline(df),
        draw_treemap_timeline(df),
        draw_trend_line(df),
        draw_heatmap(df)
    )

    output_file = "武汉房地产成交大屏_优化版.html"
    page.render(output_file)

    # 暴力但有效的后处理：往生成的 HTML 中注入一段 CSS 控制间距
    with open(output_file, "r+", encoding="utf-8") as f:
        html_content = f.read()
        # 在 head 标签结束前注入 CSS
        css_injection = """
        <style>
            .chart-container {
                margin-bottom: 100px !important;
                padding-bottom: 20px;
                border-bottom: 2px dashed #eee;
            }
        </style>
        """
        html_content = html_content.replace("</head>", f"{css_injection}\n</head>")
        f.seek(0)
        f.write(html_content)
        f.truncate()

    print(f"✅ 可视化大屏生成完毕！请用浏览器双击打开：{output_file}")

if __name__ == "__main__":
    generate_dashboard()
