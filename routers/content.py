'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 内容写入API路由模块
'''
import os
import json
import requests
import tempfile
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
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

class MergeFilesRequest(BaseModel):
    username: str  # 用户名
    output_filename: str = "merged_output.json"  # 合并后的输出文件名
    
class DirectWriteRequest(BaseModel):
    file_path: str  # 文件路径
    mind_id: str  # Mind ID
    token: str  # 认证token
    batch_size: Optional[int] = 10  # 批处理大小
    api_url: Optional[str] = "https://mindos-prek8s.mindverse.ai/gate/in/rest/os/qp/content/add"  # API地址

class ContentWriteResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class MergeFilesResponse(BaseModel):
    success: bool
    message: str
    merged_file_path: Optional[str] = None
    total_items: Optional[int] = None
    source_files: Optional[List[str]] = None

class BatchWriteResult(BaseModel):
    total_items: int
    success_count: int
    failed_count: int
    failed_items: List[Dict[str, Any]]
    processing_time: float


@content_router.post("/merge", response_model=MergeFilesResponse)
async def merge_processed_files(request: MergeFilesRequest):
    """
    将用户storage目录下的所有处理后文件合并成一个文件
    
    Args:
        request: 合并请求参数，包含username和output_filename
    
    Returns:
        MergeFilesResponse: 合并结果
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
            raise HTTPException(status_code=400, detail="没有找到可合并的数据")
        
        # 构建输出文件路径
        merged_file_path = os.path.join(storage_dir, request.output_filename)
        if not merged_file_path.endswith('.json'):
            merged_file_path += '.json'
        
        # 写入合并后的文件
        with open(merged_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        return MergeFilesResponse(
            success=True,
            message=f"成功合并 {len(processed_files)} 个文件到 {os.path.basename(merged_file_path)}",
            merged_file_path=merged_file_path,
            total_items=len(all_data),
            source_files=[os.path.basename(f) for f in processed_files]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合并文件失败: {str(e)}")


@content_router.post("/write-direct", response_model=ContentWriteResponse)
async def write_content_direct(request: DirectWriteRequest):
    """
    直接从指定文件写入内容到Mind系统
    
    Args:
        request: 直接写入请求参数，包含file_path、mind_id和token
    
    Returns:
        ContentWriteResponse: 写入结果
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {request.file_path}")
        
        # 读取数据文件
        with open(request.file_path, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
        
        # 确保数据是列表格式
        if isinstance(file_data, list):
            all_data = file_data
        else:
            all_data = [file_data]
        
        if not all_data:
            raise HTTPException(status_code=400, detail="文件中没有可写入的数据")
        
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
                "source_file": request.file_path
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"直接写入内容失败: {str(e)}")


@content_router.post("/write-upload", response_model=ContentWriteResponse)
async def write_content_upload(
    file: UploadFile = File(..., description="要上传的JSON文件"),
    mind_id: str = Form(..., description="Mind ID"),
    token: str = Form(..., description="认证token"),
    batch_size: Optional[int] = Form(10, description="批处理大小"),
    api_url: Optional[str] = Form("https://mindos-prek8s.mindverse.ai/gate/in/rest/os/qp/content/add", description="API地址")
):
    """
    通过文件上传的方式将内容写入到Mind系统
    
    Args:
        file: 上传的JSON文件
        mind_id: Mind ID
        token: 认证token
        batch_size: 批处理大小
        api_url: API地址
    
    Returns:
        ContentWriteResponse: 写入结果
    """
    try:
        # 检查文件类型
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="只支持JSON文件上传")
        
        # 读取上传的文件内容
        file_content = await file.read()
        
        try:
            # 解析JSON数据
            file_data = json.loads(file_content.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON文件格式错误: {str(e)}")
        except UnicodeDecodeError as e:
            raise HTTPException(status_code=400, detail=f"文件编码错误，请确保文件是UTF-8编码: {str(e)}")
        
        # 确保数据是列表格式
        if isinstance(file_data, list):
            all_data = file_data
        else:
            all_data = [file_data]
        
        if not all_data:
            raise HTTPException(status_code=400, detail="文件中没有可写入的数据")
        
        # 执行批量写入
        result = await _batch_write_content(
            all_data,
            mind_id,
            token,
            api_url,
            batch_size
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
                "source_file": file.filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传写入失败: {str(e)}")


@content_router.post("/write", response_model=ContentWriteResponse)
async def write_content_to_mind(request: ContentWriteRequest):
    """
    将用户数据写入到Mind系统（优化版本）
    
    Args:
        request: 写入请求参数，包含username、mind_id和token
    
    Returns:
        ContentWriteResponse: 写入结果
    """
    try:
        # 先尝试查找是否有合并文件
        storage_dir = f"/Users/wyx/code/Mindverse/spider/storage/{request.username}/output"
        merged_files = []
        
        if os.path.exists(storage_dir):
            for file in os.listdir(storage_dir):
                if file.endswith('.json') and not file.endswith('_processed.json'):
                    merged_files.append(os.path.join(storage_dir, file))
        
        # 如果有合并文件，优先使用最新的合并文件
        if merged_files:
            # 按修改时间排序，使用最新的文件
            latest_file = max(merged_files, key=os.path.getmtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                
            all_data = file_data if isinstance(file_data, list) else [file_data]
            source_info = f"merged file: {os.path.basename(latest_file)}"
            
        else:
            # 回退到原来的逻辑：读取所有处理后的文件
            processed_files = []
            if os.path.exists(storage_dir):
                for file in os.listdir(storage_dir):
                    if file.endswith('_processed.json'):
                        processed_files.append(os.path.join(storage_dir, file))
            
            if not processed_files:
                raise HTTPException(status_code=404, detail=f"未找到用户 {request.username} 的处理后文件或合并文件")
            
            all_data = []
            
            # 读取所有处理后的数据文件
            for file_path in processed_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    if isinstance(file_data, list):
                        all_data.extend(file_data)
                    else:
                        all_data.append(file_data)
            
            source_info = f"processed files: {[os.path.basename(f) for f in processed_files]}"
        
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
                "source_info": source_info
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
