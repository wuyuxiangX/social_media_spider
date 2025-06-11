'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 微博爬虫路由模块（重新设计）
'''
import os
import sys
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 添加当前模块路径，以便导入其他模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 添加spiders/weibo路径到sys.path
weibo_spider_path = os.path.join(parent_dir, 'spiders', 'weibo')
sys.path.append(weibo_spider_path)

# 导入WeiboSpiderMain类
from spiders.weibo.main import WeiboSpiderMain
from data_processor.weibo import WeiboDataProcessor

# 创建微博路由器
weibo_router = APIRouter(
    prefix="/weibo",
    tags=["weibo"],
    responses={404: {"description": "Not found"}}
)

# 数据模型定义
class WeiboResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@weibo_router.get("/crawl")
async def crawl_weibo(
    username: str,
    user_id: str,
    since_date: str = "2024-01-01",
    cookie: Optional[str] = "SCF=AspoasABOe45QQA3C80FaQ1mAMADJijY0IYgO4vdS-IIteqqcnhSxf89-jHJSzNuzokM5fsmrWQyTCH6qNHdOGk.; SUB=_2A25FO7QjDeRhGeNH7FoZ9i7LzTWIHXVmOUnrrDV6PUJbktANLXnRkW1NSms3A3j8vHOb3qBiZk1XIib6I3A8_jW1; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFfmmwdXkzj_BsQNUT36l2A5NHD95Qf1KMR1hq7S0q4Ws4DqcjMi--NiK.Xi-2Ri--ciKnRi-zNSK.N1hncehMc1Btt; SSOLoginState=1749009523; ALF=1751601523; _T_WM=65bd31df0c9d1e6033e20c541b5f524a"
):
    """
    爬取微博数据
    
    Args:
        username: 存储用户名
        user_id: 微博用户ID
        since_date: 开始日期，格式：YYYY-MM-DD
        cookie: 微博cookie
    """
    try:
        processor = WeiboDataProcessor(username=username)
        
        # 创建微博爬虫配置
        config = {
            "user_id_list": [user_id],
            "cookie": cookie,
            "since_date": since_date,
            "end_date": "now",
            "filter": 1,  # 只爬取原创微博
            "random_wait_pages": [1, 3],
            "random_wait_seconds": [3, 6],
            "global_wait": [[100, 300]],
            "write_mode": ["json"],
            "pic_download": 0,
            "video_download": 0,
            "file_download_timeout": [5, 5, 10],
            "result_dir_name": 0
        }
        
        # 创建微博爬虫实例
        spider = WeiboSpiderMain(config_dict=config)
        
        # 执行爬取
        success = spider.start_crawling()
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="爬取失败，请检查user_id和cookie是否有效"
            )
        
        # 微博爬虫会将数据保存到storage/weibo目录下的用户文件夹中
        # 文件路径格式: storage/weibo/{用户昵称或ID}/{user_id}.json
        weibo_storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "weibo")
        
        # 查找用户相关的JSON文件
        data_file_path = None
        if os.path.exists(weibo_storage_dir):
            # 遍历weibo目录下的所有子文件夹
            for subdir in os.listdir(weibo_storage_dir):
                subdir_path = os.path.join(weibo_storage_dir, subdir)
                if os.path.isdir(subdir_path):
                    # 在每个子文件夹中查找user_id.json文件
                    potential_file = os.path.join(subdir_path, f"{user_id}.json")
                    if os.path.exists(potential_file):
                        data_file_path = potential_file
                        break
                    
                    # 也查找最新的json文件作为备选
                    json_files = []
                    for file in os.listdir(subdir_path):
                        if file.endswith('.json'):
                            file_path = os.path.join(subdir_path, file)
                            json_files.append((file_path, os.path.getmtime(file_path)))
                    
                    if json_files and not data_file_path:
                        # 选择最新的文件
                        data_file_path = max(json_files, key=lambda x: x[1])[0]
                        break
        
        if not data_file_path:
            raise HTTPException(
                status_code=500, 
                detail="爬取完成但未找到生成的数据文件。请检查用户ID是否正确，或查看storage/weibo目录"
            )
        
        # 读取数据
        with open(data_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 保存到用户目录 storage/{username}/weibo/
        file_path = processor.save_weibo_data(data)
        
        # 计算微博数量
        weibo_count = 0
        if isinstance(data, dict) and "weibo" in data:
            weibo_count = len(data["weibo"])
        elif isinstance(data, list):
            weibo_count = len(data)
        
        return WeiboResponse(
            success=True,
            message=f"成功爬取微博数据，共 {weibo_count} 条",
            data={
                "username": username,
                "user_id": user_id,
                "weibo_count": weibo_count,
                "saved_file": file_path,
                "storage_dir": processor.storage_dir
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"爬取失败: {str(e)}")


@weibo_router.get("/view")
async def view_weibo_files(username: str):
    """
    查看微博数据文件
    
    Args:
        username: 用户名
    """
    try:
        processor = WeiboDataProcessor(username=username)
        user_files = processor.get_user_files()
        
        if not user_files:
            return WeiboResponse(
                success=False,
                message=f"未找到用户 {username} 的微博数据文件",
                data={
                    "username": username,
                    "storage_dir": processor.storage_dir,
                    "files": [],
                    "file_count": 0
                }
            )
        
        return WeiboResponse(
            success=True,
            message=f"成功获取用户 {username} 的微博数据文件",
            data={
                "username": username,
                "storage_dir": processor.storage_dir,
                "files": user_files,
                "file_count": len(user_files),
                "summary": {
                    "total_files": len(user_files),
                    "total_size": sum(file_info.get("file_size", 0) for file_info in user_files),
                    "total_weibo_count": sum(file_info.get("weibo_count", 0) for file_info in user_files),
                    "files_with_content": len([f for f in user_files if f.get("content") is not None]),
                    "files_with_errors": len([f for f in user_files if f.get("error") is not None])
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@weibo_router.get("/process")
async def process_weibo_file(username: str):
    """
    处理微博数据文件
    
    Args:
        username: 用户名
    """
    try:
        processor = WeiboDataProcessor(username=username)
        file_path = os.path.join(processor.storage_dir, "weibo.json")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"用户 {username} 的微博数据文件不存在，请先爬取数据")
        
        # 处理文件
        result = processor.process_file(file_path)
        
        return WeiboResponse(
            success=True,
            message="文件处理成功",
            data={
                "username": username,
                "original_file": "weibo.json",
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


@weibo_router.get("/run")
async def run_weibo_full_process(
    username: str,
    user_id: str,
    since_date: str = "2001-01-01",
    cookie: Optional[str] = "SCF=AspoasABOe45QQA3C80FaQ1mAMADJijY0IYgO4vdS-IIteqqcnhSxf89-jHJSzNuzokM5fsmrWQyTCH6qNHdOGk.; SUB=_2A25FO7QjDeRhGeNH7FoZ9i7LzTWIHXVmOUnrrDV6PUJbktANLXnRkW1NSms3A3j8vHOb3qBiZk1XIib6I3A8_jW1; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFfmmwdXkzj_BsQNUT36l2A5NHD95Qf1KMR1hq7S0q4Ws4DqcjMi--NiK.Xi-2Ri--ciKnRi-zNSK.N1hncehMc1Btt; SSOLoginState=1749009523; ALF=1751601523; _T_WM=65bd31df0c9d1e6033e20c541b5f524a"
):
    """
    微博完整流程：爬取 -> 保存 -> 处理
    
    Args:
        username: 存储用户名
        user_id: 微博用户ID
        since_date: 起始日期 (格式: 2023-01-01)
        cookie: 微博cookie (必需，防止token过期)
    """
    try:
        # 步骤1：爬取数据
        crawl_result = await crawl_weibo(
            username=username,
            user_id=user_id,
            since_date=since_date,
            cookie=cookie
        )
        
        if not crawl_result.success:
            return WeiboResponse(
                success=False,
                message=f"爬取失败: {crawl_result.message}",
                data={}
            )
        
        # 步骤2：处理数据
        try:
            process_result = await process_weibo_file(username=username)
            
            if not process_result.success:
                return WeiboResponse(
                    success=False,
                    message=f"处理失败: {process_result.message}",
                    data={
                        "crawl_result": crawl_result.data,
                        "process_error": process_result.message
                    }
                )
            
            # 步骤3：返回完整结果
            return WeiboResponse(
                success=True,
                message="微博数据爬取和处理完成",
                data={
                    "username": username,
                    "user_id": user_id,
                    "crawl_summary": {
                        "weibo_count": crawl_result.data.get("weibo_count", 0),
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
            return WeiboResponse(
                success=False,
                message=f"处理步骤失败: {str(e)}",
                data={
                    "crawl_result": crawl_result.data,
                    "process_error": str(e)
                }
            )
            
    except Exception as e:
        return WeiboResponse(
            success=False,
            message=f"完整流程失败: {str(e)}",
            data={}
        )
