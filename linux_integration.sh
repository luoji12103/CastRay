#!/bin/bash
# CastRay Linux集群快速整合脚本
# 用法: ./linux_integration.sh [选项]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
CastRay Linux集群整合脚本

用法: $0 [选项]

选项:
    --ray-address ADDR    Ray集群地址 (默认: auto)
    --install-dir DIR     安装目录 (默认: /opt/castray-system)
    --port PORT          Web服务端口 (默认: 8000)
    --systemd            安装为systemd服务
    --docker             使用Docker部署
    --check-only         仅检查环境，不执行安装
    --help               显示此帮助信息

示例:
    $0                                    # 默认安装
    $0 --ray-address ray://head:10001     # 指定Ray地址
    $0 --systemd                          # 安装为系统服务
    $0 --docker                          # Docker部署
    $0 --check-only                      # 环境检查

EOF
}

# 默认配置
RAY_ADDRESS="auto"
INSTALL_DIR="/opt/castray-system"
WEB_PORT="8000"
INSTALL_SYSTEMD=false
USE_DOCKER=false
CHECK_ONLY=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --ray-address)
            RAY_ADDRESS="$2"
            shift 2
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --port)
            WEB_PORT="$2"
            shift 2
            ;;
        --systemd)
            INSTALL_SYSTEMD=true
            shift
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查是否为root用户
check_root() {
    if [[ $INSTALL_SYSTEMD == true ]] && [[ $EUID -ne 0 ]]; then
        log_error "systemd安装需要root权限，请使用sudo运行"
        exit 1
    fi
}

# 环境检查
check_environment() {
    log_info "检查系统环境..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        log_error "不支持的操作系统"
        exit 1
    fi
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装Python 3.8+"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    if [[ $(echo "$python_version 3.8" | awk '{print ($1 < $2)}') == 1 ]]; then
        log_error "Python版本过低: $python_version，需要3.8+"
        exit 1
    fi
    log_success "Python版本: $python_version"
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_warning "未找到pip3，尝试安装..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-pip
        else
            log_error "无法自动安装pip3，请手动安装"
            exit 1
        fi
    fi
    
    # 检查Ray
    if ! python3 -c "import ray" &> /dev/null; then
        log_warning "未找到Ray，将自动安装"
    else
        ray_version=$(python3 -c "import ray; print(ray.__version__)")
        log_success "Ray版本: $ray_version"
    fi
    
    # 检查Ray集群连接
    if [[ $RAY_ADDRESS != "auto" ]]; then
        log_info "检查Ray集群连接: $RAY_ADDRESS"
        if ! python3 -c "import ray; ray.init(address='$RAY_ADDRESS')" &> /dev/null; then
            log_warning "无法连接到指定Ray集群: $RAY_ADDRESS"
        else
            log_success "Ray集群连接正常"
        fi
    else
        log_info "将使用自动Ray集群发现"
    fi
    
    # 检查端口占用
    if netstat -tuln 2>/dev/null | grep -q ":$WEB_PORT "; then
        log_warning "端口 $WEB_PORT 已被占用"
    else
        log_success "端口 $WEB_PORT 可用"
    fi
    
    # 检查Docker（如果需要）
    if [[ $USE_DOCKER == true ]]; then
        if ! command -v docker &> /dev/null; then
            log_error "Docker未安装，请先安装Docker"
            exit 1
        fi
        if ! command -v docker-compose &> /dev/null; then
            log_error "Docker Compose未安装，请先安装Docker Compose"
            exit 1
        fi
        log_success "Docker环境检查通过"
    fi
}

# 安装系统依赖
install_system_dependencies() {
    log_info "安装系统依赖..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y python3-pip python3-dev gcc g++ curl net-tools
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip python3-devel gcc gcc-c++ curl net-tools
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3-pip python3-devel gcc gcc-c++ curl net-tools
    else
        log_warning "无法识别包管理器，请手动安装依赖"
    fi
}

# 安装Python依赖
install_python_dependencies() {
    log_info "安装Python依赖..."
    
    # 创建requirements.txt如果不存在
    if [[ ! -f requirements.txt ]]; then
        cat > requirements.txt << EOF
ray>=2.4.0
fastapi>=0.100.0
uvicorn>=0.20.0
websockets>=11.0
aiofiles>=23.0.0
python-multipart>=0.0.6
jinja2>=3.1.0
EOF
    fi
    
    pip3 install -r requirements.txt
    log_success "Python依赖安装完成"
}

# 创建配置文件
create_config() {
    log_info "创建Linux配置文件..."
    
    cat > config_linux.json << EOF
{
    "ray_cluster": {
        "address": "$RAY_ADDRESS",
        "namespace": "castray",
        "create_demo_nodes": false,
        "runtime_env": {
            "working_dir": "$INSTALL_DIR"
        }
    },
    "web_server": {
        "host": "0.0.0.0",
        "port": $WEB_PORT
    },
    "file_transfer": {
        "download_dir": "$INSTALL_DIR/downloads",
        "chunk_size": 8192,
        "max_file_size": 1073741824,
        "timeout": 30
    },
    "logging": {
        "level": "INFO",
        "file": "$INSTALL_DIR/logs/castray.log",
        "max_size": 10485760,
        "backup_count": 5
    },
    "monitoring": {
        "metrics_port": 9090,
        "health_check_interval": 30
    }
}
EOF
    
    log_success "配置文件创建完成: config_linux.json"
}

# 创建目录结构
create_directories() {
    if [[ $INSTALL_SYSTEMD == true ]]; then
        log_info "创建系统目录结构..."
        sudo mkdir -p $INSTALL_DIR/{logs,downloads,temp}
        sudo chown -R $USER:$USER $INSTALL_DIR
    else
        log_info "创建目录结构..."
        mkdir -p {logs,downloads,temp}
    fi
    
    log_success "目录结构创建完成"
}

# Docker部署
deploy_with_docker() {
    log_info "使用Docker部署..."
    
    # 创建docker-compose.yml
    cat > docker-compose.yml << EOF
version: '3.8'

services:
  castray:
    build: .
    container_name: castray-system
    ports:
      - "${WEB_PORT}:8000"
    environment:
      - RAY_ADDRESS=${RAY_ADDRESS}
      - PYTHONPATH=/app
      - CASTRAY_CONFIG=/app/config_linux.json
    volumes:
      - ./downloads:/app/downloads
      - ./logs:/app/logs
      - ./config_linux.json:/app/config_linux.json
    restart: unless-stopped
    network_mode: host
EOF
    
    # 构建并启动
    docker-compose up -d
    log_success "Docker部署完成"
}

# systemd服务部署
deploy_with_systemd() {
    log_info "安装为systemd服务..."
    
    # 创建系统用户
    if ! id "castray" &>/dev/null; then
        sudo useradd -r -d $INSTALL_DIR -s /bin/bash castray
    fi
    
    # 复制文件到系统目录
    sudo cp -r ./* $INSTALL_DIR/
    sudo chown -R castray:castray $INSTALL_DIR
    
    # 创建systemd服务文件
    sudo tee /etc/systemd/system/castray.service << EOF
[Unit]
Description=CastRay Distributed File Transfer System
After=network.target
Requires=network.target

[Service]
Type=simple
User=castray
Group=castray
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=RAY_ADDRESS=$RAY_ADDRESS
Environment=PYTHONPATH=$INSTALL_DIR
Environment=CASTRAY_CONFIG=$INSTALL_DIR/config_linux.json

[Install]
WantedBy=multi-user.target
EOF
    
    # 启用并启动服务
    sudo systemctl daemon-reload
    sudo systemctl enable castray
    sudo systemctl start castray
    
    log_success "systemd服务安装完成"
}

# 普通部署
deploy_normal() {
    log_info "执行普通部署..."
    
    # 设置环境变量
    export RAY_ADDRESS=$RAY_ADDRESS
    export PYTHONPATH=$(pwd)
    export CASTRAY_CONFIG=$(pwd)/config_linux.json
    
    # 启动服务
    log_info "启动CastRay服务..."
    nohup python3 main.py > logs/castray.log 2>&1 &
    PID=$!
    echo $PID > castray.pid
    
    log_success "服务已启动，PID: $PID"
}

# 验证部署
verify_deployment() {
    log_info "验证部署状态..."
    
    # 等待服务启动
    sleep 5
    
    # 检查Web服务
    if curl -s http://localhost:$WEB_PORT/api/status > /dev/null; then
        log_success "Web服务正常运行"
    else
        log_error "Web服务未响应"
        return 1
    fi
    
    # 检查Ray连接
    if [[ $USE_DOCKER == false ]]; then
        if python3 -c "
import ray
import sys
try:
    if '$RAY_ADDRESS' == 'auto':
        ray.init()
    else:
        ray.init(address='$RAY_ADDRESS')
    print('Ray连接成功')
    ray.shutdown()
    sys.exit(0)
except Exception as e:
    print(f'Ray连接失败: {e}')
    sys.exit(1)
"; then
            log_success "Ray集群连接正常"
        else
            log_warning "Ray集群连接可能有问题"
        fi
    fi
    
    log_success "部署验证完成！"
}

# 显示部署信息
show_deployment_info() {
    echo
    log_success "🎉 CastRay Linux集群整合完成！"
    echo
    echo "📍 部署信息:"
    echo "   Web界面: http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
    echo "   API接口: http://$(hostname -I | awk '{print $1}'):$WEB_PORT/api"
    echo "   Ray地址: $RAY_ADDRESS"
    echo "   安装目录: $INSTALL_DIR"
    echo
    echo "🔧 管理命令:"
    if [[ $INSTALL_SYSTEMD == true ]]; then
        echo "   启动服务: sudo systemctl start castray"
        echo "   停止服务: sudo systemctl stop castray"
        echo "   查看状态: sudo systemctl status castray"
        echo "   查看日志: journalctl -u castray -f"
    elif [[ $USE_DOCKER == true ]]; then
        echo "   启动服务: docker-compose up -d"
        echo "   停止服务: docker-compose down"
        echo "   查看状态: docker-compose ps"
        echo "   查看日志: docker-compose logs -f"
    else
        echo "   停止服务: kill \$(cat castray.pid)"
        echo "   查看日志: tail -f logs/castray.log"
    fi
    echo
    echo "📚 更多信息请查看: INTEGRATION_GUIDE.md"
}

# 主函数
main() {
    echo "🚀 CastRay Linux集群整合脚本"
    echo "=================================="
    
    # 检查root权限
    check_root
    
    # 环境检查
    check_environment
    
    if [[ $CHECK_ONLY == true ]]; then
        log_success "环境检查完成，系统就绪！"
        exit 0
    fi
    
    # 安装依赖
    install_system_dependencies
    install_python_dependencies
    
    # 创建配置
    create_config
    create_directories
    
    # 根据选择的方式部署
    if [[ $USE_DOCKER == true ]]; then
        deploy_with_docker
    elif [[ $INSTALL_SYSTEMD == true ]]; then
        deploy_with_systemd
    else
        deploy_normal
    fi
    
    # 验证部署
    verify_deployment
    
    # 显示部署信息
    show_deployment_info
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main "$@"
