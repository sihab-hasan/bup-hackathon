from fastapi import FastAPI
from app.api.router import router as api_router

app = FastAPI(title="Energy Optimizer API")

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Energy Optimizer API"}
