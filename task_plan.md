# Task Plan: 集成 Loguru、Pydantic 并重构配置系统

## Goal
为 comment-analyzer 项目添加 loguru 和 pydantic 技术栈，重构配置系统使其解耦，设计递增序号的输出文件夹结构，并添加日志存储功能。

## Phases

### Phase 1: 添加依赖并创建基础结构
- [ ] 更新 pyproject.toml 添加 loguru 和 pydantic 依赖
- [ ] 创建 settings 模块用于 Pydantic 配置
- [ ] 创建输出管理器 (OutputManager) 处理递增序号文件夹
- [ ] 创建日志管理器 (LogManager) 处理日志存储

### Phase 2: 重构配置系统
- [ ] 使用 Pydantic 创建强类型的配置模型
- [ ] 分离文件路径配置（可独立调整）
- [ ] 创建文件夹结构配置类
- [ ] 重构原有的 Config 类使用新的 Pydantic 模型

### Phase 3: 修改 Pipeline 和 Results
- [ ] 修改 PipelineResults 使用新的输出管理器
- [ ] 添加重要字符串的日志记录功能
- [ ] 确保表格输出保存到独立文件夹且递增序号
- [ ] 更新 CommentPipeline 集成日志系统

### Phase 4: 创建输出分类文件夹
- [ ] 需求分析输出文件夹 (demand_analysis/)
- [ ] 三模型分析输出文件夹 (sentiment_models/)
- [ ] 词频统计输出文件夹 (word_frequency/)
- [ ] 派生列输出文件夹 (derived_columns/)
- [ ] 日志文件夹 (logs/)

### Phase 5: 编写测试
- [x] 测试配置系统（Pydantic 验证）
- [x] 测试输出管理器（递增序号功能）
- [x] 测试日志管理器
- [x] 集成测试整个流程

## Status: ✅ COMPLETE

### 完成的功能
1. **Pydantic 配置系统** (`src/comment_analyzer/core/settings.py`)
   - 类型安全的配置模型
   - 支持环境变量 (COMMENT_ANALYZER_*)
   - 支持 .env 文件
   - 向后兼容旧版 Config

2. **输出管理器** (`src/comment_analyzer/core/output_manager.py`)
   - 自动递增序号 (001_, 002_, ...)
   - 分类文件夹: demand_analysis/, sentiment_models/, word_frequency/, derived_columns/, logs/
   - 不覆盖原有文件

3. **日志管理器** (`src/comment_analyzer/core/log_manager.py`)
   - Loguru 结构化日志
   - 重要字符串记录
   - 日志导出为 JSON

4. **重构的 Pipeline** (`src/comment_analyzer/core/pipeline.py`)
   - 集成新配置系统
   - 集成日志系统
   - 支持 Settings 对象

### 测试覆盖
- `test_settings.py`: 25 个测试
- `test_output_manager.py`: 22 个测试
- `test_log_manager.py`: 17 个测试
- `test_integration.py`: 12 个测试
- **总计: 76 个测试 (75 passed, 1 skipped)**

## Key Decisions

1. **使用 Pydantic BaseSettings**: 支持环境变量和 .env 文件
2. **文件夹结构**:
   ```
   outputs/
   ├── demand_analysis/
   │   ├── 001_demand_analysis.csv
   │   ├── 002_demand_analysis.csv
   │   └── ...
   ├── sentiment_models/
   ├── word_frequency/
   ├── derived_columns/
   └── logs/
       └── app_2024-01-15.log
   ```
3. **递增序号策略**: 每次保存时自动查找下一个可用序号，不覆盖

## Files to Create
- `src/comment_analyzer/core/settings.py` - Pydantic 配置
- `src/comment_analyzer/core/output_manager.py` - 输出管理
- `src/comment_analyzer/core/log_manager.py` - 日志管理
- `src/comment_analyzer/utils/` - 工具函数
- `tests/test_settings.py` - 配置测试
- `tests/test_output_manager.py` - 输出管理测试
- `tests/test_log_manager.py` - 日志管理测试

## Files to Modify
- `pyproject.toml` - 添加依赖
- `src/comment_analyzer/core/config.py` - 重构使用 Pydantic
- `src/comment_analyzer/core/pipeline.py` - 集成新系统
- `src/comment_analyzer/__init__.py` - 导出新的配置类
