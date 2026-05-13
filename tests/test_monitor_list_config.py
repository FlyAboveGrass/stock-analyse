import unittest


class MonitorListConfigTest(unittest.TestCase):
    def test_load_monitor_list_from_config_filters_unsupported_symbols(self):
        from config.monitor_list import (
            get_unsupported_monitor_symbols,
            load_monitor_list_from_config,
        )

        config = {
            "notification": {
                "feishu": {
                    "monitor_list": [
                        "sh000001",
                        "sh000688",
                        "usr_ixic",
                        "nf_IF0",
                        "sz159934",
                        "hkhsi",
                        "hk01810",
                        "sh688981",
                        "sz002050",
                        "sh000905",
                    ]
                }
            }
        }

        monitor_list = load_monitor_list_from_config(config)

        self.assertEqual(
            monitor_list,
            [
                {"code": "000001.SH", "name": "上证指数", "type": "index"},
                {"code": "000688.SH", "name": "科创50", "type": "index"},
                {"code": "159934", "name": "黄金ETF", "type": "etf"},
                {"code": "HSI", "name": "恒生指数", "type": "index"},
                {"code": "01810.HK", "name": "小米集团-W", "type": "hk"},
                {"code": "688981", "name": "中芯国际", "type": "stock"},
                {"code": "002050", "name": "三花智控", "type": "stock"},
                {"code": "000905.SH", "name": "中证500", "type": "index"},
            ],
        )

        self.assertEqual(
            get_unsupported_monitor_symbols(config),
            [
                ("usr_ixic", "当前实现未接入美股/美股指数历史数据与实时行情抓取"),
                ("nf_IF0", "当前实现未接入中金所期货连续合约历史数据与实时行情抓取"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
