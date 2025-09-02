# CastRay 外部集群发现功能 - 实用手册

## 📋 功能概述

CastRay 现已支持发现和连接其他进程创建的 Ray 集群，将外部 Ray 节点无缝集成到当前系统中。

## 🎯 核心特性

- ✅ **自动发现**: 扫描本地运行的 Ray 集群
- ✅ **智能连接**: 多种方式连接外部集群  
- ✅ **节点虚拟化**: 外部节点显示为系统节点
- ✅ **实时监控**: WebSocket 实时状态更新
- ✅ **API 完整**: 全套 RESTful 管理接口

## 🚀 使用步骤

### 第一步：准备环境
```bash
# 激活 CastRay 环境
conda activate castray

# 切换到项目目录
cd "d:\MyUser\HKUSTGZ\DOIT\6G Program\CastRay"
```

### 第二步：启动 Ray 集群
在**新终端**中运行：
```bash
ray start --head --dashboard-port=8265
```

验证集群运行：
```bash
ray status
```

### 第三步：启动 CastRay
在**主终端**中运行：
```bash
python main.py
```

等待看到服务启动信息：
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 第四步：发现外部集群
使用 API 发现集群：
```bash
curl -X POST http://localhost:8000/api/cluster/discover-external
```

或运行演示脚本：
```bash
python demo_external_cluster.py
```

## 🔍 验证功能

### 1. 检查外部集群连接状态
```bash
curl http://localhost:8000/api/cluster/external-info
```

期望响应：
```json
{
  "is_connected": true,
  "external_nodes": {...},
  "connected_cluster": "127.0.0.1:8265"
}
```

### 2. 查看外部节点列表
```bash
curl http://localhost:8000/api/nodes/external
```

### 3. 查看系统整体状态
```bash
curl http://localhost:8000/api/status
```
外部节点现在会显示在总节点列表中。

## 🌐 Web 界面使用

1. 打开浏览器访问：`http://localhost:8000/ui`
2. 查看节点列表（包含外部节点）
3. 点击相关按钮进行集群管理

## 📡 可用 API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/cluster/discover-external` | POST | 自动发现外部集群 |
| `/api/cluster/external-info` | GET | 外部集群状态 |
| `/api/nodes/external` | GET | 外部节点列表 |
| `/api/cluster/connect-external` | POST | 手动连接集群 |
| `/api/cluster/disconnect-external` | DELETE | 断开外部集群 |

### 手动连接示例
```bash
curl -X POST http://localhost:8000/api/cluster/connect-external \
  -H "Content-Type: application/json" \
  -d '{"cluster_address": "127.0.0.1:8265"}'
```

## 🔧 常用操作

### 重新发现集群
```bash
# 先断开当前连接
curl -X DELETE http://localhost:8000/api/cluster/disconnect-external

# 重新发现
curl -X POST http://localhost:8000/api/cluster/discover-external
```

### 检查集群健康状态
```bash
# Ray 集群状态
ray status

# CastRay 中的外部集群状态
curl http://localhost:8000/api/cluster/external-info
```

## 🛠️ 故障排除

### 问题：无法发现外部集群

**解决方案**：
1. 确认 Ray 集群正在运行：`ray status`
2. 检查 Dashboard 可访问：`curl http://localhost:8265`
3. 检查端口占用：`netstat -an | findstr 8265`

### 问题：连接失败

**解决方案**：
1. 验证 GCS 端口可达：`telnet 127.0.0.1 10001`
2. 检查 Ray 版本兼容性：`ray --version`
3. 重启 Ray 集群并重试

### 问题：外部节点不显示

**解决方案**：
1. 确认 Ray 集群有活跃节点：`ray status`
2. 重新连接集群
3. 检查系统日志

## 💡 最佳实践

1. **启动顺序**：先启动 Ray 集群，再启动 CastRay
2. **监控**：定期检查外部集群连接状态
3. **性能**：避免频繁调用自动发现 API
4. **安全**：仅在受信任的网络环境中使用

## 📖 详细文档

- 完整教程：`USAGE_TUTORIAL.md`
- 实现总结：`IMPLEMENTATION_SUMMARY.md`
- 技术说明：`README_EXTERNAL_CLUSTERS.md`

## 🎉 成功指标

✅ 能够发现外部 Ray 集群  
✅ 外部节点显示在系统中  
✅ API 调用正常响应  
✅ Web 界面显示外部节点  

---

**🚀 现在您可以充分利用多个 Ray 集群的资源进行分布式文件传输了！**
