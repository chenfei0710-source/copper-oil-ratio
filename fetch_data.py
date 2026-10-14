#!/usr/bin/env python3
"""
铜油比指标 — 数据爬虫
从 Binance USD-M Futures API 拉取日线K线数据，计算铜油比，
输出为 data.json 供前端页面读取。

输出文件: docs/data.json
"""

import json
import time
import urllib.request
import urllib.error
import os
from datetime import datetime, timezone

API_BASE = 'https://fapi.binance.com/fapi/v1/klines'
SYMBOLS = {
    'copper': 'COPPERUSDT',
    'oil': 'OUSDT',
    'baba': 'BABAUSDT',
}
LIMIT = 200  # 拉取最近200天

def fetch_klines(symbol, interval='1d', limit=200):
    """从 Binance API 拉取K线数据"""
    url = f'{API_BASE}?symbol={symbol}&interval={interval}&limit={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': 'CopperOilTracker/1.0'})
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            print(f'  [{symbol}] 第{attempt+1}次失败: {e}')
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
            else:
                raise
    return []

def parse_close(klines):
    """提取 {timestamp_ms: close_price} 映射"""
    result = {}
    for k in klines:
        ts = k[0]        # open time
        close = float(k[4])  # close price
        result[ts] = close
    return result

def main():
    print(f'[{datetime.now(timezone.utc).isoformat()}] 开始爬取铜油比数据...')

    # 拉取三个品种
    raw_data = {}
    for key, symbol in SYMBOLS.items():
        print(f'  拉取 {symbol}...')
        klines = fetch_klines(symbol, '1d', LIMIT)
        raw_data[key] = parse_close(klines)
        print(f'    获取 {len(raw_data[key])} 条记录')
        time.sleep(0.3)  # 避免触发频率限制

    # 对齐时间戳（三者交集）
    common_ts = sorted(
        set(raw_data['copper']) & set(raw_data['oil']) & set(raw_data['baba'])
    )
    print(f'  对齐后公共时间戳: {len(common_ts)} 条')

    # 构建时间序列
    dates = []
    copper = []
    oil = []
    baba = []
    ratio = []

    for ts in common_ts:
        c = raw_data['copper'][ts]
        o = raw_data['oil'][ts]
        b = raw_data['baba'][ts]
        r = c / o
        dates.append(ts)
        copper.append(c)
        oil.append(o)
        baba.append(b)
        ratio.append(r)

    # 标准化 (起点=100)
    if ratio and ratio[0] and baba and baba[0]:
        ratio_idx = [r / ratio[0] * 100 for r in ratio]
        baba_idx = [b / baba[0] * 100 for b in baba]
    else:
        ratio_idx = []
        baba_idx = []

    # 统计
    mean_ratio = sum(ratio) / len(ratio) if ratio else 0
    latest_ratio = ratio[-1] if ratio else 0
    deviation = (latest_ratio / mean_ratio - 1) * 100 if mean_ratio else 0

    output = {
        'meta': {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'updated_at_local': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(dates),
            'source': 'Binance USD-M Futures',
            'symbols': SYMBOLS,
        },
        'stats': {
            'ratio_current': round(latest_ratio, 4),
            'ratio_mean': round(mean_ratio, 4),
            'deviation_pct': round(deviation, 2),
            'copper_current': round(copper[-1] if copper else 0, 4),
            'oil_current': round(oil[-1] if oil else 0, 4),
            'baba_current': round(baba[-1] if baba else 0, 2),
            'copper_change_pct': round((copper[-1] / copper[0] - 1) * 100, 2) if copper and copper[0] else 0,
            'oil_change_pct': round((oil[-1] / oil[0] - 1) * 100, 2) if oil and oil[0] else 0,
            'baba_change_pct': round((baba[-1] / baba[0] - 1) * 100, 2) if baba and baba[0] else 0,
            'ratio_change_pct': round((latest_ratio / ratio[0] - 1) * 100, 2) if ratio and ratio[0] else 0,
        },
        'series': {
            'dates': dates,
            'copper': copper,
            'oil': oil,
            'baba': baba,
            'ratio': ratio,
            'ratio_normalized': ratio_idx,
            'baba_normalized': baba_idx,
        },
    }

    # 输出到 docs/data.json (GitHub Pages 目录)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    docs_dir = os.path.join(script_dir, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    output_path = os.path.join(docs_dir, 'data.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

    print(f'\n数据爬取完成:')
    print(f'  铜油比: {latest_ratio:.2f} (偏离均值 {deviation:+.1f}%)')
    print(f'  铜价: ${copper[-1]:.2f} | 油价: ${oil[-1]:.4f} | BABA: ${baba[-1]:.2f}')
    print(f'  数据范围: {len(dates)} 天')
    print(f'  输出: {output_path}')

if __name__ == '__main__':
    main()
