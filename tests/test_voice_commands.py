import unittest

from modules.voice_commands import parse_voice_command


class VoiceCommandTests(unittest.TestCase):
    def test_requested_module_aliases_navigate_to_their_modules(self):
        examples = {
            "Open the stock screener": "Market Screener",
            "Show my portfolio": "Portfolio Analytics",
            "Open backtesting": "Backtesting Lab",
            "Open my homework assistant": "Study Studio",
            "Show market information": "Command Center",
        }
        for transcript, destination in examples.items():
            with self.subTest(transcript=transcript):
                self.assertEqual(
                    parse_voice_command(transcript, "Command Center"),
                    ("navigate", destination),
                )

    def test_research_command_preserves_the_company_query(self):
        self.assertEqual(
            parse_voice_command("Research NVIDIA", "Command Center"),
            ("research", "NVIDIA"),
        )

    def test_unmatched_speech_falls_back_to_study_or_asset_input(self):
        self.assertEqual(
            parse_voice_command("Explain this equation", "Study Studio"),
            ("study", "Explain this equation"),
        )
        self.assertEqual(
            parse_voice_command("AAPL", "Command Center"),
            ("asset", "AAPL"),
        )


if __name__ == "__main__":
    unittest.main()
