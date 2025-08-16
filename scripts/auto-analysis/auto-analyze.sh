#!/bin/bash

#===============================================================================
# SuperClaude Framework Auto-Analysis Script
# 自动完成框架源码深度分析和文档生成工作流
#===============================================================================

set -euo pipefail

# 脚本信息
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $*"; }

# 显示帮助信息
show_help() {
    cat << EOF
SuperClaude Framework Auto-Analysis Script v${SCRIPT_VERSION}

用法: $0 [OPTIONS] PROJECT_PATH

参数:
  PROJECT_PATH              要分析的项目路径

选项:
  -c, --config FILE        指定配置文件 (默认: config/analysis-config.yaml)
  -o, --output DIR         指定输出目录 (默认: docs/{PROJECT_NAME})
  -d, --depth LEVEL        分析深度 (1-5, 默认: 5)
  -t, --type TYPE          项目类型 (framework|library|application, 默认: auto)
  -f, --force              强制覆盖已存在的文档
  -p, --parallel           启用并行分析
  -v, --verbose            详细输出
  -h, --help               显示此帮助信息

示例:
  $0 /path/to/SuperClaude_Framework
  $0 -c custom-config.yaml -o docs/MyAnalysis /path/to/project
  $0 --depth 3 --parallel --force /path/to/framework

EOF
}

# 默认参数
CONFIG_FILE="${SCRIPT_DIR}/config/analysis-config.yaml"
OUTPUT_DIR=""
ANALYSIS_DEPTH=5
PROJECT_TYPE="auto"
FORCE_OVERWRITE=false
ENABLE_PARALLEL=false
VERBOSE=false
PROJECT_PATH=""

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -d|--depth)
                ANALYSIS_DEPTH="$2"
                shift 2
                ;;
            -t|--type)
                PROJECT_TYPE="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_OVERWRITE=true
                shift
                ;;
            -p|--parallel)
                ENABLE_PARALLEL=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$PROJECT_PATH" ]]; then
                    PROJECT_PATH="$1"
                else
                    log_error "多余的参数: $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

# 验证参数
validate_args() {
    # 检查项目路径
    if [[ -z "$PROJECT_PATH" ]]; then
        log_error "必须指定项目路径"
        show_help
        exit 1
    fi
    
    if [[ ! -d "$PROJECT_PATH" ]]; then
        log_error "项目路径不存在: $PROJECT_PATH"
        exit 1
    fi
    
    # 检查配置文件
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "配置文件不存在: $CONFIG_FILE"
        exit 1
    fi
    
    # 检查分析深度
    if [[ "$ANALYSIS_DEPTH" -lt 1 || "$ANALYSIS_DEPTH" -gt 5 ]]; then
        log_error "分析深度必须在1-5之间"
        exit 1
    fi
    
    # 设置输出目录
    if [[ -z "$OUTPUT_DIR" ]]; then
        PROJECT_NAME=$(basename "$PROJECT_PATH")
        OUTPUT_DIR="${PROJECT_ROOT}/docs/${PROJECT_NAME}"
    fi
}

# 检查依赖
check_dependencies() {
    log_step "检查依赖环境..."
    
    # 检查SuperClaude CLI
    if ! command -v superclaude &> /dev/null; then
        log_error "SuperClaude CLI未安装或不在PATH中"
        exit 1
    fi
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装"
        exit 1
    fi
    
    # 检查必要的Python包
    local required_packages=("yaml" "jinja2" "click")
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" &> /dev/null; then
            log_warn "Python包 $package 未安装，尝试安装..."
            pip3 install "$package" || {
                log_error "无法安装Python包: $package"
                exit 1
            }
        fi
    done
    
    log_success "依赖检查完成"
}

# 加载配置
load_config() {
    log_step "加载配置文件: $CONFIG_FILE"
    
    # 使用Python脚本加载YAML配置
    python3 "${SCRIPT_DIR}/tools/config-loader.py" "$CONFIG_FILE" > /tmp/analysis_config.env
    source /tmp/analysis_config.env
    rm -f /tmp/analysis_config.env
    
    log_success "配置加载完成"
}

# 初始化项目分析
init_analysis() {
    log_step "初始化项目分析..."
    
    # 创建输出目录
    if [[ -d "$OUTPUT_DIR" ]]; then
        if [[ "$FORCE_OVERWRITE" = true ]]; then
            log_warn "删除已存在的文档目录: $OUTPUT_DIR"
            rm -rf "$OUTPUT_DIR"
        else
            log_error "输出目录已存在: $OUTPUT_DIR (使用 -f 强制覆盖)"
            exit 1
        fi
    fi
    
    mkdir -p "$OUTPUT_DIR"
    log_info "创建输出目录: $OUTPUT_DIR"
    
    # 项目结构预分析
    log_info "执行项目结构预分析..."
    python3 "${SCRIPT_DIR}/tools/project-analyzer.py" \
        --project-path "$PROJECT_PATH" \
        --output-dir "$OUTPUT_DIR" \
        --project-type "$PROJECT_TYPE" \
        ${VERBOSE:+--verbose}
    
    log_success "项目分析初始化完成"
}

# 执行SuperClaude分析
run_superclaude_analysis() {
    log_step "执行SuperClaude深度分析..."
    
    # 切换到项目目录
    cd "$PROJECT_PATH"
    
    # 构建SuperClaude命令
    local sc_cmd="superclaude"
    local sc_flags="--ultra-think --seq"
    
    if [[ "$ENABLE_PARALLEL" = true ]]; then
        sc_flags="$sc_flags --delegate auto --wave-mode auto"
    fi
    
    if [[ "$VERBOSE" = true ]]; then
        sc_flags="$sc_flags --verbose"
    fi
    
    # 执行核心分析命令
    log_info "执行架构分析..."
    $sc_cmd /analyze . $sc_flags --focus architecture --scope system || {
        log_error "架构分析失败"
        return 1
    }
    
    log_info "执行安全分析..."
    $sc_cmd /analyze . $sc_flags --focus security --scope system || {
        log_error "安全分析失败"
        return 1
    }
    
    log_info "执行质量分析..."
    $sc_cmd /analyze . $sc_flags --focus quality --scope system || {
        log_error "质量分析失败"
        return 1
    }
    
    # 切换回原目录
    cd "$PROJECT_ROOT"
    
    log_success "SuperClaude分析完成"
}

# 生成文档
generate_documentation() {
    log_step "生成分析文档..."
    
    python3 "${SCRIPT_DIR}/tools/doc-generator.py" \
        --project-path "$PROJECT_PATH" \
        --output-dir "$OUTPUT_DIR" \
        --depth "$ANALYSIS_DEPTH" \
        --project-type "$PROJECT_TYPE" \
        --templates-dir "${SCRIPT_DIR}/templates" \
        ${VERBOSE:+--verbose} || {
        log_error "文档生成失败"
        return 1
    }
    
    log_success "文档生成完成"
}

# Git操作
handle_git_operations() {
    log_step "处理Git操作..."
    
    # 检查是否在Git仓库中
    if ! git -C "$PROJECT_ROOT" rev-parse --git-dir &> /dev/null; then
        log_warn "不在Git仓库中，跳过Git操作"
        return 0
    fi
    
    python3 "${SCRIPT_DIR}/tools/git-manager.py" \
        --project-root "$PROJECT_ROOT" \
        --output-dir "$OUTPUT_DIR" \
        --project-path "$PROJECT_PATH" \
        ${VERBOSE:+--verbose} || {
        log_error "Git操作失败"
        return 1
    }
    
    log_success "Git操作完成"
}

# 生成分析报告
generate_report() {
    log_step "生成分析报告..."
    
    local report_file="${OUTPUT_DIR}/analysis-report.md"
    local project_name=$(basename "$PROJECT_PATH")
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat > "$report_file" << EOF
# ${project_name} 自动分析报告

**生成时间**: $timestamp
**脚本版本**: $SCRIPT_VERSION
**分析深度**: L1-L$ANALYSIS_DEPTH
**项目类型**: $PROJECT_TYPE

## 分析统计

$(python3 "${SCRIPT_DIR}/tools/report-generator.py" --output-dir "$OUTPUT_DIR")

## 文档结构

EOF
    
    # 添加文档列表
    find "$OUTPUT_DIR" -name "*.md" -not -name "analysis-report.md" | sort | while read -r file; do
        local filename=$(basename "$file")
        local lines=$(wc -l < "$file")
        echo "- **$filename** ($lines 行)" >> "$report_file"
    done
    
    log_success "分析报告已生成: $report_file"
}

# 清理临时文件
cleanup() {
    log_step "清理临时文件..."
    rm -f /tmp/analysis_*.tmp
    log_success "清理完成"
}

# 主函数
main() {
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}SuperClaude Auto-Analysis Script${NC}"
    echo -e "${CYAN}================================${NC}"
    echo
    
    # 解析和验证参数
    parse_args "$@"
    validate_args
    
    # 显示配置信息
    log_info "项目路径: $PROJECT_PATH"
    log_info "输出目录: $OUTPUT_DIR"
    log_info "分析深度: L1-L$ANALYSIS_DEPTH"
    log_info "项目类型: $PROJECT_TYPE"
    [[ "$ENABLE_PARALLEL" = true ]] && log_info "并行模式: 启用"
    echo
    
    # 执行分析流程
    local start_time=$(date +%s)
    
    check_dependencies
    load_config
    init_analysis
    run_superclaude_analysis
    generate_documentation
    handle_git_operations
    generate_report
    cleanup
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo
    log_success "分析完成！耗时: ${duration}秒"
    log_success "文档路径: $OUTPUT_DIR"
    
    # 显示文档统计
    local doc_count=$(find "$OUTPUT_DIR" -name "*.md" | wc -l)
    local total_lines=$(find "$OUTPUT_DIR" -name "*.md" -exec wc -l {} + | tail -1 | awk '{print $1}')
    
    echo -e "${GREEN}📊 分析统计:${NC}"
    echo -e "  📄 文档数量: $doc_count"
    echo -e "  📝 总行数: $total_lines"
    echo -e "  🎯 分析深度: L1-L$ANALYSIS_DEPTH"
}

# 错误处理
trap 'log_error "脚本执行失败，在第$LINENO行"; cleanup; exit 1' ERR

# 执行主函数
main "$@"