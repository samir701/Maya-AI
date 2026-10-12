"""Unit tests for ZETTA Session and SessionManager."""

import unittest
from core.zetta.interaction.session import Session, SessionManager
from shared.types import AIRole


class TestInteractionSession(unittest.TestCase):

    def setUp(self):
        self.mgr = SessionManager()

    def test_session_creation_and_message_appending(self):
        session = self.mgr.create_session(metadata={"client": "test"})
        self.assertTrue(session.session_id.startswith("sess_"))
        self.assertEqual(session.metadata["client"], "test")

        msg1 = session.add_message(AIRole.USER, "Hello ZETTA")
        msg2 = session.add_message(AIRole.ASSISTANT, "Hello user!")

        self.assertEqual(len(session.messages), 2)
        self.assertEqual(msg1.content, "Hello ZETTA")
        self.assertEqual(msg2.content, "Hello user!")

    def test_session_manager_load_and_history(self):
        session = self.mgr.load_or_create("test_sess_1")
        self.assertEqual(session.session_id, "test_sess_1")

        self.mgr.append_message("test_sess_1", AIRole.USER, "Msg 1")
        self.mgr.append_message("test_sess_1", AIRole.USER, "Msg 2")
        self.mgr.append_message("test_sess_1", AIRole.USER, "Msg 3")

        history = self.mgr.get_history("test_sess_1", limit=2)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].content, "Msg 2")
        self.assertEqual(history[1].content, "Msg 3")

    def test_session_clear_and_close(self):
        session = self.mgr.create_session("sess_clear")
        self.mgr.append_message("sess_clear", AIRole.USER, "Temp message")
        self.assertEqual(len(session.messages), 1)

        self.mgr.clear_session("sess_clear")
        self.assertEqual(len(session.messages), 0)

        self.mgr.close_session("sess_clear")
        self.assertIsNone(self.mgr.get_session("sess_clear"))


if __name__ == "__main__":
    unittest.main()
