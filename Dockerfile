FROM python:3.11-slim

# 设置工作目录
WORKDIR /opt/castray-system

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p downloads demo_files logs && \
    chmod 755 downloads demo_files logs

# 设置环境变量
ENV PYTHONPATH=/opt/castray-system
ENV RAY_DISABLE_IMPORT_WARNING=1
ENV CASTRAY_CONFIG=/opt/castray-system/config_linux.json

# 暴露端口
EXPOSE 8000 9000-9999/udp

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# 启动命令
CMD ["python3", "main.py"]
