# CastRay 外部集群发现功能使用教程

## 📖 概述

CastRay 外部集群发现功能允许您将其他进程创建的 Ray 集群节点集成到当前的 CastRay 系统中，实现跨进程的分布式资源整合和文件传输。

### 主要功能
- 🔍 自动发现本地运行的 Ray 集群
- 🔗 连接外部 Ray 集群并获取节点信息
- 🎯 将外部节点虚拟化为 CastRay 系统节点
- 📡 实时监控外部集群状态
- 🌐 通过 RESTful API 进行集群管理

---

## 🚀 快速开始

### 步骤 1: 环境准备

确保您已安装必要的依赖：

```bash
# 激活 CastRay 环境
conda activate castray

# 验证 Ray 是否安装
ray --version

# 验证其他依赖
python -c "import requests, fastapi, uvicorn; print('Dependencies OK')"
```

### 步骤 2: 启动外部 Ray 集群

在一个新的终端窗口中启动 Ray 集群：

```bash
# 启动 Ray 集群头节点
ray start --head --dashboard-port=8265

# 查看集群状态
ray status
```

您应该看到类似的输出：
```
======== Ray Cluster Status ========
Node status
-------
Healthy:
 1 node_xxx (HEAD)

Resources
-------
 4.0/4.0 CPU
 0.0/4.68 GiB memory
 0.0/2.34 GiB object_store_memory

 1 node(s) with resource usage information
======== End Ray Cluster Status ========
```

### 步骤 3: 启动 CastRay 服务

在主终端中启动 CastRay：

```bash
# 切换到 CastRay 目录
cd "d:\MyUser\HKUSTGZ\DOIT\6G Program\CastRay"

# 启动 CastRay 服务
python main.py
```

等待服务启动，您会看到：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 🔍 使用外部集群发现功能

### 方法 1: 自动发现（推荐）

使用 API 自动发现并连接外部集群：

```bash
# 发现外部集群
curl -X POST http://localhost:8000/api/cluster/discover-external
```

成功响应示例：
```json
{
  "success": true,
  "message": "成功发现并连接到 1 个外部集群",
  "discovered_clusters": [
    {
      "nodes": 1,
      "dashboard_url": "http://127.0.0.1:8265",
      "resources": {"CPU": 4.0}
    }
  ],
  "external_nodes": {
    "ray_node_001": {
      "address": "127.0.0.1",
      "status": "alive",
      "cluster_source": "ray_status"
    }
  }
}
```

### 方法 2: 手动连接

如果知道具体的集群地址，可以手动连接：

```bash
# 手动连接到指定集群
curl -X POST http://localhost:8000/api/cluster/connect-external \
  -H "Content-Type: application/json" \
  -d '{"cluster_address": "127.0.0.1:8265"}'
```

### 方法 3: 使用演示脚本

运行提供的演示脚本：

```bash
python demo_external_cluster.py
```

---

## 📊 查看和管理外部集群

### 查看外部集群信息

```bash
# 获取外部集群连接状态
curl http://localhost:8000/api/cluster/external-info
```

响应示例：
```json
{
  "is_connected": true,
  "external_nodes": {
    "ray_node_001": {
      "address": "127.0.0.1",
      "status": "alive",
      "last_seen": "2025-09-02T10:30:45"
    }
  },
  "connected_cluster": "127.0.0.1:8265"
}
```

### 查看外部节点列表

```bash
# 获取所有外部节点
curl http://localhost:8000/api/nodes/external
```

响应示例：
```json
{
  "success": true,
  "external_nodes": [
    {
      "id": "ray_node_001",
      "address": "127.0.0.1",
      "status": "alive",
      "type": "external",
      "cluster_source": "ray_status",
      "last_seen": "2025-09-02T10:30:45"
    }
  ],
  "count": 1
}
```

### 查看系统总体状态

外部节点会自动集成到系统状态中：

```bash
# 查看包含外部节点的系统状态
curl http://localhost:8000/api/status
```

现在节点列表中会包含外部节点，显示为不同的节点类型。

---

## 🌐 Web 界面使用

### 访问 Web 界面

在浏览器中打开：
```
http://localhost:8000/ui
```

### Web 界面功能

1. **节点列表显示**
   - 本地节点和外部节点统一显示
   - 不同类型的节点有不同的图标标识
   - 实时显示节点状态

2. **外部集群管理**
   - 点击"发现外部集群"按钮自动发现
   - 查看外部集群连接状态
   - 手动输入集群地址进行连接

3. **实时通知**
   - 外部集群连接/断开时会收到通知
   - 外部节点状态变化实时更新

---

## 🔧 高级配置

### 使用配置文件

创建或修改 `config_external_cluster.json`：

```json
{
  "ray_cluster": {
    "address": "auto",
    "external_discovery": true,
    "fallback_to_local": true
  },
  "web_server": {
    "host": "0.0.0.0",
    "port": 8000
  },
  "external_cluster": {
    "enabled": true,
    "auto_discover": true,
    "connection_timeout": 10,
    "discovery_methods": ["ray_status", "dashboard_scan", "temp_dir"]
  }
}
```

启动时指定配置文件：

```bash
# 使用外部集群配置启动
export CASTRAY_CONFIG=config_external_cluster.json
python main.py
```

### 环境变量配置

```bash
# 设置 Ray 集群地址
export RAY_ADDRESS=ray://127.0.0.1:10001

# 启用外部集群发现
export EXTERNAL_CLUSTER_ENABLED=true

# 设置发现超时时间
export CLUSTER_DISCOVERY_TIMEOUT=15
```

---

## 📋 实际使用场景

### 场景 1: 利用现有 Ray 集群进行文件传输

```bash
# 1. 假设您已有一个运行中的 Ray 集群用于机器学习任务
ray start --head --dashboard-port=8265

# 2. 启动 CastRay 并发现该集群
python main.py
curl -X POST http://localhost:8000/api/cluster/discover-external

# 3. 现在可以利用 Ray 集群的节点进行文件传输
# 通过 Web 界面或 API 发起文件传输任务
```

### 场景 2: 多集群资源整合

```bash
# 启动多个 Ray 集群
ray start --head --dashboard-port=8265 --port=10001 &
ray start --head --dashboard-port=8266 --port=10002 &

# CastRay 可以发现并连接所有集群
# 将多个集群的节点整合到统一的传输网络中
```

### 场景 3: 开发环境集成

```bash
# 开发时在不同终端运行不同的 Ray 应用
# Terminal 1: 机器学习任务
ray start --head
python ml_training.py

# Terminal 2: 数据处理任务  
ray start --head --dashboard-port=8266
python data_processing.py

# Terminal 3: CastRay 文件传输
python main.py
# 自动发现并利用上述所有 Ray 集群资源
```

---

## 🧪 测试和验证

### 运行完整测试

```bash
# 运行功能演示
python demo_external_cluster.py

# 运行全面测试
python test_full_external_cluster.py
```

### 手动验证步骤

1. **验证集群发现**
   ```bash
   # 检查 Ray 集群状态
   ray status
   
   # 测试发现功能
   curl -X POST http://localhost:8000/api/cluster/discover-external
   ```

2. **验证节点集成**
   ```bash
   # 查看外部节点
   curl http://localhost:8000/api/nodes/external
   
   # 查看系统状态
   curl http://localhost:8000/api/status
   ```

3. **验证文件传输**
   - 在 Web 界面查看节点列表
   - 确认外部节点显示正常
   - 尝试发起文件传输任务

---

## 🛠️ 故障排除

### 常见问题及解决方案

#### 1. 无法发现外部集群

**症状**: 调用发现 API 返回空结果

**解决方案**:
```bash
# 检查 Ray 集群是否运行
ray status

# 检查 Dashboard 是否可访问
curl http://localhost:8265

# 检查端口是否被占用
netstat -an | findstr 8265
```

#### 2. 连接外部集群失败

**症状**: 连接 API 返回失败

**可能原因和解决方案**:
- **端口问题**: 确认 GCS 端口可达 (通常是 10001)
- **版本兼容**: 确认 Ray 版本兼容
- **防火墙**: 检查防火墙设置

```bash
# 测试端口连接
telnet 127.0.0.1 10001

# 检查 Ray 版本
ray --version
```

#### 3. 外部节点不显示

**症状**: 连接成功但节点列表为空

**解决方案**:
```bash
# 检查 Ray 集群资源
ray status

# 确认集群有可用节点
python -c "import ray; ray.init(); print(ray.nodes())"

# 重新发现集群
curl -X DELETE http://localhost:8000/api/cluster/disconnect-external
curl -X POST http://localhost:8000/api/cluster/discover-external
```

#### 4. 性能问题

**症状**: 发现过程很慢

**优化建议**:
- 减少扫描端口范围
- 增加连接超时时间
- 使用指定地址而非自动发现

```json
{
  "external_cluster": {
    "connection_timeout": 20,
    "discovery_methods": ["ray_status"],
    "port_scan_range": [8265, 8267]
  }
}
```

---

## 📈 性能优化

### 1. 发现频率优化

外部集群发现是相对重量级的操作，建议：

- 在系统启动时执行一次自动发现
- 后续使用手动连接指定集群
- 避免频繁调用自动发现 API

### 2. 连接池管理

```python
# 推荐的使用模式
# 1. 系统启动时发现集群
POST /api/cluster/discover-external

# 2. 长期保持连接
# 3. 只在必要时重新发现
```

### 3. 资源监控

定期检查外部集群状态：

```bash
# 每5分钟检查一次外部集群状态
while true; do
  curl -s http://localhost:8000/api/cluster/external-info | jq .is_connected
  sleep 300
done
```

---

## 🔒 安全注意事项

### 1. 网络安全

- 外部集群发现会扫描本地网络端口
- 确保在受信任的网络环境中使用
- 避免在生产环境中开启自动端口扫描

### 2. 资源隔离

- 外部节点与本地节点在逻辑上隔离
- 不会影响本地 Ray 集群的运行
- 文件传输时注意数据安全

### 3. 权限控制

```bash
# 确保 CastRay 进程有足够权限访问 Ray 资源
# 检查文件权限
ls -la /tmp/ray/

# 检查进程权限
ps aux | grep ray
```

---

## 📚 API 参考

### 外部集群管理 API

| 端点 | 方法 | 描述 | 参数 |
|------|------|------|------|
| `/api/cluster/discover-external` | POST | 自动发现外部集群 | 无 |
| `/api/cluster/external-info` | GET | 获取外部集群信息 | 无 |
| `/api/nodes/external` | GET | 获取外部节点列表 | 无 |
| `/api/cluster/connect-external` | POST | 手动连接外部集群 | `cluster_address` |
| `/api/cluster/disconnect-external` | DELETE | 断开外部集群连接 | 无 |

### WebSocket 事件

| 事件类型 | 描述 | 数据 |
|----------|------|------|
| `external_cluster_discovered` | 发现外部集群 | `discovered_clusters`, `external_nodes_count` |
| `external_cluster_connected` | 连接外部集群 | `cluster_address`, `external_nodes_count` |
| `external_cluster_disconnected` | 断开外部集群 | `message` |

---

## 🎯 最佳实践

### 1. 启动顺序

```bash
# 推荐的启动顺序
1. 启动 Ray 集群
2. 验证 Ray 集群状态  
3. 启动 CastRay 服务
4. 发现外部集群
5. 验证节点集成
```

### 2. 监控和维护

```bash
# 定期检查系统状态
curl http://localhost:8000/api/status

# 监控外部集群连接
curl http://localhost:8000/api/cluster/external-info

# 查看外部节点健康状态
curl http://localhost:8000/api/nodes/external
```

### 3. 故障恢复

```bash
# 如果外部集群连接丢失，重新连接
curl -X DELETE http://localhost:8000/api/cluster/disconnect-external
curl -X POST http://localhost:8000/api/cluster/discover-external
```

---

## 🎉 总结

通过本教程，您已经学会了：

- ✅ 如何设置和启动外部 Ray 集群
- ✅ 如何使用 CastRay 发现和连接外部集群
- ✅ 如何通过 API 和 Web 界面管理外部节点
- ✅ 如何处理常见问题和进行性能优化
- ✅ 安全注意事项和最佳实践

现在您可以充分利用 CastRay 的外部集群发现功能，将多个 Ray 集群的资源整合到统一的分布式文件传输系统中！

如有任何问题，请参考故障排除部分或查看详细的 API 文档。
