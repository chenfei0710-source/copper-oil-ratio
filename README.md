# 铜油比指标追踪器

Copper-Oil Ratio Tracker — 基于 Binance USD-M 永续合约数据的铜油比指标追踪系统。

## 功能

- **铜油比指标**：铜价(COPPERUSDT) / 油价(OUSDT)，经济周期经典指标
- **A股叠加**：BABAUSDT 作为A股代理，标准化后与铜油比叠加对比
- **每日自动爬取**：GitHub Actions 每天 4 次定时拉取 Binance API 数据
- **即使关机也运行**：数据爬取在 GitHub 服务器上执行，自动提交到 GitHub Pages
- **在线查看**：网页自动加载最新 data.json

## 项目结构

```
copper-oil-ratio/
├── .github/workflows/
│   └── fetch-data.yml      # GitHub Actions 定时任务（每天4次）
├── docs/
│   ├── index.html          # 前端页面（GitHub Pages 部署）
│   └── data.json           # 爬虫输出的数据（自动生成）
├── fetch_data.py           # 数据爬虫脚本
└── README.md
```

## 部署步骤

1. 在 GitHub 创建新仓库（如 `copper-oil-ratio`）
2. 推送代码：
   ```bash
   cd copper-oil-ratio
   git init
   git add .
   git commit -m "init: copper-oil ratio tracker"
   git remote add origin https://github.com/你的用户名/copper-oil-ratio.git
   git push -u origin main
   ```
3. 在仓库设置开启 GitHub Pages：Settings → Pages → Source: GitHub Actions
4. 等待 Actions 执行完成，访问 `https://你的用户名.github.io/copper-oil-ratio/`

## 指标说明

| 指标 | 含义 |
|------|------|
| 铜油比上升 | 铜相对走强 → 工业需求扩张 → 经济回暖信号 |
| 铜油比下降 | 油相对走强 → 滞胀风险上升 |
| 铜油比 vs BABA 背离 | 铜油比涨但A股不跟 → A股可能补涨 |
| 偏离均值 >15% | 警惕均值回归 |

## 数据源

- Binance USD-M Futures API (`fapi.binance.com`)
- 铜: COPPERUSDT 永续合约
- 油: OUSDT 永续合约
- A股代理: BABAUSDT 永续合约

## 本地运行

```bash
python3 fetch_data.py   # 手动爬取数据
open docs/index.html     # 本地打开页面
```

## 许可

仅供研究参考，不构成投资建议。
