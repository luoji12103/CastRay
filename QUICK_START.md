# CastRay 外部集群功能快速入门

## 🚀 5分钟快速开始

### 1️⃣ 环境检查
```bash
# 确保在正确的环境中
conda activate castray

# 检查依赖
python -c "import ray; print('Ray version:', ray.__version__)"
```

### 2️⃣ 启动Ray集群
```bash
# 新开一个终端，启动Ray集群
ray start --head --dashboard-port=8265

# 验证集群状态
ray status
```

### 3️⃣ 启动CastRay服务
```bash
# 在主终端启动CastRay
python main.py
```

### 4️⃣ 发现外部集群
```bash
# 发现并连接外部Ray集群
curl -X POST http://localhost:8000/api/cluster/discover-external
```

### 5️⃣ 查看结果
```bash
# 查看外部节点
curl http://localhost:8000/api/nodes/external

# 查看系统状态（包含外部节点）
curl http://localhost:8000/api/status
```

## 🌐 Web界面访问

打开浏览器访问：`http://localhost:8000/ui`

- 可以看到节点列表中包含外部Ray节点
- 支持通过Web界面发现和管理外部集群
- 实时显示集群连接状态

## 📋 核心API

| API | 功能 |
|-----|------|
| `POST /api/cluster/discover-external` | 自动发现外部集群 |
| `GET /api/cluster/external-info` | 查看外部集群状态 |
| `GET /api/nodes/external` | 获取外部节点列表 |
| `POST /api/cluster/connect-external` | 手动连接集群 |
| `DELETE /api/cluster/disconnect-external` | 断开外部集群 |

## 🧪 测试功能

```bash
# 运行演示脚本
python demo_external_cluster.py

# 运行完整测试
python test_full_external_cluster.py
```

## ❗ 故障排除

**无法发现集群？**
```bash
# 检查Ray是否运行
ray status

# 检查Dashboard是否可访问
curl http://localhost:8265
```

**连接失败？**
```bash
# 检查端口
netstat -an | findstr 8265

# 重新发现
curl -X DELETE http://localhost:8000/api/cluster/disconnect-external
curl -X POST http://localhost:8000/api/cluster/discover-external
```

## 📖 详细文档

完整使用教程请查看：`USAGE_TUTORIAL.md`

---

**🎉 恭喜！您已成功集成外部Ray集群到CastRay系统中！**
