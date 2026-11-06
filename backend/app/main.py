from fastapi import FastAPI

from app.routes.analysis import router as analysis_router
from app.routes.benchmark import router as benchmark_router
from app.routes.system import router as system_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SQL Eco-Optimizer",
    description="SQL query performance and carbon footprint analyzer",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    analysis_router,
    prefix="/api"
)

app.include_router(
    benchmark_router,
    prefix="/api"
)

app.include_router(
    system_router,
    prefix="/api"
)


@app.get("/")
def root():
    return {
        "message": "SQL Eco-Optimizer API is running"
    }

