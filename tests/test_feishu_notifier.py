import os
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

import notification.feishu as feishu_module
from notification.feishu import FeishuNotifier


class FeishuNotifierReportTest(unittest.TestCase):
    def setUp(self):
        os.environ["FEISHU_WEBHOOK_URL"] = "https://example.com/webhook"
        self.notifier = FeishuNotifier()

    def test_build_report_message_uses_plain_text_layout_for_feishu(self):
        report = {
            "dates": ["2026-05-08", "2026-05-09", "2026-05-12"],
            "stocks": [
                {
                    "name": "化工ETF",
                    "code": "516020",
                    "statuses": ["❌ 错误", "❌ 错误", "❌ 错误"],
                },
                {
                    "name": "上证指数",
                    "code": "000001.SH",
                    "statuses": ["✅ +0.48%", "✅ -0.00%", "✅ +1.08%"],
                },
            ],
        }

        message = self.notifier._build_report_message(report, days=3)

        self.assertIn("A股/港股/ETF MA20均线监控", message)
        self.assertIn("日期: 2026-05-08 | 2026-05-09 | 2026-05-12", message)
        self.assertIn("化工ETF（516020）: ❌ 错误 | ❌ 错误 | ❌ 错误", message)
        self.assertIn("上证指数（000001.SH）: ✅ +0.48% | ✅ -0.00% | ✅ +1.08%", message)
        self.assertNotIn("| --- |", message)
        self.assertNotIn("## ", message)

    @patch("notification.feishu.requests.post")
    def test_send_daily_report_sends_plain_text_payload(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_post.return_value = mock_response

        report = {
            "dates": ["2026-05-08", "2026-05-09", "2026-05-12"],
            "stocks": [
                {
                    "name": "化工ETF",
                    "code": "516020",
                    "statuses": ["❌ 错误", "❌ 错误", "❌ 错误"],
                }
            ],
        }

        with patch.object(self.notifier, "_generate_report", return_value=report):
            sent = self.notifier.send_daily_report(days=3)

        self.assertTrue(sent)
        self.assertEqual(mock_post.call_count, 1)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["msg_type"], "text")
        self.assertIn("日期: 2026-05-08 | 2026-05-09 | 2026-05-12", payload["content"]["text"])
        self.assertNotIn("| --- |", payload["content"]["text"])

    def test_get_stock_data_etf_falls_back_to_sina_when_em_raises(self):
        fallback_hist = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-05-08", "2026-05-09", "2026-05-12"]).date,
                "close": [1.01, 1.03, 1.05],
            }
        )
        fake_ak = SimpleNamespace(
            fund_etf_hist_em=Mock(side_effect=RuntimeError("eastmoney down")),
            fund_etf_hist_sina=Mock(return_value=fallback_hist),
        )

        with patch.dict("sys.modules", {"akshare": fake_ak}):
            hist, price_col = feishu_module.get_stock_data("516020", "etf")

        self.assertEqual(price_col, "收盘")
        self.assertEqual(hist["日期"].astype(str).tolist(), ["2026-05-08", "2026-05-09", "2026-05-12"])
        self.assertEqual(hist["收盘"].tolist(), [1.01, 1.03, 1.05])
        fake_ak.fund_etf_hist_sina.assert_called_once_with(symbol="sh516020")

    def test_get_stock_data_hk_uses_hk_daily(self):
        hk_hist = pd.DataFrame(
            {
                "date": ["2026-05-08", "2026-05-09", "2026-05-12"],
                "close": [52.1, 53.4, 54.2],
            }
        )
        fake_ak = SimpleNamespace(
            stock_hk_daily=Mock(return_value=hk_hist),
        )

        with patch.dict("sys.modules", {"akshare": fake_ak}):
            hist, price_col = feishu_module.get_stock_data("01810.HK", "hk")

        self.assertEqual(price_col, "收盘")
        self.assertEqual(hist["日期"].astype(str).tolist(), ["2026-05-08", "2026-05-09", "2026-05-12"])
        self.assertEqual(hist["收盘"].tolist(), [52.1, 53.4, 54.2])
        fake_ak.stock_hk_daily.assert_called_once_with(symbol="01810", adjust="qfq")

    def test_generate_report_uses_first_successful_symbol_dates_when_probe_fails(self):
        hist = pd.DataFrame(
            {
                "日期": pd.to_datetime(
                    [
                        "2026-04-14",
                        "2026-04-15",
                        "2026-04-16",
                        "2026-04-17",
                        "2026-04-18",
                        "2026-04-21",
                        "2026-04-22",
                        "2026-04-23",
                        "2026-04-24",
                        "2026-04-25",
                        "2026-04-28",
                        "2026-04-29",
                        "2026-04-30",
                        "2026-05-06",
                        "2026-05-07",
                        "2026-05-08",
                        "2026-05-09",
                        "2026-05-12",
                        "2026-05-13",
                        "2026-05-14",
                        "2026-05-15",
                        "2026-05-18",
                    ]
                ),
                "收盘": [float(i) for i in range(1, 23)],
            }
        )
        fake_ak = SimpleNamespace(
            fund_etf_hist_em=Mock(side_effect=RuntimeError("probe failed")),
        )

        with patch.dict("sys.modules", {"akshare": fake_ak}):
            with patch.object(
                feishu_module,
                "MONITOR_LIST",
                [{"code": "516020", "name": "化工ETF", "type": "etf"}],
            ):
                with patch.object(feishu_module, "get_stock_data", return_value=(hist, "收盘")):
                    with patch.object(feishu_module, "get_target_realtime_quotes", return_value={"etf": {}, "stock": {}, "index": {}}):
                        report = self.notifier._generate_report(days=3)

        self.assertEqual(report["dates"], ["2026-05-14", "2026-05-15", "2026-05-18"])
        self.assertEqual(len(report["stocks"]), 1)
        self.assertEqual(report["stocks"][0]["statuses"], ["✅ +5.26%", "✅ +5.00%", "✅ +4.76%"])

    @patch("notification.feishu.requests.get")
    def test_get_target_realtime_quotes_batches_monitored_symbols(self, mock_get):
        mainland_response = Mock()
        mainland_response.json.return_value = {
            "data": {
                "diff": [
                    {"f12": "516020", "f2": 1.234, "f3": 0.56, "f14": "化工ETF"},
                    {"f12": "000001", "f2": 3200.12, "f3": -0.32, "f14": "上证指数"},
                    {"f12": "002050", "f2": 25.67, "f3": 1.23, "f14": "三花智控"},
                ]
            }
        }
        hsi_response = Mock()
        hsi_response.json.return_value = {
            "data": {
                "diff": [
                    {"f12": "HSI", "f2": 2356789, "f3": 123, "f14": "恒生指数"},
                ]
            }
        }
        mock_get.side_effect = [mainland_response, hsi_response]

        quotes = feishu_module.get_target_realtime_quotes(
            [
                {"code": "516020", "name": "化工ETF", "type": "etf"},
                {"code": "000001.SH", "name": "上证指数", "type": "index"},
                {"code": "HSI", "name": "恒生指数", "type": "index"},
                {"code": "002050", "name": "三花智控", "type": "stock"},
            ]
        )

        self.assertEqual(quotes["etf"]["516020"], {"price": 1.234, "change_pct": 0.56})
        self.assertEqual(quotes["index"]["000001"], {"price": 3200.12, "change_pct": -0.32})
        self.assertEqual(quotes["stock"]["002050"], {"price": 25.67, "change_pct": 1.23})
        self.assertEqual(quotes["index"]["HSI"], {"price": 23567.89, "change_pct": 1.23})
        self.assertEqual(mock_get.call_count, 2)

        mainland_params = mock_get.call_args_list[0].kwargs["params"]
        self.assertEqual(
            mainland_params["secids"],
            "1.516020,1.000001,0.002050,?v=08926209912590994",
        )

        hsi_params = mock_get.call_args_list[1].kwargs["params"]
        self.assertEqual(hsi_params["fs"], "i:100.HSI")

    def test_get_target_realtime_quotes_includes_hk_symbols(self):
        fake_ak = SimpleNamespace(
            stock_hk_spot_em=Mock(
                return_value=pd.DataFrame(
                    {
                        "代码": ["01810", "09988"],
                        "名称": ["小米集团-W", "阿里巴巴-W"],
                        "最新价": [52.3, 84.6],
                        "涨跌幅": [1.56, -0.78],
                    }
                )
            )
        )

        with patch.dict("sys.modules", {"akshare": fake_ak}):
            quotes = feishu_module.get_target_realtime_quotes(
                [
                    {"code": "01810.HK", "name": "小米集团-W", "type": "hk"},
                    {"code": "09988.HK", "name": "阿里巴巴-W", "type": "hk"},
                ]
            )

        self.assertEqual(quotes["hk"]["01810"], {"price": 52.3, "change_pct": 1.56})
        self.assertEqual(quotes["hk"]["09988"], {"price": 84.6, "change_pct": -0.78})
        fake_ak.stock_hk_spot_em.assert_called_once_with()

    def test_generate_report_appends_today_realtime_when_history_not_updated(self):
        hist = pd.DataFrame(
            {
                "日期": pd.to_datetime(
                    [
                        "2026-04-14",
                        "2026-04-15",
                        "2026-04-16",
                        "2026-04-17",
                        "2026-04-20",
                        "2026-04-21",
                        "2026-04-22",
                        "2026-04-23",
                        "2026-04-24",
                        "2026-04-27",
                        "2026-04-28",
                        "2026-04-29",
                        "2026-04-30",
                        "2026-05-06",
                        "2026-05-07",
                        "2026-05-08",
                        "2026-05-11",
                        "2026-05-12",
                        "2026-05-13",
                        "2026-05-14",
                        "2026-05-15",
                        "2026-05-18",
                    ]
                ),
                "收盘": [float(i) for i in range(1, 23)],
            }
        )

        class FakeDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 5, 19, 13, 30, 0)

        class FakeDate(date):
            @classmethod
            def today(cls):
                return cls(2026, 5, 19)

        with patch.object(
            feishu_module,
            "MONITOR_LIST",
            [{"code": "516020", "name": "化工ETF", "type": "etf"}],
        ):
            with patch.object(feishu_module, "get_stock_data", return_value=(hist, "收盘")):
                with patch.object(
                    feishu_module,
                    "get_target_realtime_quotes",
                    return_value={"etf": {"516020": {"price": 30.0, "change_pct": 2.34}}, "stock": {}, "index": {}},
                ):
                    with patch.object(feishu_module, "datetime", FakeDateTime):
                        with patch.object(feishu_module, "date", FakeDate):
                            report = self.notifier._generate_report(days=3)

        self.assertEqual(report["dates"], ["2026-05-15", "2026-05-18", "2026-05-19"])
        self.assertEqual(report["stocks"][0]["statuses"], ["✅ +5.00%", "✅ +4.76%", "✅ +2.34%"])


if __name__ == "__main__":
    unittest.main()
