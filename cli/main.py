#!/usr/bin/env python3
"""
热点资讯聚合 Agentic AI - 命令行接口

使用方式:
    python -m cli.main "今天科技圈有什么大事"
    python -m cli.main --domain finance "最新财经热点"
    python -m cli.main --output ./reports/today.md "AI 领域进展"
    python -m cli.main --verbose "分析特斯拉动态"
    python -m cli.main --trace "AI最新动态"  # 启用可视化追踪
    python -m cli.main --trace --trace-output ./trace.html "分析热点"  # 保存追踪报告
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.agent import create_news_agent
from src.config import load_settings
from src.utils.callbacks import get_default_callbacks
from src.utils.logger import logger, set_verbose
from src.utils.templates import format_markdown_report, format_simple_output
from src.utils.tracer import create_tracing_callback, AgentTracer, RichAgentCallback


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="热点资讯聚合 Agentic AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s "今天AI领域有什么重要进展"
  %(prog)s --domain technology "最新科技新闻"
  %(prog)s --output ./report.md "分析OpenAI最新动态"
  %(prog)s --verbose --domain finance "特斯拉股价分析"
        """,
    )
    
    parser.add_argument(
        "query",
        type=str,
        help="要分析的查询或主题",
    )
    
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="限定领域（如 technology, finance, science）",
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="输出报告到文件（Markdown 格式）",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="显示详细日志",
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="覆盖默认模型（如 gpt-4o, gpt-4o-mini）",
    )

    parser.add_argument(
        "--checkpoint",
        action="store_true",
        help="启用 LangGraph checkpoint（可跨多次运行续跑/复用 VFS state）",
    )

    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default=None,
        help="checkpoint 存储目录（默认：<NEWS_AGENT_FS_BASE>/checkpoints 或 ./data/checkpoints）",
    )

    parser.add_argument(
        "--thread-id",
        type=str,
        default=None,
        help="会话 thread_id（相同 thread_id 才能复用上一次运行的状态）",
    )
    
    # 可视化追踪选项
    parser.add_argument(
        "--trace",
        "-t",
        action="store_true",
        help="启用可视化追踪（实时显示执行过程）",
    )
    
    parser.add_argument(
        "--trace-output",
        type=str,
        default=None,
        help="追踪报告输出路径（支持 .html 或 .json 格式）",
    )
    
    parser.add_argument(
        "--trace-input",
        action="store_true",
        help="在追踪中显示工具输入详情",
    )
    
    parser.add_argument(
        "--trace-output-detail",
        action="store_true",
        help="在追踪中显示工具输出详情",
    )
    
    return parser.parse_args()


def run_agent(
    query: str,
    domain: Optional[str] = None,
    model_override: Optional[str] = None,
    verbose: bool = False,
    checkpoint: bool = False,
    checkpoint_dir: Optional[str] = None,
    thread_id: Optional[str] = None,
    trace: bool = False,
    trace_output: Optional[str] = None,
    trace_input: bool = False,
    trace_output_detail: bool = False,
) -> tuple[dict, Optional[AgentTracer]]:
    """
    运行 Agent 分析查询。
    
    Args:
        query: 用户查询
        domain: 可选的领域限定
        model_override: 可选的模型覆盖
        verbose: 是否显示详细执行日志
        checkpoint: 是否启用检查点
        checkpoint_dir: 检查点目录
        thread_id: 会话线程 ID
        trace: 是否启用可视化追踪
        trace_output: 追踪报告输出路径
        trace_input: 是否显示输入详情
        trace_output_detail: 是否显示输出详情
        
    Returns:
        (Agent 运行结果, 追踪器) 元组
    """
    tracer: Optional[AgentTracer] = None
    
    logger.info(f"正在加载配置...")
    config = load_settings()
    
    # 构建完整的查询（如果指定了领域）
    full_query = query
    if domain:
        full_query = f"[领域: {domain}] {query}"
        logger.info(f"限定领域: {domain}")
    
    logger.info(f"正在创建 Agent...")
    # TODO: 如果需要 model_override，这里需要创建 ChatModel 实例
    if checkpoint:
        from src.agent.master import create_news_agent_with_checkpointing
        import hashlib

        # 默认使用 NEWS_AGENT_FS_BASE（config.filesystem.base_path）来放 checkpoints
        resolved_checkpoint_dir = checkpoint_dir
        if not resolved_checkpoint_dir:
            resolved_checkpoint_dir = str(config.filesystem.resolved_base() / "checkpoints")

        # 如果用户未提供 thread_id，则基于查询生成一个稳定的 thread_id，便于重复执行同一主题续跑
        resolved_thread_id = thread_id
        if not resolved_thread_id:
            full_key = full_query.encode("utf-8")
            resolved_thread_id = "cli-" + hashlib.sha1(full_key).hexdigest()[:10]
            logger.info(f"未提供 --thread-id，自动生成: {resolved_thread_id}")

        agent = create_news_agent_with_checkpointing(
            checkpoint_dir=resolved_checkpoint_dir,
            thread_id=resolved_thread_id,
            config=config,
        )
    else:
        agent = create_news_agent(config=config)
    
    logger.info(f"开始分析查询: {query}")
    logger.info("=" * 60)
    
    # 获取回调处理器
    callbacks = []
    
    if trace:
        # 使用可视化追踪
        callback, tracer = create_tracing_callback(
            session_name=f"query-{query[:20]}",
            show_input=trace_input,
            show_output=trace_output_detail,
        )
        callbacks.append(callback)
        logger.info("📊 已启用可视化追踪")
    else:
        # 使用默认回调
        callbacks = get_default_callbacks(verbose=verbose)
    
    # 调用 Agent（带回调）
    logger.info("🚀 开始 Agent 执行流程...")
    invoke_config = {"callbacks": callbacks}
    if checkpoint:
        # LangGraph 的 checkpointer 依赖 configurable.thread_id 来区分/复用线程状态
        invoke_config["configurable"] = {"thread_id": resolved_thread_id}  # type: ignore[name-defined]

    result = agent.invoke(
        {"messages": [{"role": "user", "content": full_query}]},
        config=invoke_config,
    )
    
    logger.info("=" * 60)
    logger.info("✅ 分析完成!")
    
    # 如果启用追踪，打印摘要并保存报告
    if trace and tracer:
        # 打印执行摘要
        callback.print_summary()
        
        # 保存追踪报告
        if trace_output:
            trace_path = Path(trace_output)
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            
            if trace_path.suffix == ".json":
                tracer.export_json(str(trace_path))
                logger.success(f"追踪数据已保存到: {trace_path}")
            else:
                # 默认保存为 HTML
                if trace_path.suffix != ".html":
                    trace_path = trace_path.with_suffix(".html")
                tracer.export_html(str(trace_path))
                logger.success(f"追踪报告已保存到: {trace_path}")
    
    return result, tracer


def main():
    """主函数"""
    args = parse_args()
    
    # 设置日志级别
    set_verbose(args.verbose)
    
    try:
        # 运行 Agent
        start_time = datetime.now()
        result, tracer = run_agent(
            query=args.query,
            domain=args.domain,
            model_override=args.model,
            verbose=args.verbose,
            checkpoint=args.checkpoint,
            checkpoint_dir=args.checkpoint_dir,
            thread_id=args.thread_id,
            trace=args.trace,
            trace_output=args.trace_output,
            trace_input=args.trace_input,
            trace_output_detail=args.trace_output_detail,
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"总耗时: {duration:.2f} 秒")
        
        # 输出结果
        if args.output:
            # 输出到文件
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            report = format_markdown_report(
                query=args.query,
                result=result,
                generation_time=end_time,
            )
            
            output_path.write_text(report, encoding="utf-8")
            logger.success(f"报告已保存到: {output_path}")
            
            # 也在终端显示简要内容
            print("\n" + "=" * 60)
            print("报告预览:")
            print("=" * 60)
            print(format_simple_output(result))
            print("=" * 60)
            print(f"\n完整报告已保存到: {output_path}")
        else:
            # 只在终端显示
            print("\n" + "=" * 60)
            print("分析结果:")
            print("=" * 60)
            print(format_simple_output(result))
            print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n用户中断")
        return 130
    except Exception as e:
        logger.error(f"运行失败: {e}")
        if args.verbose:
            logger.exception("详细错误信息:")
        return 1


if __name__ == "__main__":
    sys.exit(main())

