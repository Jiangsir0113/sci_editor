import uuid
import os
import tempfile
import time
from typing import Dict, Any

_sessions: Dict[str, Dict[str, Any]] = {}
TMP_DIR = os.path.join(tempfile.gettempdir(), "sci_editor_sessions")
SESSION_TTL = 3600  # 1 小时


def create_session(filename: str) -> str:
    doc_id = str(uuid.uuid4())
    session_dir = os.path.join(TMP_DIR, doc_id)
    os.makedirs(session_dir, exist_ok=True)
    _sessions[doc_id] = {
        "filename": filename,
        "dir": session_dir,
        "created_at": time.time(),
    }
    return doc_id


def get_session(doc_id: str) -> Dict[str, Any]:
    session = _sessions.get(doc_id)
    if session is None:
        raise KeyError(f"Session {doc_id} not found")
    return session


def session_path(doc_id: str, filename: str) -> str:
    return os.path.join(_sessions[doc_id]["dir"], filename)


def delete_session(doc_id: str) -> None:
    session = _sessions.pop(doc_id, None)
    if session:
        import shutil
        shutil.rmtree(session["dir"], ignore_errors=True)


def cleanup_expired() -> None:
    now = time.time()
    expired = [
        doc_id for doc_id, s in _sessions.items()
        if now - s["created_at"] > SESSION_TTL
    ]
    for doc_id in expired:
        delete_session(doc_id)
