'''
Author       : wyx-hhhh
Date         : 2025-06-09
LastEditTime : 2025-06-09
Description  : 即刻爬虫，支持token自动刷新
'''
import requests
import json
import os
from typing import Optional, Dict, Any

class JikeSpider:
    def __init__(self):
        # 获取当前文件所在目录，配置文件放在同一目录下
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(current_dir, "jike_config.json")
        self.base_url = "https://api.ruguoapp.com"
        self.refresh_url = f"{self.base_url}/app_auth_tokens.refresh"
        self.data_url = f"{self.base_url}/1.0/personalUpdate/single"
        
        # 默认token，如果配置文件不存在则使用
        self.default_tokens = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjoieGxKdTVnS211K2x1MEtPdGdOMmVsR1ZmMzlrSk5VSDZna1dIQnVuVVFVeng4UDc5WUdLaVwvb3ExRW5Eam1vOHV5SGdXc3cxVFVhUEZvbE03UEVVTVFZTmhWZFF3SWgzVmQ4UEgzNWFwWFUwVVJcL2xYeFNHa25pZVwvbEJcLzc1YTdRd3h4TVAxSkFNNXRaTTVlZ3NTQzkxSStBUW1leU5VZmFoSUNsQkJxMGRDakFtYnBvXC9IVkFVNDFZdjdiTVlwQ24wWThVNFhuQXNMZHZGUFFmWHBKV1ZVb0tQblRaWkFHMG9CNmpEemxcL0RZcnY3ZHh2NWJDNlJmeHpUV0R2YTRDMUh0cjFqcDlxRlhcL05RRU9hU3hFRGFtcFBVWDZNc0pQYTkwZXdGbzNXd2JcL0pKNGUxVWRzcXdvSmp2VlZiNGRPOVlmeWNyNnFCVURlUytRaUlwcmNtODdOYVk2ZUZqdG1wcDlyclQ3akJCTjg9IiwidiI6MywiaXYiOiI1R0FFSWpCa2xRSnJpTytDaUxFcWRRPT0iLCJpYXQiOjE3NDk0NDkzMTUuNDYxfQ.BV1r7ks4TXxBwxf9cya4tPvpuXw2k1ARk2YpcWBFDo4",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjoia2taR0hDbElnVTFGbHpSdFQrRUl1SFg4Uk52YUkxWmJmTlFrVVNcL2JtdXg5eFwvM2Vud3dZdjJkdmtXcExxWmN3Z0lNME1qRTY5a0tPWXpKaE53QUFxa09haDNNMGxZZjdETUlmYXVnbUl1ZnFxSVpvTmxhcnZnbmhkdjZ5TlNrTklcL2ZwWGtmY0ZJdTBEUFwvU1E2Y3UrQjRYSmdSelwvWHJnSFNyc1o3b3lTKzg9IiwidiI6MywiaXYiOiIyZXlPNmk5SUJaeCtYMTRwT1Bkb3hBPT0iLCJpYXQiOjE3NDk0NDkzMTUuNDYxfQ.YHhCO2QyA3bRfMBm7j-WLgG3bukWvMyK4zcvB6XziM8"
        }
        
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        
        # 加载或初始化token配置
        self.load_config()
    
    def load_config(self):
        """加载配置文件中的token"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.access_token = config.get('access_token', self.default_tokens['access_token'])
                    self.refresh_token = config.get('refresh_token', self.default_tokens['refresh_token'])
            else:
                # 如果配置文件不存在，使用默认token并保存
                self.access_token = self.default_tokens['access_token']
                self.refresh_token = self.default_tokens['refresh_token']
                self.save_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认token")
            self.access_token = self.default_tokens['access_token']
            self.refresh_token = self.default_tokens['refresh_token']
    
    def save_config(self):
        """保存token到配置文件"""
        try:
            config = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def refresh_access_token(self) -> bool:
        """刷新access token"""
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "x-jike-refresh-token": self.refresh_token,
            "origin": "https://web.okjike.com"
        }
        
        try:
            # 发送空的JSON对象
            response = requests.post(self.refresh_url, headers=headers, json={})
            response.raise_for_status()
            
            # 从响应头中获取新的token
            new_access_token = response.headers.get('x-jike-access-token')
            new_refresh_token = response.headers.get('x-jike-refresh-token')
            
            if new_access_token and new_refresh_token:
                self.access_token = new_access_token
                self.refresh_token = new_refresh_token
                self.save_config()
                print("Token刷新成功")
                return True
            else:
                print("刷新token失败：响应头中未找到新token")
                return False
                
        except requests.RequestException as e:
            print(f"刷新token请求失败: {e}")
            return False
    
    def get_jike_data(self, username: str = "a2d6acc1-626f-4d15-a22a-849e88a4c9f0", 
                      limit: int = 20, last_id: Optional[str] = None) -> Optional[Dict[Any, Any]]:
        """获取即刻数据，自动处理token过期"""
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "x-jike-access-token": self.access_token,
            "origin": "https://web.okjike.com"
        }

        payload = {
            "limit": limit,
            "username": username
        }
        
        # 如果提供了last_id，添加到loadMoreKey中
        if last_id:
            payload["loadMoreKey"] = {"lastId": last_id}
        
        try:
            response = requests.post(self.data_url, headers=headers, json=payload)
            
            # 如果返回401，尝试刷新token
            if response.status_code == 401:
                print("Access token已过期，尝试刷新...")
                if self.refresh_access_token():
                    # 更新header中的token并重试
                    headers["x-jike-access-token"] = self.access_token
                    response = requests.post(self.data_url, headers=headers, json=payload)
                    
                    # 如果刷新后依然401，说明refresh token也无效
                    if response.status_code == 401:
                        raise Exception("Token已失效，无法刷新。请提供有效的access_token和refresh_token")
                else:
                    raise Exception("Token刷新失败，请提供有效的access_token和refresh_token")
            
            response.raise_for_status()
            data = response.json()
            return data
            
        except requests.RequestException as e:
            print(f"请求失败: {e}")
            return None
    
    def get_last_id_from_response(self, data: Dict[Any, Any]) -> Optional[str]:
        """从响应数据中提取lastId用于下一页请求"""
        try:
            load_more_key = data.get('loadMoreKey', {})
            return load_more_key.get('lastId')
        except Exception as e:
            print(f"提取lastId失败: {e}")
            return None
    
    def get_all_jike_data(self, username: str = "a2d6acc1-626f-4d15-a22a-849e88a4c9f0", 
                         limit: int = 20, max_pages: int = 10) -> list:
        """获取所有页面的即刻数据
        
        Args:
            username: 用户名
            limit: 每页数据量
            max_pages: 最大页数限制，防止无限循环
            
        Returns:
            包含所有页面数据的列表
        """
        all_data = []
        last_id = None
        page = 1
        
        while page <= max_pages:
            print(f"正在获取第{page}页数据...")
            
            try:
                # 获取当前页数据
                data = self.get_jike_data(username=username, limit=limit, last_id=last_id)
                
                if not data:
                    print(f"第{page}页数据获取失败，停止爬取")
                    break
                
                # 检查是否有数据
                data_list = data.get('data', [])
                if not data_list:
                    print(f"第{page}页没有更多数据，爬取完成")
                    break
                
                all_data.extend(data_list)
                print(f"第{page}页获取到 {len(data_list)} 条数据")
                
                # 获取下一页的lastId
                last_id = self.get_last_id_from_response(data)
                if not last_id:
                    print("没有更多页面，爬取完成")
                    break
                
                page += 1
                
            except Exception as e:
                # 如果是token相关错误，直接抛出让上层处理
                if "token" in str(e).lower() or "401" in str(e):
                    raise e
                else:
                    print(f"第{page}页数据获取失败: {e}")
                    break
        
        print(f"总共获取到 {len(all_data)} 条数据")
        return all_data

def main():
    """主函数示例"""
    spider = JikeSpider()
    
    # 示例1：获取单页数据
    # print("=== 获取第一页数据 ===")
    # data = spider.get_jike_data()
    # if data:
    #     print(f"获取第一页数据成功，共 {len(data.get('data', []))} 条")
    #     # 获取lastId用于第二页
    #     last_id = spider.get_last_id_from_response(data)
    #     if last_id:
    #         print(f"第一页lastId: {last_id}")
            
    #         # 示例2：获取第二页数据
    #         print("\n=== 获取第二页数据 ===")
    #         page2_data = spider.get_jike_data(last_id=last_id)
    #         if page2_data:
    #             print(f"获取第二页数据成功，共 {len(page2_data.get('data', []))} 条")
    # else:
    #     print("获取数据失败")
    
    # 示例3：获取所有页面数据（限制3页作为演示）
    print("\n=== 获取所有页面数据 ===")
    all_data = spider.get_all_jike_data(max_pages=3)
    if all_data:
        print(f"总共获取到 {len(all_data)} 条数据")
        # 可以保存到文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(current_dir, 'all_data.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        print(f"数据已保存到 {output_file}")

if __name__ == "__main__":
    main()