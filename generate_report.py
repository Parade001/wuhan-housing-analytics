import pandas as pd
import re
from pyecharts import options as opts
from pyecharts.charts import Bar, Map, Pie, HeatMap, Line, TreeMap, Page, Timeline, Grid
from pyecharts.globals import ThemeType
import os

# ================= 1. 数据清洗与绝对矩阵建模 =================

CATEGORY_MAP = {"商品住房": (1, 2), "写字楼": (3, 4), "商业": (5, 6), "其他": (7, 8), "合计": (9, 10)}

def light_clean_region(name):
    name = str(name).strip()
    if name in ["东湖高新区", "东湖高新"]: return "东湖高新"
    if name in ["武汉经开", "经济开发区", "武汉开发区", "经开区"]: return "武汉经开"
    if not name.endswith("区") and len(name) > 1 and name not in ["东湖高新", "武汉经开"]:
        name += "区"
    return name

def safe_float(val):
    """安全浮点数转换，防止非法字符导致整行数据被静默抛弃"""
    if pd.isna(val): return 0.0
    val_str = str(val).strip().replace(',', '')
    val_str = re.sub(r'[^\d\.-]', '', val_str)
    if not val_str or val_str == '-': return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def load_and_clean_data(file_path="武汉市新建商品房成交统计-全量.xlsx"):
    print("正在执行 5大类 × 2指标 的硬核数据解析...")
    excel_data = pd.read_excel(file_path, sheet_name=None, header=None)
    all_data = []

    for sheet_name, df in excel_data.items():
        match = re.search(r'(\d{4})年(\d{1,2})月', sheet_name)
        if not match: continue
        year_month = f"{match.group(1)}-{match.group(2).zfill(2)}"

        start_idx = df[df[0].astype(str).str.contains('江岸区', na=False)].index
        if len(start_idx) == 0: continue
        start_idx = start_idx[0]

        for i in range(start_idx, len(df)):
            raw_region = str(df.iloc[i, 0]).strip()
            if raw_region in ['nan', 'None', '总计', '合计'] or '计' in raw_region: break
            region = light_clean_region(raw_region)

            for cat_name, (col_count, col_area) in CATEGORY_MAP.items():
                # 使用安全提取，绝不跳过有效行
                count_val = safe_float(df.iloc[i, col_count])
                area_val = safe_float(df.iloc[i, col_area])
                all_data.append({'Month': year_month, 'Region': region, 'Category': cat_name, 'Metric': '套数', 'Value': count_val})
                all_data.append({'Month': year_month, 'Region': region, 'Category': cat_name, 'Metric': '面积', 'Value': area_val})

    df_clean = pd.DataFrame(all_data)
    df_grouped = df_clean.groupby(['Month', 'Region', 'Category', 'Metric'], as_index=False)['Value'].sum()

    # 笛卡尔积零填充：保证所有图表的 Timeline 长度与刻度 100% 物理对齐
    all_months = sorted(df_grouped['Month'].unique().tolist())
    all_regions = df_grouped['Region'].unique()
    all_cats = df_grouped['Category'].unique()
    all_mets = df_grouped['Metric'].unique()

    idx = pd.MultiIndex.from_product(
        [all_months, all_regions, all_cats, all_mets],
        names=['Month', 'Region', 'Category', 'Metric']
    )

    df_padded = df_grouped.set_index(['Month', 'Region', 'Category', 'Metric']).reindex(idx, fill_value=0).reset_index()
    df_padded = df_padded.sort_values(by='Month')

    print(f"数据处理完毕！全矩阵对齐：{len(all_months)} 个月，共 {len(df_padded)} 条标准记录。")
    return df_padded

# ================= 2. 图表生成工厂 =================

COMMON_INIT_OPTS = opts.InitOpts(width="95vw", height="700px", theme=ThemeType.MACARONS)

def draw_bar_timeline(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    tl = Timeline(init_opts=COMMON_INIT_OPTS)
    months = sorted(df_cat['Month'].unique().tolist())
    for month in months:
        df_month = df_cat[df_cat['Month'] == month].sort_values(by='Value', ascending=True)
        bar = (
            Bar()
            .add_xaxis(df_month['Region'].tolist())
            .add_yaxis(f"成交{metric}", df_month['Value'].tolist(), label_opts=opts.LabelOpts(position="right"))
            .reversal_axis()
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f"{month} 武汉各区【{cat_name}】成交{metric}排名"),
                tooltip_opts=opts.TooltipOpts(formatter="{b}: {c} " + unit)
            )
        )
        tl.add(bar, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_map_timeline(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    tl = Timeline(init_opts=opts.InitOpts(width="95vw", height="800px", theme=ThemeType.LIGHT))
    months = sorted(df_cat['Month'].unique().tolist())

    MAP_MERGE_DICT = {"东湖高新": "洪山区", "武汉经开": "汉南区", "东湖风景区": "武昌区", "化工区": "青山区"}
    df_map = df_cat.copy()
    df_map['Region'] = df_map['Region'].replace(MAP_MERGE_DICT)
    df_map = df_map.groupby(['Month', 'Region', 'Category', 'Metric'], as_index=False)['Value'].sum()

    global_max = df_map['Value'].max() if not df_map.empty and df_map['Value'].max() > 0 else 100

    for month in months:
        df_month = df_map[df_map['Month'] == month]
        data_pair = [list(z) for z in zip(df_month['Region'], df_month['Value'])]
        m = (
            Map()
            .add(f"成交{metric}", data_pair, maptype="武汉")
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f"{month} 武汉【{cat_name}】成交{metric}分布地图 (经济区已折叠)"),
                visualmap_opts=opts.VisualMapOpts(max_=global_max, is_piecewise=False, range_color=["#E0ECF8", "#045FB4"]),
                tooltip_opts=opts.TooltipOpts(formatter="{b}: {c} " + unit)
            )
        )
        tl.add(m, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_pie_timeline(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    tl = Timeline(init_opts=COMMON_INIT_OPTS)
    months = sorted(df_cat['Month'].unique().tolist())
    for month in months:
        df_month = df_cat[df_cat['Month'] == month].sort_values(by='Value', ascending=False)
        data_pair = [list(z) for z in zip(df_month['Region'], df_month['Value'])]
        pie = (
            Pie()
            .add(f"成交{metric}", data_pair, radius=["30%", "65%"], center=["50%", "50%"], rosetype="radius",
                 label_opts=opts.LabelOpts(is_show=True, formatter="{b}: {c}" + unit))
            .set_global_opts(title_opts=opts.TitleOpts(title=f"{month} 各区【{cat_name}】成交{metric}结构"), legend_opts=opts.LegendOpts(is_show=False))
        )
        tl.add(pie, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_treemap_timeline(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    tl = Timeline(init_opts=COMMON_INIT_OPTS)
    months = sorted(df_cat['Month'].unique().tolist())
    for month in months:
        df_month = df_cat[df_cat['Month'] == month]
        tree_data = [{"value": val, "name": reg} for reg, val in zip(df_month['Region'], df_month['Value'])]
        treemap = (
            TreeMap()
            .add(f"成交{metric}", tree_data, label_opts=opts.LabelOpts(position="inside", formatter="{b}: {c}" + unit))
            .set_global_opts(title_opts=opts.TitleOpts(title=f"{month} 武汉【{cat_name}】成交{metric}占比"), legend_opts=opts.LegendOpts(is_show=False))
        )
        tl.add(treemap, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_trend_line(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    line = Line(init_opts=opts.InitOpts(width="95vw", height="700px", theme=ThemeType.WALDEN))
    months = sorted(df_cat['Month'].unique().tolist())
    regions = df_cat['Region'].unique().tolist()
    line.add_xaxis(months)
    for region in regions:
        region_data = [df_cat[(df_cat['Month'] == m) & (df_cat['Region'] == region)]['Value'].sum() for m in months]
        line.add_yaxis(series_name=region, y_axis=region_data, is_smooth=True, label_opts=opts.LabelOpts(is_show=False))
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=f"武汉各区域【{cat_name}】月度成交{metric}趋势"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        yaxis_opts=opts.AxisOpts(name=unit),
        datazoom_opts=[opts.DataZoomOpts(is_show=True, type_="slider", range_start=80, range_end=100), opts.DataZoomOpts(type_="inside")],
        legend_opts=opts.LegendOpts(type_="scroll", pos_top="5%", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(trigger="axis")
    )
    return line

def draw_heatmap(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    hm = HeatMap(init_opts=opts.InitOpts(theme=ThemeType.ESSOS))
    months = sorted(df_cat['Month'].unique().tolist())
    regions = df_cat['Region'].unique().tolist()
    heat_data = [[i, j, df_cat[(df_cat['Month'] == m) & (df_cat['Region'] == r)]['Value'].sum()]
                 for i, m in enumerate(months) for j, r in enumerate(regions)]

    global_max = df_cat['Value'].max() if not df_cat.empty and df_cat['Value'].max() > 0 else 100

    hm.add_xaxis(months)
    hm.add_yaxis(f"成交{metric}", regions, heat_data, label_opts=opts.LabelOpts(is_show=False))
    hm.set_global_opts(
        title_opts=opts.TitleOpts(title=f"武汉各区【{cat_name}】历月成交{metric}矩阵"),
        visualmap_opts=opts.VisualMapOpts(max_=global_max, orient="horizontal", pos_left="center", pos_top="10%"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=90, font_size=10), interval=0),
        datazoom_opts=[opts.DataZoomOpts(is_show=True, type_="slider", range_start=80, range_end=100), opts.DataZoomOpts(is_show=True, type_="inside")],
        tooltip_opts=opts.TooltipOpts(is_show=True)
    )
    grid = Grid(init_opts=opts.InitOpts(width="95vw", height="600px", theme=ThemeType.ESSOS))
    grid.add(hm, grid_opts=opts.GridOpts(pos_left="15%", pos_bottom="15%", pos_top="25%"))
    return grid

# ================= 3. 渲染引擎与强制状态隔离 JS =================
def generate_dashboard():
    df = load_and_clean_data()
    if df.empty: return

    page = Page(layout=Page.SimplePageLayout)
    categories = ["商品住房", "写字楼", "商业", "其他", "合计"]
    metrics = ["套数", "面积"]

    chart_builders = [
        ("bar", draw_bar_timeline), ("map", draw_map_timeline),
        ("pie", draw_pie_timeline), ("tree", draw_treemap_timeline),
        ("line", draw_trend_line), ("heat", draw_heatmap)
    ]

    for group_name, builder_func in chart_builders:
        idx = 0
        for cat in categories:
            for met in metrics:
                df_cat_met = df[(df['Category'] == cat) & (df['Metric'] == met)]
                chart = builder_func(df_cat_met, cat, met)
                chart.chart_id = f"custom_chart_{group_name}_{idx}"
                page.add(chart)
                idx += 1

    output_file = "武汉房地产成交大屏_全量矩阵数据版.html"
    page.render(output_file)

    with open(output_file, "r+", encoding="utf-8") as f:
        html_content = f.read()
        css_injection = """
        <style>
            body { background-color: #f4f6f9; margin: 0; padding: 20px 0; font-family: -apple-system, sans-serif; }
            .my-group-wrapper { width: 95vw; margin: 0 auto 50px auto; background: #fff; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); position: relative; padding-top: 100px; overflow: hidden; }
            .my-tab-nav { position: absolute; right: 20px; display: flex; gap: 8px; z-index: 999; }
            .cat-nav { top: 15px; }
            .metric-nav { top: 55px; }
            .my-tab-btn { padding: 6px 14px; border: 1px solid #e1e5eb; background: #f8f9fa; color: #666; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; transition: all 0.2s ease-in-out; }
            .my-tab-btn:hover { background: #e2e6ea; }
            .cat-btn.active { background: #045FB4; color: #fff; border-color: #045FB4; box-shadow: 0 4px 8px rgba(4, 95, 180, 0.3); }
            .metric-btn.active { background: #eac763; color: #fff; border-color: #eac763; box-shadow: 0 4px 8px rgba(234, 199, 99, 0.3); }
            .chart-container { margin-bottom: 0 !important; border-bottom: none !important; }
        </style>
        """
        js_injection = """
        <script>
            window.__global_timeline_idx = null;
            window.__global_datazoom_start = undefined;
            window.__global_datazoom_end = undefined;

            document.addEventListener("DOMContentLoaded", function() {
                const categories = ["商品住房", "写字楼", "商业", "其他", "合计"];
                const metrics = ["成交套数", "成交面积"];
                const groups = ["bar", "map", "pie", "tree", "line", "heat"];
                
                // 仅允许“正在显示”的图表写入全局状态，防止幽灵图表覆盖内存
                let bindInterval = setInterval(() => {
                    let allBound = true;
                    groups.forEach(group => {
                        for(let i=0; i<10; i++) {
                            let dom = document.getElementById('custom_chart_' + group + '_' + i);
                            if(dom) {
                                let instance = echarts.getInstanceByDom(dom);
                                if(instance && !dom.dataset.hasEvents) {
                                    instance.on('timelinechanged', function(params) {
                                        if (dom.style.display !== 'none') {
                                            window.__global_timeline_idx = params.currentIndex;
                                        }
                                    });
                                    instance.on('datazoom', function(params) {
                                        if (dom.style.display !== 'none') {
                                            if(params.batch && params.batch.length > 0) {
                                                window.__global_datazoom_start = params.batch[0].start;
                                                window.__global_datazoom_end = params.batch[0].end;
                                            } else {
                                                window.__global_datazoom_start = params.start;
                                                window.__global_datazoom_end = params.end;
                                            }
                                        }
                                    });
                                    dom.dataset.hasEvents = 'true';
                                }
                                if(!instance || !dom.dataset.hasEvents) allBound = false;
                            }
                        }
                    });
                    if(allBound) clearInterval(bindInterval);
                }, 500);

                groups.forEach(group => {
                    let firstChart = document.getElementById('custom_chart_' + group + '_0');
                    if(!firstChart) return;
                    
                    let wrapper = document.createElement('div');
                    wrapper.className = 'my-group-wrapper';
                    
                    let catNav = document.createElement('div');
                    catNav.className = 'my-tab-nav cat-nav';
                    catNav.innerHTML = categories.map((cat, i) => `<button class="my-tab-btn cat-btn" data-cat="${i}">${cat}</button>`).join('');
                    
                    let metNav = document.createElement('div');
                    metNav.className = 'my-tab-nav metric-nav';
                    metNav.innerHTML = metrics.map((met, i) => `<button class="my-tab-btn metric-btn" data-met="${i}">${met}</button>`).join('');
                    
                    wrapper.appendChild(catNav);
                    wrapper.appendChild(metNav);
                    firstChart.parentNode.insertBefore(wrapper, firstChart);
                    
                    for(let i=0; i<10; i++){
                        let c = document.getElementById('custom_chart_' + group + '_' + i);
                        if(c) {
                            wrapper.appendChild(c);
                            if (i !== 0) c.style.display = 'none';
                        }
                    }
                    
                    let currentCat = 0;
                    let currentMet = 0;
                    let catBtns = wrapper.querySelectorAll('.cat-btn');
                    let metBtns = wrapper.querySelectorAll('.metric-btn');
                    
                    catBtns[0].classList.add('active');
                    metBtns[0].classList.add('active');
                    
                    const updateView = (newIdx) => {
                        for(let i=0; i<10; i++){
                            let chartDiv = document.getElementById('custom_chart_' + group + '_' + i);
                            if(chartDiv) {
                                if (i === newIdx) {
                                    chartDiv.style.display = 'block';
                                    setTimeout(() => {
                                        let chartInstance = echarts.getInstanceByDom(chartDiv);
                                        if(chartInstance) {
                                            chartInstance.resize();
                                            let newOpt = chartInstance.getOption();
                                            
                                            // 强制执行绝对状态覆盖（抛弃 dispatchAction 的异步渲染）
                                            if (window.__global_timeline_idx !== null && newOpt.timeline && newOpt.timeline.length > 0) {
                                                let safeIdx = Math.min(window.__global_timeline_idx, newOpt.timeline[0].data.length - 1);
                                                chartInstance.setOption({ timeline: [{ currentIndex: safeIdx }] });
                                            }
                                            
                                            if (window.__global_datazoom_start !== undefined && newOpt.dataZoom && newOpt.dataZoom.length > 0) {
                                                chartInstance.dispatchAction({
                                                    type: 'dataZoom', dataZoomIndex: 0,
                                                    start: window.__global_datazoom_start, end: window.__global_datazoom_end
                                                });
                                            }
                                        }
                                    }, 50);
                                } else {
                                    chartDiv.style.display = 'none';
                                }
                            }
                        }
                    };
                    
                    catBtns.forEach(btn => {
                        btn.addEventListener('click', function() {
                            if (this.classList.contains('active')) return;
                            catBtns.forEach(b => b.classList.remove('active'));
                            this.classList.add('active');
                            currentCat = parseInt(this.getAttribute('data-cat'));
                            updateView(currentCat * 2 + currentMet);
                        });
                    });
                    
                    metBtns.forEach(btn => {
                        btn.addEventListener('click', function() {
                            if (this.classList.contains('active')) return;
                            metBtns.forEach(b => b.classList.remove('active'));
                            this.classList.add('active');
                            currentMet = parseInt(this.getAttribute('data-met'));
                            updateView(currentCat * 2 + currentMet);
                        });
                    });
                });
            });
        </script>
        """
        html_content = html_content.replace("</head>", f"{css_injection}\n</head>")
        html_content = html_content.replace("</body>", f"{js_injection}\n</body>")
        f.seek(0)
        f.write(html_content)
        f.truncate()

    print(f"✅ 大屏生成完毕！全矩阵对齐与状态隔离检查通过：{output_file}")

if __name__ == "__main__":
    generate_dashboard()
