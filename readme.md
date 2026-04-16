# 🏙️ Wuhan Real Estate Analytics & Visualization System
# (武汉房地产数据抓取与可视化分析系统)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Library](https://img.shields.io/badge/Pyecharts-2.0.3-red.svg)
![Status](https://img.shields.io/badge/Status-Automated-success.svg)

[English Version](#english-version) | [中文版本](#chinese-version)

---

<h2 id="chinese-version">🇨🇳 中文版本</h2>

### 📖 项目简介
本项目是一个针对武汉市住建局公开数据的自动化采集与决策支持系统。系统通过自动化脚本从官方渠道抓取每月新建商品房成交数据，经过智能化的行政区划清洗与归一化处理，最终生成包含 6 个核心维度的交互式大屏报表（HTML），为房地产市场分析提供直观的数据支撑。

### 🚀 核心工程设计 (Engineering Design)

1.  **端到端自动化流水线 (Pipeline Automation)**
    * 主程序 `main.py` 在完成数据抓取后，通过 `subprocess` 模块物理隔离并调用 `generate_report.py`。
    * 使用 `sys.executable` 确保跨环境执行时 Python 解释器的一致性，避免虚拟环境路径失效问题。

2.  **鲁棒性数据清洗引擎 (Robust Data Cleaning)**
    * **区域自动映射**：针对房管局非标准行政区（如：东湖高新、经开、化工区等）建立动态映射字典。
    * **地理坐标对齐**：通过逻辑清洗将“经济开发区”等非行政单位归并至标准行政区（如：汉南区），确保地图可视化（Geo-Map）实现 100% 坐标识别。

3.  **高性能并发抓取**
    * 采用 `requests.Session` 保持连接池，针对住建局分页列表进行快速检索。
    * 具备模块级容错（Exception Handling），个别页面解析失败不影响全局 Excel 数据库的生成。

### 📂 模块详细说明

#### 1. `main.py` (数据采集引擎)
- **分页逻辑**：自动识别 `index.shtml` 与 `index_{num}.shtml` 的切换。
- **选择器容错**：内置多个 CSS 候选选择器（`.article-content`, `.zfjg_zhengwen` 等），适配政府网站不定期更新的 DOM 结构。
- **数据存储**：将所有历史月份数据存入多 Sheet 结构的 Excel 文件。

#### 2. `generate_report.py` (可视化大屏引擎)
- **数据转换**：利用 `pandas` 跨 Sheet 汇总数据，实现月度趋势对齐。
- **可视化矩阵**：
    - **Timeline Map/Bar**：展示成交热度在时间和空间上的双重演变。
    - **HeatMap Matrix**：呈现区域间成交密度的对比。
    - **Trend Line**：支持双向 `DataZoom` 滑动缩放，处理长周期时间线。

### ⚠️ 风险控制与边界说明
- **WAF 拦截风险**：目前通过伪装 UA 和延时处理。若目标站升级防火墙，需引入代理 IP 池。
- **行政区划变更**：映射表基于 2024-2026 划分逻辑，若行政区大规模调整，需更新 `REGION_MAPPING`。
- **数据断流处理**：若住建局源表格格式突变，系统会记录日志并跳过该月，确保程序不挂断。

---

<h2 id="english-version">🇺🇸 English Version</h2>

### 📖 Overview
An institutional-grade automation system designed to scrape, clean, and visualize housing transaction data from the Wuhan Housing and Urban-Rural Development Bureau. The system transforms fragmented government tables into a high-fidelity, interactive HTML dashboard.



### 🚀 Key Technical Highlights

1.  **Subprocess Orchestration**
    * Implements a decoupled architecture where `main.py` triggers `generate_report.py` post-extraction.
    * Ensures environment consistency across different deployment scenarios (Local/Cloud).

2.  **Intelligent Regional Normalization**
    * Resolves specific "Economic Development Zones" (e.g., East Lake High-tech) into standard administrative districts via a regex-based mapping engine.
    * This ensures seamless integration with GIS data for accurate Heatmap and Map renderings.

3.  **Visualization Capabilities**
    * **Interactive UI**: Uses `pyecharts` with custom CSS injection for improved spacing and responsive layout.
    - **Multi-dimensional Analysis**: Includes Bar Timeline, Geo-Heatmap, Rosetype Pie charts, and interactive Line charts with `DataZoom`.

### 📂 Module Architecture
- **`main.py`**: Handles network I/O, session management, and Excel persistence. It features a candidate-based selector logic to handle UI variations on government portals.
- **`generate_report.py`**: The analytical core. Performs data aggregation across Excel sheets, handles coordinate mapping, and renders the 6-chart dashboard.

### ⚠️ Risk Assessment
- **Rate Limiting**: Currently mitigated via exponential backoff.
- **UI Fragility**: The crawler is sensitive to CSS selector changes; periodic maintenance of DOM pathing is required.
- **Data Scope**: Focuses on transaction volume; price-action analysis would require additional data endpoints.

---

### 🛠️ Environment & Setup
1. **Dependencies**:
   ```bash
   pip install requests beautifulsoup4 pandas openpyxl pyecharts lxml


2. 执行程序
    ```bash
   python main.py
   注意：执行 main.py 会在抓取完成后自动通过子进程触发 generate_report.py。

3. 输出产物
   武汉市新建商品房成交统计-全量.xlsx：包含所有历史抓取数据的原始数据库。

武汉房地产成交大屏_优化版.html：可交互的图形化可视化分析报告。

⚠️ 风险控制与边界说明
WAF 拦截风险：目前通过伪装 UA 和延时处理。若目标网站升级防火墙，需引入动态代理池。

行政区划变更：若未来武汉行政区划发生大规模调整，需手动更新脚本内的 REGION_MAPPING 字典。

数据断流处理：若源表格格式发生突变，系统会跳过该月份并记录日志，确保全局程序不崩溃。

<h2 id="english-version">🇺🇸 English Version</h2>

📖 Overview
An institutional-grade automation system designed to scrape, clean, and visualize housing transaction data from the Wuhan Housing Bureau. It transforms fragmented government tables into a high-fidelity, interactive HTML dashboard.

🚀 Key Technical Highlights
Subprocess Orchestration

Implements a decoupled architecture where main.py triggers generate_report.py post-extraction, ensuring process isolation.

Intelligent Regional Normalization

Resolves specific "Economic Zones" into standard administrative districts via a mapping engine for 100% GIS accuracy in map rendering.

Visualization Capabilities

Interactive UI: Uses pyecharts with custom CSS injection for optimized spacing and responsive layouts.

Multi-dimensional Analysis: Includes Bar Timeline, Geo-Heatmap, and interactive Line charts with DataZoom for long-term trends.

🛠️ Setup & Usage
1. Install Dependencies
   Bash
   pip install requests beautifulsoup4 pandas openpyxl pyecharts lxml
2. Run Engine
   Bash
   python main.py
   The visualization engine is triggered automatically upon successful data extraction.

3. Outputs
   武汉市新建商品房成交统计-全量.xlsx: Consolidated Excel database.

武汉房地产成交大屏_优化版.html: Interactive visual dashboard.

⚖️ License & Disclaimer
License: MIT

Disclaimer: This tool is for educational and analytical purposes only. Users must comply with the target website's robots.txt and usage policies.
