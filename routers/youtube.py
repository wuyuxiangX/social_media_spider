'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : YouTube路由模块
'''
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import os
import json
import time
from pydantic import BaseModel
from data_processor.youtube import YouTubeDataProcessor
from spiders.youtube.main import main

# 创建路由
youtube_router = APIRouter(
    prefix="/youtube",
    tags=["youtube"],
    responses={404: {"description": "Not found"}},
)

# 获取当前文件所在目录的父目录
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)


class YouTubeResponse(BaseModel):
    """YouTube响应模型"""
    success: bool
    message: str
    data: Dict[str, Any]


@youtube_router.get("/crawl")
async def crawl_youtube_video(query: str, max_results: int = 5):
    """
    爬取YouTube视频
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数
    """
    try:
        result = main(query, max_results)
        return YouTubeResponse(
            success=True,
            message="成功爬取YouTube视频",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理视频失败: {str(e)}")

@youtube_router.get("/view")
async def view_youtube_files():
    """
    查看YouTube字幕文件
    """
    try:
        # 获取YouTube字幕目录
        storage_dir = os.path.join(parent_dir, "storage", "youtube", "outputs")
        if not os.path.exists(storage_dir):
            return YouTubeResponse(
                success=True,
                message="YouTube字幕目录不存在",
                data={
                    "storage_dir": storage_dir,
                    "files": [],
                    "file_count": 0
                }
            )
        
        # 获取所有txt文件
        youtube_files = []
        for file in os.listdir(storage_dir):
            if file.endswith(".txt"):
                file_path = os.path.join(storage_dir, file)
                
                try:
                    # 读取文件内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    youtube_files.append({
                        "file_name": file,
                        "file_path": file_path,
                        "file_size": os.path.getsize(file_path),
                        "modified_time": os.path.getmtime(file_path),
                        "text_length": len(content),
                        "content_preview": content[:100] + "..." if len(content) > 100 else content
                    })
                except Exception as e:
                    youtube_files.append({
                        "file_name": file,
                        "file_path": file_path,
                        "file_size": os.path.getsize(file_path),
                        "modified_time": os.path.getmtime(file_path),
                        "error": str(e)
                    })
        
        # 按修改时间排序，最新的在前面
        youtube_files.sort(key=lambda x: x.get("modified_time", 0), reverse=True)
        
        return YouTubeResponse(
            success=True,
            message=f"找到 {len(youtube_files)} 个YouTube字幕文件",
            data={
                "storage_dir": storage_dir,
                "files": youtube_files,
                "file_count": len(youtube_files),
                "summary": {
                    "total_files": len(youtube_files),
                    "total_size": sum(file_info.get("file_size", 0) for file_info in youtube_files),
                    "total_text_length": sum(file_info.get("text_length", 0) for file_info in youtube_files),
                    "files_with_content": len([f for f in youtube_files if "content_preview" in f]),
                    "files_with_errors": len([f for f in youtube_files if "error" in f])
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取YouTube文件列表失败: {str(e)}")

@youtube_router.get("/process")
async def process_youtube_file(mind_id: str, username: str):
    """
    处理YouTube数据文件
    
    Args:
        username: 用户名

    """
    try:
        processor = YouTubeDataProcessor()

        storage_dir = os.path.join(parent_dir, "storage", "youtube", "outputs")
        if not os.path.exists(storage_dir):
            raise ValueError(f"YouTube字幕目录不存在: {storage_dir}")
        
        # 获取所有txt文件路径
        subtitle_files = [os.path.join(storage_dir, f) for f in os.listdir(storage_dir) if f.endswith(".txt")]
        if not subtitle_files:
            raise ValueError("未找到YouTube字幕文件")
        
        # 处理所有字幕文件
        result = processor.process_data(subtitle_files)
        
        return YouTubeResponse(
            success=True,
            message=f"成功处理 {len(subtitle_files)} 个YouTube字幕文件",
            data={
                "username": username,
                "file_count": len(subtitle_files),
                "processed_file": result.get("processed_file", ""),
                "item_count": result.get("item_count", 0),
                "processing_time": result.get("processing_time", 0),
                "files_processed": [os.path.basename(file_info.get("file_path", "")) 
                                   for file_info in result.get("original_files", [])]
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理YouTube数据失败: {str(e)}")

@youtube_router.get("/run")
async def run_youtube_full_process(
        query: str,
        max_results: int = 5,
        mind_id: str = "169949830539034624",
        username: str = "default"
):
    """
    YouTube完整流程：爬取 -> 保存 -> 处理
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数
        mind_id: 目标mind_id
        username: 用户名
    """
    try:
        # 爬取视频
        result = main(query, max_results)
        
        if not result or "subtitle_file" not in result:
            raise HTTPException(
                status_code=500,
                detail="视频处理失败或未生成字幕文件"
            )
        
        # 获取所有字幕文件
        storage_dir = os.path.join(parent_dir, "storage", "youtube", "outputs")
        if not os.path.exists(storage_dir):
            raise ValueError(f"YouTube字幕目录不存在: {storage_dir}")
        
        subtitle_files = [os.path.join(storage_dir, f) for f in os.listdir(storage_dir) if f.endswith(".txt")]
        if not subtitle_files:
            raise ValueError("未找到YouTube字幕文件")
        
        # 处理所有字幕文件
        processor = YouTubeDataProcessor()
        process_result = processor.process_data(subtitle_files)
        
        return YouTubeResponse(
            success=True,
            message=f"成功完成YouTube视频的完整处理流程，处理了 {len(subtitle_files)} 个字幕文件",
            data={
                "username": username,
                "query": query,
                "audio_file": result.get("audio_file", ""),
                "subtitle_file": result.get("subtitle_file", ""),
                "processed_file": process_result["processed_file"],
                "file_count": len(subtitle_files),
                "item_count": process_result.get("item_count", 0),
                "processing_time": process_result.get("processing_time", 0),
                "files_processed": [os.path.basename(file_info.get("file_path", "")) 
                                   for file_info in process_result.get("original_files", [])]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube完整处理流程失败: {str(e)}")
