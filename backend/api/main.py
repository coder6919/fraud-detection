import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import account, graph, rings

app = FastAPI(title="Fraud Ring Detection API")

# ALLOWED_ORIGINS is a comma-separated list, e.g. "https://your-app.vercel.app".
# Set it in Render's dashboard once the frontend has a deployed URL.
extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", *extra_origins],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(graph.router)
app.include_router(rings.router)
app.include_router(account.router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
