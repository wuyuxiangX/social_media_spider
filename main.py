'''
Author       : wyx-hhhh
Date         : 2025-06-06
LastEditTime : 2025-06-09
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

# 应用启动时的初始化
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    # 确保storage目录结构存在
    storage_dirs = [
        "storage/bilibili/bilibili_video",
        "storage/bilibili/audio/conv",
        "storage/bilibili/audio/slice", 
        "storage/bilibili/outputs",
        "storage/weibo",
        "storage/jike"
    ]
    
    for directory in storage_dirs:
        os.makedirs(directory, exist_ok=True)

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
from routers.bilibili import bilibili_router, get_bilibili_spider_status
from routers.jike import jike_router, get_jike_spider_status_summary

# 包含路由
app.include_router(weibo_router)
app.include_router(bilibili_router)
app.include_router(jike_router)

# 定义根路径的GET请求处理器
@app.get("/")
def read_root():
    return {
        "message": "综合爬虫API服务", 
        "version": "2.0.0", 
        "services": {
            "bilibili": get_bilibili_spider_status(),
            "jike": get_jike_spider_status_summary()
        },
        "general_endpoints": [
            "/health"
        ]
    }

# 健康检查接口
@app.get("/health")
def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "spider-api"}

# 如果直接运行此文件，启动服务器
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)