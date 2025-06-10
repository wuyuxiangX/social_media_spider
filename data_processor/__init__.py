'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 数据处理器工厂和统一接口
'''
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import json
from .base import BaseDataProcessor
from .jike import JikeDataProcessor
from .weibo import WeiboDataProcessor
from .bilibili import BilibiliDataProcessor


class DataSourceType(Enum):
    """数据源类型枚举"""
    JIKE = "jike"
    WEIBO = "weibo"
    BILIBILI = "bilibili"


class DataProcessorFactory:
    """数据处理器工厂类"""
    
    @staticmethod
    def create_processor(source_type: Union[str, DataSourceType], mind_id: str = "169949830539034624") -> BaseDataProcessor:
        """
        创建数据处理器
        
        Args:
            source_type: 数据源类型
            mind_id: 目标mindId
            
        Returns:
            BaseDataProcessor: 对应的数据处理器
            
        Raises:
            ValueError: 不支持的数据源类型
        """
        if isinstance(source_type, str):
            source_type = source_type.lower()
            
        if source_type == DataSourceType.JIKE.value or source_type == DataSourceType.JIKE:
            return JikeDataProcessor(mind_id)
        elif source_type == DataSourceType.WEIBO.value or source_type == DataSourceType.WEIBO:
            return WeiboDataProcessor(mind_id)
        elif source_type == DataSourceType.BILIBILI.value or source_type == DataSourceType.BILIBILI:
            return BilibiliDataProcessor(mind_id)
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}")


class UnifiedDataProcessor:
    """统一数据处理器"""
    
    def __init__(self, mind_id: str = "169949830539034624"):
        """
        初始化统一数据处理器
        
        Args:
            mind_id: 目标mindId
        """
        self.mind_id = mind_id
        self.factory = DataProcessorFactory()
    
    def process_data_from_file(self, file_path: str, source_type: Union[str, DataSourceType], 
                              **kwargs) -> Dict[str, Any]:
        """
        从文件处理数据
        
        Args:
            file_path: 数据文件路径
            source_type: 数据源类型
            **kwargs: 处理参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            return self.process_data(raw_data, source_type, **kwargs)
            
        except Exception as e:
            return {
                "success": False,
                "message": f"处理文件失败: {str(e)}",
                "data": None,
                "stats": None
            }
    
    def process_data(self, raw_data: Union[List[Dict[Any, Any]], Dict[Any, Any]], 
                    source_type: Union[str, DataSourceType], **kwargs) -> Dict[str, Any]:
        """
        处理原始数据
        
        Args:
            raw_data: 原始数据
            source_type: 数据源类型
            **kwargs: 处理参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 创建处理器
            processor = self.factory.create_processor(source_type, self.mind_id)
            
            # 标准化数据格式
            if isinstance(raw_data, dict) and source_type != DataSourceType.WEIBO.value:
                # 对于非微博数据，如果是字典格式，可能需要提取特定字段
                if "data" in raw_data:
                    data_to_process = raw_data["data"]
                elif "weibo" in raw_data:
                    data_to_process = raw_data
                else:
                    data_to_process = [raw_data]
            else:
                data_to_process = raw_data
            
            # 处理数据
            processed_data = processor.process_data(data_to_process, **kwargs)
            
            # 获取统计信息
            stats = processor.get_processing_stats(processed_data)
            
            return {
                "success": True,
                "message": f"成功处理 {len(processed_data)} 条数据",
                "data": processed_data,
                "stats": stats,
                "source_type": source_type,
                "mind_id": self.mind_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"处理数据失败: {str(e)}",
                "data": None,
                "stats": None,
                "source_type": source_type,
                "mind_id": self.mind_id
            }
    
    def batch_process_files(self, file_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量处理多个文件
        
        Args:
            file_configs: 文件配置列表，每个配置包含：
                - file_path: 文件路径
                - source_type: 数据源类型
                - options: 处理选项（可选）
                
        Returns:
            Dict[str, Any]: 批量处理结果
        """
        results = []
        total_processed = 0
        total_failed = 0
        
        for config in file_configs:
            file_path = config.get("file_path")
            source_type = config.get("source_type")
            options = config.get("options", {})
            
            if not file_path or not source_type:
                results.append({
                    "file_path": file_path,
                    "success": False,
                    "message": "缺少必要参数: file_path 或 source_type",
                    "data": None
                })
                total_failed += 1
                continue
            
            result = self.process_data_from_file(file_path, source_type, **options)
            result["file_path"] = file_path
            results.append(result)
            
            if result["success"]:
                total_processed += len(result["data"]) if result["data"] else 0
            else:
                total_failed += 1
        
        return {
            "success": True,
            "message": f"批量处理完成，共处理 {total_processed} 条数据，{total_failed} 个文件失败",
            "results": results,
            "summary": {
                "total_files": len(file_configs),
                "successful_files": len(file_configs) - total_failed,
                "failed_files": total_failed,
                "total_processed_items": total_processed
            }
        }
    
    def export_processed_data(self, processed_data: List[Dict[str, Any]], 
                             output_path: str, format_type: str = "json") -> Dict[str, Any]:
        """
        导出处理后的数据
        
        Args:
            processed_data: 处理后的数据
            output_path: 输出文件路径
            format_type: 输出格式（json, txt）
            
        Returns:
            Dict[str, Any]: 导出结果
        """
        try:
            if format_type.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_data, f, indent=2, ensure_ascii=False)
            elif format_type.lower() == "txt":
                with open(output_path, 'w', encoding='utf-8') as f:
                    for item in processed_data:
                        content = item.get("content", "")
                        f.write(f"{content}\n\n---\n\n")
            else:
                raise ValueError(f"不支持的输出格式: {format_type}")
            
            return {
                "success": True,
                "message": f"成功导出 {len(processed_data)} 条数据到 {output_path}",
                "output_path": output_path,
                "format": format_type,
                "item_count": len(processed_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"导出数据失败: {str(e)}",
                "output_path": output_path,
                "format": format_type,
                "item_count": len(processed_data)
            }
