import os
import sys
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 添加当前模块路径，以便导入其他模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 添加spiders/weibo路径到sys.path
weibo_spider_path = os.path.join(parent_dir, 'spiders', 'weibo')
sys.path.append(weibo_spider_path)

# 导入WeiboSpiderMain类 - 从spiders.weibo.main导入
from spiders.weibo.main import WeiboSpiderMain

# 创建微博路由器
weibo_router = APIRouter(
    prefix="/spider",
    tags=["weibo"],
    responses={404: {"description": "Not found"}}
)

# 数据模型定义
class WeiboSpiderRequest(BaseModel):
    user_id: str  # 用户ID，必填
    since_date: Optional[str] = "2024-01-01"  # 开始日期，格式：YYYY-MM-DD
    cookie: Optional[str] = "SCF=AspoasABOe45QQA3C80FaQ1mAMADJijY0IYgO4vdS-IIteqqcnhSxf89-jHJSzNuzokM5fsmrWQyTCH6qNHdOGk.; SUB=_2A25FO7QjDeRhGeNH7FoZ9i7LzTWIHXVmOUnrrDV6PUJbktANLXnRkW1NSms3A3j8vHOb3qBiZk1XIib6I3A8_jW1; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFfmmwdXkzj_BsQNUT36l2A5NHD95Qf1KMR1hq7S0q4Ws4DqcjMi--NiK.Xi-2Ri--ciKnRi-zNSK.N1hncehMc1Btt; SSOLoginState=1749009523; ALF=1751601523; _T_WM=65bd31df0c9d1e6033e20c541b5f524a"

class SpiderResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class FilesResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]


@weibo_router.post("/weibo", response_model=SpiderResponse)
async def crawl_weibo(request: WeiboSpiderRequest):
    """
    爬取微博数据接口
    
    Args:
        request: 爬虫请求参数，只需要user_id和cookie
        
    Returns:
        SpiderResponse: 爬取结果
    """
    try:
        # 验证必要参数
        if not request.user_id:
            raise HTTPException(status_code=400, detail="user_id不能为空")
        
        # 创建爬虫实例并开始爬取
        print(f"开始爬取用户: {request.user_id}, 开始日期: {request.since_date}")
        
        # 获取storage/weibo目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        storage_dir = os.path.join(parent_dir, "storage", "weibo")
        os.makedirs(storage_dir, exist_ok=True)
        
        # 创建配置字典，使用固定的默认值
        custom_config = {
            "user_id_list": [request.user_id],
            "filter": 1,  # 只爬原创微博
            "since_date": request.since_date,
            "end_date": "now",  # 固定到当前时间
            "random_wait_pages": [1, 3],
            "random_wait_seconds": [3, 6],
            "global_wait": [[100, 300]],
            "write_mode": ["json"],
            "pic_download": 0,  # 不下载图片
            "video_download": 0,  # 不下载视频
            "file_download_timeout": [5, 5, 10],
            "result_dir_name": 0,
            "cookie": request.cookie
        }
        
        crawler = WeiboSpiderMain(config_dict=custom_config)
        
        # 执行爬虫
        success = crawler.start_crawling()
        
        if not success:
            raise HTTPException(status_code=500, detail="爬取失败，请检查cookie和用户ID是否正确")
        
        # 获取输出文件和内容 - 从storage/weibo目录读取
        output_data = []
        if os.path.exists(storage_dir):
            for root, dirs, files in os.walk(storage_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = json.load(f)
                            
                            output_data.append({
                                "file_path": file_path,
                                "file_name": file,
                                "file_size": os.path.getsize(file_path),
                                "content": content
                            })
                        except Exception as e:
                            output_data.append({
                                "file_path": file_path,
                                "file_name": file,
                                "file_size": os.path.getsize(file_path),
                                "error": str(e)
                            })
        
        return SpiderResponse(
            success=True,
            message=f"成功爬取用户 {request.user_id} 的微博数据",
            data={
                "user_id": request.user_id,
                "output_dir": storage_dir,
                "files": output_data,
                "file_count": len(output_data),
                "summary": {
                    "total_files": len(output_data),
                    "total_size": sum(file_info.get("file_size", 0) for file_info in output_data),
                    "files_with_content": len([f for f in output_data if f.get("content") is not None]),
                    "files_with_errors": len([f for f in output_data if f.get("error") is not None])
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")


@weibo_router.get("/files/{user_id}", response_model=FilesResponse)
def get_user_files(user_id: str, output_dir: Optional[str] = None):
    """
    获取指定用户的爬取文件和内容
    
    Args:
        user_id: 用户ID
        output_dir: 输出目录路径，可选
        
    Returns:
        FilesResponse: 文件列表和内容
    """
    try:
        # 设置默认输出目录为storage/weibo
        if not output_dir:
            # 获取项目根目录下的storage/weibo目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            output_dir = os.path.join(parent_dir, "storage", "weibo")
            # 确保目录存在
            os.makedirs(output_dir, exist_ok=True)
        
        # 查找用户文件
        user_files = []
        if os.path.exists(output_dir):
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file.startswith(user_id) and file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = json.load(f)
                            
                            user_files.append({
                                "file_path": file_path,
                                "file_name": file,
                                "file_size": os.path.getsize(file_path),
                                "modified_time": os.path.getmtime(file_path),
                                "content": content
                            })
                        except Exception as e:
                            user_files.append({
                                "file_path": file_path,
                                "file_name": file,
                                "file_size": os.path.getsize(file_path),
                                "modified_time": os.path.getmtime(file_path),
                                "error": str(e)
                            })
        
        if not user_files:
            return FilesResponse(
                success=False,
                message=f"未找到用户 {user_id} 的数据文件",
                data={
                    "user_id": user_id,
                    "output_dir": output_dir,
                    "files": [],
                    "file_count": 0
                }
            )
        
        return FilesResponse(
            success=True,
            message=f"成功获取用户 {user_id} 的数据文件",
            data={
                "user_id": user_id,
                "output_dir": output_dir,
                "files": user_files,
                "file_count": len(user_files),
                "summary": {
                    "total_files": len(user_files),
                    "total_size": sum(file_info.get("file_size", 0) for file_info in user_files),
                    "files_with_content": len([f for f in user_files if f.get("content") is not None]),
                    "files_with_errors": len([f for f in user_files if f.get("error") is not None])
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")


def get_weibo_storage_dir() -> str:
    """
    获取微博数据存储目录
    
    Returns:
        str: 存储目录路径
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    storage_dir = os.path.join(parent_dir, "storage", "weibo")
    
    # 确保目录存在
    os.makedirs(storage_dir, exist_ok=True)
    
    return storage_dir


def get_weibo_output_files(output_dir: str = None):
    """
    获取微博爬虫输出文件列表和内容
    
    Args:
        output_dir: 输出目录路径，如果为None则使用默认storage目录
        
    Returns:
        list: 文件信息列表
    """
    if output_dir is None:
        output_dir = get_weibo_storage_dir()
        
    output_data = []
    if os.path.exists(output_dir):
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        
                        output_data.append({
                            "file_path": file_path,
                            "file_name": file,
                            "file_size": os.path.getsize(file_path),
                            "content": content
                        })
                    except Exception as e:
                        output_data.append({
                            "file_path": file_path,
                            "file_name": file,
                            "file_size": os.path.getsize(file_path),
                            "content": None,
                            "error": str(e)
                        })
    return output_data
