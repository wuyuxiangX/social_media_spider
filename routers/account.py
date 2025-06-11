'''
Author       : wyx-hhhh
Date         : 2025-06-10
LastEditTime : 2025-06-10
Description  : 账号管理API路由模块
'''
import os
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

# 创建账号管理路由器
account_router = APIRouter(
    prefix="/account",
    tags=["account"],
    responses={404: {"description": "Not found"}}
)

# 账号存储文件路径
ACCOUNTS_FILE = "/Users/wyx/code/Mindverse/spider/storage/accounts.json"

# 平台特有信息模型（简化版，只保留关键信息）
class PlatformInfo(BaseModel):
    """平台特有信息基类"""
    pass

class BilibiliInfo(PlatformInfo):
    """Bilibili平台特有信息"""
    uid: Optional[str] = None  # 用户UID

class JikeInfo(PlatformInfo):
    """即刻平台特有信息"""
    username: Optional[str] = None  # 即刻用户名

class WeiboInfo(PlatformInfo):
    """微博平台特有信息"""
    user_id: Optional[str] = None  # 微博用户ID

# 数据模型定义
class AccountInfo(BaseModel):
    username: str  # 用户名
    account: str   # 账号
    password: str  # 密码
    mind_id: str   # Mind ID
    token: str     # 认证token
    description: Optional[str] = ""  # 账号描述
    platform_info: Optional[Dict[str, Any]] = None  # 平台特有信息
    created_at: Optional[str] = None  # 创建时间
    updated_at: Optional[str] = None  # 更新时间

    class Config:
        json_schema_extra = {
            "example": {
                "username": "张雪峰老师",
                "account": "zhangxuefeng@example.com",
                "password": "password123",
                "mind_id": "mind_123456",
                "token": "token_abc123",
                "description": "教育博主",
                "platform_info": {
                    "bilibili": {
                        "uid": "123456789"
                    },
                    "jike": {
                        "username": "zhangxuefeng"
                    },
                    "weibo": {
                        "user_id": "1234567890"
                    }
                }
            }
        }

class AccountCreateRequest(BaseModel):
    username: str
    account: str
    password: str
    mind_id: str
    token: str
    description: Optional[str] = ""
    platform_info: Optional[Dict[str, Any]] = None  # 平台特有信息

    class Config:
        json_schema_extra = {
            "example": {
                "username": "张雪峰老师",
                "account": "zhangxuefeng@example.com",
                "password": "password123",
                "mind_id": "mind_123456",
                "token": "token_abc123",
                "description": "教育博主",
                "platform_info": {
                    "bilibili": {
                        "uid": "123456789"
                    },
                    "jike": {
                        "username": "zhangxuefeng"
                    },
                    "weibo": {
                        "user_id": "1234567890"
                    }
                }
            }
        }

class AccountUpdateRequest(BaseModel):
    account: Optional[str] = None
    password: Optional[str] = None
    mind_id: Optional[str] = None
    token: Optional[str] = None
    description: Optional[str] = None
    platform_info: Optional[Dict[str, Any]] = None  # 平台特有信息

    class Config:
        json_schema_extra = {
            "example": {
                "platform_info": {
                    "bilibili": {
                        "uid": "123456789"
                    }
                }
            }
        }

class AccountResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class AccountListResponse(BaseModel):
    success: bool
    message: str
    data: List[AccountInfo]
    total: int


def _load_accounts() -> Dict[str, AccountInfo]:
    """加载账号信息"""
    if not os.path.exists(ACCOUNTS_FILE):
        # 创建存储目录
        os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
        return {}
    
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            accounts_data = json.load(f)
            return {username: AccountInfo(**data) for username, data in accounts_data.items()}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_accounts(accounts: Dict[str, AccountInfo]) -> None:
    """保存账号信息"""
    # 确保存储目录存在
    os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
    
    # 转换为可序列化的字典
    accounts_data = {
        username: account.model_dump() for username, account in accounts.items()
    }
    
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts_data, f, ensure_ascii=False, indent=2)


@account_router.post("/create", response_model=AccountResponse)
async def create_account(request: AccountCreateRequest):
    """
    创建新账号信息
    
    支持的平台及其特有信息：
    - bilibili: uid(用户UID), bv_number(BV号), space_url(个人空间URL), nickname(昵称)
    - jike: jike_username(即刻用户名), user_id(用户ID), nickname(昵称), profile_url(个人主页URL)  
    - weibo: user_id(微博用户ID), weibo_name(微博昵称), profile_url(个人主页URL), followers_count(粉丝数), following_count(关注数)
    
    Args:
        request: 账号创建请求参数，包含平台特有信息
    
    Returns:
        AccountResponse: 创建结果
    """
    try:
        # 加载现有账号
        accounts = _load_accounts()
        
        # 检查用户名是否已存在
        if request.username in accounts:
            raise HTTPException(status_code=400, detail=f"用户名 '{request.username}' 已存在")
        
        # 创建新账号信息
        current_time = datetime.now().isoformat()
        new_account = AccountInfo(
            username=request.username,
            account=request.account,
            password=request.password,
            mind_id=request.mind_id,
            token=request.token,
            description=request.description,
            platform_info=request.platform_info,
            created_at=current_time,
            updated_at=current_time
        )
        
        # 保存账号
        accounts[request.username] = new_account
        _save_accounts(accounts)
        
        return AccountResponse(
            success=True,
            message=f"账号 '{request.username}' 创建成功",
            data=new_account.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建账号失败: {str(e)}")


@account_router.get("/get/{username}", response_model=AccountResponse)
async def get_account(username: str):
    """
    通过用户名获取账号信息
    
    Args:
        username: 用户名
    
    Returns:
        AccountResponse: 账号信息
    """
    try:
        accounts = _load_accounts()
        
        if username not in accounts:
            raise HTTPException(status_code=404, detail=f"用户名 '{username}' 不存在")
        
        account = accounts[username]
        return AccountResponse(
            success=True,
            message=f"获取账号 '{username}' 信息成功",
            data=account.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取账号信息失败: {str(e)}")


@account_router.put("/update/{username}", response_model=AccountResponse)
async def update_account(username: str, request: AccountUpdateRequest):
    """
    更新账号信息
    
    支持更新平台特有信息：
    - bilibili: uid, bv_number, space_url, nickname
    - jike: jike_username, user_id, nickname, profile_url  
    - weibo: user_id, weibo_name, profile_url, followers_count, following_count
    
    Args:
        username: 用户名
        request: 更新请求参数，可包含平台特有信息更新
    
    Returns:
        AccountResponse: 更新结果
    """
    try:
        accounts = _load_accounts()
        
        if username not in accounts:
            raise HTTPException(status_code=404, detail=f"用户名 '{username}' 不存在")
        
        account = accounts[username]
        
        # 更新非空字段
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field == 'platform_info' and account.platform_info:
                    # 对于平台信息，进行深度合并而不是直接替换
                    existing_platform_info = account.platform_info.copy()
                    for platform, info in value.items():
                        if platform in existing_platform_info:
                            existing_platform_info[platform].update(info)
                        else:
                            existing_platform_info[platform] = info
                    setattr(account, field, existing_platform_info)
                else:
                    setattr(account, field, value)
        
        # 更新时间戳
        account.updated_at = datetime.now().isoformat()
        
        # 保存更新
        accounts[username] = account
        _save_accounts(accounts)
        
        return AccountResponse(
            success=True,
            message=f"账号 '{username}' 更新成功",
            data=account.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新账号失败: {str(e)}")


@account_router.delete("/delete/{username}", response_model=AccountResponse)
async def delete_account(username: str):
    """
    删除账号信息
    
    Args:
        username: 用户名
    
    Returns:
        AccountResponse: 删除结果
    """
    try:
        accounts = _load_accounts()
        
        if username not in accounts:
            raise HTTPException(status_code=404, detail=f"用户名 '{username}' 不存在")
        
        # 删除账号
        deleted_account = accounts.pop(username)
        _save_accounts(accounts)
        
        return AccountResponse(
            success=True,
            message=f"账号 '{username}' 删除成功",
            data=deleted_account.model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除账号失败: {str(e)}")


@account_router.get("/list", response_model=AccountListResponse)
async def list_accounts():
    """
    获取所有账号列表
    
    Returns:
        AccountListResponse: 账号列表
    """
    try:
        accounts = _load_accounts()
        account_list = list(accounts.values())
        
        return AccountListResponse(
            success=True,
            message=f"获取账号列表成功，共 {len(account_list)} 个账号",
            data=account_list,
            total=len(account_list)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取账号列表失败: {str(e)}")