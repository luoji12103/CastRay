# 分布式文件传输系统

基于Ray集群的生产级分布式文件传输平台，支持单播、组播、广播传输模式，提供Web界面监控和Ray节点自主传输功能。

## 🚀 功能特性

- **Ray节点自主传输**
  - 🎯 节点主动发起文件传输
  - 📁 大文件分块传输支持
  - ✅ MD5完整性验证
  - 🔄 自动传输调度

- **多种传输模式**
  - 🎯 单播 (Unicast): 点对点文件传输
  - 📡 组播 (Multicast): 组内文件传输  
  - 📢 广播 (Broadcast): 全网文件传输

- **生产级特性**
  - ⚡ 基于Ray分布式计算框架
  - 🔄 异步文件处理
  - 📊 实时传输监控
  - 🌐 Web界面监控 (仅监控不控制)
  - � Linux集群集成支持

- **易用性**
  - 🖥️ 直观的Web监控界面
  - 📱 响应式设计
  - 🔔 实时传输通知
  - 📈 传输性能监控面板

## 📦 安装依赖

### Windows开发环境
```bash
pip install -r requirements.txt
```

### Linux生产环境
```bash
# 系统依赖 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev gcc g++ curl

# Python依赖
pip3 install -r requirements.txt
```

## 🏃‍♂️ 快速开始

### Windows开发模式
```bash
python main.py
```

### Linux生产模式

#### 方式1: 一键部署脚本
```bash
# 下载并运行部署脚本
chmod +x deploy_scripts/quick_deploy.sh
sudo ./deploy_scripts/quick_deploy.sh --install
```

#### 方式2: 手动部署到已有Ray集群
```bash
# 1. 确保Ray集群运行
ray status

# 2. 设置环境变量
export RAY_ADDRESS=auto  # 或指定Ray集群地址
export CASTRAY_CONFIG=/path/to/config_linux.json

# 3. 启动系统
python3 main.py
```

#### 方式3: Docker部署
```bash
# 连接到已有Ray集群
export RAY_ADDRESS=ray://head-node:10001
docker-compose up -d
```

## 🐧 Linux集群集成

详细的Linux部署文档请参考: [LINUX_DEPLOYMENT.md](LINUX_DEPLOYMENT.md)

### 连接到已有Ray集群

#### 自动发现
```bash
export RAY_ADDRESS=auto
python3 main.py
```

#### 指定集群地址
```bash
export RAY_ADDRESS=ray://head-node:10001
python3 main.py
```

#### 配置文件方式
```json
{
    "ray_cluster": {
        "address": "ray://head-node:10001",
        "namespace": "castray",
        "create_demo_nodes": false
    }
}
```

## 🧪 测试系统

### 基本功能测试
```bash
python test_system.py
```

## 🔧 配置选项

### 命令行参数
- `--host`: 服务器主机地址 (默认: 0.0.0.0)
- `--port`: 服务器端口 (默认: 8000)  
- `--workers`: 工作进程数 (默认: 4)
- `--dev`: 开发模式，启用自动重载

### 环境变量
- `RAY_ADDRESS`: Ray集群地址
- `LOG_LEVEL`: 日志级别

## 📖 使用说明

### 1. 启动系统
```bash
python start_production.py
```

### 2. 访问Web界面
打开浏览器访问: http://localhost:8000

### 3. 创建节点
在"节点管理"面板中创建新的消息节点

### 4. 发送消息
选择传输类型、发送节点和消息内容，点击发送

### 5. 监控状态
实时查看系统状态和消息传输情况

## 🏗️ 架构设计

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   FastAPI       │    │   Ray Cluster   │
│                 │    │   Backend       │    │                 │
│  - 消息发送界面  │◄──►│  - REST API     │◄──►│  - CastingNode  │
│  - 状态监控面板  │    │  - WebSocket    │    │  - 消息处理     │
│  - 节点管理     │    │  - 文件上传     │    │  - 分布式计算   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 核心组件

#### CastingNode (Ray远程类)
- 处理单个节点的消息收发
- 支持UDP单播、组播、广播
- 维护消息历史记录

#### CastingCluster (集群管理器) 
- 管理所有节点生命周期
- 协调消息传输
- 提供集群状态监控

#### FastAPI Backend
- RESTful API接口
- WebSocket实时通信
- 文件上传处理

#### Web Frontend
- React风格的响应式界面
- 实时状态更新
- 多功能操作面板

## 📊 API接口

### 节点管理
- `POST /api/nodes` - 创建节点
- `DELETE /api/nodes/{node_id}` - 删除节点  
- `GET /api/nodes/{node_id}/messages` - 获取节点消息

### 消息传输
- `POST /api/send` - 发送消息
- `POST /api/upload` - 上传文件

### 系统监控  
- `GET /api/status` - 获取系统状态
- `WebSocket /ws` - 实时状态推送

## 🔒 生产部署

### Docker部署
```dockerfile
FROM python:3.9
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "start_production.py"]
```

### Kubernetes部署
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cast-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cast-system
  template:
    metadata:
      labels:
        app: cast-system
    spec:
      containers:
      - name: cast-system
        image: cast-system:latest
        ports:
        - containerPort: 8000
```

## 🛠️ 扩展开发

### 自定义消息类型
```python
class CustomMessage(CastMessage):
    custom_field: str
    
# 在ray_casting.py中扩展处理逻辑
```

### 添加新的传输协议
```python
@ray.remote
class CustomCastingNode(CastingNode):
    async def send_custom_protocol(self, message, target):
        # 实现自定义协议
        pass
```

## 📈 性能优化

### Ray集群配置
```python
ray.init(
    num_cpus=8,
    num_gpus=1, 
    object_store_memory=2000000000
)
```

### 消息批处理
```python
# 批量发送消息以提高性能
async def send_batch_messages(messages):
    tasks = [cluster.send_message(msg) for msg in messages]
    return await asyncio.gather(*tasks)
```

## 🐛 故障排除

### 常见问题

1. **Ray集群启动失败**
   ```bash
   ray stop  # 停止现有集群
   ray start --head  # 重新启动
   ```

2. **端口占用**
   ```bash
   netstat -ano | findstr :8000  # Windows
   lsof -i :8000  # Linux/Mac
   ```

3. **内存不足**
   ```python
   # 减少Ray object store内存
   ray.init(object_store_memory=1000000000)
   ```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

- 项目地址: https://github.com/your-repo/cast-ray
- 文档地址: https://your-docs.com
- 问题反馈: https://github.com/your-repo/cast-ray/issues
