'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 全流程工作流路由模块 - 账号创建+数据爬取+处理+写入
'''
import os
import sys
import json
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import requests

# 添加当前模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 导入其他路由的功能
from routers.account import account_router, AccountCreateRequest, _save_accounts, _load_accounts, AccountInfo
from routers.weibo import WeiboSpiderMain, WeiboDataProcessor
from routers.bilibili import BilibiliSpider, BilibiliDataProcessor, extract_bv_number
from routers.jike import JikeSpider, JikeDataProcessor

# 创建工作流路由器
workflow_router = APIRouter(
    prefix="/workflow",
    tags=["workflow"],
    responses={404: {"description": "Not found"}}
)

# 数据模型定义
class WorkflowRequest(BaseModel):
    """全流程工作流请求模型"""
    # 账号信息
    username: str
    account: str
    password: str
    mind_id: str
    token: str
    description: Optional[str] = ""
    
    # 平台配置
    platforms: List[str]  # 要爬取的平台列表：["weibo", "bilibili", "jike"]
    
    # 微博配置
    weibo_config: Optional[Dict[str, Any]] = None
    
    # Bilibili配置
    bilibili_config: Optional[Dict[str, Any]] = None
    
    # 即刻配置
    jike_config: Optional[Dict[str, Any]] = None
    
    # 写入配置
    batch_size: Optional[int] = 10
    api_url: Optional[str] = "https://mindos-prek8s.mindverse.ai/gate/in/rest/os/qp/content/add"

    class Config:
        json_schema_extra = {
            "example": {
                "username": "张雪峰老师",
                "account": "zhangxuefeng@example.com",
                "password": "password123",
                "mind_id": "mind_123456",
                "token": "token_abc123",
                "description": "教育博主",
                "platforms": ["weibo", "bilibili", "jike"],
                "weibo_config": {
                    "user_id": "1234567890",
                    "since_date": "2024-01-01",
                    "cookie": "your_weibo_cookie_here"
                },
                "bilibili_config": {
                    "uid": "123456789",
                    "video_links": "https://www.bilibili.com/video/BV1xx411c7mD",
                    "whisper_model": "small",
                    "prompt": "以下是普通话的句子。"
                },
                "jike_config": {
                    "username": "zhangxuefeng",
                    "limit": 20,
                    "max_pages": 10,
                    "access_token": "your_access_token",
                    "refresh_token": "your_refresh_token"
                },
                "batch_size": 10
            }
        }

class WorkflowResponse(BaseModel):
    """全流程工作流响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class PlatformResult(BaseModel):
    """单个平台处理结果"""
    platform: str
    crawl_success: bool
    process_success: bool
    crawl_message: str
    process_message: str
    data_count: int
    error: Optional[str] = None

@workflow_router.post("/execute", response_model=WorkflowResponse)
async def execute_full_workflow(request: WorkflowRequest):
    """
    执行完整的工作流程：账号创建 -> 数据爬取 -> 数据处理 -> 写入Mind
    
    Args:
        request: 工作流请求参数
    
    Returns:
        WorkflowResponse: 工作流执行结果
    """
    try:
        workflow_start_time = datetime.now()
        results = {
            "account_created": False,
            "platforms_processed": [],
            "write_result": None,
            "total_items": 0,
            "processing_time": 0
        }
        
        # 第一步：创建账号
        print(f"开始为用户 {request.username} 创建账号...")
        account_result = await _create_account(request)
        results["account_created"] = account_result["success"]
        
        if not account_result["success"]:
            return WorkflowResponse(
                success=False,
                message=f"账号创建失败: {account_result['message']}",
                data=results
            )
        
        # 第二步：并行处理各个平台的数据爬取和处理
        platform_results = []
        for platform in request.platforms:
            print(f"开始处理平台: {platform}")
            platform_result = await _process_platform(platform, request)
            platform_results.append(platform_result)
            results["platforms_processed"].append({
                "platform": platform,
                "success": platform_result.crawl_success and platform_result.process_success,
                "data_count": platform_result.data_count,
                "error": platform_result.error
            })
            
            if platform_result.crawl_success and platform_result.process_success:
                results["total_items"] += platform_result.data_count
        
        # 第三步：将所有处理后的数据写入Mind系统
        if results["total_items"] > 0:
            print(f"开始写入 {results['total_items']} 条数据到Mind系统...")
            write_result = await _write_to_mind(request)
            results["write_result"] = write_result
        else:
            results["write_result"] = {
                "success": False,
                "message": "没有数据可写入",
                "total_items": 0
            }
        
        # 计算总处理时间
        workflow_end_time = datetime.now()
        results["processing_time"] = (workflow_end_time - workflow_start_time).total_seconds()
        
        # 生成最终结果
        success_platforms = [r for r in results["platforms_processed"] if r["success"]]
        total_success = len(success_platforms) > 0 and (results["write_result"]["success"] if results["write_result"] else False)
        
        message = f"工作流执行完成。账号创建: {'成功' if results['account_created'] else '失败'}, " \
                 f"成功处理平台: {len(success_platforms)}/{len(request.platforms)}, " \
                 f"数据写入: {'成功' if results['write_result'] and results['write_result']['success'] else '失败'}, " \
                 f"总处理时间: {results['processing_time']:.2f}秒"
        
        return WorkflowResponse(
            success=total_success,
            message=message,
            data=results
        )
        
    except Exception as e:
        return WorkflowResponse(
            success=False,
            message=f"工作流执行失败: {str(e)}",
            data=results if 'results' in locals() else None
        )


async def _create_account(request: WorkflowRequest) -> Dict[str, Any]:
    """创建账号"""
    try:
        # 构建平台信息
        platform_info = {}
        
        for platform in request.platforms:
            if platform == "weibo" and request.weibo_config:
                platform_info["weibo"] = {
                    "user_id": request.weibo_config.get("user_id")
                }
            elif platform == "bilibili" and request.bilibili_config:
                platform_info["bilibili"] = {
                    "uid": request.bilibili_config.get("uid")
                }
            elif platform == "jike" and request.jike_config:
                platform_info["jike"] = {
                    "username": request.jike_config.get("username")
                }
        
        # 创建账号信息
        account_info = AccountInfo(
            username=request.username,
            account=request.account,
            password=request.password,
            mind_id=request.mind_id,
            token=request.token,
            platform="multi",  # 多平台
            description=request.description,
            platform_info=platform_info,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # 保存账号
        accounts = _load_accounts()
        accounts[request.username] = account_info
        _save_accounts(accounts)
        
        return {
            "success": True,
            "message": f"账号 {request.username} 创建成功",
            "data": account_info.model_dump()
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"账号创建失败: {str(e)}",
            "data": None
        }


async def _process_platform(platform: str, request: WorkflowRequest) -> PlatformResult:
    """处理单个平台的数据爬取和处理"""
    try:
        crawl_success = False
        process_success = False
        crawl_message = ""
        process_message = ""
        data_count = 0
        error = None
        
        if platform == "weibo" and request.weibo_config:
            # 微博爬取和处理
            crawl_result, process_result = await _process_weibo(request)
            crawl_success = crawl_result["success"]
            process_success = process_result["success"]
            crawl_message = crawl_result["message"]
            process_message = process_result["message"]
            data_count = process_result.get("data_count", 0)
            
        elif platform == "bilibili" and request.bilibili_config:
            # Bilibili爬取和处理
            crawl_result, process_result = await _process_bilibili(request)
            crawl_success = crawl_result["success"]
            process_success = process_result["success"]
            crawl_message = crawl_result["message"]
            process_message = process_result["message"]
            data_count = process_result.get("data_count", 0)
            
        elif platform == "jike" and request.jike_config:
            # 即刻爬取和处理
            crawl_result, process_result = await _process_jike(request)
            crawl_success = crawl_result["success"]
            process_success = process_result["success"]
            crawl_message = crawl_result["message"]
            process_message = process_result["message"]
            data_count = process_result.get("data_count", 0)
            
        else:
            error = f"平台 {platform} 配置缺失或不支持"
        
        return PlatformResult(
            platform=platform,
            crawl_success=crawl_success,
            process_success=process_success,
            crawl_message=crawl_message,
            process_message=process_message,
            data_count=data_count,
            error=error
        )
        
    except Exception as e:
        return PlatformResult(
            platform=platform,
            crawl_success=False,
            process_success=False,
            crawl_message="",
            process_message="",
            data_count=0,
            error=str(e)
        )


async def _process_weibo(request: WorkflowRequest) -> tuple:
    """处理微博数据爬取和处理"""
    config = request.weibo_config
    
    # 爬取数据
    try:
        spider = WeiboSpiderMain()
        spider.start(
            user_id=config["user_id"], # type: ignore
            since_date=config.get("since_date", "2024-01-01"),
            cookie=config.get("cookie", "")
        )
        
        # 保存原始数据
        storage_dir = f"/Users/wyx/code/Mindverse/spider/storage/{request.username}"
        os.makedirs(storage_dir, exist_ok=True)
        
        crawl_result = {
            "success": True,
            "message": "微博数据爬取成功"
        }
    except Exception as e:
        crawl_result = {
            "success": False,
            "message": f"微博数据爬取失败: {str(e)}"
        }
        return crawl_result, {"success": False, "message": "爬取失败，跳过处理", "data_count": 0}
    
    # 处理数据
    try:
        processor = WeiboDataProcessor()
        result = processor.process_user_data(request.username)
        
        process_result = {
            "success": True,
            "message": "微博数据处理成功",
            "data_count": len(result) if isinstance(result, list) else 1
        }
    except Exception as e:
        process_result = {
            "success": False,
            "message": f"微博数据处理失败: {str(e)}",
            "data_count": 0
        }
    
    return crawl_result, process_result


async def _process_bilibili(request: WorkflowRequest) -> tuple:
    """处理Bilibili数据爬取和处理"""
    config = request.bilibili_config
    
    # 爬取数据
    try:
        spider = BilibiliSpider()
        video_links = config["video_links"].split(",") # type: ignore
        
        for video_link in video_links:
            video_link = video_link.strip()
            bv_number = extract_bv_number(video_link)
            
            spider.download_video_and_extract_text(
                video_link=video_link,
                username=request.username,
                whisper_model=config.get("whisper_model", "small"),
                prompt=config.get("prompt", "以下是普通话的句子。")
            )
        
        crawl_result = {
            "success": True,
            "message": f"Bilibili数据爬取成功，处理了 {len(video_links)} 个视频"
        }
    except Exception as e:
        crawl_result = {
            "success": False,
            "message": f"Bilibili数据爬取失败: {str(e)}"
        }
        return crawl_result, {"success": False, "message": "爬取失败，跳过处理", "data_count": 0}
    
    # 处理数据
    try:
        processor = BilibiliDataProcessor()
        result = processor.process_user_data(request.username)
        
        process_result = {
            "success": True,
            "message": "Bilibili数据处理成功",
            "data_count": len(result) if isinstance(result, list) else 1
        }
    except Exception as e:
        process_result = {
            "success": False,
            "message": f"Bilibili数据处理失败: {str(e)}",
            "data_count": 0
        }
    
    return crawl_result, process_result


async def _process_jike(request: WorkflowRequest) -> tuple:
    """处理即刻数据爬取和处理"""
    config = request.jike_config
    
    # 爬取数据
    try:
        spider = JikeSpider(
            access_token=config.get("access_token"),
            refresh_token=config.get("refresh_token")
        )
        
        spider.crawl_user_messages(
            username=config["username"], # type: ignore
            storage_username=request.username,
            limit=config.get("limit", 20),
            max_pages=config.get("max_pages", 10)
        )
        
        crawl_result = {
            "success": True,
            "message": "即刻数据爬取成功"
        }
    except Exception as e:
        crawl_result = {
            "success": False,
            "message": f"即刻数据爬取失败: {str(e)}"
        }
        return crawl_result, {"success": False, "message": "爬取失败，跳过处理", "data_count": 0}
    
    # 处理数据
    try:
        processor = JikeDataProcessor()
        result = processor.process_user_data(request.username)
        
        process_result = {
            "success": True,
            "message": "即刻数据处理成功",
            "data_count": len(result) if isinstance(result, list) else 1
        }
    except Exception as e:
        process_result = {
            "success": False,
            "message": f"即刻数据处理失败: {str(e)}",
            "data_count": 0
        }
    
    return crawl_result, process_result


async def _write_to_mind(request: WorkflowRequest) -> Dict[str, Any]:
    """将处理后的数据写入Mind系统"""
    try:
        # 构建写入请求
        from routers.content import ContentWriteRequest, _batch_write_content
        
        write_request = ContentWriteRequest(
            username=request.username,
            mind_id=request.mind_id,
            token=request.token,
            batch_size=request.batch_size,
            api_url=request.api_url
        )
        
        # 读取所有处理后的数据
        storage_dir = f"/Users/wyx/code/Mindverse/spider/storage/{request.username}/output"
        
        if not os.path.exists(storage_dir):
            return {
                "success": False,
                "message": "未找到处理后的数据文件",
                "total_items": 0
            }
        
        all_data = []
        processed_files = []
        
        for file in os.listdir(storage_dir):
            if file.endswith('_processed.json'):
                file_path = os.path.join(storage_dir, file)
                processed_files.append(file_path)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    if isinstance(file_data, list):
                        all_data.extend(file_data)
                    else:
                        all_data.append(file_data)
        
        if not all_data:
            return {
                "success": False,
                "message": "没有找到可写入的数据",
                "total_items": 0
            }
        
        # 执行批量写入
        batch_result = await _batch_write_content(
            all_data,
            request.mind_id,
            request.token,
            request.api_url,
            request.batch_size
        )
        
        return {
            "success": batch_result.success_count > 0,
            "message": f"数据写入完成，成功: {batch_result.success_count}, 失败: {batch_result.failed_count}",
            "total_items": batch_result.total_items,
            "success_count": batch_result.success_count,
            "failed_count": batch_result.failed_count,
            "processing_time": batch_result.processing_time,
            "processed_files": processed_files
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"数据写入失败: {str(e)}",
            "total_items": 0
        }


@workflow_router.get("/status/{username}")
async def get_workflow_status(username: str):
    """
    获取用户的工作流状态
    
    Args:
        username: 用户名
    
    Returns:
        用户的账号信息和数据处理状态
    """
    try:
        # 检查账号是否存在
        accounts = _load_accounts()
        if username not in accounts:
            raise HTTPException(status_code=404, detail=f"用户 {username} 不存在")
        
        account_info = accounts[username]
        
        # 检查各平台数据状态
        storage_dir = f"/Users/wyx/code/Mindverse/spider/storage/{username}"
        status = {
            "account_info": account_info.model_dump(),
            "data_status": {
                "raw_data_exists": os.path.exists(storage_dir),
                "processed_data_exists": os.path.exists(f"{storage_dir}/output"),
                "platforms": {}
            }
        }
        
        # 检查各平台的数据文件
        if os.path.exists(storage_dir):
            for platform in ["weibo", "bilibili", "jike"]:
                raw_file = f"{storage_dir}/{platform}.json"
                processed_file = f"{storage_dir}/output/{platform}_processed.json"
                
                status["data_status"]["platforms"][platform] = {
                    "raw_data": os.path.exists(raw_file),
                    "processed_data": os.path.exists(processed_file)
                }
        
        return WorkflowResponse(
            success=True,
            message=f"用户 {username} 状态获取成功",
            data=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")
