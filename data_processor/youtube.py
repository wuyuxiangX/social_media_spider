'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : YouTube数据处理器
'''
from typing import List, Dict, Any, Optional, Union
import os
import json
import time


class YouTubeDataProcessor():
    """YouTube数据处理器"""

    def _get_platform_name(self) -> str:
        """获取平台名称"""
        return "youtube"
    
    def process_data(self, raw_data: Union[str, List[str]]) -> Dict[str, Any]:
        """
        处理字幕文件，支持单个文件路径或文件路径列表
        
        Args:
            raw_data: 字幕文件路径或路径列表
            
        Returns:
            Dict[str, Any]: 处理结果，包含处理后的数据和统计信息
        """
        start_time = time.time()
        
        # 将单个文件路径转换为列表以统一处理
        if isinstance(raw_data, str):
            file_paths = [raw_data]
        else:
            file_paths = raw_data
        
        if not file_paths:
            raise ValueError("未提供有效的字幕文件路径")
        
        processed_items = []
        file_info = []
        
        # 处理每个字幕文件
        for path in file_paths:
            try:
                # 读取字幕文件
                with open(path, 'r', encoding='utf-8') as f:
                    subtitle_text = f.read().strip()
                
                # 简化处理：直接将整个字幕内容作为一个项目
                processed_item = {"content": subtitle_text}
                processed_items.append(processed_item)
                
                # 记录文件信息
                file_info.append({
                    "file_path": path,
                    "file_name": os.path.basename(path),
                    "text_length": len(subtitle_text)
                })
                
            except Exception as e:
                print(f"处理文件 {path} 失败: {str(e)}")
                file_info.append({
                    "file_path": path,
                    "file_name": os.path.basename(path),
                    "error": str(e)
                })
        
        # 使用固定路径保存处理后的数据
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        storage_dir = os.path.join(parent_dir, "storage", "default")
        
        # 确保目录存在
        os.makedirs(storage_dir, exist_ok=True)
        
        # 保存处理后的数据
        output_filename = "youtube.json"
        output_path = os.path.join(storage_dir, output_filename)
        
        # 保存数据
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_items, f, ensure_ascii=False, indent=2)
        
        processing_time = time.time() - start_time
        
        return {
            "original_files": file_info,
            "processed_file": output_path,
            "item_count": len(processed_items),
            "processing_time": processing_time
        }
