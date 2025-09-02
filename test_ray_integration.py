#!/usr/bin/env python3
"""
测试Ray集群节点发现和集成功能
"""
import asyncio
import ray
import sys
import time
from ray_casting import cluster, connect_to_ray_cluster
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ray_integration():
    """测试Ray集群集成功能"""
    
    print("🚀 开始测试Ray集群节点发现功能...")
    
    try:
        # 1. 初始化Ray集群
        print("\n1. 初始化Ray集群连接...")
        success = await cluster.initialize_ray("local", "castray")
        
        if not success:
            print("❌ Ray集群初始化失败")
            return False
        
        print("✅ Ray集群初始化成功")
        
        # 2. 获取Ray集群状态
        print("\n2. 获取Ray集群状态...")
        ray_status = {}
        if ray.is_initialized():
            ray_status = {
                "cluster_resources": ray.cluster_resources(),
                "available_resources": ray.available_resources(),
                "nodes": ray.nodes()
            }
            
            print(f"   - 集群资源: {ray_status['cluster_resources']}")
            print(f"   - 可用资源: {ray_status['available_resources']}")
            print(f"   - 节点数量: {len(ray_status['nodes'])}")
            
            for i, node in enumerate(ray_status['nodes']):
                print(f"   - 节点 {i+1}: {node.get('NodeID', 'Unknown')[:8]} "
                      f"({node.get('NodeManagerAddress', 'Unknown')}:"
                      f"{node.get('NodeManagerPort', 'Unknown')}) "
                      f"- {'活跃' if node.get('Alive', False) else '非活跃'}")
        
        # 3. 获取Ray集群节点信息
        print("\n3. 发现Ray集群节点...")
        ray_cluster_nodes = await cluster.get_ray_cluster_nodes_info()
        
        print(f"   发现 {len(ray_cluster_nodes)} 个Ray集群节点:")
        for node_id, node_info in ray_cluster_nodes.items():
            print(f"   - {node_id}: {node_info['address']}:{node_info['port']} "
                  f"(Ray ID: {node_info['ray_node_id'][:8]})")
        
        # 4. 获取系统状态
        print("\n4. 获取完整系统状态...")
        status = await cluster.get_cluster_status()
        
        print(f"   - 总节点数: {status.get('total_nodes', 0)}")
        print(f"   - 活跃节点数: {status.get('active_nodes', 0)}")
        print(f"   - Ray集群节点数: {status.get('ray_cluster_nodes_count', 0)}")
        print(f"   - 传输节点数: {status.get('casting_nodes_count', 0)}")
        
        # 5. 显示节点详细信息
        print("\n5. 节点详细信息:")
        for node_status in status.get('node_statuses', []):
            node_type = node_status.get('node_type', 'unknown')
            node_id = node_status.get('node_id', 'unknown')
            is_running = node_status.get('is_running', False)
            
            print(f"   - {node_id} ({node_type}): {'运行中' if is_running else '已停止'}")
            
            if node_type == 'ray_cluster':
                ray_address = node_status.get('ray_address', 'N/A')
                ray_node_id = node_status.get('ray_node_id', 'N/A')
                print(f"     Ray地址: {ray_address}")
                print(f"     Ray节点ID: {ray_node_id[:8]}...")
        
        # 6. 测试文件传输能力（如果有多个节点）
        if len(cluster.nodes) >= 2:
            print("\n6. 测试文件传输能力...")
            node_ids = list(cluster.nodes.keys())
            sender = node_ids[0]
            receiver = node_ids[1]
            
            print(f"   准备从 {sender} 向 {receiver} 发送测试文件...")
            
            # 创建测试文件
            test_file = "test_transfer.txt"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(f"测试文件传输\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            try:
                # 发起文件传输
                result = await cluster.initiate_node_file_transfer(
                    sender, test_file, [receiver], "unicast"
                )
                
                if result.success:
                    print(f"   ✅ 文件传输测试成功: {result.message}")
                else:
                    print(f"   ❌ 文件传输测试失败: {result.message}")
                    
            except Exception as e:
                print(f"   ❌ 文件传输测试异常: {e}")
        else:
            print("\n6. 跳过文件传输测试（节点数量不足）")
        
        print("\n✅ 所有测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理
        try:
            cluster.shutdown()
            print("\n🧹 清理完成")
        except:
            pass

async def main():
    """主函数"""
    print("=" * 60)
    print("Ray集群节点发现和集成测试")
    print("=" * 60)
    
    success = await test_ray_integration()
    
    if success:
        print("\n🎉 测试成功完成!")
        return 0
    else:
        print("\n💥 测试失败!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
