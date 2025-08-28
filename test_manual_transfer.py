#!/usr/bin/env python3
"""
测试手动文件传输功能
"""

import requests
import json
import time

def test_manual_transfer():
    """测试手动文件传输"""
    base_url = "http://localhost:8000"
    
    print("🧪 开始测试手动文件传输功能...")
    
    # 1. 获取系统状态
    print("\n📊 获取系统状态...")
    try:
        response = requests.get(f"{base_url}/api/status")
        if response.status_code == 200:
            status = response.json()
            nodes = status.get("node_statuses", [])
            print(f"✅ 发现 {len(nodes)} 个节点:")
            for node in nodes:
                print(f"  - {node['node_id']}: {'在线' if node.get('is_running') else '离线'}")
            
            if len(nodes) < 2:
                print("❌ 需要至少2个节点进行测试")
                return False
                
        else:
            print(f"❌ 获取状态失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False
    
    # 2. 发起手动传输
    print("\n🚀 发起手动文件传输...")
    try:
        sender_id = nodes[0]['node_id']
        recipient_id = nodes[1]['node_id'] if len(nodes) > 1 else nodes[0]['node_id']
        
        transfer_data = {
            "sender_id": sender_id,
            "file_name": "config.json",
            "recipients": [recipient_id]
        }
        
        print(f"📤 发送节点: {sender_id}")
        print(f"📥 接收节点: {recipient_id}")
        print(f"📄 文件: config.json")
        
        response = requests.post(
            f"{base_url}/api/file-transfers/manual",
            headers={"Content-Type": "application/json"},
            json=transfer_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 传输请求成功: {result['message']}")
            print(f"📈 传输结果:")
            for r in result.get("results", []):
                status_icon = "✅" if r["success"] else "❌"
                print(f"  {status_icon} {r['recipient']}: {r['message']}")
            return True
        else:
            print(f"❌ 传输请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 传输请求异常: {e}")
        return False

def test_with_different_files():
    """测试不同文件的传输"""
    base_url = "http://localhost:8000"
    test_files = ["config.json", "data.txt", "report.md"]
    
    print("\n🔄 测试不同文件传输...")
    
    # 获取节点列表
    response = requests.get(f"{base_url}/api/status")
    nodes = response.json().get("node_statuses", [])
    
    if len(nodes) < 2:
        print("❌ 需要至少2个节点")
        return
        
    for file_name in test_files:
        print(f"\n📄 测试文件: {file_name}")
        
        transfer_data = {
            "sender_id": nodes[0]['node_id'],
            "file_name": file_name,
            "recipients": [nodes[1]['node_id']]
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/file-transfers/manual",
                headers={"Content-Type": "application/json"},
                json=transfer_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ {file_name}: {result['message']}")
            else:
                print(f"  ❌ {file_name}: 失败 ({response.status_code})")
                
        except Exception as e:
            print(f"  ❌ {file_name}: 异常 ({e})")
        
        time.sleep(1)  # 避免过于频繁的请求

def get_transfer_statistics():
    """获取传输统计"""
    base_url = "http://localhost:8000"
    
    print("\n📊 获取传输统计...")
    try:
        response = requests.get(f"{base_url}/api/file-transfers/status")
        if response.status_code == 200:
            stats = response.json()
            
            total_successful = 0
            total_failed = 0
            total_bytes = 0
            
            for node_id, node_stats in stats.items():
                if "error" not in node_stats:
                    file_stats = node_stats.get("file_transfer_stats", {})
                    total_successful += file_stats.get("successful_transfers", 0)
                    total_failed += file_stats.get("failed_transfers", 0)
                    total_bytes += file_stats.get("bytes_transferred", 0)
                    
                    print(f"📊 {node_id}:")
                    print(f"  ✅ 成功: {file_stats.get('successful_transfers', 0)}")
                    print(f"  ❌ 失败: {file_stats.get('failed_transfers', 0)}")
                    print(f"  💾 传输字节: {file_stats.get('bytes_transferred', 0)}")
                    print(f"  🔄 活跃传输: {node_stats.get('active_transfers', 0)}")
            
            print(f"\n📈 总体统计:")
            print(f"  ✅ 总成功: {total_successful}")
            print(f"  ❌ 总失败: {total_failed}")
            print(f"  💾 总字节: {total_bytes}")
            
        else:
            print(f"❌ 获取统计失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 获取统计异常: {e}")

if __name__ == "__main__":
    print("🚀 CastRay 手动传输测试")
    print("=" * 50)
    
    # 基础测试
    success = test_manual_transfer()
    
    if success:
        # 扩展测试
        test_with_different_files()
        
        # 等待传输完成
        print("\n⏳ 等待传输完成...")
        time.sleep(3)
        
        # 获取统计
        get_transfer_statistics()
        
        print("\n🎉 测试完成!")
    else:
        print("\n❌ 基础测试失败，跳过扩展测试")
