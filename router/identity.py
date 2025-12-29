from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from fastapi import Request


# in identity.py
@dataclass(frozen=True)
class IdentityEnvelope:
    request_id: str
    user_id: Optional[str]
    user_email: Optional[str]
    user_name: Optional[str]
    user_role: Optional[str]
    workspace_id: Optional[str]
    session_id: Optional[str]
    session_id_source: str
    client_id: str
    raw: dict

def build_identity(request: Request, *, require_session: bool = False) -> IdentityEnvelope:
    h = request.headers
    request_id = h.get("x-request-id") or str(uuid4())

    owui_user_id = h.get("x-openwebui-user-id")
    owui_chat_id = h.get("x-openwebui-chat-id")

    user_id = owui_user_id or h.get("x-user-id")

    # Session: only generate if required
    session_id = owui_chat_id or h.get("x-session-id")
    if session_id:
        source = "owui_chat_id" if owui_chat_id else "x_session_id"
    else:
        if require_session:
            session_id = str(uuid4())
            source = "generated"
        else:
            source = "missing"

    return IdentityEnvelope(
        request_id=request_id,
        user_id=user_id,
        user_email=h.get("x-openwebui-user-email"),
        user_name=h.get("x-openwebui-user-name"),
        user_role=h.get("x-openwebui-user-role"),
        workspace_id=h.get("x-workspace-id"),
        session_id=session_id,
        session_id_source=source,
        client_id=h.get("x-client-id") or "owui",
        raw={
            "x-openwebui-user-id": owui_user_id,
            "x-openwebui-chat-id": owui_chat_id,
        },
    )


    return env
