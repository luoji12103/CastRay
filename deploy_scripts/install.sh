#!/bin/bash
set -e

echo "🚀 开始部署CastRay文件传输系统到Linux Ray集群"

# 检查是否以root权限运行
if [[ $EUID -ne 0 ]]; then
   echo "❌ 请以root权限运行此脚本"
   exit 1
fi

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python版本过低，需要3.8+，当前版本: $python_version"
    exit 1
fi

echo "✅ Python版本检查通过: $python_version"

# 创建系统用户
if ! id "castray" &>/dev/null; then
    useradd -r -d /opt/castray-system -s /bin/bash castray
    echo "✅ 创建系统用户: castray"
fi

# 设置目录权限
chown -R castray:castray /opt/castray-system
chmod 755 /opt/castray-system
chmod -R 755 /opt/castray-system/deploy_scripts

# 安装Python依赖
echo "📦 安装Python依赖..."
sudo -u castray python3 -m pip install --user -r /opt/castray-system/requirements.txt

# 检查Ray集群连接
echo "🔍 检查Ray集群状态..."
if ray status 2>/dev/null; then
    echo "✅ Ray集群运行正常"
else
    echo "⚠️  未检测到运行中的Ray集群，请确保Ray集群已启动"
fi

# 创建systemd服务
cp /opt/castray-system/deploy_scripts/systemd_service.conf /etc/systemd/system/castray.service
systemctl daemon-reload
systemctl enable castray

# 配置防火墙 (Ubuntu/Debian)
if command -v ufw >/dev/null 2>&1; then
    ufw allow 8000/tcp comment "CastRay Web Interface"
    ufw allow 9000:9999/udp comment "CastRay File Transfer"
fi

# 配置防火墙 (CentOS/RHEL)
if command -v firewall-cmd >/dev/null 2>&1; then
    firewall-cmd --permanent --add-port=8000/tcp
    firewall-cmd --permanent --add-port=9000-9999/udp
    firewall-cmd --reload
fi

echo "✅ CastRay系统安装完成"
echo "💡 使用以下命令启动服务:"
echo "   systemctl start castray"
echo "   systemctl status castray"
echo "   journalctl -u castray -f  # 查看日志"
echo ""
echo "🌐 Web界面访问地址: http://$(hostname -I | awk '{print $1}'):8000"
