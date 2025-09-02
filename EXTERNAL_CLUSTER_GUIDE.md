# 外部Ray集群连接测试指南

## 概述

本指南演示如何让CastRay传输系统连接到独立启动的Ray集群，并自动发现和使用集群中的节点。

## 功能特性

- ✅ 连接到外部Ray集群
- ✅ 自动发现Ray集群中的物理节点
- ✅ 将Ray节点映射为传输节点
- ✅ 在Web界面中显示外部节点
- ✅ 支持与外部节点的文件传输

## 测试步骤

### 1. 启动独立的Ray集群

在第一个终端中运行：

```bash
# 激活conda环境
conda activate castray

# 启动Ray集群（默认配置：head端口10001，3个worker）
python start_ray_cluster.py

# 或者自定义配置
python start_ray_cluster.py --head-port 10001 --workers 3 --dashboard-port 8265
```

这将启动：
- 1个Ray head节点（端口10001）
- 3个worker节点
- Ray Dashboard（端口8265）
- 一些演示Actor

### 2. 启动CastRay传输系统

在第二个终端中运行：

```bash
# 激活conda环境
conda activate castray

# 使用外部集群配置启动CastRay
python start_with_external_cluster.py

# 或者手动设置环境变量
set CASTRAY_CONFIG=config_external_cluster.json
python main.py
```

### 3. 运行测试脚本

在第三个终端中运行：

```bash
# 激活conda环境
conda activate castray

# 运行测试脚本
python test_external_cluster.py
```

### 4. 访问Web界面

打开浏览器访问：http://127.0.0.1:28823/ui

在Web界面中你应该能看到：
- Ray集群的物理节点（显示为"ray_node_1", "ray_node_2"等）
- 节点类型标记为"Ray节点"
- 节点在传输列表中可选择

## 配置文件说明

### config_external_cluster.json

```json
{
    "ray_cluster": {
        "address": "ray://127.0.0.1:10001",
        "namespace": "castray",
        "create_demo_nodes": false,
        "external_cluster": true
    },
    "web_server": {
        "host": "127.0.0.1", 
        "port": 28823
    }
}
```

关键配置项：
- `address`: 指向外部Ray集群的地址
- `create_demo_nodes`: 设为false，不创建本地演示节点
- `external_cluster`: 标记为外部集群模式

## 工作原理

### 1. 集群连接

CastRay启动时会：
- 读取配置文件中的Ray集群地址
- 连接到指定的外部Ray集群
- 不创建本地Ray集群

### 2. 节点发现

连接成功后会：
- 调用`ray.nodes()`获取物理节点信息
- 调用`ray.util.state.list_actors()`查找现有Actor
- 为每个Ray物理节点创建虚拟传输节点ID

### 3. 节点映射

```python
# 为Ray物理节点创建映射
ray_node_1 -> Ray物理节点1
ray_node_2 -> Ray物理节点2
ray_node_3 -> Ray物理节点3
```

### 4. Web界面集成

- 外部节点会在节点状态中显示
- 标记为"Ray节点"类型
- 可在传输发送/接收列表中选择

## 测试验证

### 1. 检查节点发现

```bash
curl http://127.0.0.1:28823/api/status
```

应该看到类似输出：
```json
{
  "total_nodes": 3,
  "active_nodes": 3,
  "node_statuses": [
    {
      "node_id": "ray_node_1",
      "node_type": "Ray节点",
      "is_running": true
    }
  ]
}
```

### 2. 检查Ray集群信息

```bash
curl http://127.0.0.1:28823/api/nodes/ray-info
```

### 3. 测试传输功能

```bash
curl -X POST http://127.0.0.1:28823/api/file-transfers/manual \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "ray_node_1",
    "file_name": "config.json",
    "recipients": ["ray_node_2"]
  }'
```

## 故障排除

### 1. 连接失败

```
ERROR: Ray集群初始化失败: Failed to connect to Ray cluster
```

解决方案：
- 确认Ray集群正在运行
- 检查端口10001是否被占用
- 验证防火墙设置

### 2. 节点不显示

```
WARNING: 没有发现外部节点
```

解决方案：
- 检查Ray集群是否有活跃节点
- 确认配置文件中的地址正确
- 查看Ray Dashboard确认集群状态

### 3. 传输失败

```
ERROR: 未找到接收者地址
```

解决方案：
- 外部节点目前只作为展示用途
- 实际传输需要CastingNode Actor
- 可以在外部集群中创建CastingNode实例

## 扩展说明

### 添加真正的传输节点

在外部Ray集群中创建CastingNode：

```python
# 在外部集群中运行
import ray
from ray_casting import CastingNode

# 创建传输节点
node = CastingNode.remote("external_node_1", 0)
ray.get(node.start.remote())
```

### 自定义节点发现

修改`discover_existing_nodes()`方法来：
- 查找特定类型的Actor
- 使用自定义命名规则
- 添加更多节点元数据

## 总结

此功能演示了CastRay的集群连接能力，可以：
- 连接到独立的Ray集群
- 发现和展示集群节点
- 为后续的分布式传输功能奠定基础

通过这种架构，CastRay可以扩展到真正的分布式环境，利用现有的Ray集群资源进行大规模文件传输。
