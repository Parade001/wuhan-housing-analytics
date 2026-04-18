# 🏙️ Wuhan Real Estate Analytics & Visualization System
# (武汉房地产全维数据解析与交互大屏系统)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Library](https://img.shields.io/badge/Pyecharts-2.0+-red.svg)
![Pandas](https://img.shields.io/badge/Pandas-Data_Matrix-green.svg)
![Status](https://img.shields.io/badge/Status-V14_Flagship-success.svg)

[English Version](#english-version) | [中文版本](#chinese-version)

---

<h2 id="chinese-version">🇨🇳 中文版本</h2>

### 📖 项目简介
本项目是一个针对武汉市住建局公开数据的自动化采集与多维决策分析系统。系统精准突破政务报表“合并单元格”与“动态表头”的排版陷阱，重构出 **5大物业类别 × 2大指标（套数/面积）** 的 10 维数据矩阵。最终通过深度注入原生 JavaScript 事件引擎，生成具备“状态记忆”与“局域筛选”功能的高级交互大屏，实现 1:1 财务级数据对账。

### 🚀 核心工程设计 (Hardcore Engineering)

1.  **笛卡尔积零填充 (Zero-Padding Logic)**
    * **挑战**：不同物业类型在不同月份可能无成交，导致各图表时间轴长度不一，引发维度切换时的严重错位。
    * **方案**：利用 `pandas.MultiIndex` 构建全量月份、区域、类别的笛卡尔积，强制执行零填充。确保底层 60 个图表物理结构 100% 对齐。

2.  **局部沙盒筛选引擎 (Local Sandbox Filter)**
    * **挑战**：全局筛选会导致所有图表数据丢失，且原生 ECharts 无法在单页内多表联动。
    * **方案**：针对趋势图单独注入“齿轮”筛选控件。采用局部状态机模式，允许用户在趋势图中自由组合行政区（如江岸+武昌），而排名图、热力图依然保留全武汉视角，互不干扰。

3.  **事件驱动的状态同步 (State Persistence Sync)**
    * **方案**：通过原生 JS 轮询绑定 `timelinechanged`（时间轴）与 `datazoom`（缩放条）事件。实时将用户操作的绝对帧数写入浏览器全局内存，确保切换物业类别或指标时，月份视图完美锁定。

4.  **UX 与性能极致优化**
    * **骨架屏加载**：注入全局加载动画（Loader），彻底消灭 60 个图表初次渲染时的“瀑布流”闪烁现象。
    * **数据精度压缩**：对成交面积执行 1 位小数强制四舍五入，套数转整数。在保证数据准确的前提下，极大提升了本地 HTML 的解析效率。

5.  **宏观与微观双轴对比 (Dual Y-Axis)**
    * 在趋势图中引入双 Y 轴设计：左轴服务于各行政区，右轴专属“全市总计”。将大盘走势以红色加粗虚线呈现，一眼看清区域表现与全市大盘的偏离度。

### 📂 模块说明
- **`main.py`**：高可用爬虫引擎，内置多套 Selector 容错策略，支持断点续传式的 Excel 数据持久化。
- **`generate_report.py`**：数据科学与渲染核心。负责执行安全浮点提取 (`safe_extract`)、行政区动态映射及 60 组 10 维矩阵的物理渲染。

---

<h2 id="english-version">🇺🇸 English Version</h2>

### 📖 Overview
An institutional-grade BI pipeline designed to scrape, cleanse, and visualize 10-dimensional housing data (5 Categories × 2 Metrics) from the Wuhan Housing Bureau. By injecting a custom JavaScript state engine into Pyecharts-generated HTML, the system provides a high-fidelity interactive dashboard that supports local sandbox filtering and global timeline synchronization.

### 🚀 Key Technical Highlights

1.  **Cartesian Zero-Padding**
    * Enforces absolute timeline alignment across all 60 chart instances using `pandas.MultiIndex`. This eliminates data desynchronization bugs caused by missing records in specific months or property types.
2.  **Local Sandbox Filtering**
    * Features a per-card filtering UI specifically for trend charts. This allows users to perform multi-region comparisons (e.g., Jiang'an vs. Wuchang) within a local state sandbox without affecting the macro view of other charts on the same page.
3.  **Event-Driven State Sync**
    * Captures `timelinechanged` and `datazoom` events in real-time. When a user switches between categories (e.g., Residential to Office), the system force-dispatches the current frame index to the new chart, ensuring a seamless temporal transition.
4.  **Skeleton Screen & Anti-Flicker**
    * Mitigates FOUC (Flash of Unstyled Content) by injecting a CSS-blocked loading screen, providing a premium application-like experience while 60 complex canvases are initialized.

### 🛠️ Usage
1. **Dependencies**: `pip install requests beautifulsoup4 pandas openpyxl pyecharts lxml`
2. **Execute**: `python main.py`
3. **Outputs**: 
   - `武汉市新建商品房成交统计-全量.xlsx`: The raw data matrix.
   - `武汉房地产大屏_精准对账版.html`: The 10D, state-synced dashboard.

⚖️ **Disclaimer**: For educational purposes only.
