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
from datetime import datetime

from models import CastMessage, CastType, MessageType, CastResponse, SystemStatus
from ray_casting import cluster, scheduler
from file_generator import (
    create_sample_file, parse_size_string, format_size, 
    validate_file_size, get_available_content_types, 
    PRESET_SIZES, create_preset_file
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载配置文件
def load_config():
    """根据操作系统和环境变量加载相应的配置文件"""
    
    # 首先检查环境变量指定的配置文件
    env_config = os.environ.get('CASTRAY_CONFIG')
    if env_config:
        config_path = Path(env_config)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"已加载环境变量指定的配置文件: {config_path}")
                    return config
            except Exception as e:
                logger.warning(f"环境变量配置文件 {config_path} 加载失败: {e}")
    
    # 按操作系统查找配置文件
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
            "port": int(os.environ.get("CASTRAY_PORT", "8001")),
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

@app.post("/api/cluster/discover-external")
async def discover_external_clusters():
    """发现并连接外部Ray集群"""
    try:
        from ray_cluster_discovery import discover_and_connect_external_clusters
        
        result = discover_and_connect_external_clusters()
        
        if result.get('success'):
            # 将发现的外部节点添加到集群管理器
            external_nodes = result.get('external_nodes', {})
            cluster.external_nodes.update(external_nodes)
            
            # 广播更新到WebSocket客户端
            if websocket_connections:
                notification = {
                    "type": "external_cluster_discovered",
                    "data": {
                        "discovered_clusters": result.get('discovered_clusters', []),
                        "external_nodes_count": len(external_nodes)
                    }
                }
                for ws in websocket_connections:
                    try:
                        await ws.send_text(json.dumps(notification))
                    except:
                        pass
        
        return result
        
    except ImportError:
        raise HTTPException(status_code=501, detail="外部集群发现功能不可用")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发现外部集群失败: {str(e)}")

@app.get("/api/cluster/external-info")
async def get_external_cluster_info():
    """获取外部集群信息"""
    try:
        from ray_cluster_discovery import cluster_connector
        
        return {
            "is_connected": cluster_connector.is_connected_to_external_cluster(),
            "external_nodes": cluster_connector.get_external_nodes(),
            "connected_cluster": getattr(cluster_connector, 'connected_cluster', None)
        }
        
    except ImportError:
        return {
            "is_connected": False,
            "external_nodes": {},
            "connected_cluster": None,
            "error": "外部集群发现功能不可用"
        }
    except Exception as e:
        return {
            "is_connected": False,
            "external_nodes": {},
            "connected_cluster": None,
            "error": str(e)
        }

@app.get("/api/nodes/external")
async def get_external_nodes():
    """获取外部集群节点列表"""
    try:
        # 从集群管理器获取外部节点
        external_nodes = getattr(cluster, 'external_nodes', {})
        
        # 格式化节点信息
        formatted_nodes = []
        for node_id, node_info in external_nodes.items():
            formatted_nodes.append({
                "id": node_id,
                "address": node_info.get('address', 'unknown'),
                "status": node_info.get('status', 'unknown'),
                "type": "external",
                "cluster_source": node_info.get('cluster_source', 'unknown'),
                "last_seen": node_info.get('last_seen')
            })
        
        return {
            "success": True,
            "external_nodes": formatted_nodes,
            "count": len(formatted_nodes)
        }
        
    except Exception as e:
        return {
            "success": False,
            "external_nodes": [],
            "count": 0,
            "error": str(e)
        }

@app.post("/api/cluster/connect-external")
async def connect_to_external_cluster(request: dict):
    """手动连接到指定的外部集群"""
    try:
        from ray_cluster_discovery import cluster_connector
        
        cluster_address = request.get('cluster_address')
        if not cluster_address:
            raise HTTPException(status_code=400, detail="缺少cluster_address参数")
        
        # 构造集群信息
        cluster_info = {
            'dashboard_url': cluster_address if cluster_address.startswith('http') else f'http://{cluster_address}:8265',
            'address': cluster_address,
            'nodes': 1  # 假设至少有一个节点
        }
        
        # 尝试连接到指定集群
        success = cluster_connector.connect_to_external_cluster(cluster_info)
        
        if success:
            # 获取外部节点信息
            external_nodes = cluster_connector.get_external_nodes()
            cluster.external_nodes.update(external_nodes)
            
            # 广播更新
            if websocket_connections:
                notification = {
                    "type": "external_cluster_connected",
                    "data": {
                        "cluster_address": cluster_address,
                        "external_nodes_count": len(external_nodes)
                    }
                }
                for ws in websocket_connections:
                    try:
                        await ws.send_text(json.dumps(notification))
                    except:
                        pass
            
            return {
                "success": True,
                "message": f"成功连接到外部集群: {cluster_address}",
                "external_nodes": external_nodes
            }
        else:
            return {
                "success": False,
                "message": f"连接外部集群失败: {cluster_address}"
            }
        
    except ImportError:
        raise HTTPException(status_code=501, detail="外部集群连接功能不可用")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接外部集群失败: {str(e)}")

@app.delete("/api/cluster/disconnect-external")
async def disconnect_external_cluster():
    """断开外部集群连接"""
    try:
        from ray_cluster_discovery import cluster_connector
        
        # 检查是否有连接的外部集群
        if cluster_connector.is_connected_to_external_cluster():
            # 清除外部节点
            cluster.external_nodes.clear()
            cluster_connector.external_nodes.clear()
            cluster_connector.connected_cluster = None
            
            # 广播更新
            if websocket_connections:
                notification = {
                    "type": "external_cluster_disconnected",
                    "data": {"message": "外部集群连接已断开"}
                }
                for ws in websocket_connections:
                    try:
                        await ws.send_text(json.dumps(notification))
                    except:
                        pass
            
            return {
                "success": True,
                "message": "外部集群连接已断开"
            }
        else:
            return {
                "success": False,
                "message": "没有连接的外部集群"
            }
        
    except ImportError:
        raise HTTPException(status_code=501, detail="外部集群断连功能不可用")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"断开外部集群失败: {str(e)}")

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
                # 构建完整的文件路径
                demo_files_dir = Path("demo_files")
                file_path = demo_files_dir / file_name
                
                # 检查文件是否存在
                if not file_path.exists():
                    transfer_results.append({
                        "recipient": recipient_id,
                        "success": False,
                        "message": f"文件不存在: {file_path}"
                    })
                    continue
                
                # 调用Ray节点的文件传输方法（修正参数）
                result = await sender_node.initiate_file_transfer.remote(
                    str(file_path),  # file_path
                    [recipient_id],  # recipients (列表)
                    "unicast"       # transfer_mode
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

# ============ 文件生成和传输功能 ============

@app.get("/api/file-generator/presets")
async def get_file_size_presets():
    """获取预设的文件大小选项"""
    return {
        "success": True,
        "presets": {
            name: {
                "size_bytes": size,
                "size_formatted": format_size(size),
                "description": f"预设 {name.title()} 文件"
            }
            for name, size in PRESET_SIZES.items()
        },
        "content_types": get_available_content_types()
    }

@app.get("/api/file-generator/info")
async def get_file_generator_info():
    """获取文件生成器信息和限制"""
    max_size = 1024 * 1024 * 1024  # 1GB 限制
    return {
        "success": True,
        "max_file_size": max_size,
        "max_file_size_formatted": format_size(max_size),
        "supported_units": ["B", "KB", "MB", "GB"],
        "content_types": get_available_content_types(),
        "examples": [
            "100B - 100 字节",
            "1KB - 1 千字节",
            "1.5MB - 1.5 兆字节",
            "1GB - 1 吉字节"
        ]
    }

@app.post("/api/file-generator/create")
async def create_sample_file_api(request: dict):
    """创建指定大小的示例文件"""
    try:
        # 解析请求参数
        size_input = request.get("size", "1KB")
        content_type = request.get("content_type", "text")
        file_name = request.get("file_name", "")
        include_metadata = request.get("include_metadata", True)
        
        # 解析文件大小
        try:
            size_bytes = parse_size_string(size_input)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的文件大小格式: {str(e)}")
        
        # 验证文件大小
        max_size = 1024 * 1024 * 1024  # 1GB
        if not validate_file_size(size_bytes, max_size):
            raise HTTPException(
                status_code=400, 
                detail=f"文件大小超出限制。最大允许: {format_size(max_size)}"
            )
        
        # 生成文件名
        if not file_name:
            timestamp = int(time.time())
            size_str = format_size(size_bytes).replace(" ", "").replace(".", "_")
            file_name = f"sample_{size_str}_{content_type}_{timestamp}.txt"
        
        # 确保文件名安全
        file_name = "".join(c for c in file_name if c.isalnum() or c in "._-")
        if not file_name.endswith(('.txt', '.bin', '.dat')):
            file_name += '.txt'
        
        # 创建文件路径
        file_path = static_dir / file_name
        
        # 检查文件是否已存在
        if file_path.exists():
            timestamp = int(time.time())
            name_parts = file_path.stem, timestamp, file_path.suffix
            file_path = static_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
        
        # 创建示例文件
        file_info = create_sample_file(
            file_path=file_path,
            size_bytes=size_bytes,
            content_type=content_type,
            include_metadata=include_metadata
        )
        
        # 添加额外信息
        file_info.update({
            "download_url": f"/static/{file_path.name}",
            "size_formatted": format_size(file_info["actual_size"]),
            "created_time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return {
            "success": True,
            "message": f"成功创建示例文件: {file_path.name}",
            "file_info": file_info
        }
        
    except Exception as e:
        logger.error(f"创建示例文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建示例文件失败: {str(e)}")

@app.post("/api/file-generator/create-preset")
async def create_preset_file_api(request: dict):
    """创建预设大小的示例文件"""
    try:
        preset_name = request.get("preset", "medium")
        content_type = request.get("content_type", "text")
        custom_name = request.get("file_name", "")
        
        # 验证预设名称
        if preset_name not in PRESET_SIZES:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的预设名称。可用选项: {list(PRESET_SIZES.keys())}"
            )
        
        # 生成文件名
        if custom_name:
            file_name = custom_name
        else:
            timestamp = int(time.time())
            size_str = format_size(PRESET_SIZES[preset_name]).replace(" ", "").replace(".", "_")
            file_name = f"preset_{preset_name}_{size_str}_{content_type}_{timestamp}.txt"
        
        # 确保文件名安全
        file_name = "".join(c for c in file_name if c.isalnum() or c in "._-")
        if not file_name.endswith(('.txt', '.bin', '.dat')):
            file_name += '.txt'
        
        file_path = static_dir / file_name
        
        # 创建预设文件
        file_info = create_preset_file(
            preset_name=preset_name,
            file_path=file_path,
            content_type=content_type
        )
        
        # 添加额外信息
        file_info.update({
            "preset_name": preset_name,
            "download_url": f"/static/{file_path.name}",
            "size_formatted": format_size(file_info["actual_size"]),
            "created_time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return {
            "success": True,
            "message": f"成功创建预设文件: {file_path.name}",
            "file_info": file_info
        }
        
    except Exception as e:
        logger.error(f"创建预设文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建预设文件失败: {str(e)}")

@app.post("/api/file-generator/create-and-transfer")
async def create_and_transfer_file(request: dict):
    """创建示例文件并立即传输"""
    try:
        # 创建文件部分的参数
        size_input = request.get("size", "1KB")
        content_type = request.get("content_type", "text")
        include_metadata = request.get("include_metadata", True)
        
        # 传输部分的参数
        sender_id = request.get("sender_id")
        recipients = request.get("recipients", [])
        
        # 验证传输参数
        if not sender_id or sender_id not in cluster.nodes:
            raise HTTPException(status_code=404, detail="发送节点未找到")
        
        if not recipients:
            raise HTTPException(status_code=400, detail="请指定接收节点")
        
        # 解析文件大小
        try:
            size_bytes = parse_size_string(size_input)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的文件大小格式: {str(e)}")
        
        # 验证文件大小
        max_size = 1024 * 1024 * 1024  # 1GB
        if not validate_file_size(size_bytes, max_size):
            raise HTTPException(
                status_code=400, 
                detail=f"文件大小超出限制。最大允许: {format_size(max_size)}"
            )
        
        # 生成唯一文件名
        timestamp = int(time.time())
        size_str = format_size(size_bytes).replace(" ", "").replace(".", "_")
        file_name = f"transfer_{size_str}_{content_type}_{timestamp}.txt"
        file_path = static_dir / file_name
        
        # 创建示例文件
        file_info = create_sample_file(
            file_path=file_path,
            size_bytes=size_bytes,
            content_type=content_type,
            include_metadata=include_metadata
        )
        
        # 验证接收节点
        sender_node = cluster.nodes[sender_id]
        valid_recipients = []
        for recipient_id in recipients:
            if recipient_id in cluster.nodes:
                valid_recipients.append(recipient_id)
        
        if not valid_recipients:
            raise HTTPException(status_code=400, detail="没有有效的接收节点")
        
        # 执行文件传输
        transfer_results = []
        for recipient_id in valid_recipients:
            try:
                result = await sender_node.send_file_to_node(
                    file_path=str(file_path),
                    recipient_id=recipient_id
                )
                transfer_results.append({
                    "recipient_id": recipient_id,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                transfer_results.append({
                    "recipient_id": recipient_id,
                    "success": False,
                    "error": str(e)
                })
        
        # 统计传输结果
        successful_transfers = [r for r in transfer_results if r["success"]]
        failed_transfers = [r for r in transfer_results if not r["success"]]
        
        # 广播传输状态更新
        if websocket_connections:
            notification = {
                "type": "file_generated_and_transferred",
                "data": {
                    "file_name": file_name,
                    "file_size": format_size(file_info["actual_size"]),
                    "sender_id": sender_id,
                    "successful_transfers": len(successful_transfers),
                    "failed_transfers": len(failed_transfers),
                    "total_recipients": len(recipients)
                }
            }
            for ws in websocket_connections:
                try:
                    await ws.send_text(json.dumps(notification))
                except:
                    pass
        
        return {
            "success": True,
            "message": f"成功创建并传输文件: {file_name}",
            "file_info": {
                **file_info,
                "size_formatted": format_size(file_info["actual_size"]),
                "created_time": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "transfer_summary": {
                "total_recipients": len(recipients),
                "successful_transfers": len(successful_transfers),
                "failed_transfers": len(failed_transfers),
                "transfer_results": transfer_results
            }
        }
        
    except Exception as e:
        logger.error(f"创建并传输文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建并传输文件失败: {str(e)}")

@app.get("/api/file-generator/files")
async def list_generated_files():
    """列出所有生成的示例文件"""
    try:
        files = []
        
        # 扫描static目录中的文件
        for file_path in static_dir.iterdir():
            if file_path.is_file() and (
                file_path.name.startswith(('sample_', 'preset_', 'transfer_')) or
                file_path.suffix.lower() in ['.txt', '.bin', '.dat']
            ):
                stat = file_path.stat()
                files.append({
                    "file_name": file_path.name,
                    "file_size": stat.st_size,
                    "size_formatted": format_size(stat.st_size),
                    "created_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
                    "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                    "download_url": f"/static/{file_path.name}",
                    "is_generated": file_path.name.startswith(('sample_', 'preset_', 'transfer_'))
                })
        
        # 按创建时间排序（最新的在前）
        files.sort(key=lambda x: x["created_time"], reverse=True)
        
        return {
            "success": True,
            "files": files,
            "total_count": len(files),
            "total_size": sum(f["file_size"] for f in files),
            "total_size_formatted": format_size(sum(f["file_size"] for f in files))
        }
        
    except Exception as e:
        logger.error(f"列出生成文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出生成文件失败: {str(e)}")

@app.delete("/api/file-generator/files/{file_name}")
async def delete_generated_file(file_name: str):
    """删除指定的生成文件"""
    try:
        # 确保文件名安全
        file_name = "".join(c for c in file_name if c.isalnum() or c in "._-")
        file_path = static_dir / file_name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="不是有效的文件")
        
        # 删除文件
        file_size = file_path.stat().st_size
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"成功删除文件: {file_name}",
            "deleted_size": file_size,
            "deleted_size_formatted": format_size(file_size)
        }
        
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")

@app.post("/api/file-generator/create-demo")
async def create_demo_file(request: dict):
    """为演示文件列表创建自定义大小的文件"""
    try:
        size_str = request.get("size", "1MB")
        content_type = request.get("content_type", "random")
        
        # 确保demo_files目录存在
        demo_dir = Path("demo_files")
        demo_dir.mkdir(exist_ok=True)
        
        # 解析文件大小
        actual_size = parse_size_string(size_str)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%H%M%S")
        formatted_size_name = format_size(actual_size).replace(' ', '_').lower()
        filename = f"custom_test_{formatted_size_name}_{timestamp}.bin"
        file_path = demo_dir / filename
        
        # 创建文件
        success = create_sample_file(str(file_path), actual_size, content_type)
        
        if success:
            return {
                "success": True,
                "filename": filename,
                "actual_size": actual_size,
                "formatted_size": format_size(actual_size),
                "content_type": content_type,
                "path": str(file_path)
            }
        else:
            return {"success": False, "message": "文件创建失败"}
            
    except Exception as e:
        logger.error(f"创建演示文件失败: {e}")
        return {"success": False, "message": f"创建演示文件失败: {str(e)}"}

# ============ 文件生成和传输功能结束 ============

if __name__ == "__main__":
    # 从配置文件获取Web服务器设置
    web_config = config.get("web_server", {})
    host = web_config.get("host", "0.0.0.0")
    port = web_config.get("port", 8000)
    log_level = web_config.get("log_level", "info")
    
    logger.info(f"启动Web服务器: {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level=log_level)
