from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="多智能体协作的学习系统后端服务",
    version=settings.APP_VERSION,
    docs_url="/docs",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "学习智能体系统 API", "version": settings.APP_VERSION, "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 导入路由
from app.api.v1 import auth, users, courses, agents

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["课程"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["智能体"])
