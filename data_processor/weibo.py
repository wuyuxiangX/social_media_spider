'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 微博数据处理器
'''
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import os
import json
from .base import BaseDataProcessor


class WeiboDataProcessor(BaseDataProcessor):
    """微博数据处理器"""
    
    def __init__(self, mind_id: str = "169949830539034624", username: str = "default"):
        super().__init__(mind_id, username)
    
    def _get_platform_name(self) -> str:
        """获取平台名称"""
        return "weibo"
    
    def process_data(self, raw_data: List[Dict[Any, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        处理微博原始数据
        
        Args:
            raw_data: 微博原始数据列表（可能包含用户信息和微博列表）
            **kwargs: 其他参数
                - include_user_info: 是否包含用户信息，默认True
                - max_items: 最大处理条数，默认无限制
                
        Returns:
            List[Dict[str, Any]]: 处理后的数据列表
        """
        include_user_info = kwargs.get("include_user_info", True)
        max_items = kwargs.get("max_items", None)
        
        processed_data = []
        
        # 处理不同的微博数据格式
        weibo_list = []
        user_info = {}
        
        if isinstance(raw_data, dict):
            # 如果是单个用户的数据格式 {"user": {...}, "weibo": [...]}
            user_info = raw_data.get("user", {})
            weibo_list = raw_data.get("weibo", [])
        elif isinstance(raw_data, list):
            # 如果是微博列表格式
            weibo_list = raw_data
        
        for i, weibo in enumerate(weibo_list):
            if max_items and i >= max_items:
                break
                
            try:
                processed_item = self._process_single_weibo_item(weibo, user_info, include_user_info)
                if processed_item and self.validate_data(processed_item):
                    processed_data.append(processed_item)
            except Exception as e:
                print(f"处理微博数据项失败: {str(e)}")
                continue
        
        return processed_data
    
    def _process_single_weibo_item(self, weibo: Dict[Any, Any], user_info: Dict[Any, Any] = None, 
                                  include_user_info: bool = True) -> Optional[Dict[str, Any]]:
        """
        处理单条微博数据
        
        Args:
            weibo: 单条微博数据
            user_info: 用户信息
            include_user_info: 是否包含用户信息
            
        Returns:
            Optional[Dict[str, Any]]: 处理后的数据，如果处理失败返回None
        """
        # 提取内容
        content = weibo.get("content", "")
        if not content:
            return None
        
        # 清洗内容
        clean_content = self.clean_content(content)
        if not clean_content:
            return None
        
        # 简化输出格式，只返回内容
        return {
            "content": clean_content
        }
    
    def _build_enriched_content(self, weibo: Dict[Any, Any], user_info: Dict[Any, Any], 
                               content: str, include_user_info: bool) -> str:
        """
        构建丰富的内容信息
        
        Args:
            weibo: 微博数据
            user_info: 用户信息
            content: 清洗后的基础内容
            include_user_info: 是否包含用户信息
            
        Returns:
            str: 丰富的内容
        """
        enriched_parts = []
        
        # 添加内容
        enriched_parts.append(f"内容: {content}")
        
        # 添加发布时间
        publish_time = weibo.get("publish_time", "")
        if publish_time:
            enriched_parts.append(f"发布时间: {publish_time}")
        
        # 添加微博类型信息
        is_original = weibo.get("original", True)
        weibo_type = "原创微博" if is_original else "转发微博"
        enriched_parts.append(f"类型: {weibo_type}")
        
        # 添加发布工具
        publish_tool = weibo.get("publish_tool", "")
        if publish_tool and publish_tool != "无":
            enriched_parts.append(f"发布工具: {publish_tool}")
        
        # 添加发布地点
        publish_place = weibo.get("publish_place", "")
        if publish_place and publish_place != "无":
            enriched_parts.append(f"发布地点: {publish_place}")
        
        # 添加统计信息
        stats = self._extract_stats(weibo)
        if stats:
            enriched_parts.append(f"互动数据: {stats}")
        
        # 添加媒体信息
        media_info = self._extract_media_info(weibo)
        if media_info:
            enriched_parts.append(f"媒体内容: {media_info}")
        
        # 添加用户信息
        if include_user_info and user_info:
            user_summary = self._extract_user_summary(user_info)
            if user_summary:
                enriched_parts.append(f"用户信息: {user_summary}")
        
        return " | ".join(enriched_parts)
    
    def _extract_stats(self, weibo: Dict[Any, Any]) -> str:
        """提取统计信息"""
        stats_parts = []
        
        # 提取各种计数
        count_fields = {
            "up_num": "点赞",
            "comment_num": "评论",
            "retweet_num": "转发"
        }
        
        for field, name in count_fields.items():
            count = weibo.get(field, 0)
            if count and count > 0:
                stats_parts.append(f"{name}{count}")
        
        return ", ".join(stats_parts) if stats_parts else ""
    
    def _extract_media_info(self, weibo: Dict[Any, Any]) -> str:
        """提取媒体信息"""
        media_parts = []
        
        # 检查图片
        original_pictures = weibo.get("original_pictures", "")
        if original_pictures and original_pictures != "无":
            media_parts.append("包含图片")
        
        retweet_pictures = weibo.get("retweet_pictures")
        if retweet_pictures:
            media_parts.append("包含转发图片")
        
        # 检查视频
        video_url = weibo.get("video_url", "")
        if video_url and video_url != "无":
            media_parts.append("包含视频")
        
        # 检查文章链接
        article_url = weibo.get("article_url", "")
        if article_url:
            media_parts.append("包含文章链接")
        
        return ", ".join(media_parts) if media_parts else ""
    
    def _extract_user_summary(self, user_info: Dict[Any, Any]) -> str:
        """提取用户信息摘要"""
        user_parts = []
        
        nickname = user_info.get("nickname", "")
        if nickname:
            user_parts.append(f"昵称: {nickname}")
        
        description = user_info.get("description", "")
        if description:
            # 限制描述长度
            if len(description) > 50:
                description = description[:50] + "..."
            user_parts.append(f"简介: {description}")
        
        verified_reason = user_info.get("verified_reason", "")
        if verified_reason:
            # 限制认证信息长度
            if len(verified_reason) > 30:
                verified_reason = verified_reason[:30] + "..."
            user_parts.append(f"认证: {verified_reason}")
        
        followers = user_info.get("followers", 0)
        if followers:
            user_parts.append(f"粉丝: {followers}")
        
        return ", ".join(user_parts) if user_parts else ""
    
    def extract_user_title(self, weibo: Dict[Any, Any], user_info: Dict[Any, Any] = None) -> str:
        """
        提取用户标题
        
        Args:
            weibo: 微博数据
            user_info: 用户信息
            
        Returns:
            str: 用户标题
        """
        if user_info:
            return user_info.get("nickname", "")
        return weibo.get("user_name", "")
    
    def clean_content(self, content: str) -> str:
        """
        清洗微博内容
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清洗后的内容
        """
        if not content:
            return ""
        
        # 移除@用户链接
        content = re.sub(r'@[\w\-\.]+', '', content)
        
        # 移除话题标签的#符号，保留话题内容
        content = re.sub(r'#([^#]+)#', r'\1', content)
        
        # 移除URL链接
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        
        # 移除多余的表情符号标记
        content = re.sub(r'\[[\w\u4e00-\u9fa5]+\]', '', content)
        
        # 调用父类的清洗方法
        return super().clean_content(content)
    
    def save_weibo_data(self, data: Dict[Any, Any], filename: Optional[str] = None) -> str:
        """
        保存微博数据到文件
        
        Args:
            data: 微博数据
            filename: 自定义文件名，如果为None则自动生成
            
        Returns:
            str: 保存的文件路径
        """
        return self.save_data(data, filename)
    
    def get_user_files(self, username: str = None) -> List[Dict[str, Any]]:
        """
        获取指定用户的所有文件信息
        
        Args:
            username: 用户名，如果为None则使用实例的username
            
        Returns:
            List[Dict[str, Any]]: 文件信息列表
        """
        if username is None:
            username = self.username
            
        user_files = []
        
        if not os.path.exists(self.storage_dir):
            return user_files
        
        # 查找weibo.json文件
        weibo_file = os.path.join(self.storage_dir, "weibo.json")
        if os.path.exists(weibo_file):
            try:
                with open(weibo_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                user_info = content.get("user", {})
                weibo_list = content.get("weibo", [])
                
                user_files.append({
                    "file_path": weibo_file,
                    "file_name": "weibo.json",
                    "file_size": os.path.getsize(weibo_file),
                    "modified_time": os.path.getmtime(weibo_file),
                    "content": content,
                    "user_id": user_info.get("id", ""),
                    "nickname": user_info.get("nickname", ""),
                    "weibo_count": len(weibo_list) if isinstance(weibo_list, list) else 0
                })
            except Exception as e:
                user_files.append({
                    "file_path": weibo_file,
                    "file_name": "weibo.json",
                    "file_size": os.path.getsize(weibo_file),
                    "modified_time": os.path.getmtime(weibo_file),
                    "error": str(e),
                    "weibo_count": 0
                })
        
        return user_files
    
    def get_all_users(self) -> List[str]:
        """
        获取所有用户名
        
        Returns:
            List[str]: 用户名列表
        """
        users = []
        parent_storage_dir = os.path.dirname(self.storage_dir)
        
        if not os.path.exists(parent_storage_dir):
            return users
        
        for item in os.listdir(parent_storage_dir):
            item_path = os.path.join(parent_storage_dir, item)
            if os.path.isdir(item_path) and item != ".gitkeep":
                users.append(item)
        
        return sorted(users)
    
    def _extract_file_metadata(self, content: Any) -> Dict[str, Any]:
        """从微博文件内容中提取元数据"""
        metadata = {"platform": "weibo"}
        
        if isinstance(content, dict):
            user_info = content.get("user", {})
            weibo_list = content.get("weibo", [])
            
            metadata.update({
                "user_id": user_info.get("id", ""),
                "nickname": user_info.get("nickname", ""),
                "weibo_count": len(weibo_list) if isinstance(weibo_list, list) else 0
            })
        
        return metadata
