from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.complaints import router as complaints_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AIVOA Customer Complaint Management System",
    description="AI-assisted pharmaceutical customer complaint intake and triage (demonstration prototype).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Last-resort safety net so a bug never returns a raw stack trace or
    # crashes the frontend's request — it always gets a clean JSON error.
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unexpected server error: {exc}"},
    )


app.include_router(complaints_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.app_env}
