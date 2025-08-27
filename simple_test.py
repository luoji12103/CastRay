#!/usr/bin/env python3
"""
简化版测试脚本 - 不依赖外部包
"""

import socket
import json
import time
import threading
from typing import Dict, List
import uuid

class SimpleNode:
    """简单的消息节点"""
    
    def __init__(self, node_id: str, port: int = 0):
        self.node_id = node_id
        self.port = port
        self.socket = None
        self.running = False
        self.received_messages = []
        self.sent_messages = []
        
    def start(self):
        """启动节点"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if self.port == 0:
                self.socket.bind(('localhost', 0))
                self.port = self.socket.getsockname()[1]
            else:
                self.socket.bind(('localhost', self.port))
            
            self.socket.settimeout(0.5)
            self.running = True
            print(f"✅ 节点 {self.node_id} 启动成功，端口: {self.port}")
            
            # 启动监听线程
            self.listen_thread = threading.Thread(target=self._listen_loop)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            
            return True
        except Exception as e:
            print(f"❌ 节点 {self.node_id} 启动失败: {e}")
            return False
    
    def stop(self):
        """停止节点"""
        self.running = False
        if self.socket:
            self.socket.close()
        print(f"🛑 节点 {self.node_id} 已停止")
    
    def _listen_loop(self):
        """监听消息循环"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = json.loads(data.decode('utf-8'))
                self.received_messages.append({
                    'from': f"{addr[0]}:{addr[1]}",
                    'message': message,
                    'timestamp': time.time()
                })
                print(f"📨 节点 {self.node_id} 收到消息: {message['content']}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ 节点 {self.node_id} 接收消息错误: {e}")
    
    def send_unicast(self, message: dict, target_ip: str, target_port: int):
        """发送单播消息"""
        try:
            message_data = json.dumps(message).encode('utf-8')
            self.socket.sendto(message_data, (target_ip, target_port))
            self.sent_messages.append({
                'target': f"{target_ip}:{target_port}",
                'message': message,
                'timestamp': time.time()
            })
            print(f"📤 节点 {self.node_id} 发送单播: {message['content']} -> {target_ip}:{target_port}")
            return True
        except Exception as e:
            print(f"❌ 单播发送失败: {e}")
            return False
    
    def send_broadcast(self, message: dict, broadcast_port: int):
        """发送广播消息"""
        try:
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            message_data = json.dumps(message).encode('utf-8')
            broadcast_socket.sendto(message_data, ('<broadcast>', broadcast_port))
            broadcast_socket.close()
            
            self.sent_messages.append({
                'type': 'broadcast',
                'message': message,
                'timestamp': time.time()
            })
            print(f"📡 节点 {self.node_id} 发送广播: {message['content']}")
            return True
        except Exception as e:
            print(f"❌ 广播发送失败: {e}")
            return False


class SimpleCluster:
    """简单的集群管理器"""
    
    def __init__(self):
        self.nodes: Dict[str, SimpleNode] = {}
        
    def create_node(self, node_id: str, port: int = 0) -> bool:
        """创建节点"""
        if node_id in self.nodes:
            print(f"⚠️ 节点 {node_id} 已存在")
            return False
            
        node = SimpleNode(node_id, port)
        if node.start():
            self.nodes[node_id] = node
            return True
        return False
    
    def remove_node(self, node_id: str) -> bool:
        """删除节点"""
        if node_id in self.nodes:
            self.nodes[node_id].stop()
            del self.nodes[node_id]
            return True
        return False
    
    def send_unicast(self, sender_id: str, receiver_id: str, content: str) -> bool:
        """发送单播消息"""
        if sender_id not in self.nodes or receiver_id not in self.nodes:
            print(f"❌ 节点不存在: {sender_id} 或 {receiver_id}")
            return False
            
        message = {
            'id': str(uuid.uuid4()),
            'content': content,
            'sender': sender_id,
            'timestamp': time.time()
        }
        
        sender = self.nodes[sender_id]
        receiver = self.nodes[receiver_id]
        
        return sender.send_unicast(message, 'localhost', receiver.port)
    
    def send_broadcast(self, sender_id: str, content: str) -> bool:
        """发送广播消息"""
        if sender_id not in self.nodes:
            print(f"❌ 发送节点不存在: {sender_id}")
            return False
            
        message = {
            'id': str(uuid.uuid4()),
            'content': content,
            'sender': sender_id,
            'timestamp': time.time()
        }
        
        sender = self.nodes[sender_id]
        return sender.send_broadcast(message, 9998)
    
    def get_status(self):
        """获取集群状态"""
        status = {
            'total_nodes': len(self.nodes),
            'nodes': {}
        }
        
        for node_id, node in self.nodes.items():
            status['nodes'][node_id] = {
                'port': node.port,
                'running': node.running,
                'received_count': len(node.received_messages),
                'sent_count': len(node.sent_messages)
            }
        
        return status


def test_simple_system():
    """测试简单系统"""
    print("🚀 开始测试简化版分布式消息传输系统...\n")
    
    # 创建集群
    cluster = SimpleCluster()
    
    # 创建测试节点
    nodes = ['sender', 'receiver1', 'receiver2', 'receiver3']
    print("📦 创建测试节点...")
    
    for node_id in nodes:
        if cluster.create_node(node_id):
            print(f"✅ 节点 {node_id} 创建成功")
        else:
            print(f"❌ 节点 {node_id} 创建失败")
    
    time.sleep(1)  # 等待节点启动
    
    # 显示集群状态
    status = cluster.get_status()
    print(f"\n📊 集群状态: {status['total_nodes']} 个节点")
    for node_id, info in status['nodes'].items():
        print(f"  - {node_id}: 端口 {info['port']}, 运行中: {info['running']}")
    
    # 测试单播
    print("\n🎯 测试单播消息...")
    cluster.send_unicast('sender', 'receiver1', 'Hello from sender to receiver1!')
    cluster.send_unicast('sender', 'receiver2', 'Hello from sender to receiver2!')
    
    time.sleep(1)  # 等待消息传递
    
    # 测试广播
    print("\n📡 测试广播消息...")
    cluster.send_broadcast('sender', 'Broadcast message to all!')
    
    time.sleep(1)  # 等待消息传递
    
    # 性能测试
    print("\n⚡ 性能测试 (50条消息)...")
    start_time = time.time()
    
    for i in range(50):
        cluster.send_unicast('sender', 'receiver1', f'Performance test message {i}')
    
    end_time = time.time()
    print(f"发送50条消息耗时: {end_time - start_time:.3f}秒")
    print(f"平均速度: {50/(end_time - start_time):.1f} 消息/秒")
    
    time.sleep(2)  # 等待所有消息处理
    
    # 显示消息统计
    print("\n📈 消息统计:")
    final_status = cluster.get_status()
    for node_id, info in final_status['nodes'].items():
        print(f"  - {node_id}: 发送 {info['sent_count']}, 接收 {info['received_count']}")
    
    # 清理
    print("\n🧹 清理测试环境...")
    for node_id in nodes:
        cluster.remove_node(node_id)
    
    print("✅ 测试完成!")


if __name__ == "__main__":
    test_simple_system()
