#!/bin/bash

cd /opt/castray-system

# 设置环境变量
export RAY_ADDRESS=${RAY_ADDRESS:-auto}
export PYTHONPATH=/opt/castray-system:$PYTHONPATH
export CASTRAY_CONFIG=/opt/castray-system/config_linux.json

# 检查Ray集群状态
echo "🔍 检查Ray集群连接..."
if ! ray status &>/dev/null; then
    echo "❌ 无法连接到Ray集群，请检查Ray集群状态"
    echo "💡 提示:"
    echo "   - 确保Ray集群已启动: ray start --head"
    echo "   - 检查RAY_ADDRESS环境变量: echo \$RAY_ADDRESS"
    echo "   - 查看Ray状态: ray status"
    exit 1
fi

echo "✅ Ray集群连接正常"

# 启动CastRay服务
echo "🚀 启动CastRay文件传输系统..."
exec python3 main.py
