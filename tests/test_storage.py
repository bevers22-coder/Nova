import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.storage import (
    add_to_watchlist,
    get_holdings,
    get_saved_documents,
    get_watchlist,
    initialize_storage,
    remove_from_watchlist,
    remove_holding,
    save_document,
    save_holding,
)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "nova.sqlite3"
        self.environment = patch.dict(os.environ, {"NOVA_DATA_PATH": str(self.path)})
        self.environment.start()
        initialize_storage()

    def tearDown(self):
        self.environment.stop()
        self.temp_dir.cleanup()

    def test_initial_positions_persist_and_cost_basis_stays_unknown(self):
        holdings = get_holdings()
        self.assertEqual(
            {ticker: entry["shares"] for ticker, entry in holdings.items()},
            {"NVDA": 1, "ORCL": 5, "PLTR": 1, "MRVL": 2,
             "FTNT": 1, "ABBV": 1, "MP": 1, "PG": 12},
        )
        self.assertTrue(all(entry["cost_basis"] is None for entry in holdings.values()))
        initialize_storage()
        self.assertEqual(get_holdings(), holdings)

    def test_holdings_can_be_added_updated_and_removed(self):
        save_holding("aapl", 2, 175.5)
        self.assertEqual(get_holdings()["AAPL"], {"shares": 2.0, "cost_basis": 175.5})
        save_holding("AAPL", 3)
        self.assertEqual(get_holdings()["AAPL"], {"shares": 3.0, "cost_basis": None})
        remove_holding("AAPL")
        self.assertNotIn("AAPL", get_holdings())
        with self.assertRaises(ValueError):
            save_holding("AAPL", 0)

    def test_watchlist_and_saved_documents_survive_storage_reopen(self):
        add_to_watchlist("msft")
        add_to_watchlist("MSFT")
        remove_from_watchlist("MSFT")
        add_to_watchlist("NVDA")
        save_document("Algebra Notes", "Math", "# Linear equations\nSolve for x.")
        self.assertEqual(get_watchlist(), ["NVDA"])
        self.assertEqual(get_saved_documents()[0]["title"], "Algebra Notes")

    def test_existing_parent_permissions_are_not_changed(self):
        shared_directory = Path(self.temp_dir.name) / "shared"
        shared_directory.mkdir()
        shared_directory.chmod(0o755)
        configured_path = shared_directory / "nova.sqlite3"
        with patch.dict(os.environ, {"NOVA_DATA_PATH": str(configured_path)}):
            initialize_storage()
        self.assertEqual(
            stat.S_IMODE(shared_directory.stat().st_mode),
            0o755,
        )
        self.assertEqual(stat.S_IMODE(configured_path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
