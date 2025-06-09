'''
Author       : wyx-hhhh
Date         : 2025-06-09
LastEditTime : 2025-06-09
Description  : 即刻爬虫文件处理器
'''
import os
import json
from typing import List, Dict, Any, Optional


class JikeFileHandler:
    """即刻爬虫文件处理器"""
    
    def __init__(self):
        self.storage_dir = self._get_storage_dir()
    
    def _get_storage_dir(self) -> str:
        """获取即刻数据存储目录"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        storage_dir = os.path.join(parent_dir, "storage", "jike")
        
        # 确保目录存在
        os.makedirs(storage_dir, exist_ok=True)
        
        return storage_dir
    
    def save_jike_data(self, data: List[Dict[Any, Any]], username: str, filename: Optional[str] = None) -> str:
        """
        保存即刻数据到文件
        
        Args:
            data: 即刻数据列表
            username: 用户名
            filename: 自定义文件名，如果为None则自动生成
            
        Returns:
            str: 保存的文件路径
        """
        if filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{username}_{timestamp}.json"
        
        file_path = os.path.join(self.storage_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return file_path
        except Exception as e:
            raise Exception(f"保存文件失败: {str(e)}")
    
    def get_user_files(self, username: str) -> List[Dict[str, Any]]:
        """
        获取指定用户的所有文件信息
        
        Args:
            username: 用户名
            
        Returns:
            List[Dict[str, Any]]: 文件信息列表
        """
        user_files = []
        
        if not os.path.exists(self.storage_dir):
            return user_files
        
        for file in os.listdir(self.storage_dir):
            if file.startswith(username) and file.endswith('.json'):
                file_path = os.path.join(self.storage_dir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    
                    user_files.append({
                        "file_path": file_path,
                        "file_name": file,
                        "file_size": os.path.getsize(file_path),
                        "modified_time": os.path.getmtime(file_path),
                        "content": content,
                        "data_count": len(content) if isinstance(content, list) else 1
                    })
                except Exception as e:
                    user_files.append({
                        "file_path": file_path,
                        "file_name": file,
                        "file_size": os.path.getsize(file_path),
                        "modified_time": os.path.getmtime(file_path),
                        "error": str(e),
                        "data_count": 0
                    })
        
        # 按修改时间排序，最新的在前
        user_files.sort(key=lambda x: x.get("modified_time", 0), reverse=True)
        
        return user_files
