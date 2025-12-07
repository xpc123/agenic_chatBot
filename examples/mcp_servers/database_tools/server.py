"""
示例MCP Server - 数据库工具
演示如何创建一个MCP服务器供ChatBot调用
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import uvicorn

app = FastAPI(title="Database Tools MCP Server")


# 模拟数据库
fake_db = {
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
    ],
    "products": [
        {"id": 1, "name": "Laptop", "price": 999.99},
        {"id": 2, "name": "Mouse", "price": 29.99},
    ],
}


class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    arguments: Dict[str, Any]


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/tools")
async def list_tools():
    """列出所有工具"""
    return {
        "tools": [
            {
                "name": "query_users",
                "description": "查询用户列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "返回数量限制",
                            "default": 10,
                        }
                    },
                },
            },
            {
                "name": "query_products",
                "description": "查询产品列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "返回数量限制",
                            "default": 10,
                        }
                    },
                },
            },
            {
                "name": "get_user_by_id",
                "description": "根据ID获取用户",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "用户ID",
                        }
                    },
                    "required": ["user_id"],
                },
            },
        ]
    }


@app.post("/tools/query_users/execute")
async def query_users(request: ToolExecuteRequest):
    """查询用户"""
    limit = request.arguments.get("limit", 10)
    users = fake_db["users"][:limit]
    
    return {
        "success": True,
        "result": users,
    }


@app.post("/tools/query_products/execute")
async def query_products(request: ToolExecuteRequest):
    """查询产品"""
    limit = request.arguments.get("limit", 10)
    products = fake_db["products"][:limit]
    
    return {
        "success": True,
        "result": products,
    }


@app.post("/tools/get_user_by_id/execute")
async def get_user_by_id(request: ToolExecuteRequest):
    """根据ID获取用户"""
    user_id = request.arguments.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    user = next(
        (u for u in fake_db["users"] if u["id"] == user_id),
        None
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "result": user,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)
