'''
Author       : wyx-hhhh
Date         : 2025-06-06
LastEditTime : 2025-06-10
Description  : 
'''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用实例
app = FastAPI(title="综合爬虫API", description="微博爬虫和Bilibili视频转文本API接口")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入路由模块
from routers.weibo import weibo_router
from routers.bilibili import bilibili_router
from routers.jike import jike_router
from routers.content import content_router
from routers.account import account_router
from routers.workflow import workflow_router

# 包含路由
app.include_router(weibo_router)
app.include_router(bilibili_router)
app.include_router(jike_router)
app.include_router(content_router)
app.include_router(account_router)
app.include_router(workflow_router)

@app.get("/")
async def root():
    """根路径欢迎页面"""
    return {
        "message": "综合爬虫API服务",
        "version": "1.0.0",
        "available_endpoints": {
            "账号管理": "/account",
            "微博爬虫": "/weibo", 
            "Bilibili爬虫": "/bilibili",
            "即刻爬虫": "/jike",
            "内容写入": "/content",
            "全流程工作流": "/workflow",
            "API文档": "/docs",
            "OpenAPI规范": "/openapi.json"
        },
        "status": "running"
    }

# 如果直接运行此文件，启动服务器
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3002)