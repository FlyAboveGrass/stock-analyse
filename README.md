# A股股票及ETF均线监控系统

> 自动监控A股股票和ETF的20日均线突破/跌破信号，通过Telegram推送通知

## 功能特性

- 📈 **实时监控** - 每10分钟自动获取最新股价
- 📊 **MA20计算** - 基于20日移动平均线判断趋势
- 🔔 **即时通知** - 股价突破/跌破MA20时立即推送Telegram通知
- 💾 **状态记忆** - 持久化保存状态，避免重复通知
- 🛠️ **灵活配置** - 支持自定义监控列表和间隔时间
- 📊 **MA20报表** - 生成近5日MA20状态报表

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Telegram Bot

1. 打开 Telegram，搜索 `@BotFather`
2. 发送 `/newbot` 创建机器人
3. 获取 Bot Token
4. 搜索你的机器人，点击 Start
5. 访问：`https://api.telegram.org/bot<TOKEN>/getUpdates`
6. 获取 Chat ID

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 Token 和 Chat ID
```

### 4. 运行监控服务

```bash
python main.py
```

### 5. 生成MA20报表

```bash
python test_ma20.py
# 报表将保存到 data/ma20_YYYY.MM.DD-HH:MM_监控报告.md
```

## 配置说明

修改 `config.yaml` 文件：

```yaml
monitor:
  interval: 600  # 监控间隔（秒），默认10分钟

stocks:
  - "600519"   # 贵州茅台
  - "000001"   # 平安银行
  # 添加更多股票...

etfs:
  - "510300"   # 沪深300ETF
  - "510500"   # 中证500ETF
  # 添加更多ETF...

ma:
  period: 20   # 均线周期
```

## 项目结构

```
stock-monitor/
├── config/
│   ├── __init__.py
│   └── loader.py          # 配置文件加载
├── core/
│   ├── __init__.py
│   ├── fetcher.py         # 行情数据获取
│   ├── indicator.py       # 技术指标计算
│   └── detector.py        # 信号检测
├── notification/
│   ├── __init__.py
│   └── telegram.py        # Telegram通知
├── storage/
│   ├── __init__.py
│   └── state.py           # 状态持久化
├── data/                   # 状态数据目录
├── main.py                 # 主入口
├── config.yaml             # 配置文件
├── requirements.txt       # 依赖
└── .env                    # 环境变量
```

## 部署

### 本地运行

```bash
# 方式1: 直接运行
python main.py

# 方式2: 使用 screen
screen -S stock-monitor
python main.py
# Ctrl+A D 退出 screen
```

### Docker 部署

```bash
# 构建镜像
docker build -t stock-monitor .

# 运行
docker run -d \
  --name stock-monitor \
  -e TELEGRAM_TOKEN=xxx \
  -e TELEGRAM_CHAT_ID=xxx \
  -v $(pwd)/data:/app/data \
  stock-monitor
```

### VPS 部署

```bash
# 使用 systemd
sudo cp stock-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stock-monitor
sudo systemctl start stock-monitor
```

## 监控逻辑

```
每个监控周期:
1. 获取所有监控标的的最新价格
2. 获取过去20个交易日的历史数据
3. 计算MA20 = 20日收盘价均值
4. 判断当前位置: price > MA20 (多头) / price < MA20 (空头)
5. 与上次状态对比:
   - 从below变为above → 买入信号 🚀
   - 从above变为below → 卖出信号 🔻
6. 发送通知（仅状态变化时）
7. 保存当前状态
```

## 通知示例

**突破买入信号：**
```
🚀 600519 突破20日均线

• 现价: `1850.50`
• MA20: `1820.30`
• 位置: 🌙 多头
• 时间: 2026-03-12 10:30:00
```

## 常见问题

### Q: 为什么有时候获取不到数据？
A: 可能是因为A股节假日休市，或者网络问题。程序会自动跳过并等待下次重试。

### Q: 首次运行没有收到通知？
A: 首次运行会记录状态但不会发送通知，只有状态发生变化时才会通知。

### Q: 如何修改监控间隔？
A: 修改 `config.yaml` 中的 `monitor.interval` 值（单位：秒）。

## License

MIT
