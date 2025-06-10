'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 数据清洗处理基类
'''
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import json
import os


class BaseDataProcessor(ABC):
    """数据处理基类"""
    
    def __init__(self, mind_id: str = "169949830539034624", username: str = "default"):
        """
        初始化数据处理器
        
        Args:
            mind_id: 目标mindId，默认为示例值
            username: 用户名，用于创建用户专属目录
        """
        self.mind_id = mind_id
        self.target = "addNote"
        self.type = "text"
        self.username = username
        # 延迟初始化storage_dir，让子类先初始化platform_name
        self._storage_dir = None
    
    @property
    def storage_dir(self) -> str:
        """获取存储目录，延迟初始化"""
        if self._storage_dir is None:
            self._storage_dir = self._get_storage_dir()
        return self._storage_dir
    
    def _get_storage_dir(self) -> str:
        """获取数据存储目录，按用户名分类"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        user_dir = os.path.join(parent_dir, "storage", self.username)
        
        # 确保用户目录存在
        os.makedirs(user_dir, exist_ok=True)
        
        return user_dir
    
    def _get_platform_name(self) -> str:
        """获取平台名称，子类需要重写"""
        return "unknown"
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        处理数据文件
        
        Args:
            file_path: 原始数据文件路径
            
        Returns:
            Dict[str, Any]: 处理结果，包含处理后文件路径和统计信息
        """
        start_time = datetime.now()
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取原始数据
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # 处理数据
        processed_data = self.process_data(raw_data)
        
        # 生成处理后的文件路径
        processed_file_path = self._generate_processed_file_path(file_path)
        
        # 保存处理后的数据
        original_filename = os.path.basename(file_path)
        processed_file_path = self.save_processed_data(processed_data, original_filename)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        return {
            "original_file_path": file_path,
            "processed_file_path": processed_file_path,
            "original_count": self._count_original_items(raw_data),
            "processed_count": len(processed_data),
            "processing_time": processing_time,
            "stats": self.get_processing_stats(processed_data)
        }
    
    def _generate_processed_file_path(self, original_file_path: str) -> str:
        """生成处理后文件的路径"""
        # 直接使用output目录，不创建processed子目录
        output_dir = os.path.join(self.storage_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        platform_name = self._get_platform_name()
        processed_file_name = f"{platform_name}_processed.json"
        
        return os.path.join(output_dir, processed_file_name)
    
    def _count_original_items(self, raw_data: Any) -> int:
        """计算原始数据的条目数，子类可以重写"""
        if isinstance(raw_data, list):
            return len(raw_data)
        elif isinstance(raw_data, dict):
            # 尝试找到数据列表
            for key in ["weibo", "data", "items", "posts"]:
                if key in raw_data and isinstance(raw_data[key], list):
                    return len(raw_data[key])
            return 1
        else:
            return 1
    
    def save_data(self, data: Any, filename: Optional[str] = None) -> str:
        """
        保存数据到文件
        
        Args:
            data: 要保存的数据
            filename: 自定义文件名，如果为None则自动生成
            
        Returns:
            str: 保存的文件路径
        """
        if filename is None:
            platform_name = self._get_platform_name()
            filename = f"{platform_name}.json"
        
        file_path = os.path.join(self.storage_dir, filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return file_path
        except Exception as e:
            raise Exception(f"保存文件失败: {str(e)}")
    
    def save_processed_data(self, data: Any, original_filename: str) -> str:
        """
        保存处理后的数据到output目录
        
        Args:
            data: 处理后的数据
            original_filename: 原始文件名
            
        Returns:
            str: 保存的文件路径
        """
        # 创建output目录
        output_dir = os.path.join(self.storage_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成处理后的文件名，直接使用平台名
        platform_name = self._get_platform_name()
        processed_filename = f"{platform_name}_processed.json"
        
        file_path = os.path.join(output_dir, processed_filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return file_path
        except Exception as e:
            raise Exception(f"保存处理后文件失败: {str(e)}")
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """
        获取所有数据文件信息
        
        Returns:
            List[Dict[str, Any]]: 文件信息列表
        """
        files = []
        
        if not os.path.exists(self.storage_dir):
            return files
        
        for root, dirs, filenames in os.walk(self.storage_dir):
            for filename in filenames:
                if filename.endswith('.json'):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        
                        file_info = {
                            "file_path": file_path,
                            "file_name": filename,
                            "file_size": os.path.getsize(file_path),
                            "modified_time": os.path.getmtime(file_path),
                            "content": content
                        }
                        
                        # 添加平台特定的信息
                        file_info.update(self._extract_file_metadata(content))
                        
                        files.append(file_info)
                        
                    except Exception as e:
                        files.append({
                            "file_path": file_path,
                            "file_name": filename,
                            "file_size": os.path.getsize(file_path),
                            "modified_time": os.path.getmtime(file_path),
                            "error": str(e)
                        })
        
        # 按修改时间排序，最新的在前
        files.sort(key=lambda x: x.get("modified_time", 0), reverse=True)
        
        return files
    
    def _extract_file_metadata(self, content: Any) -> Dict[str, Any]:
        """
        从文件内容中提取元数据，子类可以重写
        
        Args:
            content: 文件内容
            
        Returns:
            Dict[str, Any]: 元数据
        """
        return {}
    
    @abstractmethod
    def process_data(self, raw_data: List[Dict[Any, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        处理原始数据，转换为API所需格式
        
        Args:
            raw_data: 原始数据列表
            **kwargs: 其他参数
            
        Returns:
            List[Dict[str, Any]]: 处理后的数据列表
        """
        pass
    
    def clean_content(self, content: str) -> str:
        """
        清洗内容文本
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清洗后的内容
        """
        if not content:
            return ""
        
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content.strip())
        
        # 移除特殊字符（保留中英文、数字、常用标点）
        content = re.sub(r'[^\u4e00-\u9fa5\w\s.,!?;:()（）""''【】\\-\n]', '', content)
        
        # 限制长度（根据需要调整）
        max_length = 2000
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content
    
    def extract_user_title(self, data: Dict[Any, Any]) -> str:
        """
        提取用户标题/昵称
        
        Args:
            data: 单条数据
            
        Returns:
            str: 用户标题
        """
        # 子类可以重写此方法
        return ""
    
    def format_api_data(self, content: str, user_title: str = "") -> Dict[str, Any]:
        """
        格式化为API所需的数据结构
        
        Args:
            content: 清洗后的内容
            user_title: 用户标题
            
        Returns:
            Dict[str, Any]: API格式的数据
        """
        return {
            "mindId": self.mind_id,
            "content": content,
            "type": self.type,
            "userTitle": user_title,
            "target": self.target
        }
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据是否符合简化格式要求
        
        Args:
            data: 待验证的数据
            
        Returns:
            bool: 是否有效
        """
        # 检查是否包含content字段
        if "content" not in data:
            return False
        
        # 检查内容不为空
        if not data["content"] or not data["content"].strip():
            return False
        
        return True
    
    def get_processing_stats(self, processed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Args:
            processed_data: 处理后的数据
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_items = len(processed_data)
        valid_items = len([item for item in processed_data if self.validate_data(item)])
        total_content_length = sum(len(item.get("content", "")) for item in processed_data)
        
        return {
            "total_items": total_items,
            "valid_items": valid_items,
            "invalid_items": total_items - valid_items,
            "total_content_length": total_content_length,
            "average_content_length": total_content_length / total_items if total_items > 0 else 0,
            "processing_time": datetime.now().isoformat()
        }
