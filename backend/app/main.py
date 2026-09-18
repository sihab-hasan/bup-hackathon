from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import router as api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.schemas import ErrorDetail, ErrorResponse

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message))
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Energy Optimizer API"}
