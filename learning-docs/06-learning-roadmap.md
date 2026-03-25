# 学习路线（从快到深）

## 阶段 A：建立全局认知（1-2 小时）

1. `README.md`  
   难度：⭐  
   目标：理解项目能力边界、安装方式、最小调用方式。

2. `pyproject.toml`  
   难度：⭐  
   目标：掌握依赖分层（base/dev/viz）与测试配置。

3. `config/default.yaml` + `config/demand_keywords.json`  
   难度：⭐  
   目标：知道哪些参数可调、需求类目如何定义。

---

## 阶段 B：跑通主链路（2-4 小时）

1. `examples/basic_usage.py`  
   难度：⭐  
   目标：快速复现“加载 → 分析 → 输出摘要”。

2. `src/comment_analyzer/core/pipeline.py`  
   难度：⭐⭐⭐  
   目标：吃透 `run` 四阶段流程与 `PipelineResults`。

3. `src/comment_analyzer/core/settings.py`  
   难度：⭐⭐  
   目标：理解配置对象如何注入全流程。

---

## 阶段 C：逐模块深入（4-8 小时）

1. 预处理：`cleaner.py` / `segmenter.py` / `filter.py`  
   难度：⭐⭐  
   前置：中文分词基础  
   学习重点：文本标准化与 token 质量控制。

2. 情感：`labeler.py` / `vectorizer.py` / `classifier.py`  
   难度：⭐⭐⭐  
   前置：sklearn 基础  
   学习重点：标签策略、特征化、模型训练与评估。

3. 主题：`keywords.py` / `lda.py`  
   难度：⭐⭐⭐  
   前置：TF-IDF、LDA 基础  
   学习重点：主题词解释、coherence 使用方式。

4. 需求：`intensity.py` / `correlation.py`  
   难度：⭐⭐⭐  
   前置：统计相关性基础  
   学习重点：关键词映射、相关性矩阵构建。

---

## 阶段 D：工程化能力（3-6 小时）

1. `core/output_manager.py`  
   难度：⭐⭐  
   重点：防覆盖输出与实验追踪。

2. `core/log_manager.py`  
   难度：⭐⭐  
   重点：结构化日志与可导出审计。

3. `visualization/generator.py` + `visualization/gallery.py`  
   难度：⭐⭐⭐  
   重点：图表注册机制、manifest、上传即分析服务。

---

## 阶段 E：质量保障与改造（2-4 小时）

1. `tests/test_integration.py`  
   难度：⭐⭐  
   重点：端到端断言点、配置兼容性、输出序号逻辑。

2. 定向改造建议  
   难度：⭐⭐⭐  
   重点：
   - 修复乱码与编码统一
   - 定义 demand 输出 schema
   - 并行化耗时阶段

---

## 推荐阅读顺序（最优）

1. `README.md`
2. `pyproject.toml`
3. `config/default.yaml`
4. `examples/basic_usage.py`
5. `core/settings.py`
6. `core/pipeline.py`
7. `preprocessing/*`
8. `sentiment/*`
9. `topic/*`
10. `demand/*`
11. `core/output_manager.py`
12. `core/log_manager.py`
13. `visualization/generator.py`
14. `visualization/gallery.py`
15. `tests/test_integration.py`

