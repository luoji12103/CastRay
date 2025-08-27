# 🐧 整合到已有Linux Ray集群的完整指南

## 概述

本指南将帮助您将CastRay分布式文件传输系统完整整合到已有的Linux Ray集群中，实现生产级的分布式文件传输功能。

## 🎯 整合目标

- ✅ 连接到已有的Ray集群（而非创建新集群）
- ✅ Ray节点可自主发起文件传输
- ✅ Web界面提供监控功能
- ✅ 支持大文件分块传输
- ✅ 提供完整性验证

## 📋 前提条件

### 系统要求
- Linux操作系统 (Ubuntu 18.04+, CentOS 7+, RHEL 7+)
- Python 3.8+ 
- 已运行的Ray集群
- 网络连通性（UDP端口9000-9999）

### 已有Ray集群状态检查
```bash
# 检查Ray集群状态
ray status

# 查看集群资源
ray status --format=table

# 获取集群地址
ray status | grep "Ray runtime started"
```

## 🚀 一键快速部署

### 方式1: 使用快速部署脚本（推荐）

```bash
# 1. 下载项目文件到Linux服务器
scp -r ./CastRay user@linux-server:/tmp/

# 2. 登录Linux服务器
ssh user@linux-server

# 3. 运行一键部署脚本
cd /tmp/CastRay
chmod +x deploy_scripts/quick_deploy.sh

# 安装到系统目录 (需要root权限)
sudo ./deploy_scripts/quick_deploy.sh --install --ray-address auto

# 或者在当前目录运行 (不需要root权限)
./deploy_scripts/quick_deploy.sh --ray-address auto
```

### 方式2: Docker容器部署

```bash
# 1. 设置环境变量
export RAY_ADDRESS=$(ray status | grep -oP 'address=\\K[^,]+' | head -1)

# 2. 使用Docker Compose启动
docker-compose up -d

# 3. 检查状态
docker-compose ps
docker-compose logs castray
```

## 🔧 手动部署步骤

### 步骤1: 准备环境

```bash
# 创建项目目录
sudo mkdir -p /opt/castray-system
cd /opt/castray-system

# 上传项目文件
# 使用scp, rsync或其他方式上传所有项目文件

# 安装系统依赖
sudo apt-get update && sudo apt-get install -y python3-pip python3-dev gcc g++ curl

# 安装Python依赖
pip3 install -r requirements.txt
```

### 步骤2: 配置连接

```bash
# 获取Ray集群地址
RAY_ADDRESS=$(ray status | grep -oP 'address=\\K[^,]+' | head -1)
echo "Ray集群地址: $RAY_ADDRESS"

# 设置环境变量
export RAY_ADDRESS=$RAY_ADDRESS
export PYTHONPATH=/opt/castray-system
export CASTRAY_CONFIG=/opt/castray-system/config_linux.json
```

### 步骤3: 修改配置文件

编辑 `config_linux.json`:

```json
{
    "ray_cluster": {
        "address": "auto",
        "namespace": "castray",
        "create_demo_nodes": false,
        "runtime_env": {
            "working_dir": "/opt/castray-system"
        }
    },
    "web_server": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "file_transfer": {
        "download_dir": "/opt/castray-system/downloads"
    }
}
```

### 步骤4: 启动服务

```bash
# 直接启动
python3 main.py

# 或作为后台服务启动
nohup python3 main.py > logs/castray.log 2>&1 &
```

## 🔧 systemd服务配置

### 创建系统服务

```bash
# 1. 创建系统用户
sudo useradd -r -d /opt/castray-system -s /bin/bash castray

# 2. 设置权限
sudo chown -R castray:castray /opt/castray-system

# 3. 创建systemd服务文件
sudo tee /etc/systemd/system/castray.service << 'EOF'
[Unit]
Description=CastRay Distributed File Transfer System
After=network.target
Requires=network.target

[Service]
Type=simple
User=castray
Group=castray
WorkingDirectory=/opt/castray-system
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=RAY_ADDRESS=auto
Environment=PYTHONPATH=/opt/castray-system
Environment=CASTRAY_CONFIG=/opt/castray-system/config_linux.json

[Install]
WantedBy=multi-user.target
EOF

# 4. 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable castray
sudo systemctl start castray

# 5. 检查状态
sudo systemctl status castray
```

## 🔍 验证整合结果

### 检查Ray集群连接

```bash
# 查看Ray集群中的CastRay actors
ray list actors --filter="class_name=CastingNode"

# 检查命名空间
ray list actors --namespace=castray
```

### 测试Web接口

```bash
# 测试API接口
curl http://localhost:8000/api/status

# 检查文件传输状态
curl http://localhost:8000/api/file-transfers/status
```

### 测试节点创建和文件传输

```bash
# 创建测试节点
curl -X POST http://localhost:8000/api/nodes \\
  -H "Content-Type: application/json" \\
  -d '{"node_id": "test_node_1", "port": 9001}'

curl -X POST http://localhost:8000/api/nodes \\
  -H "Content-Type: application/json" \\
  -d '{"node_id": "test_node_2", "port": 9002}'

# 触发手动文件传输
curl -X POST http://localhost:8000/api/file-transfers/manual \\
  -H "Content-Type: application/json" \\
  -d '{
    "sender_id": "test_node_1",
    "file_name": "demo_files/data.txt",
    "recipients": ["test_node_2"]
  }'
```

## 📊 监控和管理

### Web界面访问

```bash
# 获取服务器IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Web界面访问: http://$SERVER_IP:8000"
```

### 日志监控

```bash
# systemd服务日志
journalctl -u castray -f

# 应用日志
tail -f /opt/castray-system/logs/castray.log

# Ray集群日志
ray logs
```

### 性能监控

```bash
# 查看Ray dashboard
ray dashboard

# 监控系统资源
htop
iotop
netstat -tulpn | grep :8000
```

## 🔧 高级配置

### 多Ray集群支持

如果需要连接多个Ray集群，可以配置：

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

### 负载均衡配置

使用Nginx进行负载均衡：

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
    }
    
    location /ws {
        proxy_pass http://castray_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 🐛 故障排除

### 常见问题

1. **Ray连接失败**
   ```bash
   # 检查Ray状态
   ray status
   
   # 检查网络连接
   telnet ray-head-node 10001
   
   # 重启Ray集群
   ray stop && ray start --head
   ```

2. **端口冲突**
   ```bash
   # 查看端口占用
   sudo lsof -i :8000
   
   # 修改配置文件端口
   sed -i 's/"port": 8000/"port": 8080/' config_linux.json
   ```

3. **权限问题**
   ```bash
   # 修复文件权限
   sudo chown -R castray:castray /opt/castray-system
   sudo chmod -R 755 /opt/castray-system
   ```

4. **Python依赖问题**
   ```bash
   # 重新安装依赖
   pip3 install --force-reinstall -r requirements.txt
   
   # 检查Ray版本
   python3 -c "import ray; print(ray.__version__)"
   ```

### 调试模式

```bash
# 开启详细日志
export RAY_LOG_LEVEL=DEBUG
export CASTRAY_LOG_LEVEL=DEBUG

# 启动服务
python3 main.py
```

## 📈 性能优化

### Ray集群优化

```bash
# 设置Ray内存限制
export RAY_OBJECT_STORE_MEMORY=2000000000

# 优化网络设置
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
export RAY_SCHEDULER_EVENTS=0
```

### 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# 优化网络参数
echo "net.core.rmem_max = 134217728" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max = 134217728" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

## 🎉 完成！

您的CastRay分布式文件传输系统现在已经成功整合到Linux Ray集群中！

### 验证清单

- ✅ Ray集群连接正常
- ✅ Web界面可访问
- ✅ 节点创建成功
- ✅ 文件传输功能正常
- ✅ 监控数据实时更新
- ✅ 系统服务稳定运行

### 下一步

1. 根据实际需求创建更多Ray节点
2. 配置自动文件传输规则
3. 设置监控告警
4. 扩展到更多Linux服务器

享受强大的分布式文件传输能力！🚀
