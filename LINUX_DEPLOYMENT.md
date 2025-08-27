# Linux Ray集群部署指南

## 🐧 将分布式文件传输系统整合到Linux Ray集群

### 1. 系统要求

#### 环境要求
- Linux系统 (Ubuntu 18.04+ / CentOS 7+ / RHEL 7+)
- Python 3.8+ (建议3.10+)
- 已运行的Ray集群
- 网络连通性 (UDP端口范围：9000-9999)

#### 依赖包
```bash
# 核心依赖
pip install ray==2.48.0 fastapi==0.116.1 uvicorn[standard] pydantic requests websockets

# 可选依赖
pip install psutil aiofiles python-multipart
```

### 2. 文件部署

#### 2.1 创建项目目录
```bash
# 在Ray集群的工作节点上创建项目目录
mkdir -p /opt/castray-system
cd /opt/castray-system

# 创建必要的子目录
mkdir -p {downloads,demo_files,static,logs}
chmod 755 downloads demo_files static logs
```

#### 2.2 上传项目文件
将以下文件上传到Linux系统：
```
/opt/castray-system/
├── main.py                 # FastAPI Web服务器
├── ray_casting.py          # Ray节点管理
├── file_transfer.py        # 文件传输协议
├── models.py              # 数据模型
├── config.json            # 配置文件
├── requirements.txt       # 依赖清单
├── deploy_scripts/        # 部署脚本
│   ├── install.sh
│   ├── start_service.sh
│   └── systemd_service.conf
└── logs/                  # 日志目录
```

### 3. 配置文件调整

#### 3.1 创建Linux配置文件
```bash
cat > /opt/castray-system/config_linux.json << 'EOF'
{
    "ray_cluster": {
        "address": "auto",
        "namespace": "castray",
        "runtime_env": {
            "working_dir": "/opt/castray-system"
        }
    },
    "web_server": {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info"
    },
    "file_transfer": {
        "chunk_size": 65536,
        "max_file_size": "1GB",
        "timeout": 300,
        "download_dir": "/opt/castray-system/downloads"
    },
    "networking": {
        "udp_port_range": [9000, 9999],
        "multicast_group": "224.1.1.1",
        "multicast_port": 9999
    },
    "logging": {
        "level": "INFO",
        "file": "/opt/castray-system/logs/castray.log",
        "max_size": "100MB",
        "backup_count": 5
    }
}
EOF
```

#### 3.2 修改main.py以支持Linux配置
需要更新main.py以读取Linux配置：

```python
# 在main.py开头添加配置加载
import json
import platform
from pathlib import Path

# 加载配置
def load_config():
    if platform.system() == "Linux":
        config_file = Path("/opt/castray-system/config_linux.json")
    else:
        config_file = Path("config.json")
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

config = load_config()
```

### 4. 连接到已有Ray集群

#### 4.1 自动发现Ray集群
```python
# 在ray_casting.py中修改连接逻辑
import ray
import os

async def connect_to_existing_cluster():
    """连接到已有的Ray集群"""
    try:
        # 方法1: 使用环境变量
        ray_address = os.environ.get('RAY_ADDRESS')
        if ray_address:
            ray.init(address=ray_address)
            logger.info(f"已连接到Ray集群: {ray_address}")
            return True
        
        # 方法2: 自动发现本地集群
        ray.init(address='auto')
        logger.info("已连接到本地Ray集群")
        return True
        
    except Exception as e:
        logger.error(f"连接Ray集群失败: {e}")
        return False
```

#### 4.2 设置Ray运行时环境
```python
# 配置Ray运行时环境
runtime_env = {
    "working_dir": "/opt/castray-system",
    "pip": [
        "fastapi==0.116.1",
        "uvicorn[standard]",
        "pydantic",
        "requests"
    ],
    "env_vars": {
        "PYTHONPATH": "/opt/castray-system",
        "CASTRAY_CONFIG": "/opt/castray-system/config_linux.json"
    }
}

ray.init(
    address=ray_address,
    runtime_env=runtime_env,
    namespace="castray"
)
```

### 5. 部署脚本

#### 5.1 安装脚本 (install.sh)
```bash
#!/bin/bash

cat > /opt/castray-system/deploy_scripts/install.sh << 'EOF'
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

echo "✅ CastRay系统安装完成"
echo "💡 使用以下命令启动服务:"
echo "   systemctl start castray"
echo "   systemctl status castray"
EOF

chmod +x /opt/castray-system/deploy_scripts/install.sh
```

#### 5.2 启动脚本 (start_service.sh)
```bash
cat > /opt/castray-system/deploy_scripts/start_service.sh << 'EOF'
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
    exit 1
fi

echo "✅ Ray集群连接正常"

# 启动CastRay服务
echo "🚀 启动CastRay文件传输系统..."
exec python3 main.py
EOF

chmod +x /opt/castray-system/deploy_scripts/start_service.sh
```

#### 5.3 systemd服务配置
```bash
cat > /opt/castray-system/deploy_scripts/systemd_service.conf << 'EOF'
[Unit]
Description=CastRay Distributed File Transfer System
After=network.target
Requires=network.target

[Service]
Type=simple
User=castray
Group=castray
WorkingDirectory=/opt/castray-system
ExecStart=/opt/castray-system/deploy_scripts/start_service.sh
Restart=always
RestartSec=10
Environment=RAY_ADDRESS=auto
Environment=PYTHONPATH=/opt/castray-system
Environment=CASTRAY_CONFIG=/opt/castray-system/config_linux.json

# 日志配置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=castray

# 安全配置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/castray-system

[Install]
WantedBy=multi-user.target
EOF
```

### 6. 网络配置

#### 6.1 防火墙配置
```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp comment "CastRay Web Interface"
sudo ufw allow 9000:9999/udp comment "CastRay File Transfer"

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=9000-9999/udp
sudo firewall-cmd --reload
```

#### 6.2 SELinux配置 (CentOS/RHEL)
```bash
# 如果启用了SELinux
sudo setsebool -P httpd_can_network_connect 1
sudo semanage port -a -t http_port_t -p tcp 8000 2>/dev/null || true
```

### 7. 部署流程

#### 7.1 准备工作
```bash
# 1. 确保Ray集群运行
ray status

# 2. 设置环境变量
export RAY_ADDRESS=$(ray status | grep "Ray runtime started" -A 1 | tail -1 | awk '{print $NF}')
echo "Ray集群地址: $RAY_ADDRESS"
```

#### 7.2 执行部署
```bash
# 1. 创建项目目录
sudo mkdir -p /opt/castray-system
cd /opt/castray-system

# 2. 上传文件 (使用scp或其他方式)
# scp -r ./CastRay/* user@linux-server:/opt/castray-system/

# 3. 运行安装脚本
sudo ./deploy_scripts/install.sh

# 4. 启动服务
sudo systemctl start castray
sudo systemctl status castray
```

### 8. 验证部署

#### 8.1 检查服务状态
```bash
# 检查系统服务
systemctl status castray

# 检查日志
journalctl -u castray -f

# 检查进程
ps aux | grep python3.*main.py

# 检查端口
netstat -tulpn | grep :8000
```

#### 8.2 测试功能
```bash
# 测试Web接口
curl http://localhost:8000/api/status

# 测试节点创建
curl -X POST http://localhost:8000/api/nodes \
  -H "Content-Type: application/json" \
  -d '{"node_id": "test_node", "port": 9001}'

# 查看Ray集群中的CastRay actors
ray list actors --filter="class_name=CastingNode"
```

### 9. 监控和维护

#### 9.1 日志监控
```bash
# 查看应用日志
tail -f /opt/castray-system/logs/castray.log

# 查看系统日志
journalctl -u castray -f

# 日志轮转配置
cat > /etc/logrotate.d/castray << 'EOF'
/opt/castray-system/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 castray castray
    postrotate
        systemctl reload castray
    endscript
}
EOF
```

#### 9.2 性能监控
```bash
# 监控脚本
cat > /opt/castray-system/monitor.sh << 'EOF'
#!/bin/bash
echo "=== CastRay系统状态 ==="
echo "服务状态: $(systemctl is-active castray)"
echo "Ray集群: $(ray status --address=auto 2>/dev/null | grep -o 'ALIVE\|DEAD' | head -1)"
echo "Web接口: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/status)"
echo "活跃节点: $(curl -s http://localhost:8000/api/status | jq -r '.active_nodes // "N/A"')"
echo "文件传输: $(curl -s http://localhost:8000/api/file-transfers/status | jq -r 'length')"
EOF

chmod +x /opt/castray-system/monitor.sh
```

### 10. 高可用性配置

#### 10.1 负载均衡配置 (Nginx)
```nginx
upstream castray_backend {
    server 192.168.1.10:8000;
    server 192.168.1.11:8000;
    server 192.168.1.12:8000;
}

server {
    listen 80;
    server_name castray.yourdomain.com;
    
    location / {
        proxy_pass http://castray_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /ws {
        proxy_pass http://castray_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### 11. 故障排除

#### 常见问题及解决方案

1. **Ray连接失败**
   ```bash
   # 检查Ray状态
   ray status
   
   # 重启Ray集群
   ray stop
   ray start --head --dashboard-host=0.0.0.0
   ```

2. **端口占用**
   ```bash
   # 查找占用8000端口的进程
   sudo lsof -i :8000
   
   # 修改配置使用其他端口
   sed -i 's/"port": 8000/"port": 8080/' /opt/castray-system/config_linux.json
   ```

3. **权限问题**
   ```bash
   # 修复文件权限
   sudo chown -R castray:castray /opt/castray-system
   sudo chmod -R 755 /opt/castray-system
   ```

### 12. 扩展配置

#### 多Ray集群支持
如果需要支持多个Ray集群，可以修改配置：

```json
{
    "ray_clusters": [
        {
            "name": "cluster1",
            "address": "ray://192.168.1.10:10001",
            "namespace": "castray-cluster1"
        },
        {
            "name": "cluster2", 
            "address": "ray://192.168.1.20:10001",
            "namespace": "castray-cluster2"
        }
    ]
}
```

## 🎯 快速部署总结

```bash
# 1. 准备环境
sudo mkdir -p /opt/castray-system && cd /opt/castray-system

# 2. 上传文件到Linux服务器

# 3. 执行一键部署
sudo ./deploy_scripts/install.sh

# 4. 启动服务
sudo systemctl start castray

# 5. 验证部署
curl http://localhost:8000/api/status

# 6. 访问Web界面
# http://your-server-ip:8000
```

部署完成后，您的CastRay系统将作为Ray集群的一部分运行，提供强大的分布式文件传输能力！
