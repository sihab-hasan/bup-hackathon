from fastapi import FastAPI

app = FastAPI(title="Energy Optimizer API")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the Energy Optimizer API"}
