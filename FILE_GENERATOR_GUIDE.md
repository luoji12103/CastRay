# 文件生成器功能使用指南

## 概述

CastRay系统新增了文件生成器功能，允许用户自由选择要传输的示例文件大小，在服务端创建指定大小的文件，并进行传输测试。

## 功能特性

### 1. 灵活的文件大小选择
- 支持多种单位：B（字节）、KB（千字节）、MB（兆字节）、GB（千兆字节）
- 自动大小解析和格式化
- 智能大小验证

### 2. 多种内容类型
- **文本文件** (text)：包含可读的Lorem ipsum文本内容
- **随机文件** (random)：包含随机二进制数据
- **模式文件** (pattern)：包含重复的字节模式

### 3. 预设文件大小
提供常用的文件大小预设：
- 1 KB（测试小文件）
- 10 KB（小型文档）
- 100 KB（中等文档）
- 1 MB（大型文档）
- 10 MB（媒体文件）
- 100 MB（大型媒体）

## 使用方法

### Web界面操作

1. **访问界面**
   ```
   http://localhost:8001
   ```

2. **自定义文件创建**
   - 在"自定义文件生成"区域输入文件大小
   - 选择单位（B/KB/MB/GB）
   - 选择内容类型（text/random/pattern）
   - 点击"创建文件"按钮

3. **预设文件创建**
   - 在"快速预设"区域点击任意预设按钮
   - 系统将自动创建对应大小的随机文件

4. **创建并传输**
   - 在"生成并传输"区域设置文件参数
   - 点击"创建并传输"按钮
   - 系统将创建文件并自动发起传输

5. **文件管理**
   - 查看已生成的文件列表
   - 下载生成的文件
   - 删除不需要的文件

### API接口调用

#### 1. 获取预设列表
```http
GET /api/file-generator/presets
```

#### 2. 创建文件
```http
POST /api/file-generator/create
Content-Type: application/json

{
    "size": "10MB",
    "content_type": "random"
}
```

#### 3. 创建并传输文件
```http
POST /api/file-generator/create-and-transfer
Content-Type: application/json

{
    "size": "1MB", 
    "content_type": "text"
}
```

#### 4. 列出生成的文件
```http
GET /api/file-generator/list
```

#### 5. 下载文件
```http
GET /api/file-generator/download/{filename}
```

#### 6. 删除文件
```http
DELETE /api/file-generator/delete/{filename}
```

## 实际应用场景

### 1. 网络性能测试
- 创建不同大小的文件测试传输速度
- 评估网络带宽利用率
- 测试不同文件大小的传输延迟

### 2. 系统压力测试
- 生成大文件测试系统处理能力
- 验证内存和存储限制
- 测试并发传输性能

### 3. 功能验证
- 测试文件传输的完整性
- 验证错误处理机制
- 确认系统稳定性

## 高级用法

### 1. 批量测试脚本
```python
import requests
import time

# 测试不同大小文件的传输性能
sizes = ['1KB', '10KB', '100KB', '1MB', '10MB']
for size in sizes:
    start_time = time.time()
    response = requests.post('http://localhost:8001/api/file-generator/create-and-transfer', 
                           json={'size': size, 'content_type': 'random'})
    end_time = time.time()
    print(f"文件大小: {size}, 传输时间: {end_time - start_time:.2f}秒")
```

### 2. 自动化性能监控
```python
def monitor_transfer_performance():
    for i in range(10):
        response = requests.post('http://localhost:8001/api/file-generator/create-and-transfer',
                               json={'size': '1MB', 'content_type': 'random'})
        if response.json().get('success'):
            print(f"传输 #{i+1} 成功")
        time.sleep(1)
```

## 技术实现细节

### 文件生成算法
- **文本内容**：使用Lorem ipsum生成器创建可读文本
- **随机内容**：使用加密安全的随机数生成器
- **模式内容**：创建重复的字节序列用于压缩测试

### 大小解析
- 支持标准和二进制单位转换
- 自动处理大小写敏感性
- 智能错误提示和验证

### 安全考虑
- 文件名使用时间戳和随机前缀防止冲突
- 限制文件大小防止系统资源耗尽
- 自动清理临时文件

## 故障排除

### 常见问题

1. **文件创建失败**
   - 检查磁盘空间是否充足
   - 确认文件大小格式正确
   - 验证系统权限设置

2. **传输失败**
   - 确认Ray集群正常运行
   - 检查网络连接状态
   - 验证节点配置

3. **API调用错误**
   - 确认服务正在运行
   - 检查请求格式和参数
   - 查看服务日志获取详细错误信息

### 日志查看
```bash
# 实时查看服务日志
python main.py

# 查看详细的传输日志
tail -f castray.log
```

## 性能建议

1. **大文件生成**：生成GB级别文件时确保有足够的磁盘空间
2. **并发控制**：避免同时创建过多大文件导致系统负载过高
3. **网络优化**：在本地网络环境中测试以获得最佳性能
4. **资源监控**：监控CPU、内存、磁盘使用情况

## 总结

文件生成器功能为CastRay系统提供了强大的测试能力，使用户可以：
- 快速生成任意大小的测试文件
- 验证分布式传输性能
- 进行系统压力测试
- 评估网络传输效率

通过Web界面或API接口，用户可以灵活地进行各种文件传输测试，为系统优化和性能调优提供数据支持。
