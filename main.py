
import os
from collections import defaultdict

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "ak_qckgst9a4pvvefy7c0gbumki"
EMAIL = "24f2005969@ds.study.iitm.ac.in"

redis_url = os.getenv("REDIS_URL")

if redis_url:
    r = Redis.from_url(redis_url, decode_responses=True)
else:
    r = Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=6379,
        decode_responses=True
    )


class Event(BaseModel):
    user: str
    amount: float
    ts: int


class AnalyticsRequest(BaseModel):
    events: list[Event]


@app.get("/healthz")
def health():
    try:
        r.ping()
        return {"status": "ok", "redis": "up"}
    except Exception:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.post("/hit/{key}")
def hit(key: str):
    return {"key": key, "count": r.incr(key)}


@app.get("/count/{key}")
def count(key: str):
    value = r.get(key)
    return {"key": key, "count": int(value) if value else 0}


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
