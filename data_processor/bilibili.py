'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : Bilibili数据处理器
'''
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import os
import json
from .base import BaseDataProcessor


class BilibiliDataProcessor(BaseDataProcessor):
    """Bilibili数据处理器"""
    
    def __init__(self, mind_id: str = "169949830539034624", username: str = "default"):
        super().__init__(mind_id, username)
    
    def _get_platform_name(self) -> str:
        """获取平台名称"""
        return "bilibili"
    
    def process_data(self, raw_data: Any, **kwargs) -> List[Dict[str, Any]]:
        """
        处理Bilibili原始数据
        
        Args:
            raw_data: Bilibili原始数据（可以是单个对象或列表）
            **kwargs: 其他参数
                - include_video_info: 是否包含视频信息，默认True
                - max_items: 最大处理条数，默认无限制
                - split_long_text: 是否拆分长文本，默认True
                
        Returns:
            List[Dict[str, Any]]: 处理后的数据列表
        """
        include_video_info = kwargs.get("include_video_info", True)
        max_items = kwargs.get("max_items", None)
        split_long_text = kwargs.get("split_long_text", True)
        
        processed_data = []
        
        # 统一处理为列表格式
        if isinstance(raw_data, dict):
            # 如果是单个视频对象
            data_list = [raw_data]
        elif isinstance(raw_data, list):
            # 如果已经是列表
            data_list = raw_data
        else:
            return processed_data
        
        for i, item in enumerate(data_list):
            if max_items and i >= max_items:
                break
                
            try:
                processed_items = self._process_single_bilibili_item(
                    item, include_video_info, split_long_text
                )
                for processed_item in processed_items:
                    if processed_item and self.validate_data(processed_item):
                        processed_data.append(processed_item)
            except Exception as e:
                print(f"处理Bilibili数据项失败: {str(e)}")
                continue
        
        return processed_data
    
    def _process_single_bilibili_item(self, item: Dict[Any, Any], include_video_info: bool = True,
                                     split_long_text: bool = True) -> List[Dict[str, Any]]:
        """
        处理单条Bilibili数据
        
        Args:
            item: 单条Bilibili数据
            include_video_info: 是否包含视频信息
            split_long_text: 是否拆分长文本
            
        Returns:
            List[Dict[str, Any]]: 处理后的数据列表（可能包含多条）
        """
        # 提取文本内容
        text_content = item.get("text", "")
        if not text_content:
            return []
        
        # 清洗内容
        clean_content = self.clean_content(text_content)
        if not clean_content:
            return []
        
        # 如果需要拆分长文本
        if split_long_text:
            text_chunks = self._split_long_text(clean_content)
            processed_items = []
            
            for chunk in text_chunks:
                # 简化输出格式，只返回内容
                processed_item = {"content": chunk}
                processed_items.append(processed_item)
            
            return processed_items
        else:
            # 不拆分，作为单条处理
            return [{"content": clean_content}]
    
    def _build_base_enriched_content(self, item: Dict[Any, Any], include_video_info: bool) -> str:
        """
        构建基础的丰富内容信息（不包含转录文本）
        
        Args:
            item: Bilibili数据项
            include_video_info: 是否包含视频信息
            
        Returns:
            str: 基础丰富内容
        """
        enriched_parts = []
        
        # 添加视频标题
        title = item.get("title", "")
        if title:
            enriched_parts.append(f"视频标题: {title}")
        
        # 添加BV号
        bv_number = item.get("bv_number", "")
        if bv_number:
            enriched_parts.append(f"BV号: {bv_number}")
        
        # 添加处理时间
        timestamp = item.get("timestamp", "")
        if timestamp:
            enriched_parts.append(f"处理时间: {timestamp}")
        
        # 添加处理模型信息
        if include_video_info:
            whisper_model = item.get("whisper_model", "")
            if whisper_model:
                enriched_parts.append(f"转录模型: {whisper_model}")
            
            folder_name = item.get("folder_name", "")
            if folder_name:
                enriched_parts.append(f"文件夹: {folder_name}")
        
        return " | ".join(enriched_parts) if enriched_parts else "Bilibili视频转录"
    
    def _split_long_text(self, text: str, max_length: int = 1500) -> List[str]:
        """
        拆分长文本
        
        Args:
            text: 原始文本
            max_length: 每段最大长度
            
        Returns:
            List[str]: 拆分后的文本列表
        """
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # 按句子拆分（以句号、问号、感叹号为分隔符）
        sentences = re.split(r'[。！？!?]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 如果当前块加上新句子超过长度限制
            if len(current_chunk) + len(sentence) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # 单个句子就超过长度限制，强制拆分
                    while len(sentence) > max_length:
                        chunks.append(sentence[:max_length])
                        sentence = sentence[max_length:]
                    current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # 添加最后一块
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def extract_user_title(self, data: Dict[Any, Any]) -> str:
        """
        提取用户标题
        
        Args:
            data: Bilibili数据项
            
        Returns:
            str: 用户标题
        """
        # Bilibili数据通常不包含用户信息，使用视频标题或BV号作为标识
        title = data.get("title", "")
        bv_number = data.get("bv_number", "")
        
        if title:
            return f"Bilibili - {title}"
        elif bv_number:
            return f"Bilibili - {bv_number}"
        else:
            return "Bilibili视频"
    
    def clean_content(self, content: str) -> str:
        """
        清洗Bilibili转录内容
        
        Args:
            content: 原始转录内容
            
        Returns:
            str: 清洗后的内容
        """
        if not content:
            return ""
        
        # 移除多余的空格和换行
        content = re.sub(r'\s+', ' ', content.strip())
        
        # 移除常见的转录错误标记
        content = re.sub(r'\[音乐\]|\[掌声\]|\[笑声\]|\[噪音\]', '', content)
        
        # 移除重复的词汇（ASR常见问题）
        words = content.split()
        cleaned_words = []
        prev_word = ""
        repeat_count = 0
        
        for word in words:
            if word == prev_word:
                repeat_count += 1
                if repeat_count < 3:  # 允许最多重复2次
                    cleaned_words.append(word)
            else:
                cleaned_words.append(word)
                repeat_count = 0
            prev_word = word
        
        content = " ".join(cleaned_words)
        
        # 调用父类的清洗方法
        return super().clean_content(content)
    
    def save_bilibili_data(self, data: Dict[Any, Any], filename: Optional[str] = None) -> str:
        """
        保存Bilibili数据到文件
        
        Args:
            data: Bilibili数据
            filename: 自定义文件名，如果为None则自动生成
            
        Returns:
            str: 保存的文件路径
        """
        return self.save_data(data, filename)
    
    def _extract_file_metadata(self, content: Any) -> Dict[str, Any]:
        """从Bilibili文件内容中提取元数据"""
        metadata = {"platform": "bilibili"}
        
        if isinstance(content, dict):
            metadata.update({
                "bv_number": content.get("bv_number", ""),
                "title": content.get("title", ""),
                "timestamp": content.get("timestamp", "")
            })
        
        return metadata
    
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
        
        # 查找bilibili.json文件
        bilibili_file = os.path.join(self.storage_dir, "bilibili.json")
        if os.path.exists(bilibili_file):
            try:
                with open(bilibili_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                user_files.append({
                    "file_path": bilibili_file,
                    "file_name": "bilibili.json",
                    "file_size": os.path.getsize(bilibili_file),
                    "modified_time": os.path.getmtime(bilibili_file),
                    "content": content,
                    "bv_number": content.get("bv_number", ""),
                    "title": content.get("title", ""),
                    "text_length": len(content.get("text", ""))
                })
            except Exception as e:
                user_files.append({
                    "file_path": bilibili_file,
                    "file_name": "bilibili.json",
                    "file_size": os.path.getsize(bilibili_file),
                    "modified_time": os.path.getmtime(bilibili_file),
                    "error": str(e),
                    "text_length": 0
                })
        
        return user_files
