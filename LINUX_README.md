# 🚀 CastRay Linux集群整合

将CastRay分布式文件传输系统整合到已有的Linux Ray集群中。

## 快速开始

### 一键部署 (推荐)

```bash
# 下载到Linux服务器
git clone <项目地址> 或 scp -r ./CastRay user@linux-server:/tmp/

# 登录Linux服务器并运行一键脚本
ssh user@linux-server
cd /path/to/CastRay
chmod +x linux_integration.sh

# 自动检测Ray集群并部署
./linux_integration.sh

# 或指定Ray集群地址
./linux_integration.sh --ray-address ray://head-node:10001

# 安装为系统服务 (需要sudo)
sudo ./linux_integration.sh --systemd
```

### Docker部署

```bash
# 设置Ray集群地址
export RAY_ADDRESS="ray://your-ray-head:10001"

# 启动容器
./linux_integration.sh --docker
```

## 核心功能

✅ **连接已有Ray集群** - 自动发现或手动指定Ray集群地址  
✅ **分布式文件传输** - Ray节点间自主发起文件传输  
✅ **Web监控界面** - 实时监控传输状态和集群信息  
✅ **大文件支持** - 分块传输，MD5校验  
✅ **生产就绪** - systemd服务，Docker支持，完整日志  

## 验证部署

```bash
# 检查Web界面
curl http://localhost:8000/api/status

# 创建测试节点
curl -X POST http://localhost:8000/api/nodes \
  -H "Content-Type: application/json" \
  -d '{"node_id": "test_node", "port": 9001}'

# 查看Ray集群中的CastRay节点
ray list actors --filter="class_name=CastingNode"
```

## 管理服务

### systemd服务

```bash
sudo systemctl start castray     # 启动
sudo systemctl stop castray      # 停止  
sudo systemctl status castray    # 状态
journalctl -u castray -f         # 日志
```

### Docker服务

```bash
docker-compose up -d             # 启动
docker-compose down              # 停止
docker-compose logs -f           # 日志
```

## 文档

- 📖 [完整部署指南](INTEGRATION_GUIDE.md) - 详细的Linux集群整合指南
- 🐳 [Docker部署](docker-compose.yml) - 容器化部署配置  
- ⚙️ [Linux配置](config_linux.json) - Linux环境配置文件
- 🔧 [部署脚本](deploy_scripts/) - 自动化部署工具

## 架构说明

```
Linux Ray集群
├── Ray Head Node (已有)
├── Ray Worker Nodes (已有)  
└── CastRay Integration
    ├── 连接到已有集群
    ├── 创建CastingNode actors
    ├── Web监控服务
    └── 文件传输协议
```

## 故障排除

```bash
# 检查Ray连接
ray status

# 检查服务状态  
curl http://localhost:8000/api/status

# 查看详细日志
tail -f logs/castray.log

# 检查端口占用
sudo lsof -i :8000
```

## 技术栈

- **Ray 2.4+** - 分布式计算框架
- **FastAPI** - Web API框架  
- **WebSocket** - 实时监控通信
- **UDP Socket** - 文件传输协议
- **systemd** - Linux服务管理
- **Docker** - 容器化部署

---

🎯 **目标实现**: Ray节点内由一个节点向某一或某些其他ray节点主动发起文件传输，网页端仅有监控功能 ✅
