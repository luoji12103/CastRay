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
            "address": "local",  # 改为local以启动本地集群
            "namespace": "castray",
            "create_demo_nodes": True,
            "max_retries": 3,
            "retry_delay": 2
        },
        "web_server": {
            "host": "0.0.0.0", 
            "port": int(os.environ.get("CASTRAY_PORT", "8000")),
            "log_level": "info"
        },
        "file_transfer": {
            "download_dir": os.environ.get("CASTRAY_DOWNLOAD_DIR", "downloads"),
            "chunk_size": 8192,
            "max_file_size": 100*1024*1024
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
    ray_address = ray_config.get("address", "local")
    namespace = ray_config.get("namespace", "castray")
    max_retries = ray_config.get("max_retries", 3)
    retry_delay = ray_config.get("retry_delay", 2)
    
    # 尝试初始化Ray集群连接（带重试机制）
    success = False
    for attempt in range(max_retries):
        try:
            logger.info(f"第 {attempt + 1}/{max_retries} 次尝试初始化Ray集群...")
            success = await cluster.initialize_ray(ray_address, namespace)
            if success:
                break
            else:
                logger.warning(f"第 {attempt + 1} 次尝试失败")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
        except Exception as e:
            logger.error(f"第 {attempt + 1} 次尝试时发生异常: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    
    if not success:
        logger.error("Ray集群初始化完全失败，系统将以降级模式运行")
        logger.warning("部分功能可能不可用，但基本Web界面仍可访问")
    else:
        logger.info("Ray集群初始化成功")
        
        # 根据配置决定是否创建示例节点
        create_demo_nodes = ray_config.get("create_demo_nodes", True)
        if create_demo_nodes:
            logger.info("正在创建演示节点...")
            try:
                # 创建一些示例节点
                demo_node_count = 3
                created_nodes = 0
                for i in range(demo_node_count):
                    node_id = f"node_{i+1}"
                    node_success = await cluster.create_node(node_id)
                    if node_success:
                        created_nodes += 1
                        logger.info(f"成功创建节点: {node_id}")
                    else:
                        logger.warning(f"创建节点失败: {node_id}")
                
                logger.info(f"成功创建 {created_nodes}/{demo_node_count} 个演示节点")
                
                # 启动演示传输调度器（如果有节点成功创建）
                if created_nodes > 0:
                    asyncio.create_task(scheduler.start_demo_transfers())
                    logger.info("演示传输调度器已启动")
                
            except Exception as e:
                logger.error(f"创建演示节点时发生错误: {e}")
    
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
    """主页 - 重定向到增强UI"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="0; url=/ui">
        <title>CastRay - 重定向中...</title>
    </head>
    <body>
        <p>正在重定向到增强界面... <a href="/ui">点击这里</a></p>
    </body>
    </html>
    '''

@app.get("/ui", response_class=HTMLResponse)
async def get_enhanced_ui():
    """增强的用户界面"""
    ui_file = static_dir / "enhanced_ui.html"
    if ui_file.exists():
        with open(ui_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>UI文件未找到</h1>", status_code=404)

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
