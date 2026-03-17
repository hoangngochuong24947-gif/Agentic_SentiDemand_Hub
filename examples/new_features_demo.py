"""
演示新功能的示例脚本

展示如何使用：
1. Pydantic 配置系统 (Settings)
2. 输出管理器 (OutputManager) - 自动递增序号
3. 日志管理器 (LogManager) - 结构化日志
4. 分类输出文件夹
"""

import pandas as pd
from comment_analyzer import CommentPipeline, Settings
from comment_analyzer.core.log_manager import init_logging
from comment_analyzer.core.output_manager import OutputManager


def demo_settings():
    """演示新的 Pydantic 配置系统."""
    print("=" * 60)
    print("Demo 1: Pydantic Settings")
    print("=" * 60)

    # 创建默认设置
    settings = Settings()
    print(f"App Name: {settings.app_name}")
    print(f"App Version: {settings.app_version}")
    print(f"Output Base: {settings.paths.output_base}")

    # 修改配置
    settings.paths.output_base = "./my_outputs"
    settings.topic.lda.num_topics = 8
    settings.output.sequence_padding = 4  # 0001, 0002...

    print(f"\nModified Output Base: {settings.paths.output_base}")
    print(f"Number of Topics: {settings.topic.lda.num_topics}")

    # 保存设置到 YAML
    settings.to_yaml_file("./my_config.yaml")
    print("\nSettings saved to: ./my_config.yaml")


def demo_output_manager():
    """演示输出管理器 - 自动递增序号."""
    print("\n" + "=" * 60)
    print("Demo 2: Output Manager with Auto Sequence Numbering")
    print("=" * 60)

    # 创建设置
    settings = Settings()
    settings.paths.output_base = "./demo_outputs"

    # 创建输出管理器
    manager = OutputManager(settings)

    # 创建示例数据
    df = pd.DataFrame({
        "product": ["A", "B", "C"],
        "sentiment_score": [0.8, 0.3, 0.9]
    })

    # 保存到不同分类文件夹
    info1 = manager.save_dataframe(df, "analysis.csv", category="demand")
    print(f"Saved: {info1.final_path}")

    info2 = manager.save_dataframe(df, "analysis.csv", category="demand")
    print(f"Saved: {info2.final_path}")

    info3 = manager.save_dataframe(df, "analysis.csv", category="sentiment")
    print(f"Saved: {info3.final_path}")

    # 生成摘要
    print("\n" + manager.generate_summary())


def demo_logging():
    """演示日志管理器."""
    print("\n" + "=" * 60)
    print("Demo 3: Structured Logging")
    print("=" * 60)

    # 创建设置并初始化日志
    settings = Settings()
    settings.paths.output_base = "./demo_outputs"
    settings.logging.log_to_console = True
    settings.logging.log_to_file = True
    settings.logging.level = "INFO"

    log_manager = init_logging(settings)

    # 记录分析结果
    log_manager.log_analysis("sentiment", {
        "positive": 150,
        "negative": 50,
        "neutral": 30
    })

    # 记录重要信息
    log_manager.log_important(
        "Model training completed successfully",
        category="ml",
        data={"accuracy": 0.95, "f1_score": 0.94}
    )

    # 记录模型结果
    log_manager.log_model_result(
        "svm",
        metrics={"accuracy": 0.95, "precision": 0.93, "recall": 0.92},
        params={"C": 1.0, "kernel": "linear"}
    )

    # 导出日志条目
    log_path = log_manager.export_log_entries()
    print(f"\nLog entries exported to: {log_path}")


def demo_pipeline():
    """演示完整的 Pipeline 使用新功能."""
    print("\n" + "=" * 60)
    print("Demo 4: Complete Pipeline with New Features")
    print("=" * 60)

    # 准备测试数据
    data = pd.DataFrame({
        "id": range(1, 11),
        "content": [
            "这个产品非常好用，推荐购买！",
            "质量一般，不太满意",
            "物流很快，包装很好",
            "客服态度很差，体验不好",
            "性价比高，会再次购买",
            "产品有问题，需要退换",
            "使用效果很棒，好评",
            "送货太慢，等了很久",
            "质量很好，超出预期",
            "功能齐全，操作简单",
        ]
    })

    # 配置设置
    from pathlib import Path
    settings = Settings()
    settings.paths.output_base = Path("./demo_outputs").resolve()
    settings.paths.config_dir = Path("../config").resolve()
    settings.topic.lda.num_topics = 3
    settings.logging.log_to_console = True
    settings.logging.level = "INFO"

    # 初始化日志
    init_logging(settings)

    # 创建并运行 Pipeline
    pipeline = CommentPipeline(settings=settings)
    results = pipeline.run(data, verbose=False)

    # 保存结果（自动分类到不同文件夹）
    results.save()

    # 打印摘要
    print("\n" + results.summary())
    print("\n" + results.generate_output_summary())


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Comment Analyzer - New Features Demo")
    print("=" * 60)

    demo_settings()
    demo_output_manager()
    demo_logging()
    demo_pipeline()

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("Check the ./demo_outputs folder for generated files.")
    print("=" * 60)
