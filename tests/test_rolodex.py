import unittest

from sqlalchemy import select
from sqlalchemy.orm import Session

from slack_clacks.configuration.database import add_context, get_engine, run_migrations
from slack_clacks.configuration.models import Context
from slack_clacks.rolodex.models import Alias
from slack_clacks.rolodex.operations import add_alias, list_aliases


class TestRolodexCascadeDelete(unittest.TestCase):
    def setUp(self):
        self.engine = get_engine(config_dir=":memory:")
        with self.engine.connect() as connection:
            run_migrations(connection)

    def tearDown(self):
        self.engine.dispose()

    def test_delete_context_cascades_to_aliases(self):
        with Session(self.engine) as session:
            add_context(
                session,
                name="test-ctx",
                access_token="fake-token",
                user_id="U000000001",
                workspace_id="T000000001",
                app_type="clacks",
            )
            session.commit()

        with Session(self.engine) as session:
            add_alias(session, "alice", "test-ctx", "user", "slack", "U000000002")
            add_alias(session, "bob", "test-ctx", "user", "slack", "U000000003")
            add_alias(session, "general", "test-ctx", "channel", "slack", "C000000001")
            session.commit()

        with Session(self.engine) as session:
            aliases = list_aliases(session, "test-ctx")
            self.assertEqual(len(aliases), 3)

        with Session(self.engine) as session:
            ctx = session.execute(
                select(Context).where(Context.name == "test-ctx")
            ).scalar_one()
            session.delete(ctx)
            session.commit()

        with Session(self.engine) as session:
            aliases = session.execute(select(Alias)).scalars().all()
            self.assertEqual(len(aliases), 0)

    def test_delete_context_only_deletes_its_aliases(self):
        with Session(self.engine) as session:
            add_context(
                session,
                name="ctx-a",
                access_token="fake-token-a",
                user_id="U000000001",
                workspace_id="T000000001",
                app_type="clacks",
            )
            add_context(
                session,
                name="ctx-b",
                access_token="fake-token-b",
                user_id="U000000002",
                workspace_id="T000000002",
                app_type="clacks",
            )
            session.commit()

        with Session(self.engine) as session:
            add_alias(session, "alice", "ctx-a", "user", "slack", "U000000003")
            add_alias(session, "bob", "ctx-b", "user", "slack", "U000000004")
            session.commit()

        with Session(self.engine) as session:
            ctx_a = session.execute(
                select(Context).where(Context.name == "ctx-a")
            ).scalar_one()
            session.delete(ctx_a)
            session.commit()

        with Session(self.engine) as session:
            aliases = session.execute(select(Alias)).scalars().all()
            self.assertEqual(len(aliases), 1)
            self.assertEqual(aliases[0].alias, "bob")
            self.assertEqual(aliases[0].context, "ctx-b")


class TestRolodexListLimits(unittest.TestCase):
    def setUp(self):
        self.engine = get_engine(config_dir=":memory:")
        with self.engine.connect() as connection:
            run_migrations(connection)

        with Session(self.engine) as session:
            add_context(
                session,
                name="test-ctx",
                access_token="fake-token",
                user_id="U000000001",
                workspace_id="T000000001",
                app_type="clacks",
            )
            session.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_list_aliases_returns_all_results_by_default(self):
        with Session(self.engine) as session:
            for index in range(150):
                add_alias(
                    session,
                    f"user-{index:03d}",
                    "test-ctx",
                    "user",
                    "slack",
                    f"U{index:09d}",
                )
            session.commit()

        with Session(self.engine) as session:
            aliases = list_aliases(session, "test-ctx")

        self.assertEqual(len(aliases), 150)

    def test_list_aliases_still_honors_explicit_limit(self):
        with Session(self.engine) as session:
            for index in range(5):
                add_alias(
                    session,
                    f"user-{index:03d}",
                    "test-ctx",
                    "user",
                    "slack",
                    f"U{index:09d}",
                )
            session.commit()

        with Session(self.engine) as session:
            aliases = list_aliases(session, "test-ctx", limit=2)

        self.assertEqual(len(aliases), 2)


if __name__ == "__main__":
    unittest.main()
