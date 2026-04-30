#!/usr/bin/env python3
"""
每日宏观数据监控脚本
采集全球宏观经济数据，生成报告并通过企业微信 Webhook 推送

数据源：Trading Economics、新浪财经、东方财富、财联社
"""

import requests
import re
import json
import os
from datetime import datetime, timedelta
from html.parser import HTMLParser

# ========== 配置 ==========
TZ_OFFSET = 8  # GMT+8


def get_date_range():
    """获取过去24小时的日期范围"""
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    return now, yesterday


def clean_html(html_text):
    """移除 HTML 标签"""
    clean = re.sub(r'<[^>]+>', '', html_text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


# ========== 数据源采集 ==========

def fetch_trading_economics_calendar():
    """采集 Trading Economics 经济日历"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(
            'https://tradingeconomics.com/calendar',
            headers=headers,
            timeout=30
        )
        if resp.status_code != 200:
            return results

        # 解析经济日历表格
        # 查找日历条目
        pattern = r'data\-country="([^"]*)"[^>]*data\-event="([^"]*)"[^>]*>(.*?)</'
        matches = re.findall(pattern, resp.text, re.DOTALL)

        for country, event, value_html in matches[:20]:
            value = clean_html(value_html)
            results.append({
                'source': 'Trading Economics',
                'country': country,
                'event': event,
                'value': value,
                'importance': 'high' if 'high' in value_html.lower() else 'medium'
            })
    except Exception as e:
        results.append({
            'source': 'Trading Economics',
            'error': f'采集失败: {str(e)[:100]}'
        })

    return results


def fetch_sina_finance_macro():
    """采集新浪财经宏观数据"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # 新浪财经数据接口
    urls = [
        'https://finance.sina.com.cn/mac/',
        'https://finance.sina.com.cn/data/',
    ]

    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                continue

            # 提取新闻标题和链接
            title_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]*(?:CPI|PPI|PMI|GDP|LPR|MLF|M2|社融|降准|降息|央行|利率|通胀|失业|贸易|进出口|财政|外汇|国债)[^<]*)</a>'
            matches = re.findall(title_pattern, resp.text, re.IGNORECASE)

            for link, title in matches[:10]:
                title = clean_html(title)
                if len(title) > 5:
                    results.append({
                        'source': '新浪财经',
                        'title': title,
                        'url': link,
                        'type': 'domestic'
                    })
        except Exception as e:
            continue

    return results


def fetch_eastmoney_data():
    """采集东方财富宏观数据"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        # 东方财富数据中心 - 宏观经济
        resp = requests.get(
            'https://data.eastmoney.com/macro/',
            headers=headers,
            timeout=20
        )
        if resp.status_code == 200:
            # 提取宏观指标数据
            indicator_pattern = r'<a[^>]*href="(/macro/[^"]*)"[^>]*>([^<]+)</a>'
            matches = re.findall(indicator_pattern, resp.text)

            for link, name in matches[:15]:
                name = clean_html(name)
                if len(name) > 2:
                    results.append({
                        'source': '东方财富',
                        'indicator': name,
                        'url': f'https://data.eastmoney.com{link}',
                        'type': 'domestic'
                    })
    except Exception as e:
        pass

    return results


def fetch_cls_news():
    """采集财联社快讯"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        resp = requests.get(
            'https://www.cls.cn/api/subject/articles?subject_id=0&page=1&rn=20',
            headers=headers,
            timeout=20
        )
        if resp.status_code == 200:
            data = resp.json()
            articles = data.get('data', {}).get('article_list', [])

            keywords = ['CPI', 'PPI', 'PMI', 'GDP', 'LPR', 'MLF', 'M2',
                       '央行', '利率', '通胀', '失业', '贸易', '财政',
                       '美联储', '加息', '降息', '降准', '非农', '国债',
                       '汇率', '外汇', '社融', 'GDP', '景气']

            for article in articles[:20]:
                title = article.get('title', '') or article.get('brief', '')
                if any(kw in title for kw in keywords):
                    results.append({
                        'source': '财联社',
                        'title': title,
                        'time': article.get('ctime', ''),
                        'type': 'news'
                    })
    except Exception:
        pass

    # 备用：直接抓取网页版
    if not results:
        try:
            resp = requests.get(
                'https://www.cls.cn/telegraph',
                headers=headers,
                timeout=20
            )
            if resp.status_code == 200:
                # 从HTML中提取新闻
                news_pattern = r'<title>([^<]*(?:央行|美联储|CPI|GDP|PMI|利率|通胀)[^<]*)</title>'
                matches = re.findall(news_pattern, resp.text, re.IGNORECASE)
                for title in matches[:10]:
                    results.append({
                        'source': '财联社',
                        'title': clean_html(title),
                        'type': 'news'
                    })
        except Exception:
            pass

    return results


def fetch_global_indices():
    """采集全球主要市场指数"""
    results = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    indices = {
        '上证指数': 'sh000001',
        '深证成指': 'sz399001',
        '创业板指': 'sz399006',
        '恒生指数': 'rt_hkHSI',
        '道琼斯': 'int_dji',
        '纳斯达克': 'int_nasdaq',
        '标普500': 'int_sp500',
        '日经225': 'int_nikkei',
    }

    for name, code in indices.items():
        try:
            # 新浪实时行情接口
            resp = requests.get(
                f'https://hq.sinajs.cn/list={code}',
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                # 解析行情数据
                data = resp.text.split('"')[1] if '"' in resp.text else ''
                if data:
                    parts = data.split(',')
                    if len(parts) >= 4:
                        results[name] = {
                            'price': parts[1],
                            'change': parts[2],
                            'change_pct': parts[3],
                        }
        except Exception:
            continue

    return results


# ========== 报告生成 ==========

def generate_report(intl_data, domestic_data, news_data, market_indices):
    """生成 Markdown 格式报告"""
    now = datetime.utcnow()
    beijing_time = now + timedelta(hours=TZ_OFFSET)
    date_str = beijing_time.strftime('%Y-%m-%d')
    time_str = beijing_time.strftime('%H:%M')

    lines = []
    lines.append(f'## {date_str} 每日宏观数据监控')
    lines.append(f'> 生成时间：{date_str} {time_str} (GMT+8)')
    lines.append('')

    # 1. 全球市场概况
    lines.append('### 全球市场概况')
    lines.append('')
    if market_indices:
        lines.append('| 市场 | 最新价 | 涨跌幅 |')
        lines.append('|------|--------|--------|')
        for name, data in market_indices.items():
            pct = data.get('change_pct', 'N/A')
            try:
                pct_val = float(pct)
                # 中文惯例：红涨绿跌
                emoji = '🔴' if pct_val >= 0 else '🟢'
                lines.append(f'| {name} | {data["price"]} | {emoji} {pct}% |')
            except (ValueError, TypeError):
                lines.append(f'| {name} | {data["price"]} | {pct}% |')
        lines.append('')
    else:
        lines.append('*市场数据暂未获取*')
        lines.append('')

    # 2. 国际宏观数据
    lines.append('### 国际宏观数据')
    lines.append('')
    if intl_data:
        for item in intl_data:
            if 'error' in item:
                lines.append(f'- [{item["source"]}] {item["error"]}')
            else:
                importance = '🔥' if item.get('importance') == 'high' else '📊'
                lines.append(
                    f'- {importance} **{item["country"]}**: {item["event"]} — {item["value"]}'
                )
        lines.append('')
    else:
        lines.append('*今日暂无重要国际数据发布*')
        lines.append('')

    # 3. 国内宏观数据
    lines.append('### 国内宏观数据')
    lines.append('')
    if domestic_data:
        seen = set()
        for item in domestic_data:
            title = item.get('title', '') or item.get('indicator', '')
            if title and title not in seen:
                seen.add(title)
                lines.append(f'- [{item["source"]}] {title}')
        lines.append('')
    else:
        lines.append('*今日暂无重要国内数据发布*')
        lines.append('')

    # 4. 重要资讯
    lines.append('### 重要资讯')
    lines.append('')
    if news_data:
        seen = set()
        for item in news_data[:15]:
            title = item.get('title', '')
            if title and title not in seen:
                seen.add(title)
                lines.append(f'- [{item["source"]}] {title}')
        lines.append('')
    else:
        lines.append('*今日暂无重要资讯*')
        lines.append('')

    # 5. 温馨提示
    lines.append('---')
    lines.append('')
    lines.append('*数据来源：Trading Economics、新浪财经、东方财富、财联社*')
    lines.append('*报告由 GitHub Actions 自动生成并推送*')
    lines.append('*如需查看详细分析，请使用 WorkBuddy 宏观数据监控技能*')

    return '\n'.join(lines)


# ========== 企业微信推送 ==========

def send_to_wecom(report_md, webhook_url):
    """通过企业微信 Webhook 发送 Markdown 消息"""
    if not webhook_url:
        print('[警告] 未配置企业微信 Webhook URL，跳过推送')
        return False

    # 企业微信 Markdown 消息有大小限制（约 2048 字节）
    # 截取报告摘要（前 1800 字符）
    summary = report_md[:1800]
    if len(report_md) > 1800:
        summary += '\n\n... *(报告过长，已截取摘要)*'

    payload = {
        'msgtype': 'markdown',
        'markdown': {
            'content': summary
        }
    }

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            timeout=15
        )
        result = resp.json()

        if result.get('errcode') == 0:
            print('[成功] 企业微信推送成功')
            return True
        else:
            print(f'[失败] 企业微信推送失败: {result}')
            return False
    except Exception as e:
        print(f'[错误] 推送异常: {str(e)}')
        return False


# ========== 主流程 ==========

def main():
    print('=' * 50)
    print('每日宏观数据监控开始运行')
    print('=' * 50)

    now, yesterday = get_date_range()
    print(f'采集范围: {yesterday.strftime("%Y-%m-%d")} ~ {now.strftime("%Y-%m-%d")}')

    # 并行采集各数据源
    print('\n[1/5] 采集 Trading Economics 经济日历...')
    intl_data = fetch_trading_economics_calendar()
    print(f'  获取 {len(intl_data)} 条国际数据')

    print('\n[2/5] 采集新浪财经宏观数据...')
    domestic_sina = fetch_sina_finance_macro()
    print(f'  获取 {len(domestic_sina)} 条国内数据')

    print('\n[3/5] 采集东方财富数据...')
    domestic_east = fetch_eastmoney_data()
    print(f'  获取 {len(domestic_east)} 条指标数据')

    print('\n[4/5] 采集财联社快讯...')
    news_data = fetch_cls_news()
    print(f'  获取 {len(news_data)} 条重要资讯')

    print('\n[5/5] 采集全球市场指数...')
    market_indices = fetch_global_indices()
    print(f'  获取 {len(market_indices)} 个市场指数')

    # 合并国内数据
    domestic_data = domestic_sina + domestic_east

    # 生成报告
    print('\n生成报告...')
    report = generate_report(intl_data, domestic_data, news_data, market_indices)
    print(f'报告长度: {len(report)} 字符')

    # 保存报告到文件（供 GitHub Actions Artifact 使用）
    date_str = now.strftime('%Y-%m-%d')
    report_dir = os.environ.get('GITHUB_OUTPUT', '')
    report_file = f'macro-report-{date_str}.md'

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'报告已保存: {report_file}')

    # 推送到企业微信
    webhook_url = os.environ.get('WECOM_WEBHOOK_URL', '')
    if webhook_url:
        print('\n推送到企业微信...')
        send_to_wecom(report, webhook_url)
    else:
        print('\n[警告] 未设置 WECOM_WEBHOOK_URL 环境变量，跳过企业微信推送')

    print('\n' + '=' * 50)
    print('每日宏观数据监控运行完成')
    print('=' * 50)


if __name__ == '__main__':
    main()
