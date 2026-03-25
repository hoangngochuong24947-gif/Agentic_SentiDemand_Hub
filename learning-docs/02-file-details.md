# 关键文件详解（按执行优先级）

## 1. `core/pipeline.py`（主编排器）

### 主要功能

- 对外提供 `CommentPipeline` 和 `PipelineResults`
- 统一串联 4 个阶段：
  1. 预处理
  2. 情感分析
  3. 主题建模
  4. 需求分析
- 统一保存结果、记录日志、调用可视化生成

### 关键类与函数

- `CommentPipeline.__init__`: 接受 `Settings` 或兼容 `Config`，初始化所有组件
- `_init_components`: 装配 cleaner/segmenter/vectorizer/lda/demand 分析器
- `load_data`: 支持 CSV/Excel/JSON 并按平台映射标准化列名
- `detect_text_column`: 自动识别文本列（关键词 + 回退策略）
- `run`: 执行主流程，最终返回 `PipelineResults`
- `PipelineResults.save`: 结果分类持久化
- `PipelineResults.visualize`: 一键图表生成

### 核心依赖

- `Settings`（配置）
- `LogManager`（日志）
- `OutputManager`（输出）
- 各领域模块（preprocessing/sentiment/topic/demand）

---

## 2. `core/settings.py`（类型化配置中心）

### 主要功能

- 用 Pydantic 定义完整配置模型，避免“魔法字典”
- 支持环境变量覆盖（`COMMENT_ANALYZER_PATHS__OUTPUT_BASE` 等）
- 提供路径工具方法（停用词路径、需求词路径）

### 关键配置模型

- `PathConfig`: 输出、可视化、上传、配置目录
- `DataConfig`: 平台与列识别关键词
- `PreprocessingConfig` / `SentimentConfig` / `TopicConfig` / `DemandConfig`
- `OutputConfig` / `LoggingConfig` / `VisualizationConfig`

### 设计价值

- 配置即契约：参数可发现、可校验、可追踪
- 与 legacy `Config` 并存，平滑迁移

---

## 3. `core/output_manager.py`（分类输出与序号管理）

### 主要功能

- 按类别目录保存结果：`demand_analysis`、`sentiment_models`、`word_frequency`、`derived_columns`
- 自动文件序号（如 `001_xxx.csv`）避免覆盖
- 保存 DataFrame / Text / JSON / Excel

### 关键点

- `_get_next_sequence_number` 扫描已有文件自动递增
- `SavedFileInfo` 记录输出元数据，便于汇总和追踪

---

## 4. `core/log_manager.py`（结构化日志）

### 主要功能

- 统一控制台 + 文件日志
- 支持日志轮转、保留、压缩
- 提供语义化日志接口：
  - `log_analysis`
  - `log_model_result`
  - `log_pipeline_start/end`
  - `export_log_entries`

---

## 5. 预处理模块（`preprocessing/`）

- `cleaner.py`: URL/邮箱/HTML/空白清洗，面向中文文本保留策略
- `segmenter.py`: `jieba` 分词，支持词典加载和词性抽取
- `filter.py`: 停用词过滤，支持默认词表 + 外部词表 + 增量扩展

输出到 pipeline 中间列：

- `cleaned_text`
- `segmented_text`
- `filtered_text`
- `processed_text`

---

## 6. 情感模块（`sentiment/`）

- `labeler.py`: SnowNLP 打分 + 阈值标签（positive/neutral/negative）
- `vectorizer.py`: TF-IDF 特征化
- `classifier.py`: NB/SVM/Logistic 三模型统一训练与评估（含 CV）

---

## 7. 主题模块（`topic/`）

- `keywords.py`: 语料级 TF-IDF 关键词提取
- `lda.py`: Gensim LDA 训练、主题词输出、coherence 计算

---

## 8. 需求模块（`demand/`）

- `intensity.py`: 需求强度计算（simple 或 tfidf_weighted，支持归一化）
- `correlation.py`: 需求类目相关性（cooccurrence 或 PMI）

---

## 9. 可视化模块（`visualization/`）

- `generator.py`: 注册 14 类图表生成器，输出独立 HTML，维护 `manifest.json`
- `charts/*.py`: 每类图独立函数，返回 ECharts option
- `gallery.py`: FastAPI 服务，支持图表浏览与文件上传触发全流程

---

## 10. 测试与示例

- `tests/test_integration.py`: 端到端验证（执行、保存、序号递增、日志导出、配置兼容）
- `examples/basic_usage.py`: 最小可运行流程
- `examples/new_features_demo.py`: 新配置/日志/输出能力演示

