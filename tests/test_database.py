import tempfile
import unittest
from pathlib import Path
import uuid

from ComfyUI_Prompt_Negotiator.database.repository import SessionRepository


class DatabaseTests(unittest.TestCase):
    def test_parser_message_content_is_restored_from_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = SessionRepository(Path(tmp) / "test.sqlite3")
            repo.initialize()
            sid = str(uuid.uuid4())
            repo.create_session(sid, "Test", "sys")
            legacy_metadata = {
                "response_mode": "parser",
                "structured": True,
                "prompt": "portrait",
                "suggestions": ["add rim light"],
            }
            repo.add_message(sid, "assistant", "portrait\n\n• add rim light", metadata=legacy_metadata)
            messages = repo.get_messages(sid)
            expected = '{\n  "PROMPT": "portrait",\n  "SUGGERIMENTI": [\n    "add rim light"\n  ]\n}'
            self.assertEqual(messages[0].content, expected)

    def test_session_message_and_revision_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = SessionRepository(Path(tmp) / "test.sqlite3")
            repo.initialize()
            sid = str(uuid.uuid4())
            repo.create_session(sid, "Test", "sys")
            repo.add_message(sid, "user", "ciao")
            repo.add_message(sid, "assistant", "salve")
            revision = repo.save_approval(sid, "prompt finale", "model", "ltxv")
            session = repo.get_session(sid)
            messages = repo.get_messages(sid)
            self.assertEqual(revision, 1)
            self.assertEqual(session.final_prompt, "prompt finale")
            self.assertEqual(len(messages), 2)
