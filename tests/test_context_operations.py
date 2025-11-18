import unittest

from sqlalchemy import select

from slack_clacks.configuration.database import (
    add_context,
    get_engine,
    run_migrations,
    set_current_context,
)
from slack_clacks.configuration.models import Context, CurrentContext


class TestContextOperations(unittest.TestCase):
    def setUp(self):
        self.engine = get_engine(config_dir=":memory:")
        with self.engine.connect() as connection:
            run_migrations(connection)

    def tearDown(self):
        self.engine.dispose()

    def test_add_context(self):
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            context = add_context(
                session,
                name="test-context",
                access_token="xoxp-test-token",
                user_id="U123456",
                workspace_id="T123456",
            )
            session.commit()

            self.assertEqual(context.name, "test-context")
            self.assertEqual(context.access_token, "xoxp-test-token")
            self.assertEqual(context.user_id, "U123456")
            self.assertEqual(context.workspace_id, "T123456")

        with Session(self.engine) as session:
            result = session.execute(
                select(Context).where(Context.name == "test-context")
            ).scalar_one()
            self.assertEqual(result.name, "test-context")

    def test_set_current_context(self):
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            add_context(
                session,
                name="context1",
                access_token="token1",
                user_id="U1",
                workspace_id="T1",
            )
            session.commit()

        with Session(self.engine) as session:
            current = set_current_context(session, "context1")
            session.commit()

            self.assertEqual(current.context_name, "context1")
            self.assertIsNotNone(current.timestamp)

    def test_current_context_history(self):
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            add_context(
                session, name="ctx1", access_token="t1", user_id="U1", workspace_id="T1"
            )
            add_context(
                session, name="ctx2", access_token="t2", user_id="U2", workspace_id="T2"
            )
            session.commit()

        with Session(self.engine) as session:
            set_current_context(session, "ctx1")
            session.commit()

        with Session(self.engine) as session:
            set_current_context(session, "ctx2")
            session.commit()

        with Session(self.engine) as session:
            set_current_context(session, "ctx1")
            session.commit()

        with Session(self.engine) as session:
            history = session.execute(
                select(CurrentContext).order_by(CurrentContext.timestamp)
            ).scalars()
            history_list = list(history)
            self.assertEqual(len(history_list), 3)
            self.assertEqual(history_list[0].context_name, "ctx1")
            self.assertEqual(history_list[1].context_name, "ctx2")
            self.assertEqual(history_list[2].context_name, "ctx1")

    def test_delete_context_cascades_to_current_context(self):
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            add_context(
                session, name="ctx1", access_token="t1", user_id="U1", workspace_id="T1"
            )
            add_context(
                session, name="ctx2", access_token="t2", user_id="U2", workspace_id="T2"
            )
            session.commit()

        with Session(self.engine) as session:
            set_current_context(session, "ctx1")
            session.commit()

        with Session(self.engine) as session:
            set_current_context(session, "ctx2")
            session.commit()

        with Session(self.engine) as session:
            set_current_context(session, "ctx1")
            session.commit()

        with Session(self.engine) as session:
            history_before = session.execute(select(CurrentContext)).scalars()
            self.assertEqual(len(list(history_before)), 3)

        with Session(self.engine) as session:
            context_to_delete = session.execute(
                select(Context).where(Context.name == "ctx1")
            ).scalar_one()
            session.delete(context_to_delete)
            session.commit()

        with Session(self.engine) as session:
            history_after = session.execute(select(CurrentContext)).scalars()
            history_list = list(history_after)
            self.assertEqual(len(history_list), 1)
            self.assertEqual(history_list[0].context_name, "ctx2")

        with Session(self.engine) as session:
            contexts = session.execute(select(Context)).scalars()
            context_list = list(contexts)
            self.assertEqual(len(context_list), 1)
            self.assertEqual(context_list[0].name, "ctx2")


if __name__ == "__main__":
    unittest.main()
