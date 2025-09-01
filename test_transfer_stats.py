#!/usr/bin/env python3
"""
测试传输统计更新问题
"""

import requests
import json
import time

def get_transfer_stats():
    """获取传输统计"""
    try:
        response = requests.get("http://127.0.0.1:28823/api/file-transfers/status")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取统计失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def test_manual_transfer_stats():
    """测试手动传输统计更新"""
    print("🔍 测试手动传输统计更新问题")
    print("=" * 50)
    
    # 1. 获取初始统计
    print("\n📊 获取初始传输统计...")
    initial_stats = get_transfer_stats()
    if not initial_stats:
        return False
    
    # 计算初始总数
    initial_totals = {
        "successful": 0,
        "failed": 0,
        "total": 0,
        "bytes": 0
    }
    
    for node_id, stats in initial_stats.items():
        if "file_transfer_stats" in stats:
            fs = stats["file_transfer_stats"]
            initial_totals["successful"] += fs.get("successful_transfers", 0)
            initial_totals["failed"] += fs.get("failed_transfers", 0)
            initial_totals["total"] += fs.get("total_transfers", 0)
            initial_totals["bytes"] += fs.get("bytes_transferred", 0)
    
    print(f"📈 初始统计:")
    print(f"  ✅ 成功传输: {initial_totals['successful']}")
    print(f"  ❌ 失败传输: {initial_totals['failed']}")
    print(f"  📊 总传输: {initial_totals['total']}")
    print(f"  💾 传输字节: {initial_totals['bytes']}")
    
    # 2. 获取节点列表
    print("\n🔍 获取节点列表...")
    try:
        response = requests.get("http://127.0.0.1:28823/api/status")
        nodes = response.json().get("node_statuses", [])
        if len(nodes) < 2:
            print("❌ 需要至少2个节点进行测试")
            return False
            
        sender_id = nodes[0]['node_id']
        recipient_id = nodes[1]['node_id']
        
        print(f"📤 发送节点: {sender_id}")
        print(f"📥 接收节点: {recipient_id}")
        
    except Exception as e:
        print(f"❌ 获取节点失败: {e}")
        return False
    
    # 3. 发起手动传输
    print("\n🚀 发起手动文件传输...")
    transfer_data = {
        "sender_id": sender_id,
        "file_name": "config.json",
        "recipients": [recipient_id]
    }
    
    try:
        response = requests.post(
            "http://127.0.0.1:28823/api/file-transfers/manual",
            headers={"Content-Type": "application/json"},
            json=transfer_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 传输请求发送成功")
            print(f"📋 响应: {result.get('message', '')}")
        else:
            print(f"❌ 传输请求失败: {response.status_code}")
            print(f"错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 传输请求异常: {e}")
        return False
    
    # 4. 等待一段时间让传输处理
    print("\n⏳ 等待传输处理...")
    time.sleep(3)
    
    # 5. 获取更新后的统计
    print("\n📊 获取更新后的传输统计...")
    updated_stats = get_transfer_stats()
    if not updated_stats:
        return False
    
    # 计算更新后总数
    updated_totals = {
        "successful": 0,
        "failed": 0,
        "total": 0,
        "bytes": 0
    }
    
    for node_id, stats in updated_stats.items():
        if "file_transfer_stats" in stats:
            fs = stats["file_transfer_stats"]
            updated_totals["successful"] += fs.get("successful_transfers", 0)
            updated_totals["failed"] += fs.get("failed_transfers", 0)
            updated_totals["total"] += fs.get("total_transfers", 0)
            updated_totals["bytes"] += fs.get("bytes_transferred", 0)
    
    print(f"📈 更新后统计:")
    print(f"  ✅ 成功传输: {updated_totals['successful']}")
    print(f"  ❌ 失败传输: {updated_totals['failed']}")
    print(f"  📊 总传输: {updated_totals['total']}")
    print(f"  💾 传输字节: {updated_totals['bytes']}")
    
    # 6. 计算变化
    changes = {
        "successful": updated_totals["successful"] - initial_totals["successful"],
        "failed": updated_totals["failed"] - initial_totals["failed"],
        "total": updated_totals["total"] - initial_totals["total"],
        "bytes": updated_totals["bytes"] - initial_totals["bytes"]
    }
    
    print(f"\n📊 统计变化:")
    print(f"  ✅ 成功传输变化: {changes['successful']}")
    print(f"  ❌ 失败传输变化: {changes['failed']}")
    print(f"  📊 总传输变化: {changes['total']}")
    print(f"  💾 传输字节变化: {changes['bytes']}")
    
    # 7. 分析结果
    print(f"\n🔍 问题分析:")
    
    if changes["total"] == 0:
        print("❌ 问题确认: 总传输数没有增加")
    else:
        print(f"✅ 总传输数已增加: +{changes['total']}")
    
    if changes["successful"] == 0 and changes["failed"] == 0:
        print("❌ 问题确认: 成功/失败传输数都没有变化")
    else:
        print(f"✅ 传输结果统计已更新: 成功+{changes['successful']}, 失败+{changes['failed']}")
    
    if changes["bytes"] == 0:
        print("❌ 问题确认: 传输字节数没有增加") 
    else:
        print(f"✅ 传输字节数已增加: +{changes['bytes']} bytes")
    
    # 8. 详细节点统计
    print(f"\n📋 详细节点统计对比:")
    for node_id in set(initial_stats.keys()) | set(updated_stats.keys()):
        if node_id in initial_stats and node_id in updated_stats:
            initial = initial_stats[node_id].get("file_transfer_stats", {})
            updated = updated_stats[node_id].get("file_transfer_stats", {})
            
            if (initial.get("successful_transfers", 0) != updated.get("successful_transfers", 0) or
                initial.get("failed_transfers", 0) != updated.get("failed_transfers", 0) or
                initial.get("total_transfers", 0) != updated.get("total_transfers", 0)):
                
                print(f"  🖥️ {node_id}:")
                print(f"    成功: {initial.get('successful_transfers', 0)} -> {updated.get('successful_transfers', 0)}")
                print(f"    失败: {initial.get('failed_transfers', 0)} -> {updated.get('failed_transfers', 0)}")
                print(f"    总数: {initial.get('total_transfers', 0)} -> {updated.get('total_transfers', 0)}")
                print(f"    字节: {initial.get('bytes_transferred', 0)} -> {updated.get('bytes_transferred', 0)}")
    
    return True

def test_multiple_transfers():
    """测试多次传输的统计累积"""
    print("\n🔄 测试多次传输统计累积...")
    
    for i in range(3):
        print(f"\n🚀 第 {i+1} 次传输:")
        
        # 获取节点
        response = requests.get("http://127.0.0.1:28823/api/status")
        nodes = response.json().get("node_statuses", [])
        
        if len(nodes) >= 2:
            transfer_data = {
                "sender_id": nodes[0]['node_id'],
                "file_name": ["config.json", "data.txt", "report.md"][i],
                "recipients": [nodes[1]['node_id']]
            }
            
            response = requests.post(
                "http://127.0.0.1:28823/api/file-transfers/manual",
                headers={"Content-Type": "application/json"},
                json=transfer_data
            )
            
            if response.status_code == 200:
                print(f"  ✅ 传输 {i+1} 发送成功")
            else:
                print(f"  ❌ 传输 {i+1} 发送失败")
            
            time.sleep(2)

if __name__ == "__main__":
    print("🔍 CastRay 传输统计测试")
    print("=" * 50)
    
    # 主要测试
    success = test_manual_transfer_stats()
    
    if success:
        # 额外测试
        test_multiple_transfers()
        
        print("\n📊 最终统计检查...")
        final_stats = get_transfer_stats()
        
        if final_stats:
            print("\n📋 最终传输统计:")
            for node_id, stats in final_stats.items():
                if "file_transfer_stats" in stats:
                    fs = stats["file_transfer_stats"]
                    print(f"  🖥️ {node_id}:")
                    print(f"    ✅ 成功: {fs.get('successful_transfers', 0)}")
                    print(f"    ❌ 失败: {fs.get('failed_transfers', 0)}")
                    print(f"    📊 总数: {fs.get('total_transfers', 0)}")
                    print(f"    💾 字节: {fs.get('bytes_transferred', 0)}")
        
        print("\n🎉 测试完成!")
    else:
        print("\n❌ 测试失败")
