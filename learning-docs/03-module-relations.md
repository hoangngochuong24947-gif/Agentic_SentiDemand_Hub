# 模块关联与执行流程

## 1. 总体调用关系

```mermaid
graph TD
    A["CommentPipeline.run"] --> B["Preprocessing"]
    A --> C["Sentiment Analysis"]
    A --> D["Topic Modeling"]
    A --> E["Demand Analysis"]
    A --> F["PipelineResults"]
    F --> G["OutputManager.save*"]
    F --> H["VisualizationGenerator.generate_all"]
    A --> I["LogManager"]
    A --> J["Settings"]
```

---

## 2. 预处理阶段

```mermaid
graph LR
    T["raw text column"] --> C1["TextCleaner.clean"]
    C1 --> C2["JiebaSegmenter.segment"]
    C2 --> C3["StopwordFilter.filter"]
    C3 --> C4["processed_text(join)"]
```

产物列：

- `cleaned_text`
- `segmented_text`
- `filtered_text`
- `processed_text`

---

## 3. 情感阶段

```mermaid
graph LR
    P["processed_data"] --> L["SentimentLabeler.label_batch"]
    L --> V["TFIDFVectorizer.fit_transform"]
    V --> M["Classifier.train (NB/SVM/LR)"]
    L --> SD["sentiment_distribution"]
    M --> SM["sentiment_models"]
```

---

## 4. 主题阶段

```mermaid
graph LR
    P["processed_text / filtered_text"] --> K["KeywordExtractor.extract"]
    P --> LDA["LDAModel.fit_transform"]
    K --> TK["top_keywords"]
    LDA --> TP["topics"]
```

---

## 5. 需求阶段

```mermaid
graph LR
    F["filtered_text tokens"] --> I["DemandIntensityCalculator.calculate"]
    F --> R["DemandCorrelationAnalyzer.analyze"]
    I --> DI["demand_intensity"]
    R --> DC["demand_correlation"]
```

---

## 6. 可视化链路

```mermaid
graph TD
    R["PipelineResults"] --> VG["VisualizationGenerator"]
    VG --> C1["charts/sentiment.py"]
    VG --> C2["charts/features.py"]
    VG --> C3["charts/topics.py"]
    VG --> C4["charts/demand.py"]
    VG --> HTML["standalone HTML files"]
    VG --> M["manifest.json"]
    M --> G["Gallery API / UI"]
```

---

## 7. 数据流与控制流要点

- 控制流是串行的（Preprocessing → Sentiment → Topic → Demand），便于调试和结果可解释。
- 数据流集中在 `DataFrame` 增量列上，减少模块间对象转换成本。
- `PipelineResults` 是统一输出协议，隔离“分析阶段”和“持久化/可视化阶段”。
- 配置与日志是横切关注点：`Settings` 和 `LogManager` 覆盖所有阶段。

