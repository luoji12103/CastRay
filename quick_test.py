#!/usr/bin/env python3
"""
快速测试文件生成器功能
"""

import requests
import json

def test_api():
    base_url = "http://localhost:8001"
    
    print("🔍 测试文件生成器API...")
    
    try:
        # 测试预设API
        print("\n1. 测试预设列表API...")
        response = requests.get(f"{base_url}/api/file-generator/presets")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        # 测试创建文件API
        print("\n2. 测试创建小文件...")
        create_data = {
            "size": "1KB",
            "content_type": "text"
        }
        response = requests.post(f"{base_url}/api/file-generator/create", json=create_data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {result}")
        
        if result.get('success'):
            filename = result.get('filename')
            print(f"✅ 文件创建成功: {filename}")
            
            # 测试文件列表API
            print("\n3. 测试文件列表API...")
            response = requests.get(f"{base_url}/api/file-generator/list")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
            
            # 测试删除文件
            print(f"\n4. 测试删除文件: {filename}")
            response = requests.delete(f"{base_url}/api/file-generator/delete/{filename}")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
        
        print("\n✅ 所有测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_api()
