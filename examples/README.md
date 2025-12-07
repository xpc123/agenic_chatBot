# 📦 示例代码

本目录包含 Agentic ChatBot 的各种集成示例。

## 目录结构

```
examples/
├── sdk_integration_examples.py  # SDK 集成示例
├── desktop_app_integration.py   # 桌面应用集成示例
└── mcp_servers/                 # MCP 服务器示例
    └── database_tools/          # 数据库工具 MCP 服务器
```

## SDK 集成示例

展示如何使用 Python SDK 将 ChatBot 集成到你的应用中：

```python
from chatbot_sdk import ChatBotSDK, ChatBotConfig

# 配置
config = ChatBotConfig(
    app_id="your_app_id",
    app_secret="your_app_secret",
    base_url="http://localhost:8000"
)

# 初始化 SDK
sdk = ChatBotSDK(config)
sdk.initialize()

# 发送消息
response = sdk.chat("你好，请帮我分析一下这个问题")
print(response)
```

详见 [sdk_integration_examples.py](./sdk_integration_examples.py)

## 桌面应用集成

展示如何将 ChatBot 嵌入到 PyQt/Tkinter 桌面应用：

```python
# 详见 desktop_app_integration.py
```

## MCP 服务器示例

### 数据库工具服务器

提供 SQLite 数据库查询能力的 MCP 服务器：

```bash
cd mcp_servers/database_tools
pip install -r requirements.txt
python server.py
```

详见 [mcp_servers/database_tools/README.md](./mcp_servers/database_tools/README.md)

## 运行示例

```bash
# 确保后端服务正在运行
cd ../backend
source activate.csh
python run.py

# 在另一个终端运行示例
cd ../examples
python sdk_integration_examples.py
```
