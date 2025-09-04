#!/usr/bin/env python3
"""
🎯 CastRay 自定义演示文件大小功能演示脚本
展示如何通过API创建不同大小的测试文件
"""

import requests
import time
import json
import os
from pathlib import Path

def display_banner():
    """显示演示横幅"""
    print("🚀" + "="*60 + "🚀")
    print("🎯 CastRay 自定义演示文件大小功能演示")
    print("📅 日期: 2025年9月4日")
    print("📋 功能: 自由选择测试文件大小并创建演示文件")
    print("🚀" + "="*60 + "🚀")

def check_service_health():
    """检查服务状态"""
    print("\n🔍 步骤1: 检查CastRay服务状态")
    try:
        response = requests.get("http://localhost:8002/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ CastRay服务运行正常")
            return True
        else:
            print(f"❌ 服务状态异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        return False

def demonstrate_custom_file_creation():
    """演示自定义文件创建功能"""
    print("\n🛠️  步骤2: 演示自定义文件创建")
    
    # 演示用例
    demo_cases = [
        {"size": "500KB", "description": "中小型文档测试"},
        {"size": "2MB", "description": "图片文件大小测试"},
        {"size": "10MB", "description": "音频文件大小测试"},
        {"size": "50MB", "description": "视频文件大小测试"}
    ]
    
    created_files = []
    
    for i, case in enumerate(demo_cases, 1):
        print(f"\n   📝 演示 {i}: 创建 {case['size']} 文件 ({case['description']})")
        
        try:
            # 调用API创建文件
            response = requests.post(
                "http://localhost:8002/api/file-generator/create-demo",
                json={
                    "size": case["size"],
                    "content_type": "random"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"      ✅ 创建成功!")
                    print(f"      📄 文件名: {result['filename']}")
                    print(f"      📏 实际大小: {result['formatted_size']}")
                    print(f"      📁 保存路径: demo_files/{result['filename']}")
                    created_files.append(result)
                else:
                    print(f"      ❌ 创建失败: {result.get('message')}")
            else:
                print(f"      ❌ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ 请求失败: {e}")
        
        # 添加短暂延迟
        time.sleep(1)
    
    return created_files

def show_demo_files_directory():
    """显示demo_files目录内容"""
    print("\n📁 步骤3: 查看demo_files目录内容")
    
    demo_dir = Path("demo_files")
    if demo_dir.exists():
        files = list(demo_dir.glob("*"))
        if files:
            print(f"   📋 目录中共有 {len(files)} 个文件:")
            for file_path in sorted(files):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    if size_mb >= 1:
                        size_str = f"{size_mb:.2f} MB"
                    elif size >= 1024:
                        size_str = f"{size/1024:.2f} KB"
                    else:
                        size_str = f"{size} B"
                    
                    print(f"      📄 {file_path.name} ({size_str})")
        else:
            print("   📭 目录为空")
    else:
        print("   ❌ demo_files目录不存在")

def demonstrate_web_interface_usage():
    """演示Web界面使用方法"""
    print("\n🌐 步骤4: Web界面使用演示")
    print("   💡 打开浏览器访问: http://localhost:8002")
    print("   📝 操作步骤:")
    print("      1️⃣  在'演示文件'下拉框中选择'🎯 创建自定义大小文件'")
    print("      2️⃣  输入数字大小 (例如: 5)")
    print("      3️⃣  选择单位 (KB/MB/GB)")
    print("      4️⃣  点击'📝 创建'按钮")
    print("      5️⃣  等待文件创建完成")
    print("      6️⃣  新文件会自动添加到演示文件列表")
    print("      7️⃣  选择接收节点，点击'🚀 发起文件传输'进行测试")

def test_different_file_sizes():
    """测试不同文件大小的创建性能"""
    print("\n⚡ 步骤5: 性能测试 - 不同文件大小创建时间")
    
    test_sizes = ["1KB", "100KB", "1MB", "5MB"]
    
    for size in test_sizes:
        print(f"\n   🎯 测试 {size} 文件创建...")
        start_time = time.time()
        
        try:
            response = requests.post(
                "http://localhost:8002/api/file-generator/create-demo",
                json={"size": size, "content_type": "random"},
                timeout=30
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"      ✅ 创建成功 - 耗时: {duration:.2f}秒")
                    print(f"      📄 文件: {result['filename']}")
                else:
                    print(f"      ❌ 创建失败: {result.get('message')}")
            else:
                print(f"      ❌ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ 测试失败: {e}")

def cleanup_demo_files():
    """清理演示文件"""
    print("\n🧹 步骤6: 清理演示文件")
    
    demo_dir = Path("demo_files")
    if demo_dir.exists():
        # 只清理自定义创建的文件（以custom_test_开头的）
        custom_files = list(demo_dir.glob("custom_test_*"))
        
        if custom_files:
            print(f"   🗑️  发现 {len(custom_files)} 个自定义测试文件")
            
            for file_path in custom_files:
                try:
                    file_path.unlink()
                    print(f"      ✅ 已删除: {file_path.name}")
                except Exception as e:
                    print(f"      ❌ 删除失败 {file_path.name}: {e}")
        else:
            print("   📭 没有发现需要清理的自定义测试文件")
    else:
        print("   ❌ demo_files目录不存在")

def main():
    """主演示函数"""
    display_banner()
    
    # 检查服务状态
    if not check_service_health():
        print("\n❌ 服务未运行，请先启动CastRay服务: python main.py")
        return
    
    # 演示文件创建
    created_files = demonstrate_custom_file_creation()
    
    # 显示目录内容
    show_demo_files_directory()
    
    # 演示Web界面使用
    demonstrate_web_interface_usage()
    
    # 性能测试
    test_different_file_sizes()
    
    # 总结
    print("\n📊 演示总结:")
    print(f"   ✅ 成功创建了 {len(created_files)} 个自定义大小的演示文件")
    print("   🎯 展示了API调用方式和Web界面操作方法")
    print("   ⚡ 测试了不同文件大小的创建性能")
    print("   📁 所有文件都保存在demo_files目录中")
    
    # 询问是否清理
    try:
        user_input = input("\n🤔 是否清理演示创建的测试文件? (y/n): ").lower().strip()
        if user_input == 'y':
            cleanup_demo_files()
        else:
            print("   📝 保留演示文件，可在Web界面中继续测试")
    except KeyboardInterrupt:
        print("\n\n👋 演示结束!")
    
    print("\n🎉 演示完成! 感谢使用CastRay自定义文件大小功能!")

if __name__ == "__main__":
    main()
