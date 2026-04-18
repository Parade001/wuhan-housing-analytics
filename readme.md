# 🏙️ Wuhan Real Estate Analytics & Visualization System
# (武汉房地产全维数据解析与交互大屏)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Library](https://img.shields.io/badge/Pyecharts-2.0+-red.svg)
![Pandas](https://img.shields.io/badge/Pandas-Data_Matrix-green.svg)
![Status](https://img.shields.io/badge/Status-Automated-success.svg)

[English Version](#english-version) | [中文版本](#chinese-version)

---

<h2 id="chinese-version">🇨🇳 中文版本</h2>

### 📖 项目简介
本项目是一个针对武汉市住建局公开数据的自动化采集与多维决策分析系统。系统通过自动化脚本精准突破政务报表的“脏数据”与“合并单元格”排版陷阱，重构出 **5大物业类别 × 2大指标（套数/面积）** 的 10 维数据矩阵。最终通过深度注入原生 JS/CSS，生成无视框架渲染缺陷的交互式大屏（包含 60 个独立物理图表），为房地产市场提供 1:1 绝对精确的趋势洞察。

### 🚀 核心工程设计 (Hardcore Engineering)

1.  **多维矩阵解析与笛卡尔积零填充 (Matrix Extraction & Zero-Padding)**
    * **痛点**：传统提取在遇到无成交月份时会产生数据断层，导致各图表时间轴帧数不一，引发灾难性的时间线错位。
    * **解法**：引入 `pandas.MultiIndex` 构建全量月度、区域、类别、指标的笛卡尔积。实施强一致性的零填充（Zero-Padding），确保底层 60 个图表的时间轴拥有 100% 绝对一致的帧数长度。

2.  **解耦式行政区划归一化 (Decoupled Regional Normalization)**
    * **1:1 财务级对账**：针对柱状图、折线图、热力图，保留“东湖高新”、“武汉经开”等经济区独立地位，确保可视化数据与住建局原始 Excel 分毫不差。
    * **GIS 动态折叠**：针对 ECharts 底层地图组件不支持非行政区划的缺陷，仅在渲染 Map 时启用动态路由，将经济区数据无缝折叠并入标准行政区（如洪山区、汉南区），防止渲染崩溃。

3.  **事件驱动的全局状态隔离 (Event-Driven State Sync)**
    * **痛点**：Pyecharts 的 `Page` 和 `Tab` 组件存在底层渲染冲突（白屏）及切换标签后时间线状态丢失（月份穿越）Bug。
    * **解法**：废弃框架原生组件，采用 Python 批量生成 60 个隔离的 Canvas，并在生成的 HTML 尾部暴力注入原生 JS 引擎。通过轮询绑定 `timelinechanged` 与 `datazoom` 事件，实时将用户操作帧数写入浏览器全局内存。切换 Tab 时，利用 `dispatchAction` 或 `setOption` 强行分发状态指令，实现 10 维图表间的“状态完美记忆”。

4.  **端到端自动化流水线 (Pipeline Automation)**
    * 采用子进程 (`subprocess`) 物理隔离数据采集（`main.py`）与渲染引擎（`generate_report.py`），确保依赖干净、内存安全释放。

### 📂 模块说明
- **`main.py`**：基于 `requests.Session` 的并发爬虫，内置多套 CSS Selector 容错策略，抗击政务网站 DOM 突变。生成包含全量历史的 `.xlsx` 数据库。
- **`generate_report_v7.py`**：渲染核心。执行 `safe_float` 脏数据清洗、矩阵折叠、并输出携带自定义 Flex 布局卡片（Card UI）的高级交互报告。

### ⚠️ 风险控制与边界约束
- **DOM 渲染内存压强**：为保证状态隔离，页面挂载了 60 个 ECharts 实例。低配设备在初次切换 Tab 时可能有 50ms 延迟，属正常引擎计算开销。
- **WAF 拦截策略**：当前依靠指数退避与 UA 伪装。若目标防火墙升级，需横向扩展代理池。

---

<h2 id="english-version">🇺🇸 English Version</h2>

### 📖 Overview
An institutional-grade pipeline designed to scrape, cleanse, and multi-dimensionally visualize housing transaction data from the Wuhan Housing Bureau. It bypasses conventional UI framework limits by injecting native JavaScript state-synchronization engines, transforming messy government spreadsheets into a high-fidelity, 10-dimensional (5 Categories × 2 Metrics) interactive HTML dashboard.

### 🚀 Key Technical Highlights

1.  **Cartesian Product Zero-Padding & Matrix Parsing**
    * Extracts a complex 10D matrix (Count & Area across Residential, Office, Commercial, etc.).
    * Utilizes `pandas.MultiIndex` to enforce strict zero-padding. This guarantees that all generated charts share the exact same number of timeline frames, utterly eliminating timeline desynchronization bugs caused by missing monthly data.

2.  **Event-Driven Global State Synchronization**
    * **The Hack**: Bypasses Pyecharts' buggy native `Tab` rendering by outputting 60 isolated canvases and injecting custom JS.
    * **The Engine**: Polling listeners capture `timelinechanged` and `datazoom` events in real-time, caching the absolute frame index in global memory. Switching tabs triggers a synchronized `setOption` dispatch, forcing the new chart to perfectly resume the user's exact timeline and zoom state.

3.  **Decoupled GIS Normalization**
    * Maintains independent "Economic Zones" (e.g., East Lake High-tech) for Bar/Line/Heatmap charts to ensure 1:1 financial-grade data reconciliation with original government records.
    * Dynamically folds these zones into standard administrative districts *exclusively* for Geo-Map rendering to prevent ECharts coordinate failures.

4.  **Subprocess Orchestration**
    * Complete physical isolation between the scraping engine (`main.py`) and the visualization compiler, ensuring clean memory release and environment stability.

### 🛠️ Setup & Usage

1. **Install Dependencies**
   ```bash
   pip install requests beautifulsoup4 pandas openpyxl pyecharts lxml


2.  **Run Engine**

```Bash
    python main.py

```



The visualization compiler is triggered automatically via a decoupled subprocess upon successful extraction.

Outputs

武汉市新建商品房成交统计-全量.xlsx: The consolidated, raw historical database.

武汉房地产成交大屏_终极对账版.html: The 10-dimensional, state-synced visual dashboard.

⚖️ Disclaimer: This tool is for educational and analytical purposes only. Users must comply with the target website's robots.txt and anti-scraping policies.
