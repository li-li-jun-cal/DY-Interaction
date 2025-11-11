#!/bin/bash
# DY-Interaction 部署助手脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        echo "请访问 https://docs.docker.com/get-docker/ 安装 Docker"
        exit 1
    fi
    print_info "Docker 版本: $(docker --version)"
}

# 检查 Docker Compose
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装"
        echo "请访问 https://docs.docker.com/compose/install/ 安装 Docker Compose"
        exit 1
    fi
    print_info "Docker Compose 版本: $(docker-compose --version)"
}

# 检查 .env 文件
check_env() {
    if [ ! -f ".env" ]; then
        print_warn ".env 文件不存在"
        if [ -f ".env.example" ]; then
            print_info "从 .env.example 创建 .env 文件..."
            cp .env.example .env
            print_warn "请编辑 .env 文件，填入实际配置"
            exit 0
        else
            print_error ".env.example 也不存在"
            exit 1
        fi
    fi
    print_info ".env 文件存在"
}

# 创建必要目录
create_dirs() {
    print_info "创建必要目录..."
    mkdir -p data logs config
    print_info "目录创建完成"
}

# 构建镜像
build_image() {
    print_info "构建 Docker 镜像..."
    docker-compose build
    print_info "镜像构建完成"
}

# 启动服务
start_services() {
    print_info "启动服务..."

    if [ "$1" == "all" ]; then
        docker-compose --profile maintenance up -d
    else
        docker-compose up -d
    fi

    print_info "服务启动完成"
}

# 停止服务
stop_services() {
    print_info "停止服务..."
    docker-compose down
    print_info "服务已停止"
}

# 查看状态
show_status() {
    print_info "服务状态:"
    docker-compose ps
}

# 查看日志
show_logs() {
    if [ -z "$1" ]; then
        docker-compose logs -f --tail=100
    else
        docker-compose logs -f --tail=100 "$1"
    fi
}

# 备份数据库
backup_database() {
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).db"
    print_info "备份数据库到 data/$BACKUP_FILE ..."

    if [ -f "data/dy_interaction.db" ]; then
        cp data/dy_interaction.db "data/$BACKUP_FILE"
        print_info "备份完成: data/$BACKUP_FILE"
    else
        print_error "数据库文件不存在"
        exit 1
    fi
}

# 帮助信息
show_help() {
    cat << EOF
DY-Interaction 部署助手

用法: $0 [命令] [选项]

命令:
  check        检查部署环境
  setup        初始化部署环境
  build        构建 Docker 镜像
  start [all]  启动服务 (all: 包含养号服务)
  stop         停止服务
  restart      重启服务
  status       查看服务状态
  logs [svc]   查看日志 (svc: 特定服务名)
  backup       备份数据库
  help         显示此帮助信息

示例:
  $0 check                  # 检查环境
  $0 setup                  # 初始化
  $0 start                  # 启动核心服务
  $0 start all              # 启动所有服务（包含养号）
  $0 logs crawler           # 查看爬虫日志
  $0 backup                 # 备份数据库

EOF
}

# 主函数
main() {
    case "$1" in
        check)
            print_info "检查部署环境..."
            check_docker
            check_docker_compose
            check_env
            print_info "环境检查完成 ✓"
            ;;
        setup)
            print_info "初始化部署环境..."
            check_docker
            check_docker_compose
            check_env
            create_dirs
            print_info "环境初始化完成 ✓"
            ;;
        build)
            check_docker
            check_docker_compose
            build_image
            ;;
        start)
            check_docker
            check_docker_compose
            check_env
            start_services "$2"
            show_status
            ;;
        stop)
            check_docker_compose
            stop_services
            ;;
        restart)
            check_docker_compose
            stop_services
            sleep 2
            start_services "$2"
            show_status
            ;;
        status)
            check_docker_compose
            show_status
            ;;
        logs)
            check_docker_compose
            show_logs "$2"
            ;;
        backup)
            backup_database
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
