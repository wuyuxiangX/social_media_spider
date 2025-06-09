import json
import logging
import os
import sys
from datetime import date, timedelta
from typing import List, Dict, Optional

from . import config_util

# 配置日志
logger = logging.getLogger(__name__)

class WeiboSpiderMain:
    """微博爬虫主类，提供简化的接口来执行微博数据爬取"""
    
    def __init__(self, config_path: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        初始化微博爬虫
        
        Args:
            config_path: 配置文件路径
            config_dict: 配置字典，如果提供则优先使用
        """
        self.spider = None
        
        if config_dict:
            self.config = config_dict
        elif config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            # 使用默认配置
            self.config = self._get_default_config()
        
        # 验证配置
        try:
            config_util.validate_config(self.config)
        except Exception as e:
            raise
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "user_id_list": [],
            "filter": 1,  # 只爬取原创微博
            "since_date": "2024-01-01",
            "end_date": "now",
            "random_wait_pages": [1, 3],
            "random_wait_seconds": [3, 6],
            "global_wait": [[100, 300]],
            "write_mode": ["json"],
            "pic_download": 0,
            "video_download": 0,
            "file_download_timeout": [5, 5, 10],
            "result_dir_name": 0,
            "cookie": ""
        }
    
    def set_cookie(self, cookie: str):
        """设置cookie"""
        self.config['cookie'] = cookie
    
    def set_user_ids(self, user_ids: List[str]):
        """设置要爬取的用户ID列表"""
        self.config['user_id_list'] = user_ids
    
    def set_date_range(self, since_date: str = None, end_date: str = "now"):
        """
        设置爬取日期范围
        
        Args:
            since_date: 开始日期，格式为 'yyyy-mm-dd'
            end_date: 结束日期，格式为 'yyyy-mm-dd' 或 'now'
        """
        if since_date:
            self.config['since_date'] = since_date
        if end_date:
            self.config['end_date'] = end_date
    
    def set_filter_mode(self, filter_mode: int):
        """
        设置过滤模式
        
        Args:
            filter_mode: 0-全部微博，1-只爬原创微博
        """
        self.config['filter'] = filter_mode
        mode_desc = "全部微博" if filter_mode == 0 else "只爬原创微博"
    
    def set_output_format(self, formats: List[str]):
        """
        设置输出格式
        
        Args:
            formats: 输出格式列表，可包含 'txt', 'csv', 'json', 'mongo', 'mysql'
        """
        self.config['write_mode'] = formats
    
    def enable_media_download(self, pic_download: bool = False, video_download: bool = False):
        """
        启用媒体文件下载
        
        Args:
            pic_download: 是否下载图片
            video_download: 是否下载视频
        """
        self.config['pic_download'] = 1 if pic_download else 0
        self.config['video_download'] = 1 if video_download else 0
    
    def start_crawling(self) -> bool:
        """
        开始爬取数据
        
        Returns:
            bool: 爬取是否成功
        """
        try:
            if not self.config.get('cookie'):
                print("错误: 未设置cookie")
                return False
            
            if not self.config.get('user_id_list'):
                print("错误: 未设置用户ID列表")
                return False
            
            # 设置输出目录为storage/weibo
            current_dir = os.path.dirname(os.path.abspath(__file__))
            spider_dir = os.path.dirname(current_dir)
            project_dir = os.path.dirname(spider_dir)
            storage_dir = os.path.join(project_dir, "storage", "weibo")
            os.makedirs(storage_dir, exist_ok=True)
            
            # 设置absl flags环境避免未解析错误
            self._setup_flags_environment(storage_dir)
            
            # 导入并创建Spider实例
            from .spider import Spider
            self.spider = Spider(self.config)
            
            # 执行爬取
            self.spider.start()
            
            return True
            
        except Exception as e:
            print(f"爬取过程中出现错误: {e}")
            return False
    
    def _setup_flags_environment(self, output_dir=None):
        """设置FLAGS环境，避免FLAGS未解析错误"""
        try:
            from absl import flags
            FLAGS = flags.FLAGS
            
            # 如果FLAGS还没有解析，手动解析
            if not FLAGS.is_parsed():
                # 导入已有的flags定义（在spider.py中定义）
                from . import spider  # 这会导入spider.py中定义的flags
                
                # 解析flags
                FLAGS.mark_as_parsed()
                logger.info("FLAGS已解析")
            
            # 设置输出目录
            if output_dir:
                FLAGS.output_dir = output_dir
                logger.info(f"设置输出目录为: {output_dir}")
                
        except Exception as e:
            print(f"设置FLAGS环境时出现警告: {e}")
            # 继续执行，可能FLAGS已经被正确设置了
    
    def get_recent_weibo(self, user_id: str, days: int = 7) -> bool:
        """
        获取指定用户最近几天的微博
        
        Args:
            user_id: 用户ID
            days: 天数
            
        Returns:
            bool: 爬取是否成功
        """
        since_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = "now"
        
        self.set_user_ids([user_id])
        self.set_date_range(since_date, end_date)
        
        return self.start_crawling()
    
    def batch_crawl_users(self, user_ids: List[str], since_date: str = None) -> bool:
        """
        批量爬取多个用户的微博
        
        Args:
            user_ids: 用户ID列表
            since_date: 开始日期
            
        Returns:
            bool: 爬取是否成功
        """
        self.set_user_ids(user_ids)
        if since_date:
            self.set_date_range(since_date)
        
        return self.start_crawling()
    
    def get_config(self) -> Dict:
        """获取当前配置"""
        return self.config.copy()
    
    def save_config(self, config_path: str):
        """保存当前配置到文件"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise


def quick_start_example():
    """快速开始示例"""
    print("=== 微博爬虫快速开始示例 ===")
    
    # 创建爬虫实例
    crawler = WeiboSpiderMain()
    
    # 设置cookie（需要用户提供真实的cookie）
    print("请设置您的微博cookie")
    # crawler.set_cookie("your_cookie_here")
    
    # 设置要爬取的用户ID
    user_ids = ["1676679984"]  # 示例用户ID
    crawler.set_user_ids(user_ids)
    
    # 设置只爬取最近30天的原创微博
    crawler.set_date_range(since_date="2024-01-01")
    crawler.set_filter_mode(1)  # 只爬原创
    
    # 设置输出格式为JSON
    crawler.set_output_format(["json"])
    
    # 显示当前配置
    config = crawler.get_config()
    print("当前配置:")
    print(json.dumps(config, ensure_ascii=False, indent=2))
    
    # 开始爬取（注意：需要有效的cookie才能成功）
    # success = crawler.start_crawling()
    # if success:
    #     print("爬取完成!")
    # else:
    #     print("爬取失败!")


if __name__ == "__main__":
    # 运行快速开始示例
    quick_start_example()
    
    # 或者从命令行参数运行
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        crawler = WeiboSpiderMain(config_path=config_path)
        crawler.start_crawling()
