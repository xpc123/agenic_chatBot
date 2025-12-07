# 🛠️ 脚本工具

本目录包含项目的各种脚本工具。

## 启动脚本

### start.csh - 快速启动

一键启动开发环境（csh/tcsh shell）：

```bash
cd /path/to/agentic_chatBot
source scripts/start.csh
```

功能：
- 自动创建虚拟环境（如不存在）
- 激活虚拟环境
- 检查并安装依赖
- 启动后端服务

### standalone_gui.py - 独立 GUI 模式

无需编码，配置即用的独立模式：

```bash
# 1. 复制配置模板
cp config/config.json.example config.json

# 2. 编辑配置
vi config.json

# 3. 启动
cd scripts
python standalone_gui.py
```

## 验证脚本

### validate_system.py - 系统验证

验证系统配置和依赖是否正确：

```bash
cd scripts
python validate_system.py
```

检查项目：
- 文件结构完整性
- 环境变量配置
- Python 依赖安装
- 服务健康状态

### check_completion.py - 完成度检查

检查项目功能实现完成度：

```bash
cd scripts
python check_completion.py
```

## 使用说明

所有脚本都应在项目根目录或 scripts 目录下运行。

```bash
# 从项目根目录
cd /path/to/agentic_chatBot
source scripts/start.csh

# 或进入 scripts 目录
cd scripts
python validate_system.py
```
