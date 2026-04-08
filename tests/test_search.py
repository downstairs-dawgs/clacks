import unittest

from slack_clacks.auth.constants import DEFAULT_USER_SCOPES, LITE_USER_SCOPES
from slack_clacks.auth.validation import ClacksInsufficientPermissions, validate
from slack_clacks.messaging.cli import generate_search_parser


class TestSearchScopeValidation(unittest.TestCase):
    def test_search_allowed_in_default_mode(self):
        validate("search:read", DEFAULT_USER_SCOPES, raise_on_error=True)

    def test_search_rejected_in_lite_mode(self):
        with self.assertRaises(ClacksInsufficientPermissions):
            validate("search:read", LITE_USER_SCOPES, raise_on_error=True)


class TestSearchParser(unittest.TestCase):
    def setUp(self):
        self.parser = generate_search_parser()

    def test_query_required(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args([])

    def test_defaults(self):
        args = self.parser.parse_args(["-q", "test"])
        self.assertEqual(args.query, "test")
        self.assertEqual(args.sort, "timestamp")
        self.assertEqual(args.sort_dir, "desc")
        self.assertEqual(args.limit, 20)
        self.assertIsNone(args.page)
        self.assertIsNone(args.cursor)

    def test_page_and_cursor_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["-q", "test", "--page", "2", "--cursor", "abc"])

    def test_sort_choices(self):
        args = self.parser.parse_args(["-q", "test", "-s", "score"])
        self.assertEqual(args.sort, "score")
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["-q", "test", "-s", "invalid"])

    def test_sort_dir_choices(self):
        args = self.parser.parse_args(["-q", "test", "--sort-dir", "asc"])
        self.assertEqual(args.sort_dir, "asc")
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["-q", "test", "--sort-dir", "invalid"])


if __name__ == "__main__":
    unittest.main()
