#!/usr/bin/env python3
"""
测试修复后的文件大小解析功能
"""

from file_generator import parse_size_string, format_size

def test_parse_size_string():
    """测试文件大小解析函数"""
    
    print("🧪 测试文件大小解析功能")
    print("=" * 40)
    
    test_cases = [
        "1B",
        "100B", 
        "1KB",
        "10KB",
        "1MB",
        "10MB",
        "100MB",
        "1GB",
        "5GB",
        "1.5MB",
        "0.5GB",
        "1024",  # 无单位，默认字节
        "2048KB"
    ]
    
    for test_case in test_cases:
        try:
            result = parse_size_string(test_case)
            formatted = format_size(result)
            print(f"✅ '{test_case}' -> {result:,} bytes ({formatted})")
        except Exception as e:
            print(f"❌ '{test_case}' -> Error: {e}")
    
    print("\n🚀 特别测试修复前的问题用例:")
    problem_cases = ["10MB", "5GB", "100KB"]
    
    for case in problem_cases:
        try:
            result = parse_size_string(case)
            formatted = format_size(result)
            print(f"✅ '{case}' -> {result:,} bytes ({formatted})")
        except Exception as e:
            print(f"❌ '{case}' -> Error: {e}")

if __name__ == "__main__":
    test_parse_size_string()
