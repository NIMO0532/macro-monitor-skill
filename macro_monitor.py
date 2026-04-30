#!/usr/bin/env python3
"""
每日宏观数据监控脚本 v3.0
采集全球宏观经济数据，生成报告并通过企业微信 Webhook 推送

已验证数据源（2026-04-30）:
  ✅ 新浪行情 API - A股/港股/美股实时行情（GBK 编码）
  ✅ 东方财富 API - GDP/CPI/PMI 等国内宏观经济指标
  ✅ 财联社 API - 实时财经快讯（article_title/article_brief/article_time）
  ✅ Trading Economics - 各国关键指标（HTML 解析，备用）
"""

import requests
import re
import json
import os
import time
from datetime import datetime, timedelta

# ========== 配置 ==========
TZ_OFFSET = 8
REQUEST_TIMEOUT = 20

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
      'AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0.0.0 Safari/537.36')


def get_beijing_now():
    return datetime.utcnow() + timedelta(hours=TZ_OFFSET)


def clean_html_text(html_text):
    """移除 HTML 标签和 HTML 实体"""
    clean = re.sub(r'<[^>]+>', '', html_text)
    clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&')
    clean = clean.replace('&lt;', '<').replace('&gt;', '>')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


# ========== 1. 全球市场指数 ==========

def fetch_global_indices():
    """采集全球市场指数（新浪行情 API，已验证）"""
    results = {}
    headers = {'User-Agent': UA, 'Referer': 'https://finance.sina.com.cn'}

    # A股（sh/sz 前缀）+ 港股（rt_hk）+ 美股（gb_）
    indices = {
        '上证指数': ('sh000001', 'cn'),
        '深证成指': ('sz399001', 'cn'),
        '创业板指': ('sz399006', 'cn'),
        '科创50': ('sh000688', 'cn'),
        '恒生指数': ('rt_hkHSI', 'hk'),
        '纳斯达克': ('gb_ixic', 'us'),
        '道琼斯': ('gb_dji', 'us'),
        '标普500': ('gb_spx', 'us'),
    }

    codes = ','.join(v[0] for v in indices.values())

    try:
        resp = requests.get(
            f'https://hq.sinajs.cn/list={codes}',
            headers=headers, timeout=REQUEST_TIMEOUT
        )
        content = resp.content.decode('gbk')
    except Exception as e:
        print(f'  [错误] 行情接口: {e}')
        return results

    for line in content.strip().split('\n'):
        if '=' not in line or '""' in line:
            continue

        # 提取代码：从 "var hq_str_sh000001=" 中提取 "sh000001"
        var_part = line.split('=')[0].strip()
        code = var_part.replace('var ', '').replace('hq_str_', '')
        data_str = line.split('=')[1].strip().strip('"').rstrip(';')
        if not data_str:
            continue

        parts = data_str.split(',')
        name = None
        market_type = 'cn'

        for n, (c, m) in indices.items():
            if code == c:
                name = n
                market_type = m
                break

        if not name:
            continue

        try:
            if market_type == 'cn':
                # A股: [0]名称 [1]今开 [2]昨收 [3]当前价 [4]最高 [5]最低 ...
                price = float(parts[3])
                prev = float(parts[2])
                change = price - prev
                pct = (change / prev) * 100 if prev else 0
            elif market_type == 'hk':
                # 港股: [0]代码 [1]名称 [2]今开 [3]昨收 [4]当前价 [5]最高 [6]最低 [7]涨跌 [8]涨跌幅%
                price = float(parts[4])
                change = float(parts[7])
                pct = float(parts[8])
            else:
                # 美股: [0]名称 [1]当前价 [2]涨跌幅% [3]时间 [4]涨跌额 [5]今开 [6]最高 [7]最低 ...
                price = float(parts[1])
                pct = float(parts[2])
                change = float(parts[4])

            results[name] = {
                'price': f'{price:.2f}',
                'change': f'{change:+.2f}',
                'change_pct': f'{pct:+.2f}',
            }
        except (ValueError, IndexError):
            pass

    return results


# ========== 2. 国内宏观经济指标 ==========

def fetch_eastmoney_indicator(report_name, indicator_name, value_field, time_field='TIME'):
    """从东方财富 API 获取国内宏观经济指标（已验证）"""
    results = []
    try:
        resp = requests.get(
            'https://datacenter-web.eastmoney.com/api/data/v1/get',
            params={
                'reportName': report_name,
                'columns': 'ALL',
                'pageSize': 3,
                'pageNumber': 1,
                'sortColumns': 'REPORT_DATE',
                'sortTypes': -1,
                'source': 'WEB',
                'client': 'WEB',
            },
            headers={'User-Agent': UA, 'Referer': 'https://data.eastmoney.com'},
            timeout=REQUEST_TIMEOUT
        )
        data = resp.json()
        if not data.get('success'):
            return results

        items = data.get('result', {}).get('data', [])
        for item in items:
            results.append({
                'indicator': indicator_name,
                'time': item.get(time_field, ''),
                'value': item.get(value_field, ''),
            })
    except Exception as e:
        print(f'  [错误] {indicator_name}: {e}')

    return results


def fetch_domestic_indicators():
    """获取国内核心宏观经济指标"""
    print('\n[2/5] 采集国内宏观经济指标...')
    all_data = []

    # GDP
    gdp = fetch_eastmoney_indicator('RPT_ECONOMY_GDP', 'GDP', 'DOMESTICL_PRODUCT_BASE')
    for d in gdp:
        d['unit'] = '亿元'
    all_data.extend(gdp)
    print(f'  GDP: {len(gdp)} 条')

    # CPI（同比）
    cpi = fetch_eastmoney_indicator('RPT_ECONOMY_CPI', 'CPI同比', 'NATIONAL_SAME')
    for d in cpi:
        d['unit'] = '%'
    all_data.extend(cpi)
    print(f'  CPI: {len(cpi)} 条')

    # PMI（制造业）
    pmi = fetch_eastmoney_indicator('RPT_ECONOMY_PMI', '制造业PMI', 'MAKE_INDEX')
    for d in pmi:
        d['unit'] = ''
    all_data.extend(pmi)
    print(f'  PMI: {len(pmi)} 条')

    print(f'  国内指标合计: {len(all_data)} 条')
    return all_data


# ========== 3. 财经新闻 ==========

MACRO_KEYWORDS = [
    'CPI', 'PPI', 'PMI', 'GDP', 'LPR', 'MLF', 'M2',
    '央行', '利率', '通胀', '失业', '贸易', '财政',
    '美联储', '加息', '降息', '降准', '非农', '国债',
    '汇率', '外汇', '社融', '景气', '经济数据',
    '宏观数据', '利率决议', '经济', '制造业',
]


def fetch_sina_macro_news():
    """采集新浪财经宏观新闻（已验证）"""
    results = []
    try:
        resp = requests.get(
            'https://finance.sina.com.cn/roll/',
            headers={'User-Agent': UA},
            timeout=REQUEST_TIMEOUT
        )
        resp.encoding = 'utf-8'

        titles = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{8,80})</a>', resp.text)

        seen = set()
        for link, title in titles:
            title = clean_html_text(title)
            if not title or title in seen:
                continue
            if any(kw.lower() in title.lower() for kw in MACRO_KEYWORDS):
                seen.add(title)
                results.append({'title': title, 'source': '新浪财经'})
    except Exception as e:
        print(f'  [警告] 新浪财经: {e}')

    return results


def fetch_163_macro_news():
    """采集网易财经宏观新闻（已验证）"""
    results = []
    try:
        resp = requests.get(
            'https://money.163.com/',
            headers={'User-Agent': UA},
            timeout=REQUEST_TIMEOUT
        )
        resp.encoding = 'utf-8'

        titles = re.findall(
            r'<a[^>]+href="([^"]+)"[^>]*>([^<]{10,80}(?:央行|美联储|CPI|GDP|PMI|利率|通胀|'
            r'降息|MLF|LPR|M2|国债|社融|数据|经济|制造业|失业|财政|贸易|汇率)[^<]*)</a>',
            resp.text, re.IGNORECASE
        )

        seen = set()
        for link, title in titles:
            title = clean_html_text(title)
            if not title or title in seen:
                continue
            seen.add(title)
            results.append({'title': title, 'source': '网易财经'})
    except Exception as e:
        print(f'  [警告] 网易财经: {e}')

    return results


def fetch_cls_telegraph():
    """尝试采集财联社电报（可能失效，备用）"""
    results = []
    try:
        resp = requests.get(
            'https://www.cls.cn/api/subject/articles',
            params={'subject_id': '0', 'page': '1', 'rn': '30'},
            headers={'User-Agent': UA, 'Referer': 'https://www.cls.cn'},
            timeout=REQUEST_TIMEOUT
        )
        data = resp.json()
        articles = data.get('data', [])
        now = get_beijing_now()

        for article in articles:
            title = article.get('article_title', '') or ''
            brief = article.get('article_brief', '') or ''
            article_time = article.get('article_time', 0)

            full_text = f'{title} {brief}'
            if not any(kw in full_text for kw in MACRO_KEYWORDS):
                continue

            if article_time:
                try:
                    pub = datetime.fromtimestamp(int(article_time))
                    if now - pub > timedelta(hours=48):
                        continue
                except (ValueError, TypeError, OSError):
                    pass

            time_str = ''
            if article_time:
                try:
                    time_str = datetime.fromtimestamp(int(article_time)).strftime('%H:%M')
                except:
                    pass

            results.append({
                'title': title,
                'brief': brief[:100] if brief else '',
                'time': time_str,
                'source': '财联社',
            })
    except Exception:
        pass

    return results


# ========== 4. 国际宏观数据（HTML 解析，备用） ==========

def fetch_trading_economics():
    """从 Trading Economics 获取各国关键指标（HTML 解析，辅助）"""
    results = []
    headers = {'User-Agent': UA}

    countries = {
        'united-states': '美国',
        'china': '中国',
        'euro-area': '欧元区',
        'japan': '日本',
    }

    for code, name in countries.items():
        try:
            resp = requests.get(
                f'https://tradingeconomics.com/{code}',
                headers=headers, timeout=REQUEST_TIMEOUT
            )
            if resp.status_code != 200:
                continue

            # 提取表格中的指标数据
            # TE 的指标页面有 table 行，每行包含 indicator name 和 latest value
            row_pattern = r'<td[^>]*>([^<]*(?:GDP|Inflation|Unemployment|Interest Rate|Current Account|Balance of Trade|Government Debt|Consumer Confidence|Retail Sales|Industrial Production)[^<]*)</td>\s*<td[^>]*>(?:<[^>]*>)*([^<]+)(?:</[^>]*>)*</td>'
            matches = re.findall(row_pattern, resp.text, re.IGNORECASE)

            for indicator, value in matches[:5]:
                indicator = re.sub(r'<[^>]+>', '', indicator).strip()
                value = re.sub(r'<[^>]+>', '', value).strip()
                if indicator and value and len(indicator) > 3:
                    results.append({
                        'country': name,
                        'indicator': indicator,
                        'value': value,
                    })
        except Exception:
            continue

    return results


# ========== 报告生成 ==========

COUNTRY_NAMES = {
    'US': '美国', 'united-states': '美国',
    'CN': '中国', 'china': '中国',
    'EU': '欧元区', 'euro-area': '欧元区',
    'JP': '日本', 'japan': '日本',
    'GB': '英国', 'united-kingdom': '英国',
    'AU': '澳大利亚', 'australia': '澳大利亚',
}


def format_value(val):
    """格式化数值，添加单位"""
    if val is None:
        return 'N/A'
    s = str(val).strip()
    try:
        f = float(s)
        if abs(f) >= 10000:
            return f'{f:,.1f}'
        elif abs(f) >= 100:
            return f'{f:.1f}'
        else:
            return f'{f:.2f}'
    except (ValueError, TypeError):
        return s


def generate_report(market_indices, domestic_indicators, news_data, intl_indicators):
    """生成 Markdown 报告"""
    now = get_beijing_now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')

    lines = []
    lines.append(f'## {date_str} 每日宏观数据监控')
    lines.append(f'> 生成时间：{date_str} {time_str} (GMT+8)')
    lines.append('')

    # 1. 全球市场概况
    lines.append('### 全球市场概况')
    lines.append('')
    if market_indices:
        lines.append('| 市场 | 最新价 | 涨跌 | 涨跌幅 |')
        lines.append('|:----:|:------:|:----:|:------:|')
        for name, d in market_indices.items():
            pct = d.get('change_pct', '0')
            try:
                pct_val = float(pct)
                lines.append(f'| {name} | {d["price"]} | {d["change"]} | {pct}% |')
            except ValueError:
                lines.append(f'| {name} | {d["price"]} | {d["change"]} | {pct}% |')
        lines.append('')
    else:
        lines.append('> 非交易时段，暂无市场数据')
        lines.append('')

    # 2. 国内宏观经济指标（最新值）
    lines.append('### 国内宏观经济指标')
    lines.append('')
    if domestic_indicators:
        # 按指标类型分组，取最新
        by_indicator = {}
        for item in domestic_indicators:
            ind = item.get('indicator', '')
            if ind not in by_indicator:
                by_indicator[ind] = item

        lines.append('| 指标 | 时间 | 最新值 |')
        lines.append('|:----:|:----:|:------:|')
        for ind_name, item in by_indicator.items():
            val = format_value(item.get('value', ''))
            unit = item.get('unit', '')
            t = item.get('time', '')[:15]
            lines.append(f'| {ind_name} | {t} | **{val}{unit}** |')
        lines.append('')
    else:
        lines.append('> 暂无数据')
        lines.append('')

    # 3. 国际宏观经济指标
    if intl_indicators:
        lines.append('### 国际宏观经济指标')
        lines.append('')
        lines.append('| 国家 | 指标 | 最新值 |')
        lines.append('|:----:|:----:|:------:|')
        for item in intl_indicators[:15]:
            country = COUNTRY_NAMES.get(item.get('country', ''), item.get('country', ''))
            lines.append(f'| {country} | {item["indicator"]} | {item["value"]} |')
        lines.append('')

    # 4. 重要资讯
    lines.append('### 重要财经资讯')
    lines.append('')
    if news_data:
        count = 0
        for item in news_data[:15]:
            title = item.get('title', '')
            brief = item.get('brief', '')
            source = item.get('source', '')
            t = item.get('time', '')
            if title:
                prefix = f'[{source}] ' if source else ''
                time_str = f' _{t}_' if t else ''
                lines.append(f'- {prefix}{title}{time_str}')
                if brief:
                    lines.append(f'  > {brief}')
                count += 1
        lines.append('')
    else:
        lines.append('> 今日暂无重要资讯')
        lines.append('')

    # 页脚
    lines.append('---')
    lines.append('> 数据来源：新浪行情、东方财富数据中心、新浪财经、网易财经、Trading Economics')
    lines.append('> 由 [macro-monitor-skill](https://github.com) 自动生成')

    return '\n'.join(lines)


# ========== 企业微信推送 ==========

def send_to_wecom(report_md, webhook_url):
    """企业微信 Webhook 推送"""
    max_len = 2048
    summary = report_md[:max_len]
    if len(report_md) > max_len:
        summary += '\n\n> ...已截取摘要，完整报告见 GitHub Actions Artifact'

    payload = {
        'msgtype': 'markdown',
        'markdown': {'content': summary}
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        result = resp.json()
        if result.get('errcode') == 0:
            print('[成功] 企业微信推送成功')
            return True
        else:
            print(f'[失败] errcode={result.get("errcode")}, errmsg={result.get("errmsg")}')
            return False
    except Exception as e:
        print(f'[错误] {e}')
        return False


# ========== 主流程 ==========

def main():
    print('=' * 55)
    print(' 每日宏观数据监控 v3.0')
    print('=' * 55)

    now = get_beijing_now()
    print(f'当前时间: {now.strftime("%Y-%m-%d %H:%M")} (GMT+8)')

    # 1. 全球市场指数
    print('\n[1/5] 采集全球市场指数...')
    market_indices = fetch_global_indices()
    print(f'  获取 {len(market_indices)} 个指数')
    for name, d in market_indices.items():
        print(f'    {name}: {d["price"]} ({d["change_pct"]}%)')

    # 2. 国内宏观经济指标
    domestic_indicators = fetch_domestic_indicators()

    # 3. 财经新闻
    print('\n[3/5] 采集财经新闻...')
    news_sina = fetch_sina_macro_news()
    print(f'  新浪财经: {len(news_sina)} 条')
    news_163 = fetch_163_macro_news()
    print(f'  网易财经: {len(news_163)} 条')
    news_cls = fetch_cls_telegraph()
    print(f'  财联社: {len(news_cls)} 条')
    news_data = news_sina + news_163 + news_cls
    # 去重
    seen_titles = set()
    unique_news = []
    for item in news_data:
        t = item.get('title', '')
        if t and t not in seen_titles:
            seen_titles.add(t)
            unique_news.append(item)
    news_data = unique_news
    print(f'  新闻合计: {len(news_data)} 条（去重后）')

    # 4. 国际宏观指标
    print('\n[4/5] 采集国际宏观指标...')
    intl_indicators = fetch_trading_economics()
    print(f'  获取 {len(intl_indicators)} 条')

    # 5. 生成报告
    print('\n[5/5] 生成报告...')
    report = generate_report(market_indices, domestic_indicators, news_data, intl_indicators)
    print(f'  报告长度: {len(report)} 字符')

    # 保存报告
    date_str = now.strftime('%Y-%m-%d')
    report_file = f'macro-report-{date_str}.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'  已保存: {report_file}')

    # 推送
    webhook_url = os.environ.get('WECOM_WEBHOOK_URL', '')
    if webhook_url:
        print('\n推送到企业微信...')
        send_to_wecom(report, webhook_url)
    else:
        print('\n[提示] 未设置 WECOM_WEBHOOK_URL，跳过推送')

    print('\n' + '=' * 55)
    print(' 运行完成')
    print('=' * 55)


if __name__ == '__main__':
    main()
