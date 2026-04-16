import requests
import urllib3
from bs4 import BeautifulSoup
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import time
from urllib.parse import urljoin
import subprocess
import sys
import os

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://zgj.wuhan.gov.cn"
START_PAGE = "index.shtml"  # 首页文件名
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"),
}

def get_page_url(page_num):
    """根据页码生成对应页面URL，第0页是index.shtml，其余是index_{num}.shtml"""
    if page_num == 0:
        return urljoin(BASE_URL + "/xxgk/xxgkml/sjfb/spzfxysydjcjb/", "index.shtml")
    else:
        return urljoin(BASE_URL + "/xxgk/xxgkml/sjfb/spzfxysydjcjb/", f"index_{page_num}.shtml")

def get_links_from_page(url):
    resp = requests.get(url, headers=HEADERS, verify=False)
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'lxml')

    # 解析链接
    links = []
    for a in soup.select('a[href][title]'):
        title = a['title'].strip()
        href = a['href']
        if "新建商品房成交统计情况" in title:
            full_url = href if href.startswith("http") else urljoin(url, href)
            links.append((title, full_url))
    return links

def get_table_from_page(url):
    resp = requests.get(url, headers=HEADERS, verify=False)
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'lxml')

    candidates = [
        ".article-content",
        ".zfjg_zhengwen",
        ".TRS_Editor",
        ".table-responsive"
    ]
    content_div = None
    for selector in candidates:
        content_div = soup.select_one(selector)
        if content_div:
            break

    if not content_div:
        table = soup.find("table")
        if not table:
            print(f"❌ 未找到容器或表格: {url}")
            return None
    else:
        table = content_div.find("table")
        if not table:
            print(f"❌ 找到容器但无表格: {url}")
            return None

    data = []
    for row in table.find_all("tr"):
        cols = [col.get_text(strip=True) for col in row.find_all(["td", "th"])]
        if cols:
            data.append(cols)

    if not data:
        print(f"⚠️ 表格为空: {url}")
        return None

    return pd.DataFrame(data)

def save_to_excel():
    all_links = []
    page_num = 0
    while True:
        url = get_page_url(page_num)
        print(f"正在抓取第 {page_num + 1} 页，URL: {url}")
        links = get_links_from_page(url)
        if not links:
            print(f"第 {page_num + 1} 页没有抓取到目标链接，结束分页。")
            break
        print(f"第 {page_num + 1} 页抓取到 {len(links)} 条链接。")
        all_links.extend(links)
        page_num += 1
        time.sleep(0.5)

    wb = Workbook()
    wb.remove(wb.active)

    for title, url in all_links:
        print(f"抓取详情页数据：{title} | {url}")
        df = get_table_from_page(url)
        if df is not None:
            sheet_title = title[:31].replace(":", "：").replace("/", "-").replace("\\", "-")
            ws = wb.create_sheet(title=sheet_title)
            for r in dataframe_to_rows(df, index=False, header=False):
                ws.append(r)
        else:
            print(f"⚠️ 无法提取表格：{url}")

    wb.save("武汉市新建商品房成交统计-全量.xlsx")
    print("✅ 数据保存完毕：武汉市新建商品房成交统计-全量.xlsx")

if __name__ == "__main__":
    save_to_excel()

if __name__ == "__main__":
    try:
        # 1. 执行主抓取逻辑
        save_to_excel()

        # 2. 调用生成报表脚本
        # 获取当前脚本所在目录，确保路径跨平台兼容
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_script = os.path.join(current_dir, "generate_report.py")

        if os.path.exists(target_script):
            print(f"🚀 正在启动报表生成程序: {target_script}")

            # 使用 sys.executable 确保使用当前相同的 Python 解释器环境
            result = subprocess.run(
                [sys.executable, target_script],
                check=True,       # 如果 generate_report.py 返回非零退出码，抛出异常
                text=True,
                capture_output=False # 设置为 False 则直接在当前终端打印输出
            )

            if result.returncode == 0:
                print("✨ 报表生成成功！")
        else:
            print(f"❌ 错误：未找到文件 {target_script}")

    except subprocess.CalledProcessError as e:
        print(f"💥 报表生成脚本执行失败，退出码: {e.returncode}")
    except Exception as e:
        print(f"⚠️ 程序运行过程中出现未知异常: {e}")
