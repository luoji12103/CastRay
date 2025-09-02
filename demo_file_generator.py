#!/usr/bin/env python3
"""
文件生成器功能演示脚本
展示如何使用CastRay的文件生成器进行测试
"""

import requests
import time
import json

def demo_file_generator():
    """演示文件生成器的主要功能"""
    
    print("🚀 CastRay 文件生成器功能演示")
    print("=" * 50)
    
    base_url = "http://localhost:8001"
    
    # 检查服务状态
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ CastRay 服务运行正常")
        else:
            print("❌ 服务状态异常")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        print("请确保运行: python main.py")
        return
    
    print("\n📋 1. 获取预设文件大小列表")
    try:
        response = requests.get(f"{base_url}/api/file-generator/presets")
        presets = response.json()
        print("可用预设:")
        for preset in presets['presets']:
            print(f"  📄 {preset['label']} - {preset['size']}")
    except Exception as e:
        print(f"❌ 获取预设失败: {e}")
    
    print("\n🛠️  2. 创建自定义文件")
    test_cases = [
        {"size": "1KB", "content_type": "text", "description": "1KB文本文件"},
        {"size": "100KB", "content_type": "random", "description": "100KB随机文件"},
        {"size": "1MB", "content_type": "pattern", "description": "1MB模式文件"}
    ]
    
    created_files = []
    
    for test_case in test_cases:
        print(f"\n   创建 {test_case['description']}...")
        try:
            response = requests.post(
                f"{base_url}/api/file-generator/create",
                json={
                    "size": test_case["size"],
                    "content_type": test_case["content_type"]
                }
            )
            result = response.json()
            if result.get('success'):
                print(f"   ✅ 成功创建: {result['filename']} ({result['formatted_size']})")
                created_files.append(result['filename'])
            else:
                print(f"   ❌ 创建失败: {result.get('message')}")
        except Exception as e:
            print(f"   ❌ 创建失败: {e}")
    
    print("\n📂 3. 查看生成的文件列表")
    try:
        response = requests.get(f"{base_url}/api/file-generator/list")
        files_list = response.json()
        if files_list.get('success'):
            files = files_list.get('files', [])
            print(f"当前共有 {len(files)} 个生成的文件:")
            for file_info in files:
                print(f"  📄 {file_info['filename']} - {file_info['formatted_size']}")
        else:
            print("❌ 获取文件列表失败")
    except Exception as e:
        print(f"❌ 获取文件列表失败: {e}")
    
    print("\n🚀 4. 创建并传输文件")
    try:
        response = requests.post(
            f"{base_url}/api/file-generator/create-and-transfer",
            json={
                "size": "500KB",
                "content_type": "random"
            }
        )
        result = response.json()
        if result.get('success'):
            print(f"✅ 文件创建并传输成功!")
            print(f"   文件: {result['filename']}")
            print(f"   大小: {result['formatted_size']}")
            if result.get('transfer_info'):
                print(f"   传输信息: {result['transfer_info']}")
        else:
            print(f"❌ 创建并传输失败: {result.get('message')}")
    except Exception as e:
        print(f"❌ 创建并传输失败: {e}")
    
    print("\n🧹 5. 清理测试文件")
    cleanup_count = 0
    for filename in created_files:
        try:
            response = requests.delete(f"{base_url}/api/file-generator/delete/{filename}")
            result = response.json()
            if result.get('success'):
                print(f"   🗑️  已删除: {filename}")
                cleanup_count += 1
            else:
                print(f"   ❌ 删除失败: {filename}")
        except Exception as e:
            print(f"   ❌ 删除 {filename} 失败: {e}")
    
    print(f"\n✅ 演示完成! 共清理了 {cleanup_count} 个测试文件")
    print("\n💡 提示:")
    print("   - 访问 http://localhost:8001 查看Web界面")
    print("   - 在Web界面中可以更方便地使用文件生成器功能")
    print("   - 支持自定义文件大小: B、KB、MB、GB")
    print("   - 支持三种内容类型: text、random、pattern")

def performance_test():
    """简单的性能测试"""
    print("\n⚡ 性能测试")
    print("-" * 30)
    
    base_url = "http://localhost:8001"
    sizes = ["1KB", "10KB", "100KB", "1MB"]
    
    for size in sizes:
        print(f"\n测试 {size} 文件...")
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{base_url}/api/file-generator/create-and-transfer",
                json={"size": size, "content_type": "random"}
            )
            end_time = time.time()
            
            if response.json().get('success'):
                duration = end_time - start_time
                print(f"  ✅ {size} 文件创建并传输耗时: {duration:.2f} 秒")
            else:
                print(f"  ❌ {size} 文件测试失败")
                
        except Exception as e:
            print(f"  ❌ {size} 文件测试出错: {e}")
        
        time.sleep(0.5)  # 避免过于频繁的请求

if __name__ == "__main__":
    demo_file_generator()
    
    # 询问是否运行性能测试
    run_perf = input("\n是否运行性能测试? (y/n): ").lower().strip()
    if run_perf == 'y':
        performance_test()
    
    print("\n🎉 演示结束!")
