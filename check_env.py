#!/usr/bin/env python3
"""检查环境变量配置是否正确"""

from dotenv import load_dotenv
import os
import sys

# 加载 .env 文件
load_dotenv()


def check_api_key(key_name: str, required: bool = False) -> bool:
    """检查单个 API key 是否配置"""
    value = os.getenv(key_name)
    
    if value and not value.startswith("YOUR_"):
        # 显示部分 key（隐藏中间部分）
        if len(value) > 10:
            masked = f"{value[:8]}...{value[-4:]}"
        else:
            masked = "***"
        print(f"  ✅ {key_name}: {masked}")
        return True
    else:
        status = "❌ 必需" if required else "⚠️  可选"
        print(f"  {status} {key_name}: 未配置")
        return False


def main():
    print("=" * 60)
    print("环境变量配置检查")
    print("=" * 60)
    
    all_good = True
    
    # 1. 检查 LLM 配置
    print("\n📌 LLM 配置")
    print("-" * 60)
    
    has_openai = check_api_key("OPENAI_API_KEY")
    has_azure_key = check_api_key("AZURE_OPENAI_API_KEY")
    
    # 如果配置了 Azure key，检查其他必需项
    has_azure_endpoint = False
    has_azure_version = False
    has_azure_deployment = False
    
    if has_azure_key:
        has_azure_endpoint = check_api_key("AZURE_OPENAI_ENDPOINT")
        has_azure_deployment = check_api_key("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    # Azure 配置完整性检查（不需要 API_VERSION）
    has_azure = has_azure_key and has_azure_endpoint and has_azure_deployment
    
    if not has_openai and not has_azure:
        print("\n  ❌ 错误：至少需要配置 OpenAI 或 Azure OpenAI！")
        print("\n  请在 .env 文件中配置：")
        print("    - OPENAI_API_KEY=sk-... (OpenAI)")
        print("  或")
        print("    - AZURE_OPENAI_API_KEY=...")
        print("    - AZURE_OPENAI_ENDPOINT=https://...")
        print("    - AZURE_OPENAI_DEPLOYMENT_NAME=...")
        all_good = False
    else:
        if has_openai and has_azure:
            print("\n  ✓ 检测到 OpenAI 和 Azure 配置")
            print("  → 系统将优先使用 Azure OpenAI")
        elif has_openai:
            print("\n  ✓ 将使用 OpenAI")
        elif has_azure:
            print("\n  ✓ 将使用 Azure OpenAI")
    
    # 2. 检查搜索工具配置
    print("\n📌 搜索工具配置")
    print("-" * 60)
    
    has_tavily = check_api_key("TAVILY_API_KEY", required=True)
    if not has_tavily:
        print("\n  ❌ 错误：TAVILY_API_KEY 是必需的！")
        print("  请访问 https://tavily.com/ 获取 API key")
        all_good = False
    
    check_api_key("BRAVE_API_KEY")
    check_api_key("FIRECRAWL_API_KEY")
    
    # 3. 检查可选配置
    print("\n📌 可选配置")
    print("-" * 60)
    
    fs_base = os.getenv("NEWS_AGENT_FS_BASE", "./data")
    print(f"  ℹ️  文件系统路径: {fs_base}")
    
    # 4. 总结
    print("\n" + "=" * 60)
    if all_good:
        print("✅ 配置检查通过！可以开始使用。")
        print("\n下一步：")
        print("  1. 运行测试：uv run pytest tests/ -v")
        print("  2. 创建 agent：from src.agent import create_news_agent")
        return 0
    else:
        print("❌ 配置不完整，请修复上述问题。")
        print("\n帮助：")
        print("  1. 复制配置文件：cp env.example .env")
        print("  2. 编辑 .env 文件，填入你的 API keys")
        print("  3. 查看详细文档：cat ENV_SETUP.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())

