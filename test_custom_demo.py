#!/usr/bin/env python3
"""
测试新增的自定义演示文件创建功能
"""

import requests
import time

def test_custom_demo_file():
    """测试自定义演示文件创建API"""
    
    print("🎯 测试自定义演示文件创建功能")
    print("=" * 50)
    
    base_url = "http://localhost:8001"
    
    # 等待服务启动
    print("正在等待服务启动...")
    for i in range(10):
        try:
            response = requests.get(f"{base_url}/api/health", timeout=3)
            if response.status_code == 200:
                print("✅ 服务已启动")
                break
        except:
            pass
        print(f"等待中...({i+1}/10)")
        time.sleep(2)
    else:
        print("❌ 服务启动超时")
        return
    
    # 测试用例
    test_cases = [
        {"size": "5MB", "description": "5MB演示文件"},
        {"size": "100KB", "description": "100KB演示文件"},
        {"size": "1GB", "description": "1GB演示文件"},
    ]
    
    created_files = []
    
    for test_case in test_cases:
        print(f"\n📝 测试创建: {test_case['description']}")
        
        try:
            response = requests.post(
                f"{base_url}/api/file-generator/create-demo",
                json={
                    "size": test_case["size"],
                    "content_type": "random"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"   ✅ 创建成功: {result['filename']}")
                    print(f"   📏 实际大小: {result['formatted_size']}")
                    print(f"   📁 路径: {result['path']}")
                    created_files.append(result['filename'])
                else:
                    print(f"   ❌ 创建失败: {result.get('message')}")
            else:
                print(f"   ❌ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
    
    print(f"\n📋 测试总结:")
    print(f"   成功创建 {len(created_files)} 个演示文件")
    print("   这些文件已保存到 demo_files 目录")
    print("   可以在Web界面的演示文件下拉列表中看到它们")
    
    # 列出demo_files目录的文件
    try:
        import os
        demo_dir = "demo_files"
        if os.path.exists(demo_dir):
            files = os.listdir(demo_dir)
            print(f"\n📁 demo_files 目录内容:")
            for file in files:
                file_path = os.path.join(demo_dir, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    print(f"   📄 {file} ({size:,} bytes)")
    except Exception as e:
        print(f"❌ 无法列出目录内容: {e}")
    
    print(f"\n💡 使用说明:")
    print("   1. 在Web界面中，选择'演示文件'下拉框")
    print("   2. 选择'🎯 创建自定义大小文件'")
    print("   3. 输入数字和选择单位（KB/MB/GB）")
    print("   4. 点击'📝 创建'按钮")
    print("   5. 创建的文件将自动添加到演示文件列表中")

if __name__ == "__main__":
    test_custom_demo_file()
