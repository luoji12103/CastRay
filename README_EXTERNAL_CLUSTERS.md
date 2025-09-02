# CastRay 外部集群发现功能说明

## 功能概述

CastRay 系统现在支持发现和连接其他进程创建的 Ray 集群，将外部 Ray 节点作为虚拟节点加入到当前的节点列表中。这使得 CastRay 可以利用现有的 Ray 集群资源进行分布式文件传输。

## 核心功能

### 1. 自动集群发现
- **多种发现方式**: 通过 Ray status、Dashboard 扫描、临时目录分析等方式发现本地 Ray 集群
- **智能端口扫描**: 自动扫描常用的 Ray Dashboard 端口 (8265-8269)
- **集群信息提取**: 获取集群节点数量、资源信息、Dashboard URL 等

### 2. 外部集群连接
- **灵活连接方式**: 支持通过 Dashboard URL 或 GCS 地址连接外部集群
- **多端口尝试**: 自动尝试多个可能的 GCS 端口进行连接
- **连接状态管理**: 跟踪外部集群连接状态和节点信息

### 3. 节点虚拟化
- **虚拟节点映射**: 将外部 Ray 节点映射为 CastRay 系统中的虚拟节点
- **节点状态同步**: 实时同步外部节点的状态信息
- **统一节点管理**: 外部节点与本地节点统一管理和显示

### 4. API 集成
- **RESTful 接口**: 提供完整的外部集群管理 API
- **WebSocket 通知**: 实时推送集群连接状态变化
- **错误处理**: 优雅处理连接失败和模块不可用情况

## 文件结构

```
CastRay/
├── ray_cluster_discovery.py      # 核心集群发现模块
├── ray_casting.py                # 增强的 Ray 集群管理
├── main.py                      # 新增外部集群 API 端点
├── config_external_cluster.json  # 外部集群配置文件
├── test_full_external_cluster.py # 全面功能测试脚本
└── README_EXTERNAL_CLUSTERS.md   # 本文档
```

## API 端点

### 1. 发现外部集群
```
POST /api/cluster/discover-external
```
- **功能**: 自动发现并连接本地运行的 Ray 集群
- **响应**: 返回发现的集群信息和连接结果

### 2. 获取外部集群信息
```
GET /api/cluster/external-info
```
- **功能**: 获取当前外部集群连接状态
- **响应**: 连接状态、外部节点信息、集群地址等

### 3. 获取外部节点列表
```
GET /api/nodes/external
```
- **功能**: 获取所有外部集群节点的详细信息
- **响应**: 格式化的外部节点列表

### 4. 手动连接外部集群
```
POST /api/cluster/connect-external
Content-Type: application/json

{
  "cluster_address": "127.0.0.1:8265"
}
```
- **功能**: 手动连接到指定的外部集群
- **参数**: cluster_address - 集群地址或 Dashboard URL

### 5. 断开外部集群连接
```
DELETE /api/cluster/disconnect-external
```
- **功能**: 断开当前的外部集群连接并清除外部节点

## 使用场景

### 场景 1: 利用现有 Ray 集群
```bash
# 1. 启动独立的 Ray 集群
ray start --head --dashboard-port=8265

# 2. 启动 CastRay 服务
python main.py

# 3. 发现并连接外部集群
curl -X POST http://localhost:8000/api/cluster/discover-external

# 4. 查看节点列表（包含外部节点）
curl http://localhost:8000/api/status
```

### 场景 2: 多集群资源整合
```bash
# 启动多个 Ray 集群
ray start --head --dashboard-port=8265 --port=10001
ray start --head --dashboard-port=8266 --port=10002

# CastRay 可以发现并连接所有集群
# 将所有外部节点整合到统一的传输网络中
```

### 场景 3: 动态集群管理
```python
import requests

# 连接到特定集群
requests.post('http://localhost:8000/api/cluster/connect-external', 
              json={'cluster_address': 'http://192.168.1.100:8265'})

# 查看外部节点
response = requests.get('http://localhost:8000/api/nodes/external')
print(response.json())

# 断开连接
requests.delete('http://localhost:8000/api/cluster/disconnect-external')
```

## 配置选项

### 环境变量配置
```bash
# 启用外部集群模式
export CASTRAY_CONFIG=config_external_cluster.json

# 自定义 Ray 集群地址
export RAY_ADDRESS=ray://127.0.0.1:10001
```

### 配置文件示例
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
    "connection_timeout": 10
  }
}
```

## 技术实现

### 集群发现机制
1. **Ray Status 解析**: 解析 `ray status` 命令输出获取集群信息
2. **Dashboard 扫描**: 通过 HTTP 请求检查 Dashboard 端点
3. **临时目录扫描**: 分析 Ray 临时文件目录获取集群信息
4. **端口扫描**: 检查常用端口的服务可用性

### 连接策略
1. **多端口尝试**: 依次尝试常见的 GCS 端口 (10001, 6379, Dashboard端口-1)
2. **超时处理**: 设置合理的连接超时避免长时间等待
3. **错误恢复**: 连接失败时自动尝试下一个端口或方法
4. **状态保持**: 维护连接状态和节点信息缓存

### 节点管理
1. **虚拟节点创建**: 为每个外部 Ray Actor 创建对应的虚拟节点
2. **状态同步**: 定期更新外部节点的状态信息
3. **资源映射**: 将 Ray 资源信息映射到 CastRay 节点属性
4. **生命周期管理**: 处理外部节点的上线、下线事件

## 故障排除

### 常见问题

1. **无法发现外部集群**
   - 检查 Ray 集群是否正在运行: `ray status`
   - 确认 Dashboard 端口可访问: `curl http://localhost:8265`
   - 检查防火墙设置

2. **连接外部集群失败**
   - 验证集群地址格式正确
   - 确认 GCS 端口可达
   - 检查 Ray 版本兼容性

3. **外部节点不显示**
   - 确认外部集群有可用的 Ray Actor
   - 检查节点资源是否充足
   - 验证网络连接稳定性

### 调试工具

```bash
# 测试外部集群发现功能
python test_full_external_cluster.py

# 查看详细日志
python main.py --log-level=DEBUG

# 手动测试 API
curl -X POST http://localhost:8000/api/cluster/discover-external
curl http://localhost:8000/api/cluster/external-info
curl http://localhost:8000/api/nodes/external
```

## 性能考虑

1. **发现频率**: 集群发现操作相对重量级，建议按需执行而非定期扫描
2. **连接复用**: 保持外部集群连接以避免频繁重连开销
3. **节点缓存**: 缓存外部节点信息以减少 Ray 集群查询频率
4. **超时设置**: 合理设置连接和操作超时以平衡响应性和稳定性

## 安全注意事项

1. **网络访问**: 外部集群发现会扫描本地网络端口，确保在受信任的环境中使用
2. **资源隔离**: 外部节点与本地节点在逻辑上隔离，避免资源冲突
3. **权限控制**: 确保 CastRay 进程有足够权限访问 Ray 集群资源
4. **数据安全**: 外部集群连接可能涉及跨进程数据传输，注意数据安全

## 未来扩展

1. **远程集群支持**: 扩展到支持远程 Ray 集群的发现和连接
2. **集群健康检查**: 定期检查外部集群健康状态并自动重连
3. **负载均衡**: 在多个外部集群之间进行智能负载分配
4. **集群拓扑**: 可视化显示集群拓扑和节点关系图
5. **性能监控**: 监控外部集群的性能指标和资源使用情况
