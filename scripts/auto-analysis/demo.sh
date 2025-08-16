#!/bin/bash

#===============================================================================
# SuperClaude Auto-Analysis Demo Script
# 演示自动分析系统的完整功能
#===============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_OUTPUT_DIR="${SCRIPT_DIR}/demo-output"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}════════════════════════════════════════${NC}"
echo -e "${CYAN}SuperClaude Auto-Analysis Demo${NC}"
echo -e "${CYAN}════════════════════════════════════════${NC}"
echo ""

# 清理之前的演示输出
if [[ -d "$DEMO_OUTPUT_DIR" ]]; then
    echo -e "${YELLOW}清理之前的演示输出...${NC}"
    rm -rf "$DEMO_OUTPUT_DIR"
fi

# 演示1: 配置验证
echo -e "${BLUE}🔧 演示1: 配置文件验证${NC}"
echo "验证配置文件格式..."
python3 "$SCRIPT_DIR/tools/config-loader.py" --validate "$SCRIPT_DIR/config/analysis-config.yaml"
echo -e "${GREEN}✅ 配置文件验证通过${NC}"
echo ""

# 演示2: 项目分析器
echo -e "${BLUE}📊 演示2: 项目结构分析${NC}"
echo "分析当前项目结构..."
mkdir -p "$DEMO_OUTPUT_DIR"
python3 "$SCRIPT_DIR/tools/project-analyzer.py" \
    --project-path "$SCRIPT_DIR/../.." \
    --output-dir "$DEMO_OUTPUT_DIR" \
    --project-type framework \
    --verbose
echo ""

# 演示3: 文档生成器
echo -e "${BLUE}📝 演示3: 文档生成${NC}"
echo "基于分析结果生成文档..."
python3 "$SCRIPT_DIR/tools/doc-generator.py" \
    --project-path "$SCRIPT_DIR/../.." \
    --output-dir "$DEMO_OUTPUT_DIR" \
    --depth 2 \
    --project-type framework \
    --templates-dir "$SCRIPT_DIR/templates" \
    --verbose
echo ""

# 演示4: 报告生成
echo -e "${BLUE}📈 演示4: 分析报告生成${NC}"
echo "生成统计和质量报告..."
echo "=== 统计报告 ==="
python3 "$SCRIPT_DIR/tools/report-generator.py" \
    --output-dir "$DEMO_OUTPUT_DIR" \
    --format summary
echo ""
echo "=== 质量报告 ==="
python3 "$SCRIPT_DIR/tools/report-generator.py" \
    --output-dir "$DEMO_OUTPUT_DIR" \
    --format quality
echo ""

# 演示5: 生成的文档概览
echo -e "${BLUE}📄 演示5: 生成的文档概览${NC}"
echo "生成的文档列表："
if [[ -d "$DEMO_OUTPUT_DIR" ]]; then
    find "$DEMO_OUTPUT_DIR" -name "*.md" -type f | while read -r file; do
        lines=$(wc -l < "$file")
        filename=$(basename "$file")
        echo -e "  ${GREEN}✓${NC} $filename ($lines 行)"
    done
else
    echo -e "${RED}❌ 未找到生成的文档${NC}"
fi
echo ""

# 演示6: 文档内容预览
echo -e "${BLUE}👀 演示6: README内容预览${NC}"
readme_file="$DEMO_OUTPUT_DIR/README.md"
if [[ -f "$readme_file" ]]; then
    echo "README.md 前20行内容："
    echo "------------------------"
    head -20 "$readme_file"
    echo "------------------------"
    echo "(查看完整内容: cat $readme_file)"
else
    echo -e "${RED}❌ README.md 未生成${NC}"
fi
echo ""

# 演示7: 项目元数据展示
echo -e "${BLUE}🔍 演示7: 项目元数据${NC}"
metadata_file="$DEMO_OUTPUT_DIR/project-metadata.json"
if [[ -f "$metadata_file" ]]; then
    echo "项目元数据摘要："
    python3 -c "
import json
with open('$metadata_file') as f:
    data = json.load(f)
    print(f'  项目名称: {data.get(\"name\", \"N/A\")}')
    print(f'  项目类型: {data.get(\"type\", \"N/A\")}')
    print(f'  技术栈: {\", \".join(data.get(\"technologies\", []))}')
    print(f'  文件数量: {data.get(\"structure\", {}).get(\"total_files\", \"N/A\")}')
    print(f'  代码行数: {data.get(\"structure\", {}).get(\"total_lines\", \"N/A\")}')
    print(f'  复杂度: {data.get(\"complexity\", {}).get(\"level\", \"N/A\")}')
"
else
    echo -e "${RED}❌ 项目元数据文件未生成${NC}"
fi
echo ""

# 演示8: 模拟完整工作流
echo -e "${BLUE}🚀 演示8: 完整工作流测试${NC}"
echo "测试完整的自动分析脚本（深度1，不执行Git操作）..."

# 创建临时配置文件（禁用Git）
temp_config="$DEMO_OUTPUT_DIR/no-git-config.yaml"
cp "$SCRIPT_DIR/config/analysis-config.yaml" "$temp_config"
cat >> "$temp_config" << EOF

# 禁用Git操作（演示用）
git:
  auto_commit:
    enabled: false
  auto_push:
    enabled: false
EOF

# 清理演示输出目录以测试完整流程
rm -rf "$DEMO_OUTPUT_DIR/full-test"

# 执行完整分析（但限制深度和禁用Git）
echo "执行命令: ./auto-analyze.sh --config $temp_config --depth 1 --output $DEMO_OUTPUT_DIR/full-test --force $SCRIPT_DIR/../.."

# 注意：这里只是演示命令，实际执行需要SuperClaude环境
echo -e "${YELLOW}注意: 完整分析需要SuperClaude环境，这里仅展示命令格式${NC}"
echo ""

# 演示总结
echo -e "${CYAN}════════════════════════════════════════${NC}"
echo -e "${CYAN}演示总结${NC}"
echo -e "${CYAN}════════════════════════════════════════${NC}"

echo -e "${GREEN}✅ 已成功演示的功能:${NC}"
echo "  🔧 配置文件加载和验证"
echo "  📊 项目结构自动分析"
echo "  📝 基于模板的文档自动生成"
echo "  📈 统计和质量报告生成"
echo "  🔍 项目元数据提取"

echo ""
echo -e "${YELLOW}📁 演示输出目录: $DEMO_OUTPUT_DIR${NC}"
echo -e "${YELLOW}📖 详细文档: $SCRIPT_DIR/README.md${NC}"
echo -e "${YELLOW}🎯 使用示例: $SCRIPT_DIR/example-usage.sh${NC}"

echo ""
echo -e "${BLUE}要运行完整的分析流程，请确保:${NC}"
echo "  1. 已安装并配置SuperClaude CLI"
echo "  2. 项目在Git仓库中（如需自动提交）"
echo "  3. 有足够的磁盘空间用于生成文档"

echo ""
echo -e "${CYAN}感谢使用SuperClaude Auto-Analysis System!${NC}"