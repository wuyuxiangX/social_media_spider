import os
import json
import time
import logging
from typing import Optional, List, Dict, Any
from spiders.bilibili.utils import download_video
from spiders.bilibili.exAudio import process_audio_split
import spiders.bilibili.speech2text as speech2text

logger = logging.getLogger(__name__)

class BilibiliSpider:
    """Bilibili视频爬虫类，负责下载视频并转换为文本"""
    
    def __init__(self, whisper_model: str = "small"):
        """
        初始化Bilibili爬虫
        
        Args:
            whisper_model: 使用的Whisper模型名称
        """
        self.whisper_model = whisper_model
        self.model_loaded = False
        # 设置存储基础目录 - 使用绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        self.storage_base = os.path.join(project_root, "storage", "bilibili")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保所需目录存在"""
        directories = [
            f"{self.storage_base}/bilibili_video",
            f"{self.storage_base}/audio/conv", 
            f"{self.storage_base}/audio/slice",
            f"{self.storage_base}/outputs"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _load_whisper_model(self):
        """加载Whisper模型"""
        if not self.model_loaded:
            try:
                speech2text.load_whisper(self.whisper_model)
                self.model_loaded = True
                logger.info(f"Whisper模型 {self.whisper_model} 加载成功")
            except Exception as e:
                logger.error(f"Whisper模型加载失败: {e}")
                raise
    
    def process_single_video(self, bv_number: str, prompt: str = "以下是普通话的句子。") -> Dict[str, Any]:
        """
        处理单个视频
        
        Args:
            bv_number: BV号（可带或不带BV前缀）
            prompt: Whisper转换提示词
            
        Returns:
            包含处理结果的字典
        """
        try:
            # 确保BV号格式正确
            if bv_number.startswith("BV"):
                bv_number = bv_number[2:]
            
            # 加载模型
            self._load_whisper_model()
            
            # 下载视频
            logger.info(f"开始下载视频: BV{bv_number}")
            file_identifier = download_video(bv_number, self.storage_base)
            
            # 处理音频
            logger.info("开始处理音频")
            folder_name = process_audio_split(file_identifier, self.storage_base)
            
            # 转换为文本
            logger.info("开始转换文本")
            text_content = speech2text.run_analysis(
                folder_name, 
                model=self.whisper_model, 
                prompt=prompt, 
                return_text=True,
                base_path=self.storage_base
            )
            
            # 获取视频标题
            video_title = self._get_video_title(file_identifier)
            
            # 保存结果到文件
            output_filename = f"{self.storage_base}/outputs/{folder_name}.json"
            result_data = {
                "bv_number": f"BV{bv_number}",
                "title": video_title,
                "text": text_content,
                "folder_name": folder_name,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "whisper_model": self.whisper_model
            }
            
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            result_data["output_file"] = output_filename
            logger.info(f"视频处理完成: {output_filename}")
            
            return result_data
            
        except Exception as e:
            error_msg = f"处理视频 BV{bv_number} 失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def process_multiple_videos(self, bv_numbers: List[str], prompt: str = "以下是普通话的句子。") -> Dict[str, Any]:
        """
        批量处理多个视频
        
        Args:
            bv_numbers: BV号列表
            prompt: Whisper转换提示词
            
        Returns:
            包含所有处理结果的字典
        """
        try:
            # 加载模型
            self._load_whisper_model()
            
            results = {
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "whisper_model": self.whisper_model,
                "videos": {}
            }
            
            total_videos = len(bv_numbers)
            for i, bv_number in enumerate(bv_numbers, 1):
                logger.info(f"处理视频 {i}/{total_videos}: {bv_number}")
                
                try:
                    result = self.process_single_video(bv_number, prompt)
                    results["videos"][result["bv_number"]] = {
                        "title": result["title"],
                        "text": result["text"],
                        "folder_name": result["folder_name"]
                    }
                except Exception as e:
                    results["videos"][bv_number] = {
                        "error": str(e)
                    }
            
            # 保存批量处理结果
            output_filename = f"{self.storage_base}/outputs/multiple_videos_{time.strftime('%Y%m%d%H%M%S')}.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            results["output_file"] = output_filename
            logger.info(f"批量处理完成: {output_filename}")
            
            return results
            
        except Exception as e:
            error_msg = f"批量处理失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _get_video_title(self, file_identifier: str) -> str:
        """获取视频标题"""
        try:
            bv_folder = f"{self.storage_base}/bilibili_video/{file_identifier}"
            if os.path.exists(bv_folder) and os.path.isdir(bv_folder):
                mp4_files = [f for f in os.listdir(bv_folder) if f.endswith('.mp4')]
                if mp4_files:
                    return os.path.splitext(mp4_files[0])[0]
            return ""
        except Exception:
            return ""
