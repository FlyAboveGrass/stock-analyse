#!/usr/bin/env python3
"""验证飞书 MA20 日报是否完整生成。"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notification.feishu import FeishuNotifier, MONITOR_LIST


def main() -> int:
    os.environ.setdefault("FEISHU_WEBHOOK_URL", "https://example.com/webhook")

    notifier = FeishuNotifier()
    report = notifier._generate_report(days=3)

    dates = report.get("dates", [])
    stocks = report.get("stocks", [])
    stock_count = len(stocks)
    expected_count = len(MONITOR_LIST)

    failures = []

    if len(dates) != 3:
        failures.append(f"最近交易日数量异常: expected=3 actual={len(dates)}")

    if stock_count != expected_count:
        failures.append(f"监控项数量异常: expected={expected_count} actual={stock_count}")

    for stock in stocks:
        bad_statuses = [status for status in stock.get("statuses", []) if status.startswith("❌")]
        if bad_statuses:
            failures.append(
                f"{stock['name']}（{stock['code']}）存在异常状态: {' | '.join(stock['statuses'])}"
            )

    print(notifier._build_report_message(report, days=3))

    if failures:
        print("\n验证失败:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\n验证通过: 所有监控项均正常展示。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
