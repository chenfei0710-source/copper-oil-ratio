#!/usr/bin/env python3
"""
铜油比指标 — 数据爬虫
- 铜/油: Binance USD-M Futures API
- 上证指数: 腾讯财经 K线API
输出: docs/data.json
"""

import json
import time
import urllib.request
import urllib.error
import os
from datetime import datetime, timezone

BINANCE_API = 'https://fapi.binance.com/fapi/v1/klines'
SSE_API = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get'

SYMBOLS = {
    'copper': 'COPPERUSDT',
    'oil': 'OUSDT',
}
LIMIT = 200


def fetch_binance_klines(symbol, interval='1d', limit=200):
    """Binance K线"""
    url = f'{BINANCE_API}?symbol={symbol}&interval={interval}&limit={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': 'CopperOilTracker/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            print(f'  [{symbol}] retry {attempt+1}: {e}')
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                raise
    return []


def fetch_sse_klines(datalen=200):
    """上证指数日K线 (腾讯接口) — 返回 {date_str: close}"""
    url = f'{SSE_API}?param=sh000001,day,,,200,qfq'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            day_list = data.get('data', {}).get('sh000001', {}).get('day', [])
            # 格式: [["2026-06-01","open","close","high","low","volume"], ...]
            result = {}
            for row in day_list:
                if len(row) >= 3:
                    date_str = row[0]
                    close = float(row[2])  # close = index 2
                    result[date_str] = close
            return result
        except Exception as e:
            print(f'  [SSE] retry {attempt+1}: {e}')
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                raise
    return {}


def parse_binance_close(klines):
    """{timestamp_ms: close_price}"""
    result = {}
    for k in klines:
        result[k[0]] = float(k[4])
    return result


def main():
    print(f'[{datetime.now(timezone.utc).isoformat()}] 开始爬取铜油比 + 上证指数数据...')

    # ── Binance: 铜 + 油 ────────────────────────────────
    raw = {}
    for key, symbol in SYMBOLS.items():
        print(f'  拉取 Binance {symbol}...')
        klines = fetch_binance_klines(symbol, '1d', LIMIT)
        raw[key] = parse_binance_close(klines)
        print(f'    获取 {len(raw[key])} 条')
        time.sleep(0.3)

    # ── 上证指数 ────────────────────────────────────────
    print(f'  拉取上证指数 sh000001...')
    sse_raw = fetch_sse_klines()
    print(f'    获取 {len(sse_raw)} 条')

    # ── 对齐: Binance 用 timestamp_ms, 上证用 date_str ───
    # 将 Binance timestamp 转为 date_str 用于匹配
    copper_map = raw['copper']
    oil_map = raw['oil']

    # 构建 date_str -> {copper, oil} 映射
    binance_dates = {}
    for ts, c in copper_map.items():
        if ts in oil_map:
            d = datetime.utcfromtimestamp(ts / 1000).strftime('%Y-%m-%d')
            binance_dates[d] = {'copper': c, 'oil': oil_map[ts]}

    # 取交集
    common_dates = sorted(set(binance_dates) & set(sse_raw))
    print(f'  对齐后公共日期: {len(common_dates)} 条')

    dates = []
    copper = []
    oil = []
    sse = []
    ratio = []

    for d in common_dates:
        c = binance_dates[d]['copper']
        o = binance_dates[d]['oil']
        s = sse_raw[d]
        r = c / o
        dates.append(d)
        copper.append(c)
        oil.append(o)
        sse.append(s)
        ratio.append(r)

    # 标准化 (起点=100)
    if ratio and sse:
        ratio_idx = [r / ratio[0] * 100 for r in ratio]
        sse_idx = [s / sse[0] * 100 for s in sse]
    else:
        ratio_idx = []
        sse_idx = []

    # 统计
    mean_ratio = sum(ratio) / len(ratio) if ratio else 0
    latest_ratio = ratio[-1] if ratio else 0
    deviation = (latest_ratio / mean_ratio - 1) * 100 if mean_ratio else 0

    output = {
        'meta': {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'updated_at_local': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(dates),
            'data_range': f'{dates[0]} ~ {dates[-1]}' if dates else '',
            'sources': {
                'copper': 'Binance COPPERUSDT',
                'oil': 'Binance OUSDT',
                'sse': 'Tencent sh000001 (上证指数)',
            },
        },
        'stats': {
            'ratio_current': round(latest_ratio, 4),
            'ratio_mean': round(mean_ratio, 4),
            'deviation_pct': round(deviation, 2),
            'copper_current': round(copper[-1] if copper else 0, 4),
            'oil_current': round(oil[-1] if oil else 0, 4),
            'sse_current': round(sse[-1] if sse else 0, 2),
            'copper_change_pct': round((copper[-1] / copper[0] - 1) * 100, 2) if copper and copper[0] else 0,
            'oil_change_pct': round((oil[-1] / oil[0] - 1) * 100, 2) if oil and oil[0] else 0,
            'sse_change_pct': round((sse[-1] / sse[0] - 1) * 100, 2) if sse and sse[0] else 0,
            'ratio_change_pct': round((latest_ratio / ratio[0] - 1) * 100, 2) if ratio and ratio[0] else 0,
        },
        'series': {
            'dates': dates,
            'copper': copper,
            'oil': oil,
            'sse': sse,
            'ratio': ratio,
            'ratio_normalized': ratio_idx,
            'sse_normalized': sse_idx,
        },
    }

    # 输出
    script_dir = os.path.dirname(os.path.abspath(__file__))
    docs_dir = os.path.join(script_dir, 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    output_path = os.path.join(docs_dir, 'data.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

    print(f'\n数据爬取完成:')
    print(f'  铜油比: {latest_ratio:.2f} (偏离均值 {deviation:+.1f}%)')
    print(f'  铜价: ${copper[-1]:.2f} | 油价: ${oil[-1]:.4f}')
    print(f'  上证指数: {sse[-1]:.2f}')
    print(f'  数据范围: {dates[0]} ~ {dates[-1]} ({len(dates)} 天)')
    print(f'  输出: {output_path}')


if __name__ == '__main__':
    main()
