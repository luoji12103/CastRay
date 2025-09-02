#!/usr/bin/env python3
"""
独立的Ray集群启动脚本
用于启动Ray head节点和多个worker节点
"""

import ray
import time
import argparse
import logging
import subprocess
import sys
import os
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RayClusterManager:
    def __init__(self, head_port=10001, dashboard_port=8265):
        self.head_port = head_port
        self.dashboard_port = dashboard_port
        self.head_address = f"127.0.0.1:{head_port}"
        
    def start_head_node(self):
        """启动Ray head节点"""
        logger.info(f"启动Ray head节点，端口: {self.head_port}")
        
        try:
            # 如果已经有Ray实例在运行，先关闭
            if ray.is_initialized():
                ray.shutdown()
            
            # 强制启动新的head节点，不连接现有集群
            ray.init(
                ignore_reinit_error=True,
                dashboard_port=self.dashboard_port,
                include_dashboard=True,
                log_to_driver=False,
                # 不指定num_cpus，让Ray自动检测
            )
            
            logger.info(f"✅ Ray head节点启动成功")
            logger.info(f"🌐 Ray Dashboard: http://127.0.0.1:{self.dashboard_port}")
            
            # 获取集群地址
            try:
                context = ray.get_runtime_context()
                logger.info(f"🔗 连接地址: {context.gcs_address}")
            except:
                logger.info(f"🔗 Ray集群已启动")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ray head节点启动失败: {e}")
            return False
    
    def start_worker_nodes(self, num_workers=3):
        """启动多个worker节点"""
        logger.info(f"启动 {num_workers} 个worker节点...")
        
        # 注意：在这个简化版本中，我们不启动独立的worker进程
        # 而是通过创建Actor来模拟多节点行为
        logger.info("🚀 创建Ray Actor作为虚拟worker节点...")
        
        worker_actors = []
        
        for i in range(num_workers):
            try:
                worker_name = f"worker_{i+1}"
                logger.info(f"创建虚拟worker: {worker_name}")
                
                # 创建一个简单的Worker Actor
                @ray.remote
                class WorkerNode:
                    def __init__(self, name):
                        self.name = name
                        self.task_count = 0
                    
                    def get_status(self):
                        return {"name": self.name, "tasks": self.task_count}
                    
                    def process_task(self, task):
                        self.task_count += 1
                        return f"Worker {self.name} processed task: {task}"
                
                # 创建Actor实例
                worker = WorkerNode.remote(worker_name)
                worker_actors.append({
                    'name': worker_name,
                    'actor': worker
                })
                
                logger.info(f"✅ 虚拟worker {worker_name} 创建成功")
                
            except Exception as e:
                logger.error(f"❌ 启动worker节点 worker_{i+1} 失败: {e}")
        
        logger.info(f"✅ 已创建 {len(worker_actors)} 个虚拟worker节点")
        return worker_actors
    
    def create_demo_actors(self):
        """在集群中创建一些演示Actor"""
        logger.info("创建演示Actor...")
        
        try:
            @ray.remote
            class DemoNode:
                def __init__(self, node_id):
                    self.node_id = node_id
                    self.message_count = 0
                    
                def get_info(self):
                    return {
                        'node_id': self.node_id,
                        'message_count': self.message_count,
                        'status': 'running'
                    }
                
                def send_message(self, message):
                    self.message_count += 1
                    return f"Node {self.node_id} received: {message}"
            
            # 创建几个演示节点
            demo_actors = {}
            for i in range(3):
                node_id = f"demo_node_{i+1}"
                actor = DemoNode.remote(node_id)
                demo_actors[node_id] = actor
                logger.info(f"✅ 创建演示Actor: {node_id}")
            
            # 测试Actor通信
            logger.info("测试Actor通信...")
            for node_id, actor in demo_actors.items():
                result = ray.get(actor.send_message.remote("Hello from cluster manager"))
                logger.info(f"📤 {result}")
            
            return demo_actors
            
        except Exception as e:
            logger.error(f"❌ 创建演示Actor失败: {e}")
            return {}
    
    def show_cluster_info(self):
        """显示集群信息"""
        try:
            cluster_resources = ray.cluster_resources()
            available_resources = ray.available_resources()
            nodes = ray.nodes()
            
            logger.info("🎯 Ray集群信息:")
            logger.info(f"  总节点数: {len(nodes)}")
            logger.info(f"  总CPU: {cluster_resources.get('CPU', 0)}")
            logger.info(f"  可用CPU: {available_resources.get('CPU', 0)}")
            logger.info(f"  总内存: {cluster_resources.get('memory', 0)/1024/1024/1024:.1f} GB")
            
            logger.info("📋 节点详情:")
            for i, node in enumerate(nodes):
                logger.info(f"  节点 {i+1}: {node['NodeID'][:8]}... "
                          f"(CPU: {node['Resources'].get('CPU', 0)}, "
                          f"状态: {'活跃' if node['Alive'] else '离线'})")
            
        except Exception as e:
            logger.error(f"❌ 获取集群信息失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ray集群管理器")
    parser.add_argument("--head-port", type=int, default=10001, help="Head节点端口")
    parser.add_argument("--dashboard-port", type=int, default=8265, help="Dashboard端口")
    parser.add_argument("--workers", type=int, default=3, help="Worker节点数量")
    parser.add_argument("--no-demo", action="store_true", help="不创建演示Actor")
    
    args = parser.parse_args()
    
    manager = RayClusterManager(args.head_port, args.dashboard_port)
    
    try:
        # 启动head节点
        if not manager.start_head_node():
            logger.error("❌ Head节点启动失败，退出")
            return
        
        # 等待head节点完全启动
        time.sleep(3)
        
        # 启动worker节点
        worker_processes = manager.start_worker_nodes(args.workers)
        
        # 等待worker节点连接
        time.sleep(5)
        
        # 显示集群信息
        manager.show_cluster_info()
        
        # 创建演示Actor
        if not args.no_demo:
            demo_actors = manager.create_demo_actors()
        
        logger.info("🎉 Ray集群启动完成!")
        logger.info(f"🔗 其他程序可以使用以下地址连接: ray://127.0.0.1:{args.head_port}")
        logger.info("ℹ️  按 Ctrl+C 停止集群")
        
        # 保持运行
        try:
            while True:
                time.sleep(10)
                # 定期显示集群状态
                logger.info("💓 集群心跳检查...")
                manager.show_cluster_info()
                
        except KeyboardInterrupt:
            logger.info("🛑 收到停止信号，正在关闭集群...")
            
            # 关闭Ray
            ray.shutdown()
            logger.info("✅ 集群已关闭")
            
    except Exception as e:
        logger.error(f"❌ 集群管理错误: {e}")
        ray.shutdown()

if __name__ == "__main__":
    main()
