import pandas as pd
import re
from pyecharts import options as opts
from pyecharts.charts import Bar, Map, Pie, HeatMap, Line, TreeMap, Page, Timeline, Grid
from pyecharts.globals import ThemeType
import os
import json

# ================= 1. 数据清洗与多维度预处理 =================

CATEGORY_MAP = {"商品住房": (1, 2), "写字楼": (3, 4), "商业": (5, 6), "其他": (7, 8), "合计": (9, 10)}
TOTAL_KEYWORDS = ['总计', '合计', '全市总计', '全市合计', '全市']

def light_clean_region(name):
    name = str(name).strip()
    if name in ["东湖高新区", "东湖高新"]: return "东湖高新"
    if name in ["武汉经开", "经济开发区", "武汉开发区", "经开区"]: return "武汉经开"
    if not name.endswith("区") and len(name) > 1 and name not in ["东湖高新", "武汉经开"]:
        name += "区"
    return name

def safe_extract(val, metric_type):
    if pd.isna(val): return 0 if metric_type == '套数' else 0.0
    val_str = str(val).strip().replace(',', '')
    val_str = re.sub(r'[^\d\.-]', '', val_str)
    if not val_str or val_str == '-': return 0 if metric_type == '套数' else 0.0
    try:
        f_val = float(val_str)
        return int(f_val) if metric_type == '套数' else round(f_val, 1)
    except ValueError:
        return 0 if metric_type == '套数' else 0.0

def load_and_clean_data(file_path="武汉市新建商品房成交统计-全量.xlsx"):
    print("正在执行包含【全市合计】的全维矩阵解析...")
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
            if pd.isna(df.iloc[i, 0]) or raw_region in ['nan', 'None', '']: continue

            is_total_row = any(k in raw_region for k in TOTAL_KEYWORDS)
            region = '⭐ 全市总计' if is_total_row else light_clean_region(raw_region)

            for cat_name, (col_count, col_area) in CATEGORY_MAP.items():
                count_val = safe_extract(df.iloc[i, col_count], '套数')
                area_val = safe_extract(df.iloc[i, col_area], '面积')

                if count_val > 0 or is_total_row:
                    all_data.append({'Month': year_month, 'Region': region, 'Category': cat_name, 'Metric': '套数', 'Value': count_val})
                if area_val > 0 or is_total_row:
                    all_data.append({'Month': year_month, 'Region': region, 'Category': cat_name, 'Metric': '面积', 'Value': area_val})

            if is_total_row: break

    df_clean = pd.DataFrame(all_data)
    df_grouped = df_clean.groupby(['Month', 'Region', 'Category', 'Metric'], as_index=False)['Value'].sum()

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
    return df_padded

# ================= 2. 图表生成工厂 =================

COMMON_INIT_OPTS = opts.InitOpts(width="95vw", height="700px", theme=ThemeType.MACARONS)

def draw_bar_timeline(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    tl = Timeline(init_opts=COMMON_INIT_OPTS)
    months = sorted(df_cat['Month'].unique().tolist())
    for month in months:
        df_month = df_cat[(df_cat['Month'] == month) & (df_cat['Region'] != '⭐ 全市总计')].sort_values(by='Value', ascending=True)
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
    df_map = df_cat[df_cat['Region'] != '⭐ 全市总计'].copy()
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
        df_month = df_cat[(df_cat['Month'] == month) & (df_cat['Region'] != '⭐ 全市总计')].sort_values(by='Value', ascending=False)
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
        df_month = df_cat[(df_cat['Month'] == month) & (df_cat['Region'] != '⭐ 全市总计')]
        tree_data = [{"value": val, "name": reg} for reg, val in zip(df_month['Region'], df_month['Value'])]
        treemap = (
            TreeMap()
            .add(f"成交{metric}", tree_data, label_opts=opts.LabelOpts(position="inside", formatter="{b}: {c}" + unit))
            .set_global_opts(title_opts=opts.TitleOpts(title=f"{month} 武汉【{cat_name}】成交{metric}占比"), legend_opts=opts.LegendOpts(is_show=False))
        )
        tl.add(treemap, month)
    tl.add_schema(is_auto_play=False, play_interval=1500)
    return tl

def draw_heatmap(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    hm = HeatMap(init_opts=opts.InitOpts(theme=ThemeType.ESSOS))
    months = sorted(df_cat['Month'].unique().tolist())
    regions = sorted([r for r in df_cat['Region'].unique() if r != '⭐ 全市总计'])
    df_filtered = df_cat[df_cat['Region'] != '⭐ 全市总计']
    heat_data = [[i, j, df_filtered[(df_filtered['Month'] == m) & (df_filtered['Region'] == r)]['Value'].sum()]
                 for i, m in enumerate(months) for j, r in enumerate(regions)]
    global_max = df_filtered['Value'].max() if not df_filtered.empty and df_filtered['Value'].max() > 0 else 100
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

def draw_trend_line(df_cat, cat_name, metric):
    unit = "套" if metric == "套数" else "㎡"
    line = Line(init_opts=opts.InitOpts(width="95vw", height="700px", theme=ThemeType.WALDEN))
    months = sorted(df_cat['Month'].unique().tolist())
    regions = sorted([r for r in df_cat['Region'].unique() if r != '⭐ 全市总计'])
    line.add_xaxis(months)
    line.extend_axis(yaxis=opts.AxisOpts(name=f"大盘总{unit}", type_="value", position="right", splitline_opts=opts.SplitLineOpts(is_show=False)))
    for region in regions:
        region_data = [df_cat[(df_cat['Month'] == m) & (df_cat['Region'] == region)]['Value'].sum() for m in months]
        line.add_yaxis(series_name=region, y_axis=region_data, is_smooth=True, label_opts=opts.LabelOpts(is_show=False), symbol_size=4)
    if '⭐ 全市总计' in df_cat['Region'].unique():
        total_data = [df_cat[(df_cat['Month'] == m) & (df_cat['Region'] == '⭐ 全市总计')]['Value'].sum() for m in months]
        line.add_yaxis(
            series_name='⭐ 全市总计 (右轴)', y_axis=total_data, yaxis_index=1, is_smooth=True, label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=4, type_="dashed", color="#FF3333"),
            itemstyle_opts=opts.ItemStyleOpts(color="#FF3333"), symbol_size=8, z=10
        )
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=f"武汉【{cat_name}】各区成交与大盘宏观趋势对照"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        yaxis_opts=opts.AxisOpts(name=f"各区{unit}"),
        datazoom_opts=[opts.DataZoomOpts(is_show=True, type_="slider", range_start=80, range_end=100), opts.DataZoomOpts(type_="inside")],
        legend_opts=opts.LegendOpts(type_="scroll", pos_top="5%", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(trigger="axis")
    )
    return line

# ================= 3. 渲染引擎与【局部筛选条件渲染】 =================
def generate_dashboard():
    df = load_and_clean_data()
    if df.empty: return
    print("正在编译 V14 精准控制版大屏...")
    all_regions = sorted([r for r in df['Region'].unique() if r != '⭐ 全市总计'])
    all_regions_js = json.dumps(all_regions, ensure_ascii=False)
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

    output_file = "武汉房地产大屏_全量矩阵.html"
    page.render(output_file)

    with open(output_file, "r+", encoding="utf-8") as f:
        html_content = f.read()
        combined_injection = """
        <div id="app-loader" style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:#f4f6f9; z-index:99999; display:flex; flex-direction:column; justify-content:center; align-items:center; font-family:sans-serif;">
            <div style="font-size: 60px; margin-bottom: 20px; animation: bounce 1s infinite alternate;">🎛️</div>
            <h2 style="color:#333;">正在构建精准筛选沙盒...</h2>
            <style>@keyframes bounce { from { transform: translateY(0); } to { transform: translateY(-20px); } }</style>
        </div>
        <style>
            body { background-color: #f4f6f9; margin: 0; padding: 20px 0; font-family: -apple-system, sans-serif; }
            .chart-container { display: none; margin-bottom: 0 !important; border-bottom: none !important; }
            .my-group-wrapper { width: 95vw; margin: 0 auto 50px auto; background: #fff; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); position: relative; padding-top: 140px; overflow: visible; }
            .my-controls { position: absolute; top: 15px; right: 20px; display: flex; flex-direction: column; gap: 10px; align-items: flex-end; z-index: 1000; }
            .my-tab-row { display: flex; gap: 8px; }
            .my-btn { padding: 6px 14px; border: 1px solid #e1e5eb; background: #f8f9fa; color: #666; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; transition: all 0.2s; }
            .my-btn:hover { background: #e2e6ea; }
            .cat-btn.active { background: #045FB4; color: #fff; border-color: #045FB4; box-shadow: 0 4px 8px rgba(4, 95, 180, 0.3); }
            .metric-btn.active { background: #eac763; color: #fff; border-color: #eac763; box-shadow: 0 4px 8px rgba(234, 199, 99, 0.3); }
            .filter-btn { background: #fff; border-color: #045FB4; color: #045FB4; }
            .my-filter-panel { position: absolute; top: 40px; right: 0; background: #fff; border: 1px solid #ddd; box-shadow: 0 8px 24px rgba(0,0,0,0.15); border-radius: 8px; width: 340px; padding: 20px; z-index: 10001; display: none; text-align: left; }
            .filter-actions { display: flex; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
            .action-btn { background: #f0f2f5; border: 1px solid #ddd; padding: 5px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold; }
            .filter-checkboxes { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; max-height: 300px; overflow-y: auto; }
            .check-item { display: flex; align-items: center; cursor: pointer; color: #555; font-size: 13px; }
            .apply-btn { width: 100%; background: #28a745; color: #fff; border: none; padding: 10px; border-radius: 6px; font-weight: bold; cursor: pointer; }
        </style>
        <script>
            const ALL_REGIONS = """ + all_regions_js + """;
            window.__global_timeline_idx = null;
            window.__global_datazoom_start = undefined;
            window.__global_datazoom_end = undefined;
            function initDashboard() {
                const categories = ["商品住房", "写字楼", "商业", "其他", "合计"];
                const metrics = ["成交套数", "成交面积"];
                const groups = ["bar", "map", "pie", "tree", "line", "heat"];
                let bindInterval = setInterval(() => {
                    let allBound = true;
                    groups.forEach(group => {
                        for(let i=0; i<10; i++) {
                            let dom = document.getElementById('custom_chart_' + group + '_' + i);
                            if(dom) {
                                let instance = echarts.getInstanceByDom(dom);
                                if(instance && !dom.dataset.hasEvents) {
                                    instance.on('timelinechanged', (p) => { if (dom.style.display !== 'none') window.__global_timeline_idx = p.currentIndex; });
                                    instance.on('datazoom', (p) => { 
                                        if (dom.style.display !== 'none') {
                                            let b = p.batch ? p.batch[0] : p;
                                            window.__global_datazoom_start = b.start; window.__global_datazoom_end = b.end;
                                        }
                                    });
                                    dom.dataset.hasEvents = 'true';
                                }
                                if(!instance) allBound = false;
                            }
                        }
                    });
                    if(allBound) clearInterval(bindInterval);
                }, 500);
                groups.forEach(group => {
                    let firstChart = document.getElementById('custom_chart_' + group + '_0');
                    if(!firstChart) return;
                    let localSelectedRegions = [...ALL_REGIONS];
                    let wrapper = document.createElement('div');
                    wrapper.className = 'my-group-wrapper';
                    let controls = document.createElement('div');
                    controls.className = 'my-controls';
                    let catRow = document.createElement('div');
                    catRow.className = 'my-tab-row';
                    catRow.innerHTML = categories.map((cat, i) => `<button class="my-btn cat-btn" data-cat="${i}">${cat}</button>`).join('');
                    let metRow = document.createElement('div');
                    metRow.className = 'my-tab-row';
                    metRow.innerHTML = metrics.map((met, i) => `<button class="my-btn metric-btn" data-met="${i}">${met}</button>`).join('');
                    controls.appendChild(catRow);
                    controls.appendChild(metRow);
                    
                    // 【核心逻辑】：只有 line (趋势图) 需要渲染区域筛选
                    if (group === 'line') {
                        let filterContainer = document.createElement('div');
                        filterContainer.className = 'my-filter-container';
                        let cbHtml = ALL_REGIONS.map(r => `<label class="check-item"><input type="checkbox" class="region-cb" value="${r}" checked> ${r}</label>`).join('');
                        filterContainer.innerHTML = `
                            <button class="my-btn filter-btn">⚙️ 区域对比筛选</button>
                            <div class="my-filter-panel">
                                <div class="filter-actions"><button class="action-btn s-all">全选</button><button class="action-btn i-sel">反选</button></div>
                                <div class="filter-checkboxes">${cbHtml}</div>
                                <div class="filter-apply"><button class="apply-btn">确定应用</button></div>
                            </div>
                        `;
                        controls.appendChild(filterContainer);
                        let fBtn = filterContainer.querySelector('.filter-btn'), fPanel = filterContainer.querySelector('.my-filter-panel');
                        fBtn.onclick = () => fPanel.style.display = fPanel.style.display === 'block' ? 'none' : 'block';
                        filterContainer.querySelector('.s-all').onclick = () => fPanel.querySelectorAll('.region-cb').forEach(cb => cb.checked = true);
                        filterContainer.querySelector('.i-sel').onclick = () => fPanel.querySelectorAll('.region-cb').forEach(cb => cb.checked = !cb.checked);
                        filterContainer.querySelector('.apply-btn').onclick = () => {
                            let sel = []; fPanel.querySelectorAll('.region-cb:checked').forEach(cb => sel.push(cb.value));
                            if(!sel.length) { alert("至少选一个区"); return; }
                            localSelectedRegions = sel; fBtn.innerText = `⚙️ 已选 ${sel.length} 个区`; fPanel.style.display = 'none';
                            updateLocalView(parseInt(wrapper.querySelector('.cat-btn.active').dataset.cat)*2 + parseInt(wrapper.querySelector('.metric-btn.active').dataset.met));
                        };
                    }
                    wrapper.appendChild(controls);
                    firstChart.parentNode.insertBefore(wrapper, firstChart);
                    for(let i=0; i<10; i++){ let c = document.getElementById('custom_chart_'+group+'_'+i); if(c) wrapper.appendChild(c); }
                    wrapper.querySelectorAll('.cat-btn')[0].classList.add('active');
                    wrapper.querySelectorAll('.metric-btn')[0].classList.add('active');

                    const updateLocalView = (tIdx) => {
                        for(let i=0; i<10; i++){
                            let dom = document.getElementById('custom_chart_'+group+'_'+i); if(!dom) continue;
                            if (i === tIdx) {
                                dom.style.setProperty('display', 'block', 'important');
                                setTimeout(() => {
                                    let chart = echarts.getInstanceByDom(dom);
                                    if(chart) {
                                        if(!dom.origOpt) dom.origOpt = JSON.parse(JSON.stringify(chart.getOption()));
                                        let opt = JSON.parse(JSON.stringify(dom.origOpt));
                                        if (group === 'line') {
                                            let leg = {}; opt.series.forEach(s => leg[s.name] = s.name.includes('总计') || localSelectedRegions.includes(s.name));
                                            if(!opt.legend) opt.legend = [{}]; opt.legend[0].selected = leg;
                                        }
                                        chart.setOption(opt, true); chart.resize();
                                        if (window.__global_timeline_idx !== null && opt.timeline) chart.setOption({ timeline: [{ currentIndex: Math.min(window.__global_timeline_idx, opt.timeline[0].data.length-1) }] });
                                        if (window.__global_datazoom_start !== undefined && opt.dataZoom) chart.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: window.__global_datazoom_start, end: window.__global_datazoom_end });
                                    }
                                }, 50);
                            } else { dom.style.setProperty('display', 'none', 'important'); }
                        }
                    };
                    wrapper.querySelectorAll('.my-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            if (this.classList.contains('active') || this.classList.contains('filter-btn') || this.closest('.my-filter-panel')) return;
                            let p = this.parentElement; p.querySelectorAll('.my-btn').forEach(b => b.classList.remove('active'));
                            this.classList.add('active');
                            updateLocalView(parseInt(wrapper.querySelector('.cat-btn.active').dataset.cat)*2 + parseInt(wrapper.querySelector('.metric-btn.active').dataset.met));
                        });
                    });
                    updateLocalView(0);
                });
                setTimeout(() => { document.getElementById('app-loader').style.display = 'none'; }, 800);
            }
            if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', initDashboard); } else { initDashboard(); }
        </script>
        """
        html_content = html_content.replace("</body>", f"{combined_injection}\n</body>")
        f.seek(0); f.write(html_content); f.truncate()
    print(f"✅ 生成完毕！筛选功能已精准限定至趋势图：{output_file}")

if __name__ == "__main__":
    generate_dashboard()
