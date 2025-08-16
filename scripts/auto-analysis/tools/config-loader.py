#!/usr/bin/env python3
"""
SuperClaude Auto-Analysis Configuration Loader
配置文件加载和环境变量生成工具
"""

import sys
import yaml
import argparse
from pathlib import Path


def load_yaml_config(config_file):
    """加载YAML配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"错误: 配置文件未找到 {config_file}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"错误: YAML格式错误 {e}", file=sys.stderr)
        sys.exit(1)


def config_to_env(config, prefix="", result=None):
    """将配置转换为环境变量格式"""
    if result is None:
        result = []
    
    for key, value in config.items():
        env_key = f"{prefix}{key.upper()}" if prefix else key.upper()
        
        if isinstance(value, dict):
            config_to_env(value, f"{env_key}_", result)
        elif isinstance(value, list):
            # 列表转换为逗号分隔的字符串
            env_value = ",".join(str(v) for v in value)
            result.append(f'export {env_key}="{env_value}"')
        elif isinstance(value, bool):
            env_value = "true" if value else "false"
            result.append(f'export {env_key}="{env_value}"')
        else:
            # 转义特殊字符
            env_value = str(value).replace('"', '\\"')
            result.append(f'export {env_key}="{env_value}"')
    
    return result


def main():
    parser = argparse.ArgumentParser(description="SuperClaude配置文件加载器")
    parser.add_argument("config_file", help="YAML配置文件路径")
    parser.add_argument("--validate", action="store_true", help="仅验证配置文件")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_yaml_config(args.config_file)
    
    if args.validate:
        print("配置文件格式正确", file=sys.stderr)
        return
    
    # 生成环境变量
    env_vars = config_to_env(config)
    
    # 输出环境变量设置
    for env_var in env_vars:
        print(env_var)


if __name__ == "__main__":
    main()