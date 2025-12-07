# Database Tools MCP Server

一个示例MCP服务器，提供数据库查询工具。

## 运行

```bash
cd mcp_examples/database_tools
pip install -r requirements.txt
python server.py
```

服务将在 http://localhost:3001 启动。

## 提供的工具

- `query_users`: 查询用户列表
- `query_products`: 查询产品列表
- `get_user_by_id`: 根据ID获取用户

## 集成到ChatBot

在 `backend/config/mcp_servers.json` 中添加:

```json
{
  "servers": [
    {
      "name": "database_tools",
      "url": "http://localhost:3001",
      "description": "数据库查询工具",
      "enabled": true
    }
  ]
}
```
