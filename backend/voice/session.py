import asyncio
import json
import os
from dataclasses import dataclass, field
from uuid import uuid4

STATE_FILE = os.path.join(os.path.dirname(__file__), ".session_store.json")

@dataclass
class VoiceSession:
    session_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    audio_queue: asyncio.Queue = field(
        default_factory=lambda: asyncio.Queue(maxsize=100)
    )
    is_active: bool = False
    user_id: str | None = None
    pending_plan: dict | None = None
    pending_actions: list[dict] = field(default_factory=list)
    detected_language: str = "hi-IN"
    total_chunks: int = 0
    total_bytes: int = 0

class VoiceSessionManager:
    def __init__(self):
        self.sessions: dict[str, VoiceSession] = {}
        self.user_sessions: dict[str, VoiceSession] = {}
        self._load_persisted_state()

    def _load_persisted_state(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for uid, sdata in data.items():
                    s = VoiceSession(user_id=uid)
                    s.pending_plan = sdata.get("pending_plan")
                    s.pending_actions = sdata.get("pending_actions", [])
                    s.detected_language = sdata.get("detected_language", "hi-IN")
                    self.sessions[s.session_id] = s
                    self.user_sessions[uid] = s
        except Exception as e:
            print(f"Session store load note: {e}")

    def save_persisted_state(self):
        try:
            data = {}
            for uid, s in self.user_sessions.items():
                if s.pending_actions or s.pending_plan:
                    data[uid] = {
                        "pending_plan": s.pending_plan,
                        "pending_actions": s.pending_actions,
                        "detected_language": s.detected_language,
                    }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Session store save note: {e}")

    def create_session(self) -> VoiceSession:
        session = VoiceSession()
        self.sessions[session.session_id] = session
        return session

    def get_or_create_for_user(self, user_id: str) -> VoiceSession:
        if user_id in self.user_sessions:
            return self.user_sessions[user_id]
        session = VoiceSession(user_id=user_id)
        self.sessions[session.session_id] = session
        self.user_sessions[user_id] = session
        return session

    def remove_session(self, session_id: str):
        session = self.sessions.pop(session_id, None)
        if session and session.user_id:
            if not session.pending_actions and not session.pending_plan:
                self.user_sessions.pop(session.user_id, None)
                self.save_persisted_state()

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

voice_sessions = VoiceSessionManager()
