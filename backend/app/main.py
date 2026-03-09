from fastapi import FastAPI

app = FastAPI(
    title="智能出版学习系统",
    description="智能体既是出版社（编写教材）又是作者（答疑互动）",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {
        "message": "智能出版学习系统 API",
        "status": "running",
        "version": "0.1.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/v1/status")
async def status():
    return {
        "api": "ok",
        "database": "ok",
        "vector_store": "ok"
    }
