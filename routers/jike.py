'''
Author       : wyx-hhhh
Date         : 2025-06-09
LastEditTime : 2025-06-09
Description  : 即刻爬虫路由模块
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
from file_handler.jike import JikeFileHandler

# 创建即刻路由器
jike_router = APIRouter(
    prefix="/spider",
    tags=["jike"],
    responses={404: {"description": "Not found"}}
)

# 数据模型定义
class JikeSpiderRequest(BaseModel):
    username: str = "a2d6acc1-626f-4d15-a22a-849e88a4c9f0"  # 即刻用户名，默认值
    limit: Optional[int] = 20  # 每页数据量
    max_pages: Optional[int] = 10  # 最大页数限制
    access_token: Optional[str] = None  # 可选的访问令牌
    refresh_token: Optional[str] = None  # 可选的刷新令牌

class JikeSpiderResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class JikeFilesResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]


@jike_router.post("/jike", response_model=JikeSpiderResponse)
async def crawl_jike(request: JikeSpiderRequest):
    """
    爬取即刻数据接口
    
    Args:
        request: 爬虫请求参数
        
    Returns:
        JikeSpiderResponse: 爬取结果
    """
    try:
        # 验证必要参数
        if not request.username:
            raise HTTPException(status_code=400, detail="username不能为空")
        
        print(f"开始爬取即刻用户: {request.username}, 页数限制: {request.max_pages}")
        
        # 创建爬虫实例（会自动加载本地配置的token）
        spider = JikeSpider()
        print(f"本地配置token状态 - access_token前10位: {spider.access_token[:10]}...")
        
        # 首先尝试使用本地配置的token进行爬取
        try:
            print("第一次尝试：使用本地配置文件中的token")
            all_data = spider.get_all_jike_data(
                username=request.username,
                limit=request.limit,
                max_pages=request.max_pages
            )
            
            if all_data:
                print("使用本地token爬取成功")
            else:
                raise Exception("未获取到数据")
                
        except Exception as e:
            print(f"使用本地token爬取失败: {str(e)}")
            
            # 检查用户是否提供了有效的token
            if (request.access_token and request.access_token.strip() and 
                request.refresh_token and request.refresh_token.strip()):
                
                print("第二次尝试：使用用户提供的token")
                spider.access_token = request.access_token.strip()
                spider.refresh_token = request.refresh_token.strip()
                spider.save_config()
                
                try:
                    all_data = spider.get_all_jike_data(
                        username=request.username,
                        limit=request.limit,
                        max_pages=request.max_pages
                    )
                    
                    if all_data:
                        print("使用用户提供的token爬取成功")
                    else:
                        raise Exception("未获取到数据")
                        
                except Exception as retry_error:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"使用用户提供的token也无法爬取数据: {str(retry_error)}"
                    )
            else:
                # 用户没有提供有效token，提示需要提供
                raise HTTPException(
                    status_code=401, 
                    detail=f"本地token无效({str(e)})，请在请求中提供有效的access_token和refresh_token参数"
                )
        
        if not all_data:
            raise HTTPException(
                status_code=500, 
                detail="爬取失败，未获取到任何数据。可能是token已过期，请提供有效的access_token和refresh_token参数重新尝试"
            )
        
        # 保存数据到文件
        file_handler = JikeFileHandler()
        file_path = file_handler.save_jike_data(all_data, request.username)
        
        return JikeSpiderResponse(
            success=True,
            message=f"成功爬取用户 {request.username} 的即刻数据，共 {len(all_data)} 条",
            data={
                "username": request.username,
                "data_count": len(all_data),
                "saved_file": file_path,
                "data": all_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")


@jike_router.get("/jike/files/{username}", response_model=JikeFilesResponse)
def get_jike_user_files(username: str):
    """
    获取指定用户的即刻数据文件
    
    Args:
        username: 用户名
        
    Returns:
        JikeFilesResponse: 文件列表和内容
    """
    try:
        file_handler = JikeFileHandler()
        user_files = file_handler.get_user_files(username)
        
        if not user_files:
            return JikeFilesResponse(
                success=False,
                message=f"未找到用户 {username} 的数据文件",
                data={
                    "username": username,
                    "storage_dir": file_handler.storage_dir,
                    "files": [],
                    "file_count": 0
                }
            )
        
        return JikeFilesResponse(
            success=True,
            message=f"成功获取用户 {username} 的数据文件",
            data={
                "username": username,
                "storage_dir": file_handler.storage_dir,
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
        raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")


def get_jike_spider_status_summary():
    """获取即刻爬虫状态摘要信息，用于主路由"""
    try:
        from spiders.jike.main import JikeSpider
        
        return {
            "available": True,
            "endpoints": [
                "/spider/jike",
                "/spider/jike/files/{username}"
            ],
            "features": [
                "即刻动态数据爬取",
                "自动token刷新",
                "分页数据获取",
                "数据文件查询"
            ]
        }
    except ImportError:
        return {
            "available": False,
            "error": "JikeSpider模块导入失败"
        }
    except Exception as e:
        return {
            "available": False,
            "error": f"获取状态失败: {str(e)}"
        }