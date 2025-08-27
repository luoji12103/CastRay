#!/bin/bash

# CastRay分布式文件传输系统 - Linux部署脚本
# 适用于已有Ray集群的Linux环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# 显示帮助信息
show_help() {
    cat << EOF
CastRay分布式文件传输系统 - Linux部署脚本

用法: $0 [选项]

选项:
    -h, --help              显示此帮助信息
    -i, --install           安装模式 (需要root权限)
    -d, --docker            使用Docker部署
    -r, --ray-address ADDR  指定Ray集群地址 (默认: auto)
    -p, --port PORT         指定Web服务端口 (默认: 8000)
    --check-only            仅检查环境，不安装
    --systemd               创建systemd服务
    --no-demo               不创建演示节点

示例:
    $0 --install                          # 标准安装
    $0 --docker                           # Docker部署
    $0 --install --ray-address ray://head:10001  # 连接到指定Ray集群
    $0 --check-only                       # 仅检查环境

EOF
}

# 检查系统环境
check_environment() {
    print_header "🔍 环境检查"
    
    # 检查操作系统
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        print_error "此脚本仅支持Linux系统"
        exit 1
    fi
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        print_error "未找到Python3，请先安装Python 3.8+"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.8"
    
    if ! printf '%s\n%s\n' "$required_version" "$python_version" | sort -V -C; then
        print_error "Python版本过低: $python_version，需要3.8+"
        exit 1
    fi
    
    print_status "Python版本: $python_version ✓"
    
    # 检查pip
    if ! python3 -m pip --version &> /dev/null; then
        print_error "未找到pip，请先安装pip"
        exit 1
    fi
    
    # 检查Ray
    if python3 -c "import ray" &> /dev/null; then
        ray_version=$(python3 -c "import ray; print(ray.__version__)")
        print_status "Ray版本: $ray_version ✓"
    else
        print_warning "Ray未安装，将在依赖安装时安装"
    fi
    
    # 检查Ray集群状态
    if command -v ray &> /dev/null; then
        if ray status --address="${RAY_ADDRESS:-auto}" &> /dev/null; then
            print_status "Ray集群连接正常 ✓"
        else
            print_warning "无法连接到Ray集群，请确保Ray集群已启动"
        fi
    fi
    
    # 检查网络端口
    if ss -tuln | grep -q ":${WEB_PORT:-8000} "; then
        print_warning "端口 ${WEB_PORT:-8000} 已被占用"
    else
        print_status "端口 ${WEB_PORT:-8000} 可用 ✓"
    fi
}

# 安装依赖
install_dependencies() {
    print_header "📦 安装依赖"
    
    # 安装系统依赖
    if command -v apt-get &> /dev/null; then
        print_status "检测到Debian/Ubuntu系统，安装系统依赖..."
        sudo apt-get update
        sudo apt-get install -y curl netcat-traditional gcc g++ python3-pip python3-dev
    elif command -v yum &> /dev/null; then
        print_status "检测到CentOS/RHEL系统，安装系统依赖..."
        sudo yum update -y
        sudo yum install -y curl nc gcc gcc-c++ python3-pip python3-devel
    elif command -v dnf &> /dev/null; then
        print_status "检测到Fedora系统，安装系统依赖..."
        sudo dnf update -y
        sudo dnf install -y curl nc gcc gcc-c++ python3-pip python3-devel
    fi
    
    # 安装Python依赖
    print_status "安装Python依赖..."
    python3 -m pip install --user -r requirements.txt
    
    print_status "依赖安装完成 ✓"
}

# 创建目录结构
setup_directories() {
    print_header "📁 设置目录结构"
    
    local install_dir="${INSTALL_DIR:-/opt/castray-system}"
    
    if [[ "$INSTALL_MODE" == "true" ]]; then
        # 安装模式，需要root权限
        sudo mkdir -p "$install_dir"/{downloads,demo_files,logs}
        
        # 创建系统用户
        if ! id "castray" &>/dev/null; then
            sudo useradd -r -d "$install_dir" -s /bin/bash castray
            print_status "创建系统用户: castray"
        fi
        
        # 复制文件
        sudo cp -r . "$install_dir/"
        sudo chown -R castray:castray "$install_dir"
        sudo chmod 755 "$install_dir"
        sudo chmod +x "$install_dir/deploy_scripts"/*.sh
        
        # 复制配置文件
        if [[ -f "config_linux.json" ]]; then
            sudo cp config_linux.json "$install_dir/"
        fi
        
        print_status "文件已复制到: $install_dir"
    else
        # 当前目录模式
        mkdir -p downloads demo_files logs
        chmod 755 downloads demo_files logs
        print_status "目录结构已设置"
    fi
}

# 配置防火墙
configure_firewall() {
    print_header "🔥 配置防火墙"
    
    local web_port="${WEB_PORT:-8000}"
    
    # Ubuntu/Debian
    if command -v ufw &> /dev/null; then
        sudo ufw allow "$web_port/tcp" comment "CastRay Web Interface"
        sudo ufw allow 9000:9999/udp comment "CastRay File Transfer"
        print_status "UFW防火墙规则已添加"
    fi
    
    # CentOS/RHEL
    if command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --permanent --add-port="$web_port/tcp"
        sudo firewall-cmd --permanent --add-port=9000-9999/udp
        sudo firewall-cmd --reload
        print_status "Firewalld防火墙规则已添加"
    fi
}

# 创建systemd服务
create_systemd_service() {
    if [[ "$CREATE_SYSTEMD" == "true" && "$INSTALL_MODE" == "true" ]]; then
        print_header "⚙️ 创建systemd服务"
        
        sudo cp deploy_scripts/systemd_service.conf /etc/systemd/system/castray.service
        
        # 更新服务文件中的配置
        sudo sed -i "s|RAY_ADDRESS=auto|RAY_ADDRESS=${RAY_ADDRESS:-auto}|" /etc/systemd/system/castray.service
        
        sudo systemctl daemon-reload
        sudo systemctl enable castray
        
        print_status "systemd服务已创建并启用"
    fi
}

# Docker部署
deploy_with_docker() {
    print_header "🐳 Docker部署"
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 设置环境变量
    export RAY_ADDRESS="${RAY_ADDRESS:-auto}"
    
    # 构建并启动
    print_status "构建Docker镜像..."
    docker-compose build
    
    print_status "启动容器..."
    docker-compose up -d
    
    print_status "Docker部署完成"
    
    # 显示状态
    echo ""
    print_header "📊 部署状态"
    docker-compose ps
}

# 启动服务
start_service() {
    print_header "🚀 启动服务"
    
    if [[ "$INSTALL_MODE" == "true" && "$CREATE_SYSTEMD" == "true" ]]; then
        # 使用systemd启动
        sudo systemctl start castray
        sleep 3
        
        if sudo systemctl is-active --quiet castray; then
            print_status "CastRay服务已启动 ✓"
            print_status "查看状态: systemctl status castray"
            print_status "查看日志: journalctl -u castray -f"
        else
            print_error "CastRay服务启动失败"
            print_error "查看日志: journalctl -u castray"
            exit 1
        fi
    else
        # 直接启动
        print_status "正在启动CastRay系统..."
        export RAY_ADDRESS="${RAY_ADDRESS:-auto}"
        export PYTHONPATH="$(pwd):$PYTHONPATH"
        
        if [[ -f "config_linux.json" ]]; then
            export CASTRAY_CONFIG="$(pwd)/config_linux.json"
        fi
        
        nohup python3 main.py > logs/castray.log 2>&1 &
        echo $! > castray.pid
        
        sleep 3
        
        if ps -p "$(cat castray.pid)" > /dev/null; then
            print_status "CastRay服务已启动 ✓ (PID: $(cat castray.pid))"
            print_status "查看日志: tail -f logs/castray.log"
        else
            print_error "CastRay服务启动失败"
            print_error "查看日志: cat logs/castray.log"
            exit 1
        fi
    fi
}

# 验证部署
verify_deployment() {
    print_header "✅ 验证部署"
    
    local web_port="${WEB_PORT:-8000}"
    local max_attempts=10
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f "http://localhost:$web_port/api/status" > /dev/null; then
            print_status "Web接口响应正常 ✓"
            break
        else
            print_warning "等待Web接口启动... ($attempt/$max_attempts)"
            sleep 3
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        print_error "Web接口验证失败"
        return 1
    fi
    
    # 获取系统IP
    local server_ip=$(hostname -I | awk '{print $1}')
    
    echo ""
    print_header "🎉 部署成功！"
    echo ""
    echo "Web管理界面: http://$server_ip:$web_port"
    echo "API状态接口: http://$server_ip:$web_port/api/status"
    echo ""
    echo "管理命令:"
    if [[ "$INSTALL_MODE" == "true" && "$CREATE_SYSTEMD" == "true" ]]; then
        echo "  启动服务: systemctl start castray"
        echo "  停止服务: systemctl stop castray"
        echo "  查看状态: systemctl status castray"
        echo "  查看日志: journalctl -u castray -f"
    else
        echo "  停止服务: kill \$(cat castray.pid)"
        echo "  查看日志: tail -f logs/castray.log"
    fi
}

# 主函数
main() {
    # 默认值
    INSTALL_MODE="false"
    DOCKER_MODE="false"
    CHECK_ONLY="false"
    CREATE_SYSTEMD="false"
    CREATE_DEMO="true"
    RAY_ADDRESS="auto"
    WEB_PORT="8000"
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -i|--install)
                INSTALL_MODE="true"
                CREATE_SYSTEMD="true"
                shift
                ;;
            -d|--docker)
                DOCKER_MODE="true"
                shift
                ;;
            -r|--ray-address)
                RAY_ADDRESS="$2"
                shift 2
                ;;
            -p|--port)
                WEB_PORT="$2"
                shift 2
                ;;
            --check-only)
                CHECK_ONLY="true"
                shift
                ;;
            --systemd)
                CREATE_SYSTEMD="true"
                shift
                ;;
            --no-demo)
                CREATE_DEMO="false"
                shift
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示配置
    print_header "🔧 部署配置"
    echo "安装模式: $INSTALL_MODE"
    echo "Docker模式: $DOCKER_MODE"
    echo "Ray地址: $RAY_ADDRESS"
    echo "Web端口: $WEB_PORT"
    echo "创建systemd服务: $CREATE_SYSTEMD"
    echo "创建演示节点: $CREATE_DEMO"
    echo ""
    
    # 检查环境
    check_environment
    
    if [[ "$CHECK_ONLY" == "true" ]]; then
        print_status "环境检查完成"
        exit 0
    fi
    
    # 检查权限
    if [[ "$INSTALL_MODE" == "true" && $EUID -ne 0 ]]; then
        print_error "安装模式需要root权限，请使用sudo运行"
        exit 1
    fi
    
    # 执行部署
    if [[ "$DOCKER_MODE" == "true" ]]; then
        deploy_with_docker
    else
        install_dependencies
        setup_directories
        configure_firewall
        create_systemd_service
        start_service
        verify_deployment
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
