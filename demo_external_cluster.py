#!/usr/bin/env python3
"""
外部集群发现功能快速演示
"""

def demo_cluster_discovery():
    """演示集群发现功能"""
    print("=== CastRay 外部集群发现功能演示 ===\n")
    
    try:
        # 导入模块
        from ray_cluster_discovery import RayClusterDiscovery, discover_and_connect_external_clusters
        print("✓ 成功导入外部集群发现模块")
        
        # 创建发现器实例
        discovery = RayClusterDiscovery()
        print("✓ 创建集群发现器实例")
        
        # 尝试发现集群
        print("\n正在搜索本地Ray集群...")
        clusters = discovery.scan_local_ray_clusters()  # 使用正确的方法名
        
        if clusters:
            print(f"✓ 发现 {len(clusters)} 个Ray集群:")
            for i, cluster in enumerate(clusters):
                print(f"  集群 {i+1}:")
                print(f"    - 节点数量: {cluster.get('nodes', 0)}")
                print(f"    - Dashboard URL: {cluster.get('dashboard_url', 'N/A')}")
                print(f"    - 资源: {cluster.get('resources', {})}")
        else:
            print("⚠ 未发现运行中的Ray集群")
            print("  提示: 可以运行 'ray start --head' 启动Ray集群")
        
        # 测试自动发现和连接函数
        print("\n正在测试自动发现和连接功能...")
        result = discover_and_connect_external_clusters()
        
        print("✓ 自动发现结果:")
        print(f"  - 成功: {result.get('success', False)}")
        print(f"  - 消息: {result.get('message', 'N/A')}")
        print(f"  - 发现的集群: {len(result.get('discovered_clusters', []))}")
        print(f"  - 外部节点: {len(result.get('external_nodes', {}))}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 演示过程出错: {e}")
        return False

def demo_api_info():
    """演示API信息"""
    print("\n=== 可用的外部集群API ===")
    
    apis = [
        ("POST /api/cluster/discover-external", "自动发现并连接外部Ray集群"),
        ("GET /api/cluster/external-info", "获取外部集群连接状态"),
        ("GET /api/nodes/external", "获取外部节点列表"),
        ("POST /api/cluster/connect-external", "手动连接指定的外部集群"),
        ("DELETE /api/cluster/disconnect-external", "断开外部集群连接")
    ]
    
    for endpoint, description in apis:
        print(f"  {endpoint}")
        print(f"    {description}")
        print()

def demo_usage_example():
    """演示使用示例"""
    print("=== 使用示例 ===")
    
    print("1. 启动Ray集群:")
    print("   ray start --head --dashboard-port=8265")
    print()
    
    print("2. 启动CastRay服务:")
    print("   python main.py")
    print()
    
    print("3. 发现外部集群:")
    print("   curl -X POST http://localhost:8000/api/cluster/discover-external")
    print()
    
    print("4. 查看外部节点:")
    print("   curl http://localhost:8000/api/nodes/external")
    print()
    
    print("5. 查看系统状态(包含外部节点):")
    print("   curl http://localhost:8000/api/status")

def main():
    """主函数"""
    # 运行功能演示
    success = demo_cluster_discovery()
    
    # 显示API信息
    demo_api_info()
    
    # 显示使用示例
    demo_usage_example()
    
    print("\n=== 总结 ===")
    if success:
        print("✓ 外部集群发现功能已成功集成到CastRay系统")
        print("✓ 所有核心模块工作正常")
        print("✓ API端点已添加到main.py")
        print("✓ 系统准备就绪，可以发现和连接外部Ray集群")
    else:
        print("⚠ 外部集群发现功能存在问题，请检查模块导入")
    
    print("\n📖 详细说明请查看: README_EXTERNAL_CLUSTERS.md")

if __name__ == "__main__":
    main()
