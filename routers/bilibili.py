import os
import sys
import re
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 添加当前模块路径，以便导入其他模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 添加spiders/bilibili路径到sys.path
bilibili_spider_path = os.path.join(parent_dir, 'spiders', 'bilibili')
sys.path.append(bilibili_spider_path)

# 导入BilibiliSpider类
from spiders.bilibili.main import BilibiliSpider

# 创建bilibili路由器
bilibili_router = APIRouter(
    prefix="/spider",
    tags=["bilibili"],
    responses={404: {"description": "Not found"}}
)

# 数据模型定义
class BilibiliSpiderRequest(BaseModel):
    video_link: str  # 单个视频链接
    whisper_model: Optional[str] = "small"  # Whisper模型
    prompt: Optional[str] = "以下是普通话的句子。"  # 转换提示词

class MultipleBilibiliSpiderRequest(BaseModel):
    video_links: List[str]  # 多个视频链接
    whisper_model: Optional[str] = "small"  # Whisper模型
    prompt: Optional[str] = "以下是普通话的句子。"  # 转换提示词

class BilibiliSpiderResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

def extract_bv_number(video_link: str) -> str:
    """从视频链接中提取BV号"""
    pattern = r'BV[A-Za-z0-9]+'
    matches = re.findall(pattern, video_link)
    if not matches:
        raise ValueError(f"无效的视频链接: {video_link}，未找到BV号")
    return matches[0]

@bilibili_router.post("/bilibili", response_model=BilibiliSpiderResponse)
async def crawl_single_bilibili_video(request: BilibiliSpiderRequest):
    """
    爬取单个Bilibili视频并转换为文本
    
    Args:
        request: 包含视频链接和处理参数的请求
        
    Returns:
        BilibiliSpiderResponse: 处理结果
    """
    try:
        # 提取BV号
        bv_number = extract_bv_number(request.video_link)
        
        # 创建爬虫实例
        spider = BilibiliSpider(whisper_model=request.whisper_model)
        
        # 处理视频
        result = spider.process_single_video(bv_number, request.prompt)
        
        return BilibiliSpiderResponse(
            success=True,
            message=f"视频 {bv_number} 处理成功",
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@bilibili_router.post("/bilibili/multiple", response_model=BilibiliSpiderResponse)
async def crawl_multiple_bilibili_videos(request: MultipleBilibiliSpiderRequest):
    """
    批量爬取Bilibili视频并转换为文本
    
    Args:
        request: 包含多个视频链接和处理参数的请求
        
    Returns:
        BilibiliSpiderResponse: 批量处理结果
    """
    try:
        # 提取所有BV号
        bv_numbers = []
        for link in request.video_links:
            bv_number = extract_bv_number(link)
            bv_numbers.append(bv_number)
        
        # 创建爬虫实例
        spider = BilibiliSpider(whisper_model=request.whisper_model)
        
        # 批量处理视频
        result = spider.process_multiple_videos(bv_numbers, request.prompt)
        
        return BilibiliSpiderResponse(
            success=True,
            message=f"批量处理完成，共处理 {len(bv_numbers)} 个视频",
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@bilibili_router.get("/bilibili/models")
async def list_available_whisper_models():
    """
    获取可用的Whisper模型列表
    
    Returns:
        List[str]: 可用模型列表
    """
    return {
        "success": True,
        "message": "获取模型列表成功",
        "data": {
            "models": ["tiny", "base", "small", "medium", "large"]
        }
    }

@bilibili_router.get("/bilibili/files")
async def list_bilibili_files():
    """
    获取Bilibili爬虫生成的文件列表
    
    Returns:
        文件列表信息
    """
    try:
        files_info = {
            "videos": [],
            "outputs": []
        }
        
        # 获取正确的storage路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        storage_base = os.path.join(project_root, "storage", "bilibili")
        
        # 获取视频文件信息
        video_dir = os.path.join(storage_base, "bilibili_video")
        if os.path.exists(video_dir):
            for item in os.listdir(video_dir):
                item_path = os.path.join(video_dir, item)
                if os.path.isdir(item_path):
                    files_info["videos"].append({
                        "bv_number": item,
                        "path": item_path
                    })
        
        # 获取输出文件信息
        output_dir = os.path.join(storage_base, "outputs")
        if os.path.exists(output_dir):
            for file in os.listdir(output_dir):
                if file.endswith(('.json', '.txt')):
                    file_path = os.path.join(output_dir, file)
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    files_info["outputs"].append({
                        "filename": file,
                        "path": file_path,
                        "size": file_size
                    })
        
        return BilibiliSpiderResponse(
            success=True,
            message="获取文件列表成功",
            data=files_info
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

def get_bilibili_spider_status():
    """获取Bilibili爬虫状态信息"""
    try:
        # 检查依赖模块
        from spiders.bilibili.main import BilibiliSpider
        status = {
            "available": True,
            "endpoints": [
                "/spider/bilibili",
                "/spider/bilibili/multiple", 
                "/spider/bilibili/models",
                "/spider/bilibili/files"
            ],
            "features": [
                "单个视频转文本",
                "批量视频转文本",
                "支持多种Whisper模型",
                "自动音频处理"
            ]
        }
    except ImportError:
        status = {
            "available": False,
            "error": "BilibiliSpider模块导入失败"
        }
    
    return status