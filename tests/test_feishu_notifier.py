import os
import unittest
from unittest.mock import Mock, patch

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

        self.assertIn("A股/ETF MA20均线监控", message)
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


if __name__ == "__main__":
    unittest.main()
