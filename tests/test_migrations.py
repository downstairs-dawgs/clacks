import unittest

from sqlalchemy import inspect

from slack_clacks.configuration.database import get_engine, run_migrations


class TestMigrations(unittest.TestCase):
    def test_initial_migration(self):
        engine = get_engine(config_dir=":memory:")

        with engine.connect() as connection:
            run_migrations(connection)

            inspector = inspect(connection)

            table_names = inspector.get_table_names()
            self.assertIn("contexts", table_names)
            self.assertIn("current_context", table_names)

            contexts_columns = {
                col["name"] for col in inspector.get_columns("contexts")
            }
            self.assertEqual(
                contexts_columns,
                {"name", "access_token", "user_id", "workspace_id", "app_type"},
            )

            current_context_columns = {
                col["name"] for col in inspector.get_columns("current_context")
            }
            self.assertEqual(current_context_columns, {"timestamp", "context_name"})

            contexts_pk = inspector.get_pk_constraint("contexts")
            self.assertEqual(contexts_pk["constrained_columns"], ["name"])

            current_context_pk = inspector.get_pk_constraint("current_context")
            self.assertEqual(current_context_pk["constrained_columns"], ["timestamp"])

            current_context_fks = inspector.get_foreign_keys("current_context")
            self.assertEqual(len(current_context_fks), 1)
            fk = current_context_fks[0]
            self.assertEqual(fk["constrained_columns"], ["context_name"])
            self.assertEqual(fk["referred_table"], "contexts")
            self.assertEqual(fk["referred_columns"], ["name"])
            self.assertEqual(fk["options"]["ondelete"], "CASCADE")


if __name__ == "__main__":
    unittest.main()
