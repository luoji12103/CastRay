#!/usr/bin/env python3
"""
生产环境启动脚本
"""

import os
import sys
import subprocess
import time
import signal
import atexit
from pathlib import Path

class ProductionManager:
    def __init__(self):
        self.processes = []
        self.ray_process = None
        
    def start_ray_cluster(self):
        """启动Ray集群"""
        print("🚀 启动Ray集群...")
        try:
            # 检查是否已有Ray集群运行
            result = subprocess.run(['ray', 'status'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Ray集群已在运行")
                return True
            
            # 启动Ray头节点
            cmd = ['ray', 'start', '--head', '--port=6379', '--dashboard-host=0.0.0.0']
            self.ray_process = subprocess.Popen(cmd)
            
            # 等待Ray启动
            time.sleep(5)
            
            # 验证启动
            result = subprocess.run(['ray', 'status'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Ray集群启动成功")
                return True
            else:
                print("❌ Ray集群启动失败")
                return False
                
        except Exception as e:
            print(f"❌ Ray集群启动异常: {e}")
            return False
    
    def start_web_server(self, host="0.0.0.0", port=8000, workers=4):
        """启动Web服务器"""
        print(f"🌐 启动Web服务器 (端口: {port}, 工作进程: {workers})...")
        
        cmd = [
            'uvicorn', 
            'main:app',
            f'--host={host}',
            f'--port={port}',
            f'--workers={workers}',
            '--log-level=info'
        ]
        
        try:
            process = subprocess.Popen(cmd)
            self.processes.append(process)
            print(f"✅ Web服务器启动成功，访问: http://{host}:{port}")
            return True
        except Exception as e:
            print(f"❌ Web服务器启动失败: {e}")
            return False
    
    def stop_all(self):
        """停止所有服务"""
        print("🛑 正在停止所有服务...")
        
        # 停止Web服务器
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=10)
                print("✅ Web服务器已停止")
            except subprocess.TimeoutExpired:
                process.kill()
                print("⚠️ Web服务器被强制终止")
        
        # 停止Ray集群
        if self.ray_process:
            try:
                subprocess.run(['ray', 'stop'], timeout=10)
                print("✅ Ray集群已停止")
            except:
                print("⚠️ Ray集群停止时出现问题")
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            print(f"\\n收到信号 {signum}，正在优雅关闭...")
            self.stop_all()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        atexit.register(self.stop_all)
    
    def check_dependencies(self):
        """检查依赖"""
        print("🔍 检查依赖...")
        
        required_commands = ['ray', 'uvicorn']
        missing = []
        
        for cmd in required_commands:
            try:
                subprocess.run([cmd, '--version'], capture_output=True, check=True)
                print(f"✅ {cmd} 已安装")
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(cmd)
                print(f"❌ {cmd} 未安装")
        
        if missing:
            print(f"\\n请安装缺失的依赖: {', '.join(missing)}")
            print("运行: pip install -r requirements.txt")
            return False
        
        return True
    
    def run(self, host="0.0.0.0", port=8000, workers=4):
        """运行生产环境"""
        print("=== 分布式消息传输系统 - 生产环境启动 ===\\n")
        
        if not self.check_dependencies():
            return False
        
        self.setup_signal_handlers()
        
        # 启动Ray集群
        if not self.start_ray_cluster():
            return False
        
        # 启动Web服务器
        if not self.start_web_server(host, port, workers):
            self.stop_all()
            return False
        
        print(f"\\n🎉 系统启动完成!")
        print(f"📊 Web界面: http://{host}:{port}")
        print(f"📊 Ray Dashboard: http://{host}:8265")
        print("\\n按 Ctrl+C 停止服务\\n")
        
        # 保持运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='分布式消息传输系统 - 生产环境')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=8000, help='服务器端口')
    parser.add_argument('--workers', type=int, default=4, help='工作进程数')
    parser.add_argument('--dev', action='store_true', help='开发模式（单进程）')
    
    args = parser.parse_args()
    
    manager = ProductionManager()
    
    if args.dev:
        print("🔧 开发模式启动...")
        # 开发模式：单进程，自动重载
        if manager.start_ray_cluster():
            cmd = ['uvicorn', 'main:app', f'--host={args.host}', f'--port={args.port}', '--reload']
            try:
                subprocess.run(cmd)
            except KeyboardInterrupt:
                manager.stop_all()
    else:
        # 生产模式：多进程
        success = manager.run(args.host, args.port, args.workers)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
