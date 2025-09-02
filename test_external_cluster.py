#!/usr/bin/env python3
"""
测试脚本：连接外部Ray集群并读取节点
"""

import asyncio
import time
import logging
import json
import requests
import signal
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_external_cluster_connection():
    """测试连接外部Ray集群功能"""
    
    logger.info("🧪 开始测试外部Ray集群连接功能")
    
    # 1. 检查配置文件
    config_file = Path("config_external_cluster.json")
    if not config_file.exists():
        logger.error("❌ 配置文件不存在: config_external_cluster.json")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"✅ 加载配置文件成功")
        logger.info(f"   Ray地址: {config['ray_cluster']['address']}")
        logger.info(f"   Web端口: {config['web_server']['port']}")
    except Exception as e:
        logger.error(f"❌ 配置文件加载失败: {e}")
        return False
    
    return True

def test_api_endpoints():
    """测试API端点"""
    
    base_url = "http://127.0.0.1:28823"
    
    logger.info("🔗 测试API端点...")
    
    endpoints_to_test = [
        ("/api/status", "系统状态"),
        ("/api/file-transfers/status", "文件传输状态"),
        ("/api/nodes/ray-info", "Ray集群信息")
    ]
    
    for endpoint, description in endpoints_to_test:
        try:
            url = f"{base_url}{endpoint}"
            logger.info(f"   测试 {description}: {url}")
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"   ✅ {description} 响应正常")
                
                if endpoint == "/api/status":
                    logger.info(f"      总节点数: {data.get('total_nodes', 'N/A')}")
                    logger.info(f"      活跃节点: {data.get('active_nodes', 'N/A')}")
                    
                    node_statuses = data.get('node_statuses', [])
                    for node in node_statuses:
                        node_type = node.get('node_type', '普通节点')
                        status = "在线" if node.get('is_running') else "离线"
                        logger.info(f"      节点: {node['node_id']} ({node_type}) - {status}")
                
            else:
                logger.warning(f"   ⚠️ {description} 响应异常: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"   ❌ 无法连接到 {description}")
        except Exception as e:
            logger.error(f"   ❌ 测试 {description} 失败: {e}")

def test_node_discovery():
    """测试节点发现功能"""
    
    logger.info("🔍 测试节点发现功能...")
    
    try:
        response = requests.get("http://127.0.0.1:28823/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # 检查是否发现了外部节点
            external_nodes = []
            for node in data.get('node_statuses', []):
                if node.get('node_type') in ['Ray节点', '外部Actor']:
                    external_nodes.append(node)
            
            if external_nodes:
                logger.info(f"✅ 发现了 {len(external_nodes)} 个外部节点:")
                for node in external_nodes:
                    logger.info(f"   - {node['node_id']} ({node.get('node_type', 'unknown')})")
            else:
                logger.warning("⚠️ 没有发现外部节点，可能Ray集群未运行或连接失败")
        else:
            logger.error(f"❌ 获取节点状态失败: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ 测试节点发现失败: {e}")

def test_transfer_with_external_nodes():
    """测试与外部节点的传输"""
    
    logger.info("📤 测试与外部节点的传输...")
    
    try:
        # 获取可用节点
        response = requests.get("http://127.0.0.1:28823/api/status", timeout=5)
        if response.status_code != 200:
            logger.error("❌ 无法获取节点列表")
            return
        
        data = response.json()
        nodes = data.get('node_statuses', [])
        
        if len(nodes) < 2:
            logger.warning("⚠️ 节点数量不足，无法测试传输")
            return
        
        # 选择发送者和接收者
        sender = nodes[0]['node_id']
        recipients = [node['node_id'] for node in nodes[1:3]]  # 最多选择2个接收者
        
        logger.info(f"   发送者: {sender}")
        logger.info(f"   接收者: {recipients}")
        
        # 发起传输测试
        transfer_data = {
            "sender_id": sender,
            "file_name": "config.json",
            "recipients": recipients
        }
        
        response = requests.post(
            "http://127.0.0.1:28823/api/file-transfers/manual",
            json=transfer_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                logger.info(f"✅ 传输请求已发起: {result.get('message', '')}")
            else:
                logger.warning(f"⚠️ 传输请求失败: {result.get('message', '')}")
        else:
            logger.error(f"❌ 传输请求失败: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ 测试传输失败: {e}")

def main():
    """主测试函数"""
    
    print("=" * 60)
    print("🚀 CastRay外部Ray集群连接测试")
    print("=" * 60)
    
    # 1. 测试配置
    if not test_external_cluster_connection():
        logger.error("❌ 配置测试失败，退出")
        return
    
    # 等待用户启动外部Ray集群
    print("\n📋 请按以下步骤操作:")
    print("1. 在一个新的终端中运行: python start_ray_cluster.py")
    print("2. 等待Ray集群完全启动")
    print("3. 在另一个终端中运行: python main.py")
    print("4. 按任意键继续测试...")
    input()
    
    # 2. 测试API端点
    test_api_endpoints()
    
    # 等待一下让系统稳定
    time.sleep(2)
    
    # 3. 测试节点发现
    test_node_discovery()
    
    # 等待一下
    time.sleep(2)
    
    # 4. 测试传输功能
    test_transfer_with_external_nodes()
    
    print("\n" + "=" * 60)
    print("🎉 测试完成!")
    print("=" * 60)
    
    # 5. 提供后续测试建议
    print("\n📝 后续测试建议:")
    print("1. 访问Web界面: http://127.0.0.1:28823/ui")
    print("2. 检查节点列表是否包含Ray集群节点")
    print("3. 尝试手动发起文件传输")
    print("4. 观察传输统计更新")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
