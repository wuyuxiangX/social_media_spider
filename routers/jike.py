'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 即刻爬虫路由模块（重新设计）
'''
import os
import sys
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 添加当前模块路径，以便导入其他模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 添加spiders/jike路径到sys.path
jike_spider_path = os.path.join(parent_dir, 'spiders', 'jike')
sys.path.append(jike_spider_path)

# 导入JikeSpider类
from spiders.jike.main import JikeSpider
from data_processor.jike import JikeDataProcessor

# 创建即刻路由器
jike_router = APIRouter(
    prefix="/jike",
    tags=["jike"],
    responses={404: {"description": "Not found"}}
)

# 数据模型定义
class JikeResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@jike_router.get("/crawl")
async def crawl_jike(
    username: str,
    jike_username: str = "a2d6acc1-626f-4d15-a22a-849e88a4c9f0",
    limit: int = 20,
    max_pages: int = 10,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None
):
    """
    爬取即刻数据
    
    Args:
        username: 存储用户名
        jike_username: 即刻用户名
        limit: 每页数据量
        max_pages: 最大页数限制
        access_token: 可选的访问令牌
        refresh_token: 可选的刷新令牌
    """
    try:
        processor = JikeDataProcessor(username=username)
        spider = JikeSpider()  # 即刻爬虫不需要username参数
        
        # 执行爬取
        try:
            data = spider.get_all_jike_data(
                username=jike_username,
                limit=limit,
                max_pages=max_pages
            )
        except Exception as e:
            if "token" in str(e).lower():
                raise HTTPException(
                    status_code=401,
                    detail=f"本地token无效({str(e)})，请在请求中提供有效的access_token和refresh_token参数"
                )
            else:
                raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")
        
        if not data:
            raise HTTPException(
                status_code=500, 
                detail="爬取失败，未获取到任何数据。可能是token已过期，请提供有效的access_token和refresh_token参数重新尝试"
            )
        
        # 保存数据到文件
        file_path = processor.save_jike_data(data)
        
        return JikeResponse(
            success=True,
            message=f"成功爬取即刻数据，共 {len(data)} 条",
            data={
                "username": username,
                "jike_username": jike_username,
                "data_count": len(data),
                "saved_file": file_path,
                "storage_dir": processor.storage_dir
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")


@jike_router.get("/view")
async def view_jike_files(username: str):
    """
    查看即刻数据文件
    
    Args:
        username: 用户名
    """
    try:
        processor = JikeDataProcessor(username=username)
        user_files = processor.get_user_files()
        
        if not user_files:
            return JikeResponse(
                success=False,
                message=f"未找到用户 {username} 的即刻数据文件",
                data={
                    "username": username,
                    "storage_dir": processor.storage_dir,
                    "files": [],
                    "file_count": 0
                }
            )
        
        return JikeResponse(
            success=True,
            message=f"成功获取用户 {username} 的即刻数据文件",
            data={
                "username": username,
                "storage_dir": processor.storage_dir,
                "files": user_files,
                "file_count": len(user_files),
                "summary": {
                    "total_files": len(user_files),
                    "total_size": sum(file_info.get("file_size", 0) for file_info in user_files),
                    "total_data_count": sum(file_info.get("data_count", 0) for file_info in user_files),
                    "files_with_content": len([f for f in user_files if f.get("content") is not None]),
                    "files_with_errors": len([f for f in user_files if f.get("error") is not None])
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@jike_router.get("/process")
async def process_jike_file(username: str):
    """
    处理即刻数据文件
    
    Args:
        username: 用户名
    """
    try:
        processor = JikeDataProcessor(username=username)
        file_path = os.path.join(processor.storage_dir, "jike.json")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"用户 {username} 的即刻数据文件不存在，请先爬取数据")
        
        # 处理文件
        result = processor.process_file(file_path)
        
        return JikeResponse(
            success=True,
            message="文件处理成功",
            data={
                "username": username,
                "original_file": "jike.json",
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


@jike_router.get("/run")
async def run_jike_full_process(
    username: str,
    jike_username: str = "a2d6acc1-626f-4d15-a22a-849e88a4c9f0",
    limit: int = 20,
    max_pages: int = 5,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None
):
    """
    即刻完整流程：爬取 -> 保存 -> 处理
    
    Args:
        username: 存储用户名
        jike_username: 即刻用户名
        limit: 每页数据量
        max_pages: 最大页数限制
        access_token: 可选的访问令牌
        refresh_token: 可选的刷新令牌
    """
    try:
        # 步骤1：爬取数据
        crawl_result = await crawl_jike(
            username=username,
            jike_username=jike_username,
            limit=limit,
            max_pages=max_pages,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        if not crawl_result.success:
            return JikeResponse(
                success=False,
                message=f"爬取失败: {crawl_result.message}",
                data={}
            )
        
        # 步骤2：处理数据
        try:
            process_result = await process_jike_file(username=username)
            
            if not process_result.success:
                return JikeResponse(
                    success=False,
                    message=f"处理失败: {process_result.message}",
                    data={
                        "crawl_result": crawl_result.data,
                        "process_error": process_result.message
                    }
                )
            
            # 步骤3：返回完整结果
            return JikeResponse(
                success=True,
                message="即刻数据爬取和处理完成",
                data={
                    "username": username,
                    "jike_username": jike_username,
                    "crawl_summary": {
                        "data_count": crawl_result.data.get("data_count", 0),
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
            return JikeResponse(
                success=False,
                message=f"处理步骤失败: {str(e)}",
                data={
                    "crawl_result": crawl_result.data,
                    "process_error": str(e)
                }
            )
            
    except Exception as e:
        return JikeResponse(
            success=False,
            message=f"完整流程失败: {str(e)}",
            data={}
        )
