#!/usr/bin/env python3
"""
外部集群发现功能全面测试脚本
测试CastRay系统的外部Ray集群发现和连接功能
"""

import os
import sys
import time
import json
import requests
import subprocess
from pathlib import Path

def test_cluster_discovery_module():
    """测试集群发现模块"""
    print("=== 测试集群发现模块 ===")
    
    try:
        from ray_cluster_discovery import RayClusterDiscovery, discover_and_connect_external_clusters
        
        # 测试集群发现
        discovery = RayClusterDiscovery()
        print("✓ 集群发现模块导入成功")
        
        # 发现本地集群
        clusters = discovery.discover_clusters()
        print(f"发现的集群数量: {len(clusters)}")
        
        for i, cluster in enumerate(clusters):
            print(f"集群 {i+1}:")
            print(f"  - 节点数量: {cluster.get('nodes', 0)}")
            print(f"  - Dashboard URL: {cluster.get('dashboard_url', 'N/A')}")
            print(f"  - 资源: {cluster.get('resources', {})}")
        
        # 测试自动发现和连接
        print("\n=== 测试自动发现和连接 ===")
        result = discover_and_connect_external_clusters()
        print(f"自动发现结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 集群发现模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 集群发现测试失败: {e}")
        return False

def test_api_endpoints():
    """测试API端点"""
    print("\n=== 测试API端点 ===")
    
    # 假设CastRay服务在localhost:8000运行
    base_url = "http://localhost:8000"
    
    endpoints = [
        ("/api/cluster/discover-external", "POST"),
        ("/api/cluster/external-info", "GET"),
        ("/api/nodes/external", "GET"),
        ("/api/cluster/connect-external", "POST"),
        ("/api/cluster/disconnect-external", "DELETE")
    ]
    
    results = {}
    
    for endpoint, method in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                if "connect-external" in endpoint:
                    # 测试连接外部集群的API
                    test_data = {"cluster_address": "127.0.0.1:8265"}
                    response = requests.post(url, json=test_data, timeout=5)
                else:
                    response = requests.post(url, json={}, timeout=5)
            elif method == "DELETE":
                response = requests.delete(url, timeout=5)
            
            results[endpoint] = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code == 200 else response.text
            }
            
            print(f"✓ {method} {endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if endpoint == "/api/nodes/external":
                    node_count = data.get('count', 0)
                    print(f"  外部节点数量: {node_count}")
                elif endpoint == "/api/cluster/external-info":
                    is_connected = data.get('is_connected', False)
                    print(f"  外部集群连接状态: {'已连接' if is_connected else '未连接'}")
            
        except requests.exceptions.ConnectionError:
            results[endpoint] = {
                "success": False,
                "error": "无法连接到CastRay服务 (localhost:8000)"
            }
            print(f"✗ {method} {endpoint}: 连接失败")
        except Exception as e:
            results[endpoint] = {
                "success": False,
                "error": str(e)
            }
            print(f"✗ {method} {endpoint}: {e}")
    
    return results

def start_test_ray_cluster():
    """启动测试用的Ray集群"""
    print("\n=== 启动测试Ray集群 ===")
    
    try:
        # 检查是否已有Ray集群运行
        result = subprocess.run(["ray", "status"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ 检测到现有Ray集群")
            print(result.stdout)
            return True
        else:
            print("未检测到Ray集群，尝试启动新集群...")
            
            # 启动Ray集群
            subprocess.run(["ray", "start", "--head", "--dashboard-port=8265"], 
                         timeout=30, check=True)
            
            # 等待集群启动
            time.sleep(5)
            
            # 验证集群状态
            result = subprocess.run(["ray", "status"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✓ Ray集群启动成功")
                print(result.stdout)
                return True
            else:
                print("✗ Ray集群启动失败")
                return False
                
    except subprocess.TimeoutExpired:
        print("✗ Ray命令超时")
        return False
    except subprocess.CalledProcessError as e:
        print(f"✗ Ray命令执行失败: {e}")
        return False
    except FileNotFoundError:
        print("✗ Ray命令未找到，请确保Ray已安装")
        return False

def test_external_cluster_connection():
    """测试外部集群连接"""
    print("\n=== 测试外部集群连接 ===")
    
    try:
        from ray_cluster_discovery import cluster_connector
        
        # 构造测试集群信息
        test_cluster = {
            'dashboard_url': 'http://127.0.0.1:8265',
            'address': '127.0.0.1:8265',
            'nodes': 1,
            'resources': {'CPU': 4.0}
        }
        
        print(f"尝试连接到测试集群: {test_cluster['dashboard_url']}")
        
        # 测试连接
        success = cluster_connector.connect_to_external_cluster(test_cluster)
        
        if success:
            print("✓ 外部集群连接成功")
            
            # 获取外部节点信息
            external_nodes = cluster_connector.get_external_nodes()
            print(f"获取到外部节点: {len(external_nodes)} 个")
            
            for node_id, node_info in external_nodes.items():
                print(f"  - 节点 {node_id}: {node_info}")
            
            # 检查连接状态
            is_connected = cluster_connector.is_connected_to_external_cluster()
            print(f"连接状态: {'已连接' if is_connected else '未连接'}")
            
            return True
        else:
            print("✗ 外部集群连接失败")
            return False
            
    except Exception as e:
        print(f"✗ 外部集群连接测试失败: {e}")
        return False

def test_node_integration():
    """测试节点集成功能"""
    print("\n=== 测试节点集成功能 ===")
    
    try:
        # 测试CastRay系统是否正确识别外部节点
        response = requests.get("http://localhost:8000/api/status", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            total_nodes = data.get('total_nodes', 0)
            
            # 获取外部节点信息
            ext_response = requests.get("http://localhost:8000/api/nodes/external", timeout=5)
            if ext_response.status_code == 200:
                ext_data = ext_response.json()
                external_node_count = ext_data.get('count', 0)
                
                print(f"✓ 系统总节点数: {total_nodes}")
                print(f"✓ 外部节点数: {external_node_count}")
                
                if external_node_count > 0:
                    print("✓ 外部节点成功集成到CastRay系统中")
                    return True
                else:
                    print("⚠ 未检测到外部节点")
                    return False
            else:
                print("✗ 无法获取外部节点信息")
                return False
        else:
            print("✗ 无法获取系统状态")
            return False
            
    except Exception as e:
        print(f"✗ 节点集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("CastRay 外部集群发现功能全面测试")
    print("=" * 60)
    
    # 设置工作目录
    os.chdir(Path(__file__).parent)
    
    test_results = {}
    
    print("提示: 此测试需要按顺序进行以下操作:")
    print("1. 启动Ray集群")
    print("2. 测试集群发现模块")
    print("3. 启动CastRay服务")
    print("4. 测试API端点")
    print("5. 测试系统集成")
    print()
    
    # 1. 测试集群发现模块
    test_results['module_test'] = test_cluster_discovery_module()
    
    # 2. 启动测试Ray集群
    test_results['ray_cluster'] = start_test_ray_cluster()
    
    # 3. 测试外部集群连接
    if test_results['ray_cluster']:
        test_results['external_connection'] = test_external_cluster_connection()
    
    print("\n请在新终端中启动CastRay服务:")
    print("python main.py")
    print("等待服务启动后按Enter继续...")
    input()
    
    # 4. 测试API端点（需要CastRay服务运行）
    test_results['api_endpoints'] = test_api_endpoints()
    
    # 5. 测试节点集成
    test_results['node_integration'] = test_node_integration()
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结:")
    
    for test_name, result in test_results.items():
        if isinstance(result, bool):
            status = "✓ 通过" if result else "✗ 失败"
            print(f"  {test_name}: {status}")
        elif isinstance(result, dict):
            # API测试结果
            passed = sum(1 for r in result.values() if r.get('success', False))
            total = len(result)
            print(f"  {test_name}: {passed}/{total} 通过")
    
    print("\n功能说明:")
    print("✓ 外部集群发现: 自动扫描并发现本地运行的Ray集群")
    print("✓ 集群连接: 连接到外部Ray集群并获取节点信息")
    print("✓ 节点虚拟化: 将外部Ray节点映射为CastRay系统中的虚拟节点")
    print("✓ API集成: 提供完整的外部集群管理API")
    print("✓ 实时更新: 通过WebSocket向客户端推送集群状态变化")
    
    print("\n使用方法:")
    print("1. 自动发现: POST /api/cluster/discover-external")
    print("2. 手动连接: POST /api/cluster/connect-external")
    print("3. 查看状态: GET /api/cluster/external-info")
    print("4. 获取节点: GET /api/nodes/external")
    print("5. 断开连接: DELETE /api/cluster/disconnect-external")

if __name__ == "__main__":
    main()
