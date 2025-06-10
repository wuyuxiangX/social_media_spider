import os
import sys
import re
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 获取项目根目录并添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from data_processor.bilibili import BilibiliDataProcessor
from spiders.bilibili.main import BilibiliSpider

bilibili_router = APIRouter(
    prefix="/bilibili",
    tags=["bilibili"],
    responses={404: {"description": "Not found"}}
)

class BilibiliResponse(BaseModel):
    success: bool
    message: str
    data: dict

def extract_bv_number(video_link: str) -> str:
    """从视频链接中提取BV号"""
    pattern = r'BV[a-zA-Z0-9]+'
    match = re.search(pattern, video_link)
    if match:
        return match.group()
    else:
        raise ValueError(f"无法从链接中提取BV号: {video_link}")

@bilibili_router.get("/crawl")
async def crawl_bilibili(
    username: str,
    video_links: str,  # 支持多个链接，用逗号分隔
    whisper_model: str = "small",
    prompt: str = "以下是普通话的句子。"
):
    """
    爬取Bilibili视频数据
    
    Args:
        username: 存储用户名
        video_links: 视频链接（多个链接用逗号分隔）
        whisper_model: Whisper模型
        prompt: 转换提示词
    """
    try:
        processor = BilibiliDataProcessor(username=username)
        
        # 解析多个视频链接
        links = [link.strip() for link in video_links.split(',') if link.strip()]
        if not links:
            raise HTTPException(status_code=400, detail="请提供至少一个视频链接")
        
        all_video_data = []
        
        for video_link in links:
            try:
                # 提取BV号
                bv_number = extract_bv_number(video_link)
                
                # 创建Bilibili爬虫实例
                spider = BilibiliSpider()
                
                # 执行爬取和处理
                result = spider.process_single_video(
                    bv_number=bv_number,
                    prompt=prompt
                )
                
                if not result:
                    print(f"视频 {video_link} 处理失败")
                    continue
                
                # B站爬虫直接返回数据，构建标准格式
                video_data = {
                    "bv_number": result.get("bv_number", bv_number),
                    "video_link": video_link,
                    "title": result.get("title", ""),
                    "text": result.get("text", ""),
                    "whisper_model": result.get("whisper_model", whisper_model),
                    "prompt": prompt,
                    "timestamp": result.get("timestamp", ""),
                    "folder_name": result.get("folder_name", "")
                }
                
                all_video_data.append(video_data)
                    
            except Exception as e:
                print(f"处理视频 {video_link} 失败: {str(e)}")
                continue
        
        if not all_video_data:
            raise HTTPException(
                status_code=500, 
                detail="所有视频处理都失败了"
            )
        
        # 保存所有视频数据到一个文件
        file_path = processor.save_bilibili_data(all_video_data)
        
        return BilibiliResponse(
            success=True,
            message=f"成功处理 {len(all_video_data)} 个B站视频",
            data={
                "username": username,
                "video_count": len(all_video_data),
                "videos": [{"bv_number": v.get("bv_number"), "title": v.get("title")} for v in all_video_data],
                "total_text_length": sum(len(v.get("text", "")) for v in all_video_data),
                "saved_file": file_path,
                "storage_dir": processor.storage_dir
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理视频失败: {str(e)}")

@bilibili_router.get("/view")
async def view_bilibili_files(username: str):
    """
    查看用户的Bilibili数据文件
    
    Args:
        username: 用户名
    """
    try:
        processor = BilibiliDataProcessor(username=username)
        user_files = processor.get_user_files()
        
        return BilibiliResponse(
            success=True,
            message=f"成功获取用户 {username} 的Bilibili数据文件",
            data={
                "username": username,
                "storage_dir": processor.storage_dir,
                "files": user_files,
                "file_count": len(user_files),
                "summary": {
                    "total_files": len(user_files),
                    "total_size": sum(file_info.get("file_size", 0) for file_info in user_files),
                    "total_text_length": sum(file_info.get("text_length", 0) for file_info in user_files),
                    "files_with_content": len([f for f in user_files if f.get("content") is not None]),
                    "files_with_errors": len([f for f in user_files if f.get("error") is not None])
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@bilibili_router.get("/process")
async def process_bilibili_file(username: str):
    """
    处理Bilibili数据文件
    
    Args:
        username: 用户名
    """
    try:
        processor = BilibiliDataProcessor(username=username)
        file_path = os.path.join(processor.storage_dir, "bilibili.json")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"用户 {username} 的Bilibili数据文件不存在，请先爬取数据")
        
        # 处理文件
        result = processor.process_file(file_path)
        
        return BilibiliResponse(
            success=True,
            message="文件处理成功",
            data={
                "username": username,
                "original_file": "bilibili.json",
                "processed_file": os.path.basename(result["processed_file_path"]),
                "processed_file_path": result["processed_file_path"],
                "original_count": result["original_count"],
                "processed_count": result["processed_count"],
                "processing_time": result["processing_time"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")

@bilibili_router.get("/run")
async def run_bilibili_full_process(
    username: str,
    video_links: str,  # 支持多个链接，用逗号分隔
    whisper_model: str = "small",
    prompt: str = "以下是普通话的句子。"
):
    """
    B站完整流程：爬取 -> 保存 -> 处理
    
    Args:
        username: 存储用户名
        video_links: 视频链接（多个链接用逗号分隔）
        whisper_model: Whisper模型
        prompt: 转换提示词
    """
    try:
        # 步骤1：爬取数据
        crawl_result = await crawl_bilibili(
            username=username,
            video_links=video_links,
            whisper_model=whisper_model,
            prompt=prompt
        )
        
        if not crawl_result.success:
            return BilibiliResponse(
                success=False,
                message=f"爬取失败: {crawl_result.message}",
                data={}
            )
        
        # 步骤2：处理数据
        try:
            process_result = await process_bilibili_file(username=username)
            
            if not process_result.success:
                return BilibiliResponse(
                    success=False,
                    message=f"处理失败: {process_result.message}",
                    data={
                        "crawl_result": crawl_result.data,
                        "process_error": process_result.message
                    }
                )
            
            # 步骤3：返回完整结果
            return BilibiliResponse(
                success=True,
                message="B站数据爬取和处理完成",
                data={
                    "username": username,
                    "video_links": video_links,
                    "crawl_summary": {
                        "video_count": crawl_result.data.get("video_count", 0),
                        "total_text_length": crawl_result.data.get("total_text_length", 0),
                        "saved_file": crawl_result.data.get("saved_file", ""),
                        "storage_dir": crawl_result.data.get("storage_dir", "")
                    },
                    "process_summary": {
                        "original_count": process_result.data.get("original_count", 0),
                        "processed_count": process_result.data.get("processed_count", 0),
                        "processed_file": process_result.data.get("processed_file", ""),
                        "processing_time": process_result.data.get("processing_time", "")
                    }
                }
            )
            
        except Exception as e:
            return BilibiliResponse(
                success=False,
                message=f"处理步骤失败: {str(e)}",
                data={
                    "crawl_result": crawl_result.data,
                    "process_error": str(e)
                }
            )
            
    except Exception as e:
        return BilibiliResponse(
            success=False,
            message=f"完整流程失败: {str(e)}",
            data={}
        )
