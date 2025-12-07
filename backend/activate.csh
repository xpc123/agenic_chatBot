#!/bin/csh
# 激活虚拟环境的便捷脚本 (for csh/tcsh shell)
# 使用方法: source activate.csh

set SCRIPT_DIR=`dirname $0`
cd $SCRIPT_DIR
source venv/bin/activate.csh
echo "✅ 虚拟环境已激活"
echo "Python: `which python`"
echo "Pip: `which pip`"
echo ""
echo "提示: 使用 'deactivate' 退出虚拟环境"
