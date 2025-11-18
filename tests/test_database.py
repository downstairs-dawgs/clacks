import tempfile
import unittest
from pathlib import Path

from platformdirs import user_config_dir

from slack_clacks.configuration.database import get_config_dir


class TestGetConfigDir(unittest.TestCase):
    def test_default_config_dir(self):
        result = get_config_dir()
        expected = Path(user_config_dir("slack-clacks"))
        self.assertEqual(result, expected)
        self.assertTrue(result.exists())

    def test_custom_config_dir_as_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = f"{tmpdir}/custom_config"
            result = get_config_dir(custom_path)
            self.assertEqual(result, Path(custom_path))
            self.assertTrue(result.exists())

    def test_custom_config_dir_as_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom_config"
            result = get_config_dir(custom_path)
            self.assertEqual(result, custom_path)
            self.assertTrue(result.exists())

    def test_creates_nested_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "a" / "b" / "c"
            result = get_config_dir(nested_path)
            self.assertEqual(result, nested_path)
            self.assertTrue(result.exists())


if __name__ == "__main__":
    unittest.main()
