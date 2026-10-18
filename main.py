
import time
import json
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
started = time.monotonic()
logs = deque(maxlen=1000)

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests"
)

API_KEY = "ak_qckgst9a4pvvefy7c0gbumki"
EMAIL = "24f2005969@ds.study.iitm.ac.in"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Event(BaseModel):
    user: str
    amount: float
    ts: int


class AnalyticsRequest(BaseModel):
    events: list[Event]


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    REQUESTS.inc()
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    logs.append({
        "level": "info",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "request_id": request_id
    })
    response.headers["X-Request-ID"] = request_id
    return response


@app.post("/analytics")
def analytics(
    body: AnalyticsRequest,
    x_api_key: str | None = Header(default=None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    users = set()
    totals = defaultdict(float)
    revenue = 0.0

    for event in body.events:
        users.add(event.user)
        if event.amount > 0:
            revenue += event.amount
            totals[event.user] += event.amount

    top_user = max(totals, key=totals.get) if totals else None

    return {
        "email": EMAIL,
        "total_events": len(body.events),
        "unique_users": len(users),
        "revenue": revenue,
        "top_user": top_user
    }


@app.get("/work")
def work(n: int = 1):
    n = max(0, min(n, 1000000))
    total = sum(range(n))
    return {"email": EMAIL, "done": n}


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_s": max(0.0, time.monotonic() - started)
    }


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    limit = max(0, min(limit, 1000))
    return list(logs)[-limit:] if limit else []
