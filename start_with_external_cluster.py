#!/usr/bin/env python3
"""
启动脚本：使用外部Ray集群配置启动CastRay
"""

import os
import sys
import logging
from pathlib import Path

# 设置环境变量使用外部集群配置
os.environ['CASTRAY_CONFIG'] = 'config_external_cluster.json'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 启动CastRay (外部Ray集群模式)")
    logger.info(f"📋 配置文件: {os.environ.get('CASTRAY_CONFIG')}")
    
    # 导入并启动主程序
    try:
        import subprocess
        # 直接调用main.py
        result = subprocess.run([sys.executable, "main.py"], 
                              capture_output=False, 
                              text=True)
        if result.returncode != 0:
            logger.error(f"❌ 主程序退出，返回码: {result.returncode}")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
