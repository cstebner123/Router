from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
from sqlalchemy import text
from router.db import engine
from fastapi import APIRouter, Request
from router.identity import build_identity
import logging

LMSTUDIO_BASE = "http://127.0.0.1:1234"  # hardcoded for now

app = FastAPI(title="Router", version="0.1.0")


log = logging.getLogger("router.headers")

@app.middleware("http")
async def log_incoming_headers(request: Request, call_next):
    # TEMPORARY DEBUG — REMOVE AFTER VERIFYING
    log.warning(
        "INCOMING HEADERS: %s",
        {
            k: v
            for k, v in request.headers.items()
            if k.lower().startswith("x-") or k.lower().startswith("authorization")
        }
    )
    response = await call_next(request)
    return response

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/v1/db/health")
async def db_health():
    async with engine.connect() as conn:
        val = await conn.scalar(text("SELECT 1"))
    return {"ok": True, "db": "up", "select_1": int(val)}

r = APIRouter()
@r.get("/v1/whoami")
def whoami(request: Request):
    ident = build_identity(request, require_session=False)
    return {
        "request_id": ident.request_id,
        "identity": {
            "user_id": ident.user_id,
            "user_email": ident.user_email,
            "user_name": ident.user_name,
            "user_role": ident.user_role,
            "workspace_id": ident.workspace_id,
            "session_id": ident.session_id,
            "session_id_source": ident.session_id_source,
            "client_id": ident.client_id,
        },
        "raw_hint": ident.raw,
    }
app.include_router(r)



async def _proxy(request: Request, path: str) -> Response:
    """
    Generic JSON proxy for OpenAI-compatible endpoints.
    """
    url = f"{LMSTUDIO_BASE}{path}"

    # Preserve query params
    params = dict(request.query_params)

    # Copy headers, but drop hop-by-hop headers
    headers = dict(request.headers)
    headers.pop("host", None)
    # Ensure upstream treats it like JSON
    headers.setdefault("content-type", "application/json")

    body = await request.body()

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        upstream = await client.request(
            method=request.method,
            url=url,
            params=params,
            content=body,
            headers=headers,
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


async def _proxy_stream(request: Request, path: str) -> StreamingResponse:
    url = f"{LMSTUDIO_BASE}{path}"
    params = dict(request.query_params)

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.setdefault("content-type", "application/json")

    body = await request.body()

    async def gen():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                method=request.method,
                url=url,
                params=params,
                content=body,
                headers=headers,
            ) as upstream:
                async for chunk in upstream.aiter_bytes():
                    if chunk:
                        yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
    )



@app.get("/v1/models")
async def v1_models(request: Request):
    return await _proxy(request, "/v1/models")


@app.post("/v1/embeddings")
async def v1_embeddings(request: Request):
    return await _proxy(request, "/v1/embeddings")


@app.post("/v1/chat/completions")
async def v1_chat_completions(request: Request):
    # If the client asked for streaming, proxy as stream
    payload = await request.json()
    if payload.get("stream") is True:
        return await _proxy_stream(request, "/v1/chat/completions")
    return await _proxy(request, "/v1/chat/completions")


# Nice error surface if LM Studio is down
@app.exception_handler(httpx.ConnectError)
async def connect_error_handler(_request: Request, exc: httpx.ConnectError):
    return JSONResponse(
        status_code=502,
        content={"error": {"message": f"Upstream LM Studio unreachable at {LMSTUDIO_BASE}: {exc}"}},
    )
