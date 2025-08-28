import ray
import asyncio
import socket
import threading
import time
import json
import uuid
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from models import CastMessage, CastType, MessageType, CastResponse, NodeStatus
from file_transfer import FileTransferManager, FileTransferMessage, FileTransferProtocol
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_to_ray_cluster(ray_address: Optional[str] = None, namespace: str = "castray"):
    """连接到已有的Ray集群或启动新集群"""
    try:
        # 如果Ray已经初始化，先关闭
        if ray.is_initialized():
            ray.shutdown()
        
        # 获取Ray集群地址
        if ray_address is None:
            ray_address = os.environ.get('RAY_ADDRESS', 'local')
        
        # 配置运行时环境
        runtime_env = {}
        if platform.system() == "Linux":
            runtime_env = {
                "working_dir": os.getcwd(),
                "env_vars": {
                    "PYTHONPATH": os.getcwd(),
                    "RAY_DISABLE_IMPORT_WARNING": "1"
                }
            }
        
        # 简化初始化逻辑，强制使用本地模式避免连接问题
        if ray_address in ['auto', 'local', None]:
            # 启动本地集群
            logger.info("启动本地Ray集群...")
            cpu_count = os.cpu_count() or 2
            num_cpus = max(1, cpu_count // 2)  # 使用一半CPU核心
            
            ray.init(
                namespace=namespace, 
                runtime_env=runtime_env,
                ignore_reinit_error=True,
                dashboard_host='127.0.0.1',  # 改为本地地址
                dashboard_port=8265,
                object_store_memory=100*1024*1024,  # 100MB
                num_cpus=num_cpus,
                _temp_dir=os.path.join(os.getcwd(), "ray_temp")  # 指定临时目录
            )
            logger.info("成功启动本地Ray集群")
            logger.info(f"Ray Dashboard: http://127.0.0.1:8265")
            logger.info(f"Ray集群资源: {ray.cluster_resources()}")
            return True
        else:
            # 连接到指定地址 - 不提供硬件资源参数
            logger.info(f"尝试连接到指定Ray集群: {ray_address}")
            ray.init(address=ray_address, namespace=namespace, runtime_env=runtime_env)
            logger.info(f"成功连接到Ray集群: {ray_address}")
            logger.info(f"Ray集群资源: {ray.cluster_resources()}")
            return True
        
    except Exception as e:
        logger.error(f"Ray集群初始化失败: {e}")
        
        # 最后的后备方案：最简单的本地初始化
        try:
            logger.info("尝试最简单的Ray本地初始化...")
            if ray.is_initialized():
                ray.shutdown()
            ray.init(ignore_reinit_error=True, log_to_driver=False)
            logger.info("使用简化模式成功启动Ray")
            return True
        except Exception as fallback_e:
            logger.error(f"最简化Ray初始化也失败: {fallback_e}")
            return False

@ray.remote
class CastingNode:
    """Ray远程类，处理单个节点的消息传输和文件传输"""
    
    def __init__(self, node_id: str, port: int = 0):
        self.node_id = node_id
        self.port = port
        self.is_running = False
        self.socket = None
        self.message_handlers = {}
        self.received_messages = []
        self.sent_messages = []
        
        # 文件传输管理器
        self.file_transfer_manager = FileTransferManager(f"downloads/{node_id}")
        self.file_msg_factory = FileTransferMessage()
        
        # 自动传输任务队列
        self.auto_transfer_queue = []
        self.auto_transfer_enabled = True
        
    async def start(self):
        """启动节点"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if self.port == 0:
                self.socket.bind(('localhost', 0))
                self.port = self.socket.getsockname()[1]
            else:
                self.socket.bind(('localhost', self.port))
            
            self.socket.settimeout(0.1)
            self.is_running = True
            logger.info(f"节点 {self.node_id} 启动在端口 {self.port}")
            return True
        except Exception as e:
            logger.error(f"节点 {self.node_id} 启动失败: {e}")
            return False
    
    async def stop(self):
        """停止节点"""
        self.is_running = False
        if self.socket:
            self.socket.close()
        logger.info(f"节点 {self.node_id} 已停止")
    
    async def send_unicast(self, message: dict, target_ip: str, target_port: int):
        """发送单播消息"""
        try:
            if not self.socket:
                return {"success": False, "error": "Socket not initialized"}
            
            message_data = json.dumps(message).encode('utf-8')
            self.socket.sendto(message_data, (target_ip, target_port))
            
            self.sent_messages.append({
                "type": "unicast",
                "target": f"{target_ip}:{target_port}",
                "message": message,
                "timestamp": time.time()
            })
            
            return {"success": True, "target": f"{target_ip}:{target_port}"}
        except Exception as e:
            logger.error(f"单播发送失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_multicast(self, message: dict, group_ip: str, group_port: int):
        """发送组播消息"""
        try:
            multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 设置TTL
            multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            
            message_data = json.dumps(message).encode('utf-8')
            multicast_socket.sendto(message_data, (group_ip, group_port))
            multicast_socket.close()
            
            self.sent_messages.append({
                "type": "multicast", 
                "group": f"{group_ip}:{group_port}",
                "message": message,
                "timestamp": time.time()
            })
            
            return {"success": True, "group": f"{group_ip}:{group_port}"}
        except Exception as e:
            logger.error(f"组播发送失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_broadcast(self, message: dict, broadcast_port: int):
        """发送广播消息"""
        try:
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            message_data = json.dumps(message).encode('utf-8')
            broadcast_socket.sendto(message_data, ('<broadcast>', broadcast_port))
            broadcast_socket.close()
            
            self.sent_messages.append({
                "type": "broadcast",
                "port": broadcast_port,
                "message": message,
                "timestamp": time.time()
            })
            
            return {"success": True, "broadcast_port": broadcast_port}
        except Exception as e:
            logger.error(f"广播发送失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def listen_for_messages(self):
        """监听接收消息"""
        while self.is_running:
            try:
                if self.socket:
                    data, addr = self.socket.recvfrom(65536)  # 增大缓冲区以支持文件块
                    message = json.loads(data.decode('utf-8'))
                    
                    # 检查是否为文件传输消息
                    if message.get("type", "").startswith("file_"):
                        await self.handle_file_message(message, addr)
                    else:
                        # 普通消息
                        self.received_messages.append({
                            "from": f"{addr[0]}:{addr[1]}",
                            "message": message,
                            "timestamp": time.time()
                        })
                        
                        logger.info(f"节点 {self.node_id} 收到来自 {addr} 的消息: {message}")
                    
            except socket.timeout:
                # 处理自动传输队列
                if self.auto_transfer_enabled:
                    await self.process_auto_transfers()
                continue
            except Exception as e:
                if self.is_running:
                    logger.error(f"接收消息错误: {e}")
            
            await asyncio.sleep(0.01)
    
    async def initiate_file_transfer(self, file_path: str, recipients: List[str], 
                                   transfer_mode: str = "unicast"):
        """主动发起文件传输"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return {"success": False, "error": "文件不存在"}
            
            # 创建传输会话
            file_id = await self.file_transfer_manager.initiate_file_transfer(
                file_path, recipients, transfer_mode, self.node_id
            )
            
            # 发送传输请求
            request_msg = self.file_msg_factory.create_transfer_request(
                file_path, file_id, self.node_id, recipients, transfer_mode
            )
            
            # 根据传输模式发送请求
            success_count = 0
            if transfer_mode == "unicast":
                # 单播到每个接收者
                for recipient in recipients:
                    # 这里需要获取接收者的地址，暂时使用本地地址示例
                    success = await self._send_message_to_recipient(request_msg, recipient)
                    if success:
                        success_count += 1
            elif transfer_mode == "broadcast":
                # 广播
                success = await self._send_broadcast_message(request_msg)
                if success:
                    success_count = len(recipients)
            
            logger.info(f"节点 {self.node_id} 发起文件传输: {file_path} -> {recipients}")
            
            return {
                "success": success_count > 0,
                "file_id": file_id,
                "recipients_notified": success_count,
                "transfer_mode": transfer_mode
            }
            
        except Exception as e:
            logger.error(f"发起文件传输失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_message_to_recipient(self, message: dict, recipient_id: str):
        """向特定接收者发送消息"""
        try:
            # 这里应该根据recipient_id查找实际的网络地址
            # 暂时使用示例端口映射
            port_mapping = {
                "node_1": 64406, "node_2": 64409, "node_3": 64412
            }
            
            if recipient_id in port_mapping:
                message_data = json.dumps(message).encode('utf-8')
                self.socket.sendto(message_data, ('localhost', port_mapping[recipient_id]))
                return True
            else:
                logger.warning(f"未找到接收者地址: {recipient_id}")
                return False
        except Exception as e:
            logger.error(f"发送消息到 {recipient_id} 失败: {e}")
            return False
    
    async def _send_broadcast_message(self, message: dict):
        """发送广播消息"""
        try:
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            message_data = json.dumps(message).encode('utf-8')
            broadcast_socket.sendto(message_data, ('<broadcast>', 9998))
            broadcast_socket.close()
            
            return True
        except Exception as e:
            logger.error(f"广播消息失败: {e}")
            return False
    
    async def handle_file_message(self, message: dict, sender_addr):
        """处理文件传输相关消息"""
        try:
            msg_type = message.get("type", "")
            
            if msg_type == "file_transfer_request":
                # 处理文件传输请求
                response = self.file_transfer_manager.handle_transfer_request(message, auto_accept=True)
                await self._send_response_to_sender(response, sender_addr)
                
                logger.info(f"节点 {self.node_id} 接收文件传输请求: {message['file_info']['file_name']}")
                
            elif msg_type == "file_chunk":
                # 处理文件块
                ack = self.file_transfer_manager.handle_chunk_message(message)
                await self._send_response_to_sender(ack, sender_addr)
                
                # 检查是否接收完所有块
                file_id = message["file_id"]
                chunks = self.file_transfer_manager.received_chunks.get(file_id, [])
                expected_chunks = message["chunk"].get("total_chunks", 0)
                
                if len(chunks) == expected_chunks:
                    # 完成文件传输
                    file_info = {"file_name": f"received_file_{file_id}", "file_hash": ""}
                    complete_response = self.file_transfer_manager.complete_file_transfer(file_id, file_info)
                    await self._send_response_to_sender(complete_response, sender_addr)
                    
            elif msg_type in ["file_transfer_accept", "file_transfer_reject"]:
                # 处理传输响应
                file_id = message["file_id"]
                transfer = self.file_transfer_manager.get_transfer_status(file_id)
                
                if transfer and msg_type == "file_transfer_accept":
                    # 开始发送文件块
                    await self._start_sending_chunks(file_id, sender_addr)
                    
            elif msg_type == "file_chunk_ack":
                # 处理块确认
                logger.debug(f"收到块确认: {message}")
                
            elif msg_type == "file_transfer_complete":
                # 处理传输完成
                logger.info(f"文件传输完成: {message}")
                
        except Exception as e:
            logger.error(f"处理文件消息失败: {e}")
    
    async def _send_response_to_sender(self, response: dict, sender_addr):
        """向发送者发送响应"""
        try:
            response_data = json.dumps(response).encode('utf-8')
            self.socket.sendto(response_data, sender_addr)
        except Exception as e:
            logger.error(f"发送响应失败: {e}")
    
    async def _start_sending_chunks(self, file_id: str, receiver_addr):
        """开始发送文件块"""
        try:
            transfer = self.file_transfer_manager.get_transfer_status(file_id)
            if not transfer:
                return
            
            chunks = transfer["chunks"]
            for chunk in chunks:
                chunk_msg = self.file_msg_factory.create_chunk_message(
                    file_id, chunk, self.node_id
                )
                
                chunk_data = json.dumps(chunk_msg).encode('utf-8')
                self.socket.sendto(chunk_data, receiver_addr)
                
                # 添加小延迟避免网络拥塞
                await asyncio.sleep(0.01)
                
            logger.info(f"完成发送 {len(chunks)} 个文件块")
            
        except Exception as e:
            logger.error(f"发送文件块失败: {e}")
    
    def schedule_auto_transfer(self, file_path: str, recipients: List[str], 
                             transfer_mode: str = "unicast", delay: float = 0):
        """安排自动文件传输"""
        if self.auto_transfer_enabled:
            transfer_task = {
                "file_path": file_path,
                "recipients": recipients,
                "transfer_mode": transfer_mode,
                "schedule_time": time.time() + delay,
                "attempts": 0,
                "max_attempts": 3
            }
            self.auto_transfer_queue.append(transfer_task)
            logger.info(f"安排自动传输: {file_path} -> {recipients} (延迟: {delay}秒)")
    
    async def process_auto_transfers(self):
        """处理自动传输队列"""
        current_time = time.time()
        completed_tasks = []
        
        for i, task in enumerate(self.auto_transfer_queue):
            if current_time >= task["schedule_time"]:
                try:
                    result = await self.initiate_file_transfer(
                        task["file_path"], 
                        task["recipients"], 
                        task["transfer_mode"]
                    )
                    
                    if result["success"]:
                        logger.info(f"自动传输成功: {task['file_path']}")
                        completed_tasks.append(i)
                    else:
                        task["attempts"] += 1
                        if task["attempts"] >= task["max_attempts"]:
                            logger.error(f"自动传输失败，已达最大重试次数: {task['file_path']}")
                            completed_tasks.append(i)
                        else:
                            # 重新安排
                            task["schedule_time"] = current_time + 10  # 10秒后重试
                            
                except Exception as e:
                    logger.error(f"处理自动传输任务失败: {e}")
                    completed_tasks.append(i)
        
        # 移除已完成的任务
        for i in reversed(completed_tasks):
            del self.auto_transfer_queue[i]
    
    def get_status(self):
        """获取节点状态"""
        file_stats = self.file_transfer_manager.get_statistics()
        
        return {
            "node_id": self.node_id,
            "port": self.port,
            "is_running": self.is_running,
            "received_count": len(self.received_messages),
            "sent_count": len(self.sent_messages),
            "last_activity": max(
                [msg["timestamp"] for msg in self.received_messages] +
                [msg["timestamp"] for msg in self.sent_messages] + [0]
            ),
            "file_transfer_stats": file_stats,
            "active_transfers": len(self.file_transfer_manager.get_all_transfers()),
            "auto_transfer_queue": len(self.auto_transfer_queue),
            "auto_transfer_enabled": self.auto_transfer_enabled
        }
    
    def get_messages(self, count: int = 50):
        """获取最近的消息"""
        all_messages = []
        
        for msg in self.received_messages[-count:]:
            all_messages.append({
                "direction": "received",
                **msg
            })
        
        for msg in self.sent_messages[-count:]:
            all_messages.append({
                "direction": "sent", 
                **msg
            })
        
        return sorted(all_messages, key=lambda x: x["timestamp"], reverse=True)[:count]


class CastingCluster:
    """消息传输集群管理器"""
    
    def __init__(self):
        self.nodes: Dict[str, Any] = {}  # Ray actor handles
        self.node_ports: Dict[str, int] = {}
        self.is_initialized = False
        
    async def initialize_ray(self, ray_address: Optional[str] = None, namespace: str = "castray"):
        """初始化Ray集群连接"""
        try:
            # 使用新的连接函数
            success = connect_to_ray_cluster(ray_address, namespace)
            if success:
                self.is_initialized = True
                logger.info("Ray集群初始化成功")
                return True
            else:
                logger.error("Ray集群初始化失败")
                return False
        except Exception as e:
            logger.error(f"Ray集群初始化失败: {e}")
            try:
                ray.init(ignore_reinit_error=True)
                self.is_initialized = True
                logger.info("Ray本地模式初始化成功")
                return True
            except Exception as e2:
                logger.error(f"Ray本地模式初始化也失败: {e2}")
                return False
    
    async def create_node(self, node_id: str, port: int = 0) -> bool:
        """创建新节点"""
        try:
            if not self.is_initialized:
                await self.initialize_ray()
            
            node_ref = CastingNode.remote(node_id, port)
            success = await node_ref.start.remote()
            
            if success:
                self.nodes[node_id] = node_ref
                if port == 0:
                    # 获取实际分配的端口
                    status = await node_ref.get_status.remote()
                    self.node_ports[node_id] = status["port"]
                else:
                    self.node_ports[node_id] = port
                    
                logger.info(f"节点 {node_id} 创建成功，端口: {self.node_ports[node_id]}")
                return True
            return False
        except Exception as e:
            logger.error(f"创建节点 {node_id} 失败: {e}")
            return False
    
    async def remove_node(self, node_id: str) -> bool:
        """移除节点"""
        try:
            if node_id in self.nodes:
                await self.nodes[node_id].stop.remote()
                del self.nodes[node_id]
                if node_id in self.node_ports:
                    del self.node_ports[node_id]
                logger.info(f"节点 {node_id} 已移除")
                return True
            return False
        except Exception as e:
            logger.error(f"移除节点 {node_id} 失败: {e}")
            return False
    
    async def send_message(self, cast_message: CastMessage) -> CastResponse:
        """发送消息"""
        start_time = time.time()
        results = []
        failed_recipients = []
        
        try:
            if cast_message.sender not in self.nodes:
                return CastResponse(
                    success=False,
                    message="发送节点不存在",
                    recipients_count=0
                )
            
            sender_node = self.nodes[cast_message.sender]
            message_data = {
                "id": cast_message.id,
                "content": cast_message.content,
                "message_type": cast_message.message_type,
                "timestamp": cast_message.timestamp or time.time()
            }
            
            if cast_message.cast_type == CastType.UNICAST:
                # 单播
                for recipient in cast_message.recipients:
                    if recipient in self.node_ports:
                        result = await sender_node.send_unicast.remote(
                            message_data, 'localhost', self.node_ports[recipient]
                        )
                        results.append(result)
                        if not result.get("success"):
                            failed_recipients.append(recipient)
                    else:
                        failed_recipients.append(recipient)
            
            elif cast_message.cast_type == CastType.MULTICAST:
                # 组播
                group_ip = "224.1.1.1"  # 示例组播地址
                group_port = 9999
                result = await sender_node.send_multicast.remote(
                    message_data, group_ip, group_port
                )
                results.append(result)
                if not result.get("success"):
                    failed_recipients = cast_message.recipients
            
            elif cast_message.cast_type == CastType.BROADCAST:
                # 广播
                broadcast_port = 9998
                result = await sender_node.send_broadcast.remote(
                    message_data, broadcast_port
                )
                results.append(result)
                if not result.get("success"):
                    failed_recipients = list(self.nodes.keys())
            
            delivery_time = time.time() - start_time
            success_count = len([r for r in results if r.get("success")])
            
            return CastResponse(
                success=success_count > 0,
                message=f"消息发送完成，成功: {success_count}, 失败: {len(failed_recipients)}",
                recipients_count=success_count,
                failed_recipients=failed_recipients,
                delivery_time=delivery_time
            )
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return CastResponse(
                success=False,
                message=f"发送失败: {str(e)}",
                recipients_count=0,
                failed_recipients=cast_message.recipients
            )
    
    async def get_cluster_status(self) -> dict:
        """获取集群状态"""
        try:
            node_statuses = []
            for node_id, node_ref in self.nodes.items():
                try:
                    status = await node_ref.get_status.remote()
                    node_statuses.append(status)
                except:
                    node_statuses.append({
                        "node_id": node_id,
                        "is_running": False,
                        "error": "无法获取状态"
                    })
            
            ray_status = {}
            try:
                if ray.is_initialized():
                    ray_status = {
                        "cluster_resources": ray.cluster_resources(),
                        "available_resources": ray.available_resources(),
                        "nodes": len(ray.nodes())
                    }
            except:
                ray_status = {"error": "无法获取Ray状态"}
            
            return {
                "total_nodes": len(self.nodes),
                "active_nodes": len([s for s in node_statuses if s.get("is_running", False)]),
                "node_statuses": node_statuses,
                "ray_cluster": ray_status,
                "node_ports": self.node_ports
            }
        except Exception as e:
            logger.error(f"获取集群状态失败: {e}")
            return {"error": str(e)}
    
    async def get_node_messages(self, node_id: str, count: int = 50) -> list:
        """获取节点消息"""
        try:
            if node_id in self.nodes:
                return await self.nodes[node_id].get_messages.remote(count)
            return []
        except Exception as e:
            logger.error(f"获取节点 {node_id} 消息失败: {e}")
            return []
    
    async def initiate_node_file_transfer(self, sender_id: str, file_path: str, 
                                         recipients: List[str], transfer_mode: str = "unicast") -> CastResponse:
        """通过节点发起文件传输"""
        start_time = time.time()
        
        try:
            if sender_id not in self.nodes:
                return CastResponse(
                    success=False,
                    message="发送节点不存在",
                    recipients_count=0
                )
            
            sender_node = self.nodes[sender_id]
            result = await sender_node.initiate_file_transfer.remote(
                file_path, recipients, transfer_mode
            )
            
            delivery_time = time.time() - start_time
            
            if result["success"]:
                return CastResponse(
                    success=True,
                    message=f"文件传输已发起: {result['file_id']}",
                    recipients_count=result["recipients_notified"],
                    delivery_time=delivery_time
                )
            else:
                return CastResponse(
                    success=False,
                    message=f"文件传输发起失败: {result.get('error', '未知错误')}",
                    recipients_count=0,
                    delivery_time=delivery_time
                )
                
        except Exception as e:
            logger.error(f"发起节点文件传输失败: {e}")
            return CastResponse(
                success=False,
                message=f"发起失败: {str(e)}",
                recipients_count=0
            )
    
    async def schedule_auto_file_transfer(self, sender_id: str, file_path: str, 
                                        recipients: List[str], transfer_mode: str = "unicast",
                                        delay: float = 0) -> bool:
        """安排自动文件传输"""
        try:
            if sender_id not in self.nodes:
                logger.error(f"发送节点不存在: {sender_id}")
                return False
            
            sender_node = self.nodes[sender_id]
            await sender_node.schedule_auto_transfer.remote(
                file_path, recipients, transfer_mode, delay
            )
            
            logger.info(f"已安排节点 {sender_id} 的自动文件传输: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"安排自动文件传输失败: {e}")
            return False
    
    async def get_file_transfer_status(self, node_id: Optional[str] = None) -> dict:
        """获取文件传输状态"""
        try:
            if node_id:
                # 获取特定节点的状态
                if node_id in self.nodes:
                    status = await self.nodes[node_id].get_status.remote()
                    return {node_id: status}
                else:
                    return {"error": f"节点 {node_id} 不存在"}
            else:
                # 获取所有节点的状态
                all_status = {}
                for nid, node_ref in self.nodes.items():
                    try:
                        status = await node_ref.get_status.remote()
                        all_status[nid] = status
                    except Exception as e:
                        all_status[nid] = {"error": str(e)}
                
                return all_status
                
        except Exception as e:
            logger.error(f"获取文件传输状态失败: {e}")
            return {"error": str(e)}
    
    def shutdown(self):
        """关闭集群"""
        try:
            for node_id in list(self.nodes.keys()):
                asyncio.create_task(self.remove_node(node_id))
            if ray.is_initialized():
                ray.shutdown()
            logger.info("集群已关闭")
        except Exception as e:
            logger.error(f"关闭集群失败: {e}")


class NodeScheduler:
    """节点任务调度器 - 用于演示自动文件传输"""
    
    def __init__(self, cluster: CastingCluster):
        self.cluster = cluster
        self.running = False
        self.demo_files_dir = Path("demo_files")
        self.demo_files_dir.mkdir(exist_ok=True)
        
        # 创建演示文件
        self._create_demo_files()
    
    def _create_demo_files(self):
        """创建演示文件"""
        demo_files = [
            ("config.json", {"server": "localhost", "port": 8080, "timeout": 30}),
            ("data.txt", "这是一个测试文件\n包含多行数据\n用于演示文件传输功能"),
            ("report.md", "# 系统报告\n\n## 状态\n- 系统运行正常\n- 所有节点在线")
        ]
        
        for filename, content in demo_files:
            file_path = self.demo_files_dir / filename
            if not file_path.exists():
                if isinstance(content, dict):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
                logger.info(f"创建演示文件: {file_path}")
    
    async def start_demo_transfers(self):
        """启动演示传输"""
        self.running = True
        logger.info("开始演示自动文件传输...")
        
        while self.running:
            try:
                # 检查集群状态
                status = await self.cluster.get_cluster_status()
                active_nodes = [node['node_id'] for node in status.get('node_statuses', []) 
                              if node.get('is_running', False)]
                
                if len(active_nodes) >= 2:
                    # 随机选择发送者和接收者
                    import random
                    sender = random.choice(active_nodes)
                    receivers = [node for node in active_nodes if node != sender]
                    
                    if receivers:
                        # 随机选择文件
                        demo_files = list(self.demo_files_dir.glob("*"))
                        if demo_files:
                            file_to_send = random.choice(demo_files)
                            selected_receivers = random.sample(receivers, min(2, len(receivers)))
                            
                            # 发起传输
                            await self.cluster.schedule_auto_file_transfer(
                                sender, str(file_to_send), selected_receivers, "unicast", 0
                            )
                            
                            logger.info(f"演示传输: {sender} -> {selected_receivers} 文件: {file_to_send.name}")
                
                # 等待30秒后进行下一次传输
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"演示传输错误: {e}")
                await asyncio.sleep(10)
    
    def stop_demo_transfers(self):
        """停止演示传输"""
        self.running = False
        logger.info("停止演示传输")
    
    async def manual_transfer_demo(self, sender_id: str, file_name: str, recipients: List[str]):
        """手动触发演示传输"""
        file_path = self.demo_files_dir / file_name
        if file_path.exists():
            result = await self.cluster.initiate_node_file_transfer(
                sender_id, str(file_path), recipients, "unicast"
            )
            return result
        else:
            return CastResponse(
                success=False,
                message=f"演示文件不存在: {file_name}",
                recipients_count=0
            )


# 全局集群实例
cluster = CastingCluster()

# 全局调度器实例
scheduler = NodeScheduler(cluster)
