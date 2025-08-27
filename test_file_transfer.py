#!/usr/bin/env python3
"""
文件传输功能测试脚本
测试Ray节点自主发起文件传输功能
"""

import asyncio
import os
import time
import requests
import json
from pathlib import Path

# 测试配置
API_BASE = "http://localhost:8000"
TEST_NODES = ["node_A", "node_B", "node_C"]
TEST_FILE = "test_transfer.txt"

def create_test_file():
    """创建测试文件"""
    file_path = Path(TEST_FILE)
    content = f"""
测试文件传输功能
创建时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
文件大小: 这是一个用于测试分布式文件传输系统的示例文件。
包含中文和英文内容，用于验证文件完整性。

Test File Transfer Function
Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}
This is a sample file for testing distributed file transfer system.
Contains both Chinese and English content to verify file integrity.

数据内容:
""" + "A" * 1000  # 添加一些数据

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 测试文件已创建: {file_path} ({len(content.encode('utf-8'))} 字节)")
    return file_path

def test_api_connection():
    """测试API连接"""
    try:
        response = requests.get(f"{API_BASE}/api/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ API连接成功")
            print(f"   总节点数: {status.get('total_nodes', 0)}")
            print(f"   活跃节点: {status.get('active_nodes', 0)}")
            return True
        else:
            print(f"❌ API连接失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API连接异常: {e}")
        return False

def create_test_nodes():
    """创建测试节点"""
    print("\n🔧 创建测试节点...")
    created_nodes = []
    
    for i, node_id in enumerate(TEST_NODES):
        try:
            response = requests.post(
                f"{API_BASE}/api/nodes",
                json={"node_id": node_id, "port": 9000 + i},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"✅ 节点 {node_id} 创建成功")
                    created_nodes.append(node_id)
                else:
                    print(f"⚠️ 节点 {node_id} 创建失败: {result.get('message')}")
            else:
                print(f"❌ 节点 {node_id} 创建请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 创建节点 {node_id} 时异常: {e}")
    
    time.sleep(2)  # 等待节点启动
    return created_nodes

def test_file_transfer_status():
    """测试文件传输状态API"""
    print("\n📊 检查文件传输状态...")
    try:
        response = requests.get(f"{API_BASE}/api/file-transfers/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ 文件传输状态获取成功")
            
            for node_id, node_status in status.items():
                stats = node_status.get("file_transfer_stats", {})
                print(f"   {node_id}: 成功:{stats.get('successful_transfers', 0)} "
                      f"失败:{stats.get('failed_transfers', 0)} "
                      f"字节:{stats.get('bytes_transferred', 0)}")
            return True
        else:
            print(f"❌ 获取状态失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 状态检查异常: {e}")
        return False

def test_manual_transfer(sender, recipients, file_name):
    """测试手动文件传输"""
    print(f"\n🚀 测试手动传输: {sender} -> {recipients}")
    try:
        response = requests.post(
            f"{API_BASE}/api/file-transfers/manual",
            json={
                "sender_id": sender,
                "file_name": file_name,
                "recipients": recipients
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ 手动传输触发成功: {result.get('message')}")
                
                # 显示详细结果
                for transfer_result in result.get("results", []):
                    recipient = transfer_result.get("recipient")
                    success = transfer_result.get("success")
                    message = transfer_result.get("message", "")
                    status_icon = "✅" if success else "❌"
                    print(f"   {status_icon} {sender} -> {recipient}: {message}")
                
                return True
            else:
                print(f"❌ 手动传输失败: {result.get('message')}")
                return False
        else:
            print(f"❌ 手动传输请求失败: {response.status_code}")
            print(f"   响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 手动传输异常: {e}")
        return False

def test_auto_transfer_toggle(node_id, enabled=True):
    """测试自动传输开关"""
    action = "启用" if enabled else "禁用"
    print(f"\n🔄 {action}节点 {node_id} 的自动传输...")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/file-transfers/auto/toggle",
            json={"node_id": node_id, "enabled": enabled},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ {action}成功: {result.get('message')}")
                return True
            else:
                print(f"❌ {action}失败: {result.get('message')}")
                return False
        else:
            print(f"❌ {action}请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ {action}异常: {e}")
        return False

def run_comprehensive_test():
    """运行综合测试"""
    print("🎯 开始文件传输功能综合测试\n")
    
    # 1. 创建测试文件
    test_file = create_test_file()
    
    # 2. 测试API连接
    if not test_api_connection():
        print("❌ 测试终止: API连接失败")
        return
    
    # 3. 创建测试节点
    created_nodes = create_test_nodes()
    if len(created_nodes) < 2:
        print("❌ 测试终止: 需要至少2个节点")
        return
    
    print(f"✅ 成功创建 {len(created_nodes)} 个节点: {created_nodes}")
    
    # 4. 等待节点完全启动
    print("\n⏳ 等待节点完全启动...")
    time.sleep(3)
    
    # 5. 检查文件传输状态
    test_file_transfer_status()
    
    # 6. 测试自动传输开关
    if len(created_nodes) >= 1:
        test_auto_transfer_toggle(created_nodes[0], True)
        time.sleep(1)
        test_auto_transfer_toggle(created_nodes[0], False)
        time.sleep(1)
        test_auto_transfer_toggle(created_nodes[0], True)
    
    # 7. 测试手动文件传输
    if len(created_nodes) >= 2:
        # 单一接收者
        test_manual_transfer(
            created_nodes[0], 
            [created_nodes[1]], 
            str(test_file)
        )
        time.sleep(2)
        
        # 多个接收者
        if len(created_nodes) >= 3:
            test_manual_transfer(
                created_nodes[0], 
                created_nodes[1:], 
                str(test_file)
            )
            time.sleep(2)
    
    # 8. 再次检查传输状态
    test_file_transfer_status()
    
    # 9. 清理测试文件
    try:
        os.remove(test_file)
        print(f"\n🧹 测试文件已清理: {test_file}")
    except:
        pass
    
    print(f"\n🎉 文件传输功能测试完成！")
    print(f"   请通过Web界面 {API_BASE} 查看实时监控数据")

if __name__ == "__main__":
    try:
        run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试执行异常: {e}")
    
    print("\n💡 提示:")
    print("   1. 确保主服务器正在运行: python main.py")
    print("   2. 访问Web界面查看节点状态和传输监控")
    print("   3. 通过WebSocket可以看到实时传输活动")
