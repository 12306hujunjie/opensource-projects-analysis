#!/bin/bash

#===============================================================================
# SuperClaude Auto-Analysis Usage Examples
# 展示各种使用场景的示例脚本
#===============================================================================

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_ANALYZE="$SCRIPT_DIR/auto-analyze.sh"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}SuperClaude Auto-Analysis Usage Examples${NC}"
echo "========================================================"

# 检查主脚本是否存在
if [[ ! -f "$AUTO_ANALYZE" ]]; then
    echo "错误: auto-analyze.sh 未找到"
    exit 1
fi

# 示例1: 基础使用
echo -e "\n${GREEN}示例1: 基础分析${NC}"
echo "分析SuperClaude Framework项目："
echo "命令: $AUTO_ANALYZE /path/to/SuperClaude_Framework"
echo ""

# 示例2: 指定输出目录
echo -e "${GREEN}示例2: 指定输出目录${NC}"
echo "将分析结果输出到指定目录："
echo "命令: $AUTO_ANALYZE -o docs/MyAnalysis /path/to/project"
echo ""

# 示例3: 自定义深度和类型
echo -e "${GREEN}示例3: 自定义分析参数${NC}"
echo "设置分析深度为3，项目类型为library："
echo "命令: $AUTO_ANALYZE --depth 3 --type library /path/to/project"
echo ""

# 示例4: 启用并行分析
echo -e "${GREEN}示例4: 高性能并行分析${NC}"
echo "启用并行分析以提高速度："
echo "命令: $AUTO_ANALYZE --parallel --verbose /path/to/large/project"
echo ""

# 示例5: 强制覆盖现有分析
echo -e "${GREEN}示例5: 强制覆盖分析${NC}"
echo "强制覆盖现有的分析结果："
echo "命令: $AUTO_ANALYZE --force --output docs/RefreshAnalysis /path/to/project"
echo ""

# 示例6: 使用自定义配置
echo -e "${GREEN}示例6: 自定义配置分析${NC}"
echo "使用自定义配置文件进行分析："
echo "命令: $AUTO_ANALYZE --config custom-config.yaml /path/to/project"
echo ""

# 示例7: 完整参数示例
echo -e "${GREEN}示例7: 完整参数组合${NC}"
echo "使用所有可用参数的完整示例："
cat << 'EOF'
命令: ./auto-analyze.sh \
  --config config/analysis-config.yaml \
  --output docs/ComprehensiveAnalysis \
  --depth 5 \
  --type framework \
  --parallel \
  --force \
  --verbose \
  /path/to/SuperClaude_Framework
EOF
echo ""

# 实际运行示例 (如果提供了项目路径)
if [[ $# -gt 0 ]]; then
    echo -e "${YELLOW}执行实际分析示例...${NC}"
    
    PROJECT_PATH="$1"
    EXAMPLE_OUTPUT="$SCRIPT_DIR/example-output"
    
    echo "项目路径: $PROJECT_PATH"
    echo "输出目录: $EXAMPLE_OUTPUT"
    echo ""
    
    # 执行基础分析示例
    echo "执行命令: $AUTO_ANALYZE --depth 2 --force --verbose --output $EXAMPLE_OUTPUT $PROJECT_PATH"
    
    if [[ -d "$PROJECT_PATH" ]]; then
        "$AUTO_ANALYZE" \
            --depth 2 \
            --force \
            --verbose \
            --output "$EXAMPLE_OUTPUT" \
            "$PROJECT_PATH"
    else
        echo "错误: 项目路径不存在: $PROJECT_PATH"
    fi
else
    echo -e "${YELLOW}提示:${NC} 要运行实际示例，请提供项目路径:"
    echo "  $0 /path/to/your/project"
fi

echo ""
echo "========================================================"
echo -e "${BLUE}更多使用说明请参考 README.md${NC}"