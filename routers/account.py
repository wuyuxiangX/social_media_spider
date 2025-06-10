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

# 数据模型定义
class AccountInfo(BaseModel):
    username: str  # 用户名
    account: str   # 账号
    password: str  # 密码
    mind_id: str   # Mind ID
    token: str     # 认证token
    platform: Optional[str] = "mindverse"  # 平台名称
    description: Optional[str] = ""  # 账号描述
    created_at: Optional[str] = None  # 创建时间
    updated_at: Optional[str] = None  # 更新时间

class AccountCreateRequest(BaseModel):
    username: str
    account: str
    password: str
    mind_id: str
    token: str
    platform: Optional[str] = "mindverse"
    description: Optional[str] = ""

class AccountUpdateRequest(BaseModel):
    account: Optional[str] = None
    password: Optional[str] = None
    mind_id: Optional[str] = None
    token: Optional[str] = None
    platform: Optional[str] = None
    description: Optional[str] = None

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
    
    Args:
        request: 账号创建请求参数
    
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
            platform=request.platform,
            description=request.description,
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
    
    Args:
        username: 用户名
        request: 更新请求参数
    
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


@account_router.get("/search", response_model=AccountListResponse)
async def search_accounts(
    keyword: Optional[str] = None,
    platform: Optional[str] = None
):
    """
    搜索账号信息
    
    Args:
        keyword: 搜索关键词（在用户名、账号、描述中搜索）
        platform: 平台筛选
    
    Returns:
        AccountListResponse: 搜索结果
    """
    try:
        accounts = _load_accounts()
        account_list = list(accounts.values())
        
        # 根据关键词筛选
        if keyword:
            keyword = keyword.lower()
            account_list = [
                account for account in account_list
                if keyword in account.username.lower() 
                or keyword in account.account.lower()
                or keyword in account.description.lower()
            ]
        
        # 根据平台筛选
        if platform:
            account_list = [
                account for account in account_list
                if account.platform == platform
            ]
        
        return AccountListResponse(
            success=True,
            message=f"搜索完成，找到 {len(account_list)} 个匹配账号",
            data=account_list,
            total=len(account_list)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索账号失败: {str(e)}")