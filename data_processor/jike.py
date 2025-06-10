'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 即刻数据处理器
'''
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import os
import json
from .base import BaseDataProcessor


class JikeDataProcessor(BaseDataProcessor):
    """即刻数据处理器"""
    
    def __init__(self, mind_id: str = "169949830539034624", username: str = "default"):
        super().__init__(mind_id, username)
    
    def _get_platform_name(self) -> str:
        """获取平台名称"""
        return "jike"
    
    def process_data(self, raw_data: List[Dict[Any, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        处理即刻原始数据
        
        Args:
            raw_data: 即刻原始数据列表
            **kwargs: 其他参数
                - include_user_info: 是否包含用户信息，默认True
                - max_items: 最大处理条数，默认无限制
                
        Returns:
            List[Dict[str, Any]]: 处理后的数据列表
        """
        include_user_info = kwargs.get("include_user_info", True)
        max_items = kwargs.get("max_items", None)
        
        processed_data = []
        
        for i, item in enumerate(raw_data):
            if max_items and i >= max_items:
                break
                
            try:
                processed_item = self._process_single_jike_item(item, include_user_info)
                if processed_item and self.validate_data(processed_item):
                    processed_data.append(processed_item)
            except Exception as e:
                print(f"处理即刻数据项失败: {str(e)}")
                continue
        
        return processed_data
    
    def _process_single_jike_item(self, item: Dict[Any, Any], include_user_info: bool = True) -> Optional[Dict[str, Any]]:
        """
        处理单条即刻数据
        
        Args:
            item: 单条即刻数据
            include_user_info: 是否包含用户信息
            
        Returns:
            Optional[Dict[str, Any]]: 处理后的数据，如果处理失败返回None
        """
        # 提取内容
        content = item.get("content", "")
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
    
    def _build_enriched_content(self, content: str, action_time: str, post_type: str, 
                               item: Dict[Any, Any], include_user_info: bool) -> str:
        """
        构建丰富的内容信息
        
        Args:
            content: 清洗后的基础内容
            action_time: 发布时间
            post_type: 帖子类型
            item: 原始数据项
            include_user_info: 是否包含用户信息
            
        Returns:
            str: 丰富的内容
        """
        enriched_parts = []
        
        # 添加内容
        enriched_parts.append(f"内容: {content}")
        
        # 添加时间信息
        if action_time:
            try:
                # 转换时间格式
                dt = datetime.fromisoformat(action_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                enriched_parts.append(f"发布时间: {formatted_time}")
            except:
                enriched_parts.append(f"发布时间: {action_time}")
        
        # 添加帖子类型
        if post_type:
            type_mapping = {
                "ORIGINAL_POST": "原创帖子",
                "REPOST": "转发",
                "COMMENT": "评论"
            }
            type_name = type_mapping.get(post_type, post_type)
            enriched_parts.append(f"类型: {type_name}")
        
        # 添加话题信息
        topics = self._extract_topics(item)
        if topics:
            enriched_parts.append(f"话题: {', '.join(topics)}")
        
        # 添加统计信息
        stats = self._extract_stats(item)
        if stats:
            enriched_parts.append(f"互动数据: {stats}")
        
        # 添加用户信息
        if include_user_info:
            user_info = self._extract_user_info(item)
            if user_info:
                enriched_parts.append(f"用户信息: {user_info}")
        
        return " | ".join(enriched_parts)
    
    def _extract_topics(self, item: Dict[Any, Any]) -> List[str]:
        """提取话题信息"""
        topics = []
        
        # 从不同字段提取话题
        topic_fields = ["topic", "topics", "targetTopic"]
        for field in topic_fields:
            if field in item and item[field]:
                if isinstance(item[field], dict):
                    topic_content = item[field].get("content", "")
                    if topic_content:
                        topics.append(topic_content)
                elif isinstance(item[field], list):
                    for topic in item[field]:
                        if isinstance(topic, dict):
                            topic_content = topic.get("content", "")
                            if topic_content:
                                topics.append(topic_content)
        
        return topics
    
    def _extract_stats(self, item: Dict[Any, Any]) -> str:
        """提取统计信息"""
        stats_parts = []
        
        # 提取各种计数
        count_fields = {
            "likeCount": "点赞",
            "commentCount": "评论", 
            "repostCount": "转发",
            "shareCount": "分享"
        }
        
        for field, name in count_fields.items():
            if field in item and item[field]:
                stats_parts.append(f"{name}{item[field]}")
        
        return ", ".join(stats_parts) if stats_parts else ""
    
    def _extract_user_info(self, item: Dict[Any, Any]) -> str:
        """提取用户信息"""
        user_info_parts = []
        
        # 从用户字段提取信息
        user = item.get("user", {})
        if user:
            screen_name = user.get("screenName", "")
            if screen_name:
                user_info_parts.append(f"昵称: {screen_name}")
            
            brief_intro = user.get("briefIntro", "")
            if brief_intro:
                # 限制简介长度
                if len(brief_intro) > 50:
                    brief_intro = brief_intro[:50] + "..."
                user_info_parts.append(f"简介: {brief_intro}")
        
        return ", ".join(user_info_parts) if user_info_parts else ""
    
    def extract_user_title(self, data: Dict[Any, Any]) -> str:
        """
        提取用户标题
        
        Args:
            data: 即刻数据项
            
        Returns:
            str: 用户标题
        """
        user = data.get("user", {})
        if user:
            return user.get("screenName", "")
        return ""
    
    def clean_content(self, content: str) -> str:
        """
        清洗即刻内容
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清洗后的内容
        """
        if not content:
            return ""
        
        # 移除@用户链接
        content = re.sub(r'@[\w\-\.]+', '', content)
        
        # 移除URL链接
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        
        # 调用父类的清洗方法
        return super().clean_content(content)
    
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
        
        # 查找jike.json文件
        jike_file = os.path.join(self.storage_dir, "jike.json")
        if os.path.exists(jike_file):
            try:
                with open(jike_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                user_files.append({
                    "file_path": jike_file,
                    "file_name": "jike.json",
                    "file_size": os.path.getsize(jike_file),
                    "modified_time": os.path.getmtime(jike_file),
                    "content": content,
                    "data_count": len(content) if isinstance(content, list) else 1
                })
            except Exception as e:
                user_files.append({
                    "file_path": jike_file,
                    "file_name": "jike.json",
                    "file_size": os.path.getsize(jike_file),
                    "modified_time": os.path.getmtime(jike_file),
                    "error": str(e),
                    "data_count": 0
                })
        
        return user_files
    
    def save_jike_data(self, data: List[Dict[Any, Any]], filename: Optional[str] = None) -> str:
        """
        保存即刻数据到文件
        
        Args:
            data: 即刻数据列表
            filename: 自定义文件名，如果为None则自动生成
            
        Returns:
            str: 保存的文件路径
        """
        return self.save_data(data, filename)
    
    def _extract_file_metadata(self, content: Any) -> Dict[str, Any]:
        """从即刻文件内容中提取元数据"""
        if isinstance(content, list) and content:
            return {
                "data_count": len(content),
                "platform": "jike"
            }
        return {"platform": "jike"}
