from fastapi import FastAPI, WebSocket, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import uuid
import time
import json
import os
import platform
from pathlib import Path
from typing import List, Dict
import logging

from models import CastMessage, CastType, MessageType, CastResponse, SystemStatus
from ray_casting import cluster, scheduler

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载配置文件
def load_config():
    """根据操作系统加载相应的配置文件"""
    if platform.system() == "Linux":
        # Linux环境配置
        config_paths = [
            Path("/opt/castray-system/config_linux.json"),
            Path("/etc/castray/config.json"),
            Path("config_linux.json")
        ]
    else:
        # Windows环境配置  
        config_paths = [
            Path("config.json"),
            Path("config_windows.json")
        ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"已加载配置文件: {config_path}")
                    return config
            except Exception as e:
                logger.warning(f"配置文件 {config_path} 加载失败: {e}")
    
    # 返回默认配置
    logger.info("使用默认配置")
    return {
        "ray_cluster": {
            "address": os.environ.get("RAY_ADDRESS", "auto"),
            "namespace": "castray"
        },
        "web_server": {
            "host": "0.0.0.0", 
            "port": int(os.environ.get("CASTRAY_PORT", "8000")),
            "log_level": "info"
        },
        "file_transfer": {
            "download_dir": os.environ.get("CASTRAY_DOWNLOAD_DIR", "downloads")
        }
    }

# 加载配置
config = load_config()

app = FastAPI(title="分布式消息传输系统", version="1.0.0")

# 存储WebSocket连接
websocket_connections: List[WebSocket] = []

# WebSocket广播函数
async def broadcast_to_websockets(message: dict):
    """向所有WebSocket连接广播消息"""
    if not websocket_connections:
        return
    
    disconnected = []
    message_text = json.dumps(message)
    
    for websocket in websocket_connections:
        try:
            await websocket.send_text(message_text)
        except Exception:
            disconnected.append(websocket)
    
    # 移除断开的连接
    for ws in disconnected:
        if ws in websocket_connections:
            websocket_connections.remove(ws)

# 创建静态文件目录
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("正在启动分布式消息传输系统...")
    
    # 从配置获取Ray集群设置
    ray_config = config.get("ray_cluster", {})
    ray_address = ray_config.get("address", "auto")
    namespace = ray_config.get("namespace", "castray")
    
    # 初始化Ray集群连接
    success = await cluster.initialize_ray(ray_address, namespace)
    if not success:
        logger.error("Ray集群初始化失败，系统可能无法正常工作")
        return
    
    # 根据配置决定是否创建示例节点
    create_demo_nodes = ray_config.get("create_demo_nodes", True)
    if create_demo_nodes:
        # 创建一些示例节点
        for i in range(3):
            node_id = f"node_{i+1}"
            await cluster.create_node(node_id)
        
        # 启动演示传输调度器
        asyncio.create_task(scheduler.start_demo_transfers())
    
    logger.info("系统启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    logger.info("正在关闭系统...")
    scheduler.stop_demo_transfers()
    cluster.shutdown()
    logger.info("系统关闭完成")

@app.get("/", response_class=HTMLResponse)
async def get_homepage():
    """主页"""
    html_content = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>分布式消息传输系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: Arial, sans-serif; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .button { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin: 5px; }
            .button:hover { background: #2980b9; }
            .button.success { background: #27ae60; }
            .button.danger { background: #e74c3c; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
            .form-group input, .form-group select, .form-group textarea { 
                width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; 
            }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
            .status-item { background: #ecf0f1; padding: 15px; border-radius: 4px; text-align: center; }
            .status-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
            .status-label { color: #7f8c8d; margin-top: 5px; }
            .message-log { max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: #f9f9f9; }
            .message-item { padding: 8px; margin-bottom: 5px; border-left: 4px solid #3498db; background: white; }
            .message-sent { border-left-color: #27ae60; }
            .message-received { border-left-color: #e74c3c; }
            .node-status { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
            .node-online { background: #27ae60; }
            .node-offline { background: #e74c3c; }
            #connectionStatus { padding: 10px; border-radius: 4px; margin-bottom: 20px; }
            .connected { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .disconnected { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 分布式消息与文件传输系统</h1>
                <p>基于Ray集群的自动化传输监控平台 - 节点自主发起传输</p>
            </div>

            <div id="connectionStatus" class="disconnected">
                ⚠️ 正在连接到服务器...
            </div>

            <div class="grid">
                <!-- 系统状态 -->
                <div class="card">
                    <h3>📊 系统状态</h3>
                    <div class="status-grid" id="systemStatus">
                        <div class="status-item">
                            <div class="status-value" id="totalNodes">-</div>
                            <div class="status-label">总节点数</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="activeNodes">-</div>
                            <div class="status-label">活跃节点</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="totalTransfers">-</div>
                            <div class="status-label">文件传输</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="rayNodes">-</div>
                            <div class="status-label">Ray节点</div>
                        </div>
                    </div>
                </div>

                <!-- 传输监控 -->
                <div class="card">
                    <h3>� 文件传输监控</h3>
                    <div class="status-grid" id="transferStats">
                        <div class="status-item">
                            <div class="status-value" id="successfulTransfers">-</div>
                            <div class="status-label">成功传输</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="failedTransfers">-</div>
                            <div class="status-label">失败传输</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="bytesTransferred">-</div>
                            <div class="status-label">传输字节</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="activeTransfers">-</div>
                            <div class="status-label">进行中</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 手动操作面板 -->
            <div class="card">
                <h3>🎮 手动操作 (管理员)</h3>
                <div class="grid">
                    <div>
                        <div class="form-group">
                            <label>发送节点:</label>
                            <select id="senderNode">
                                <option value="">选择发送节点</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>演示文件:</label>
                            <select id="demoFile">
                                <option value="config.json">config.json</option>
                                <option value="data.txt">data.txt</option>
                                <option value="report.md">report.md</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <div class="form-group">
                            <label>接收节点:</label>
                            <select id="recipients" multiple>
                            </select>
                            <small>按住Ctrl选择多个节点</small>
                        </div>
                        <button class="button" onclick="triggerManualTransfer()">手动触发文件传输</button>
                    </div>
                </div>
            </div>

            <div class="grid">
                <!-- 节点列表和状态 -->
                <div class="card">
                    <h3>🖥️ 节点状态监控</h3>
                    <div id="nodesList"></div>
                </div>

                <!-- 传输活动日志 -->
                <div class="card">
                    <h3>� 传输活动日志</h3>
                    <div class="message-log" id="transferLog">
                        <div style="text-align: center; color: #7f8c8d; padding: 20px;">
                            监控节点自主发起的文件传输活动...
                        </div>
                    </div>
                </div>
            </div>

            <!-- 演示文件列表 -->
            <div class="card">
                <h3>📁 可用演示文件</h3>
                <div class="grid">
                    <div class="status-item">
                        <div class="status-label">config.json</div>
                        <small>配置文件 (JSON格式)</small>
                    </div>
                    <div class="status-item">
                        <div class="status-label">data.txt</div>
                        <small>文本数据文件</small>
                    </div>
                    <div class="status-item">
                        <div class="status-label">report.md</div>
                        <small>Markdown报告文件</small>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let totalTransfers = 0;
            let transferLog = [];

            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() {
                    document.getElementById('connectionStatus').innerHTML = '✅ 已连接到服务器';
                    document.getElementById('connectionStatus').className = 'connected';
                    loadStatus();
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === 'status_update') {
                        updateStatus(data.data);
                    } else if (data.type === 'transfer_activity') {
                        updateTransferLog(data.data);
                    }
                };
                
                ws.onclose = function() {
                    document.getElementById('connectionStatus').innerHTML = '❌ 连接已断开，正在重连...';
                    document.getElementById('connectionStatus').className = 'disconnected';
                    setTimeout(connectWebSocket, 3000);
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket错误:', error);
                };
            }

            async function loadStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    updateStatus(data);
                    
                    // 加载文件传输状态
                    const transferResponse = await fetch('/api/file-transfers/status');
                    const transferData = await transferResponse.json();
                    updateTransferStats(transferData);
                } catch (error) {
                    console.error('加载状态失败:', error);
                }
            }

            function updateStatus(data) {
                document.getElementById('totalNodes').textContent = data.total_nodes || 0;
                document.getElementById('activeNodes').textContent = data.active_nodes || 0;
                document.getElementById('rayNodes').textContent = 
                    data.ray_cluster?.nodes || data.ray_cluster?.error || 'N/A';
                
                updateNodesList(data.node_statuses || []);
                updateNodeSelects(data.node_statuses || []);
            }

            function updateTransferStats(data) {
                let totalSuccessful = 0;
                let totalFailed = 0;
                let totalBytes = 0;
                let totalActive = 0;
                
                Object.values(data).forEach(nodeData => {
                    if (nodeData.file_transfer_stats) {
                        const stats = nodeData.file_transfer_stats;
                        totalSuccessful += stats.successful_transfers || 0;
                        totalFailed += stats.failed_transfers || 0;
                        totalBytes += stats.bytes_transferred || 0;
                    }
                    totalActive += nodeData.active_transfers || 0;
                });
                
                document.getElementById('successfulTransfers').textContent = totalSuccessful;
                document.getElementById('failedTransfers').textContent = totalFailed;
                document.getElementById('bytesTransferred').textContent = formatBytes(totalBytes);
                document.getElementById('activeTransfers').textContent = totalActive;
                document.getElementById('totalTransfers').textContent = totalSuccessful + totalFailed;
            }

            function updateNodesList(nodes) {
                const nodesList = document.getElementById('nodesList');
                nodesList.innerHTML = nodes.map(node => {
                    const autoTransfers = node.auto_transfer_queue || 0;
                    const fileStats = node.file_transfer_stats || {};
                    
                    return `
                        <div style="padding: 10px; border-bottom: 1px solid #eee;">
                            <span class="node-status ${node.is_running ? 'node-online' : 'node-offline'}"></span>
                            <strong>${node.node_id}</strong> 
                            (端口: ${node.port || 'N/A'})
                            <br>
                            <small>
                                消息: 收${node.received_count || 0}/发${node.sent_count || 0} | 
                                文件传输: 成功${fileStats.successful_transfers || 0}/失败${fileStats.failed_transfers || 0} |
                                队列: ${autoTransfers}
                            </small>
                            ${node.auto_transfer_enabled ? 
                                '<span style="color: green;">●</span> 自动传输已启用' : 
                                '<span style="color: red;">●</span> 自动传输已禁用'
                            }
                        </div>
                    `;
                }).join('');
            }

            function updateNodeSelects(nodes) {
                const senderSelect = document.getElementById('senderNode');
                const recipientsSelect = document.getElementById('recipients');
                
                const options = nodes.map(node => 
                    `<option value="${node.node_id}">${node.node_id}</option>`
                ).join('');
                
                senderSelect.innerHTML = '<option value="">选择发送节点</option>' + options;
                recipientsSelect.innerHTML = options;
            }

            function updateTransferLog(activity) {
                transferLog.unshift({
                    ...activity,
                    timestamp: new Date().toLocaleString()
                });
                
                // 保持最新50条记录
                if (transferLog.length > 50) {
                    transferLog = transferLog.slice(0, 50);
                }
                
                const logContainer = document.getElementById('transferLog');
                logContainer.innerHTML = transferLog.map(log => `
                    <div class="message-item" style="border-left-color: ${getActivityColor(log.type)};">
                        <strong>[${log.type}]</strong> ${log.node_id || 'System'}<br>
                        <small>${log.timestamp}</small><br>
                        ${log.description || JSON.stringify(log)}
                    </div>
                `).join('');
            }

            function getActivityColor(activityType) {
                const colors = {
                    'transfer_start': '#3498db',
                    'transfer_complete': '#27ae60',
                    'transfer_error': '#e74c3c',
                    'file_received': '#9b59b6',
                    'auto_transfer': '#f39c12'
                };
                return colors[activityType] || '#7f8c8d';
            }

            async function triggerManualTransfer() {
                const sender = document.getElementById('senderNode').value;
                const fileName = document.getElementById('demoFile').value;
                const recipientSelect = document.getElementById('recipients');
                const recipients = Array.from(recipientSelect.selectedOptions).map(opt => opt.value);
                
                if (!sender || recipients.length === 0) {
                    alert('请选择发送节点和接收节点');
                    return;
                }
                
                try {
                    const response = await fetch('/api/file-transfers/manual', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            sender_id: sender,
                            file_name: fileName,
                            recipients: recipients
                        })
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        alert(`手动传输已触发\\n接收者: ${recipients.join(', ')}\\n文件: ${fileName}`);
                        loadStatus();
                    } else {
                        alert('手动传输失败: ' + result.message);
                    }
                } catch (error) {
                    alert('触发手动传输时发生错误: ' + error.message);
                }
            }

            function formatBytes(bytes) {
                if (bytes === 0) return '0 B';
                const k = 1024;
                const sizes = ['B', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }

            // 页面加载时连接WebSocket
            window.onload = function() {
                connectWebSocket();
            };

            // 定期更新状态
            setInterval(loadStatus, 5000);
        </script>
    </body>
    </html>
    '''
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # 定期发送状态更新
            status = await cluster.get_cluster_status()
            await websocket.send_text(json.dumps({
                "type": "status_update",
                "data": status
            }))
            await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    return await cluster.get_cluster_status()

@app.post("/api/nodes")
async def create_node(request: dict):
    """创建新节点"""
    node_id = request.get("node_id")
    port = request.get("port", 0)
    
    if not node_id:
        raise HTTPException(status_code=400, detail="节点ID不能为空")
    
    success = await cluster.create_node(node_id, port)
    
    return {
        "success": success,
        "message": "节点创建成功" if success else "节点创建失败"
    }

@app.delete("/api/nodes/{node_id}")
async def remove_node(node_id: str):
    """删除节点"""
    success = await cluster.remove_node(node_id)
    
    return {
        "success": success,
        "message": "节点删除成功" if success else "节点删除失败"
    }

@app.post("/api/send")
async def send_message(message: CastMessage):
    """发送消息"""
    response = await cluster.send_message(message)
    
    # 通知所有WebSocket客户端
    if websocket_connections:
        notification = {
            "type": "message_received",
            "data": {
                "message_id": message.id,
                "cast_type": message.cast_type,
                "sender": message.sender
            }
        }
        for ws in websocket_connections:
            try:
                await ws.send_text(json.dumps(notification))
            except:
                pass
    
    return response

@app.get("/api/nodes/{node_id}/messages")
async def get_node_messages(node_id: str, count: int = 50):
    """获取节点消息"""
    messages = await cluster.get_node_messages(node_id, count)
    return messages

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件"""
    try:
        # 保存文件
        filename = file.filename or f"upload_{int(time.time())}"
        file_path = static_dir / filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {
            "success": True,
            "message": "文件上传成功",
            "file_path": str(file_path),
            "file_size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.get("/api/file-transfers/status")
async def get_file_transfer_status():
    """获取所有节点的文件传输状态"""
    status = {}
    for node_id, node in cluster.nodes.items():
        try:
            # 获取文件传输统计
            file_stats = await node.get_file_transfer_stats()
            active_transfers = await node.get_active_transfers_count()
            
            status[node_id] = {
                "file_transfer_stats": file_stats,
                "active_transfers": active_transfers,
                "auto_transfer_enabled": getattr(node, 'auto_transfer_enabled', False),
                "auto_transfer_queue": getattr(node, 'auto_transfer_queue', 0)
            }
        except Exception as e:
            status[node_id] = {
                "error": str(e),
                "file_transfer_stats": {},
                "active_transfers": 0,
                "auto_transfer_enabled": False,
                "auto_transfer_queue": 0
            }
    
    return status

@app.post("/api/file-transfers/manual")
async def trigger_manual_transfer(request: dict):
    """手动触发文件传输"""
    sender_id = request.get("sender_id")
    file_name = request.get("file_name", "demo_file.txt")
    recipients = request.get("recipients", [])
    
    if not sender_id or sender_id not in cluster.nodes:
        raise HTTPException(status_code=404, detail="发送节点未找到")
    
    if not recipients:
        raise HTTPException(status_code=400, detail="请指定接收节点")
    
    try:
        sender_node = cluster.nodes[sender_id]
        
        # 验证接收节点存在
        valid_recipients = []
        for recipient_id in recipients:
            if recipient_id in cluster.nodes:
                valid_recipients.append(recipient_id)
        
        if not valid_recipients:
            raise HTTPException(status_code=400, detail="没有有效的接收节点")
        
        # 触发文件传输
        transfer_results = []
        for recipient_id in valid_recipients:
            try:
                result = await sender_node.initiate_file_transfer(
                    target_node_id=recipient_id,
                    file_path=file_name,
                    transfer_type="manual"
                )
                transfer_results.append({
                    "recipient": recipient_id,
                    "success": result.get("success", False),
                    "message": result.get("message", "")
                })
            except Exception as e:
                transfer_results.append({
                    "recipient": recipient_id,
                    "success": False,
                    "message": str(e)
                })
        
        # 广播传输活动
        if websocket_connections:
            activity = {
                "type": "transfer_start",
                "node_id": sender_id,
                "description": f"手动传输 {file_name} 到 {len(valid_recipients)} 个节点",
                "recipients": valid_recipients,
                "file_name": file_name
            }
            await broadcast_to_websockets({
                "type": "transfer_activity",
                "data": activity
            })
        
        successful_transfers = sum(1 for r in transfer_results if r["success"])
        
        return {
            "success": successful_transfers > 0,
            "message": f"成功触发 {successful_transfers}/{len(valid_recipients)} 个传输",
            "results": transfer_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发文件传输失败: {str(e)}")

@app.post("/api/file-transfers/auto/toggle")
async def toggle_auto_transfer(request: dict):
    """切换自动文件传输功能"""
    node_id = request.get("node_id")
    enabled = request.get("enabled", True)
    
    if not node_id or node_id not in cluster.nodes:
        raise HTTPException(status_code=404, detail="节点未找到")
    
    try:
        node = cluster.nodes[node_id]
        
        if enabled:
            await node.enable_auto_transfer()
            message = f"节点 {node_id} 自动传输已启用"
        else:
            await node.disable_auto_transfer()
            message = f"节点 {node_id} 自动传输已禁用"
        
        return {
            "success": True,
            "message": message,
            "enabled": enabled
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换自动传输失败: {str(e)}")

if __name__ == "__main__":
    # 从配置文件获取Web服务器设置
    web_config = config.get("web_server", {})
    host = web_config.get("host", "0.0.0.0")
    port = web_config.get("port", 8000)
    log_level = web_config.get("log_level", "info")
    
    logger.info(f"启动Web服务器: {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level=log_level)
