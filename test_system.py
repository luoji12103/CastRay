import asyncio
import json
import time
import uuid
from ray_casting import cluster
from models import CastMessage, CastType, MessageType

async def test_casting_system():
    """测试消息传输系统"""
    print("🧪 开始测试分布式消息传输系统...")
    
    # 初始化集群
    await cluster.initialize_ray()
    
    # 创建测试节点
    test_nodes = ["sender", "receiver1", "receiver2", "receiver3"]
    
    print("\n📦 创建测试节点...")
    for node_id in test_nodes:
        success = await cluster.create_node(node_id)
        if success:
            print(f"✅ 节点 {node_id} 创建成功")
        else:
            print(f"❌ 节点 {node_id} 创建失败")
    
    # 等待节点启动
    await asyncio.sleep(2)
    
    # 获取集群状态
    status = await cluster.get_cluster_status()
    print(f"\n📊 集群状态: {status['total_nodes']} 个节点，{status['active_nodes']} 个活跃")
    
    # 测试单播
    print("\n🎯 测试单播消息...")
    unicast_msg = CastMessage(
        id=str(uuid.uuid4()),
        cast_type=CastType.UNICAST,
        message_type=MessageType.TEXT,
        content="Hello from unicast test!",
        sender="sender",
        recipients=["receiver1", "receiver2"]
    )
    
    response = await cluster.send_message(unicast_msg)
    print(f"单播结果: {response.success}, 接收者: {response.recipients_count}, 时间: {response.delivery_time:.3f}秒")
    
    # 测试组播
    print("\n📡 测试组播消息...")
    multicast_msg = CastMessage(
        id=str(uuid.uuid4()),
        cast_type=CastType.MULTICAST,
        message_type=MessageType.JSON,
        content={"type": "multicast_test", "data": [1, 2, 3]},
        sender="sender",
        group_id="test_group"
    )
    
    response = await cluster.send_message(multicast_msg)
    print(f"组播结果: {response.success}, 接收者: {response.recipients_count}, 时间: {response.delivery_time:.3f}秒")
    
    # 测试广播
    print("\n📢 测试广播消息...")
    broadcast_msg = CastMessage(
        id=str(uuid.uuid4()),
        cast_type=CastType.BROADCAST,
        message_type=MessageType.TEXT,
        content="Broadcast to all nodes!",
        sender="sender"
    )
    
    response = await cluster.send_message(broadcast_msg)
    print(f"广播结果: {response.success}, 接收者: {response.recipients_count}, 时间: {response.delivery_time:.3f}秒")
    
    # 等待消息处理
    await asyncio.sleep(2)
    
    # 检查消息接收情况
    print("\n📨 检查消息接收情况...")
    for node_id in test_nodes:
        messages = await cluster.get_node_messages(node_id, 10)
        print(f"节点 {node_id}: {len(messages)} 条消息")
        for msg in messages[:3]:  # 显示前3条
            print(f"  - [{msg['direction']}] {msg.get('type', 'unknown')} at {time.ctime(msg['timestamp'])}")
    
    # 性能测试
    print("\n⚡ 性能测试 (100条消息)...")
    start_time = time.time()
    
    tasks = []
    for i in range(100):
        msg = CastMessage(
            id=f"perf_test_{i}",
            cast_type=CastType.UNICAST,
            message_type=MessageType.TEXT,
            content=f"Performance test message {i}",
            sender="sender",
            recipients=["receiver1"]
        )
        tasks.append(cluster.send_message(msg))
    
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    successful = len([r for r in results if r.success])
    total_time = end_time - start_time
    
    print(f"性能测试结果:")
    print(f"  - 总消息: 100")
    print(f"  - 成功: {successful}")
    print(f"  - 失败: {100 - successful}")
    print(f"  - 总时间: {total_time:.3f}秒")
    print(f"  - 平均速度: {100/total_time:.1f} 消息/秒")
    
    # 清理
    print("\n🧹 清理测试环境...")
    for node_id in test_nodes:
        await cluster.remove_node(node_id)
    
    cluster.shutdown()
    print("✅ 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_casting_system())
