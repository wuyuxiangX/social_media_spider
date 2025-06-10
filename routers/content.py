'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 内容写入API路由模块
'''
import os
import json
import requests
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

# 创建内容写入路由器
content_router = APIRouter(
    prefix="/content",
    tags=["content"],
    responses={404: {"description": "Not found"}}
)

# 数据模型定义
class ContentWriteRequest(BaseModel):
    username: str  # 用户名
    mind_id: str  # Mind ID
    token: str  # 认证token
    batch_size: Optional[int] = 10  # 批处理大小
    api_url: Optional[str] = "https://mindos-prek8s.mindverse.ai/gate/in/rest/os/qp/content/add"  # API地址

class ContentWriteResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class BatchWriteResult(BaseModel):
    total_items: int
    success_count: int
    failed_count: int
    failed_items: List[Dict[str, Any]]
    processing_time: float


@content_router.post("/write", response_model=ContentWriteResponse)
async def write_content_to_mind(request: ContentWriteRequest):
    """
    将用户数据写入到Mind系统
    
    Args:
        request: 写入请求参数，包含username、mind_id和token
    
    Returns:
        ContentWriteResponse: 写入结果
    """
    try:
        # 构建处理后的文件路径
        storage_dir = f"/Users/wyx/code/Mindverse/spider/storage/{request.username}/output"
        
        # 查找所有处理后的文件
        processed_files = []
        if os.path.exists(storage_dir):
            for file in os.listdir(storage_dir):
                if file.endswith('_processed.json'):
                    processed_files.append(os.path.join(storage_dir, file))
        
        if not processed_files:
            raise HTTPException(status_code=404, detail=f"未找到用户 {request.username} 的处理后文件")
        
        all_data = []
        
        # 读取所有处理后的数据文件
        for file_path in processed_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                if isinstance(file_data, list):
                    all_data.extend(file_data)
                else:
                    all_data.append(file_data)
        
        if not all_data:
            raise HTTPException(status_code=400, detail="没有找到可写入的数据")
        
        # 执行批量写入
        result = await _batch_write_content(
            all_data,
            request.mind_id,
            request.token,
            request.api_url,
            request.batch_size
        )
        
        return ContentWriteResponse(
            success=result.success_count > 0,
            message=f"批量写入完成，成功: {result.success_count}, 失败: {result.failed_count}",
            data={
                "total_items": result.total_items,
                "success_count": result.success_count,
                "failed_count": result.failed_count,
                "failed_items": result.failed_items,
                "processing_time": result.processing_time,
                "success_rate": (result.success_count / result.total_items * 100) if result.total_items > 0 else 0,
                "processed_files": processed_files
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入内容失败: {str(e)}")


async def _batch_write_content(
    data_list: List[Dict[str, Any]],
    mind_id: str,
    token: str,
    api_url: str,
    batch_size: int = 10
) -> BatchWriteResult:
    """
    批量写入内容到Mind系统
    
    Args:
        data_list: 要写入的数据列表
        mind_id: Mind ID
        token: 认证token
        api_url: API地址
        batch_size: 批处理大小
    
    Returns:
        BatchWriteResult: 批量写入结果
    """
    start_time = datetime.now()
    total_items = len(data_list)
    success_count = 0
    failed_count = 0
    failed_items = []
    
    # 设置请求头（基于提供的curl示例）
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'appid': 'os-internal',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'lang': 'undefined',
        'origin': 'https://mindos-prek8s.mindverse.ai',
        'platform': 'web',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://mindos-prek8s.mindverse.ai/home-mobile',
        'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'timestamp': str(int(datetime.now().timestamp() * 1000)),
        'timezone': 'Asia/Shanghai',
        'token': token,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
    }
    
    # 分批处理
    for i in range(0, total_items, batch_size):
        batch = data_list[i:i + batch_size]
        
        for item in batch:
            try:
                # 构建请求数据
                request_data = {
                    "mindId": mind_id,
                    "content": item.get("content", ""),
                    "type": item.get("type", "text"),
                    "userTitle": item.get("userTitle", ""),
                    "target": "addNote"
                }
                
                # 发送请求
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=request_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    success_count += 1
                else:
                    failed_count += 1
                    failed_items.append({
                        "item": item,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "request_data": request_data
                    })
                    
            except Exception as e:
                failed_count += 1
                failed_items.append({
                    "item": item,
                    "error": str(e),
                    "request_data": request_data if 'request_data' in locals() else None
                })
    
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    return BatchWriteResult(
        total_items=total_items,
        success_count=success_count,
        failed_count=failed_count,
        failed_items=failed_items,
        processing_time=processing_time
    )
