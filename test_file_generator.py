#!/usr/bin/env python3
"""
文件生成和传输功能测试脚本
"""

import requests
import json
import time
from pathlib import Path

def test_file_generator_api():
    """测试文件生成API功能"""
    base_url = "http://localhost:8000"
    
    print("=== CastRay 文件生成和传输功能测试 ===\n")
    
    # 1. 获取文件生成器信息
    print("1. 获取文件生成器信息...")
    try:
        response = requests.get(f"{base_url}/api/file-generator/info")
        if response.status_code == 200:
            info = response.json()
            print(f"✓ 最大文件大小: {info['max_file_size_formatted']}")
            print(f"✓ 支持的内容类型: {list(info['content_types'].keys())}")
            print(f"✓ 支持的单位: {info['supported_units']}")
        else:
            print(f"✗ 获取信息失败: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 2. 获取预设选项
    print("2. 获取预设文件大小...")
    try:
        response = requests.get(f"{base_url}/api/file-generator/presets")
        if response.status_code == 200:
            presets = response.json()
            print("✓ 可用预设:")
            for name, info in presets['presets'].items():
                print(f"   - {name}: {info['size_formatted']}")
        else:
            print(f"✗ 获取预设失败: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")
    
    print()
    
    # 3. 创建自定义大小的文件
    print("3. 创建自定义大小的文件...")
    test_sizes = ["1KB", "10KB", "100KB"]
    
    for size in test_sizes:
        try:
            data = {
                "size": size,
                "content_type": "text",
                "include_metadata": True
            }
            
            response = requests.post(f"{base_url}/api/file-generator/create", json=data)
            if response.status_code == 200:
                result = response.json()
                file_info = result['file_info']
                print(f"✓ 创建 {size} 文件成功:")
                print(f"   文件名: {file_info['file_name']}")
                print(f"   实际大小: {file_info['size_formatted']}")
                print(f"   MD5: {file_info['md5_hash'][:16]}...")
            else:
                print(f"✗ 创建 {size} 文件失败: {response.status_code}")
                print(f"   错误: {response.text}")
        except Exception as e:
            print(f"✗ 创建 {size} 文件请求失败: {e}")
    
    print()
    
    # 4. 创建预设文件
    print("4. 创建预设文件...")
    try:
        data = {
            "preset": "medium",
            "content_type": "pattern"
        }
        
        response = requests.post(f"{base_url}/api/file-generator/create-preset", json=data)
        if response.status_code == 200:
            result = response.json()
            file_info = result['file_info']
            print(f"✓ 创建预设文件成功:")
            print(f"   文件名: {file_info['file_name']}")
            print(f"   预设: {file_info['preset_name']}")
            print(f"   大小: {file_info['size_formatted']}")
        else:
            print(f"✗ 创建预设文件失败: {response.status_code}")
    except Exception as e:
        print(f"✗ 创建预设文件请求失败: {e}")
    
    print()
    
    # 5. 列出生成的文件
    print("5. 列出生成的文件...")
    try:
        response = requests.get(f"{base_url}/api/file-generator/files")
        if response.status_code == 200:
            result = response.json()
            files = result['files']
            print(f"✓ 找到 {result['total_count']} 个文件:")
            print(f"   总大小: {result['total_size_formatted']}")
            
            for i, file_info in enumerate(files[:5]):  # 只显示前5个
                status = "📄" if file_info['is_generated'] else "📁"
                print(f"   {status} {file_info['file_name']} ({file_info['size_formatted']})")
            
            if len(files) > 5:
                print(f"   ... 还有 {len(files) - 5} 个文件")
        else:
            print(f"✗ 列出文件失败: {response.status_code}")
    except Exception as e:
        print(f"✗ 列出文件请求失败: {e}")
    
    print()

def test_file_transfer_with_generation():
    """测试文件生成和传输功能"""
    base_url = "http://localhost:8000"
    
    print("6. 测试文件生成并传输功能...")
    
    # 首先获取可用节点
    try:
        response = requests.get(f"{base_url}/api/status")
        if response.status_code == 200:
            status = response.json()
            nodes = [node['node_id'] for node in status.get('node_statuses', [])]
            
            if len(nodes) >= 2:
                sender = nodes[0]
                recipients = nodes[1:3]  # 最多选择2个接收节点
                
                print(f"✓ 可用节点: {len(nodes)} 个")
                print(f"   发送节点: {sender}")
                print(f"   接收节点: {recipients}")
                
                # 创建并传输文件
                data = {
                    "size": "50KB",
                    "content_type": "text",
                    "sender_id": sender,
                    "recipients": recipients,
                    "include_metadata": True
                }
                
                response = requests.post(f"{base_url}/api/file-generator/create-and-transfer", json=data)
                if response.status_code == 200:
                    result = response.json()
                    transfer_summary = result['transfer_summary']
                    
                    print(f"✓ 文件生成并传输成功:")
                    print(f"   文件: {result['file_info']['file_name']}")
                    print(f"   大小: {result['file_info']['size_formatted']}")
                    print(f"   成功传输: {transfer_summary['successful_transfers']}/{transfer_summary['total_recipients']}")
                    
                    if transfer_summary['failed_transfers'] > 0:
                        print(f"   失败传输: {transfer_summary['failed_transfers']}")
                else:
                    print(f"✗ 文件生成并传输失败: {response.status_code}")
                    print(f"   错误: {response.text}")
            else:
                print(f"⚠ 节点数量不足 ({len(nodes)} 个)，无法测试传输功能")
                print("   需要至少2个节点来测试传输")
        else:
            print(f"✗ 获取节点状态失败: {response.status_code}")
    except Exception as e:
        print(f"✗ 测试传输功能失败: {e}")

def test_error_handling():
    """测试错误处理"""
    base_url = "http://localhost:8000"
    
    print("\n7. 测试错误处理...")
    
    # 测试无效的文件大小
    print("   测试无效文件大小...")
    try:
        data = {"size": "invalid_size"}
        response = requests.post(f"{base_url}/api/file-generator/create", json=data)
        if response.status_code == 400:
            print("   ✓ 正确处理无效文件大小")
        else:
            print(f"   ✗ 错误处理异常: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
    
    # 测试超大文件
    print("   测试超大文件...")
    try:
        data = {"size": "10GB"}  # 超过1GB限制
        response = requests.post(f"{base_url}/api/file-generator/create", json=data)
        if response.status_code == 400:
            print("   ✓ 正确处理超大文件")
        else:
            print(f"   ✗ 错误处理异常: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
    
    # 测试无效预设
    print("   测试无效预设...")
    try:
        data = {"preset": "invalid_preset"}
        response = requests.post(f"{base_url}/api/file-generator/create-preset", json=data)
        if response.status_code == 400:
            print("   ✓ 正确处理无效预设")
        else:
            print(f"   ✗ 错误处理异常: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")

def main():
    """主测试函数"""
    print("提示: 请确保CastRay服务正在运行 (python main.py)")
    print("按Enter继续测试...")
    input()
    
    # 基本功能测试
    test_file_generator_api()
    
    # 传输功能测试
    test_file_transfer_with_generation()
    
    # 错误处理测试
    test_error_handling()
    
    print("\n=== 测试完成 ===")
    print("\n💡 使用建议:")
    print("1. 通过Web界面访问: http://localhost:8000/ui")
    print("2. 使用API创建自定义大小的文件")
    print("3. 利用预设快速创建常用大小的文件")
    print("4. 结合文件传输功能进行性能测试")
    
    print("\n🚀 可用的API端点:")
    endpoints = [
        "GET  /api/file-generator/info - 获取生成器信息",
        "GET  /api/file-generator/presets - 获取预设选项", 
        "POST /api/file-generator/create - 创建自定义文件",
        "POST /api/file-generator/create-preset - 创建预设文件",
        "POST /api/file-generator/create-and-transfer - 创建并传输",
        "GET  /api/file-generator/files - 列出生成的文件",
        "DELETE /api/file-generator/files/{name} - 删除文件"
    ]
    
    for endpoint in endpoints:
        print(f"   {endpoint}")

if __name__ == "__main__":
    main()
