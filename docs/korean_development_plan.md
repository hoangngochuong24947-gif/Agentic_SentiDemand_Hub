# 韩语评论分析开发方案

## 模块拆分

- `settings.py`：新增 `data.language` 与 `segmentation.backend`，让韩语能力按配置启用。
- `segmenter.py`：保留 `jieba` 中文链路，新增 `KoreanSegmenter` 和 `MultilingualSegmenter`。
- `labeler.py`：新增轻量韩语词典情感法，中文默认仍走 `SnowNLP`。
- `config/`：补充韩语停用词、情感词典、需求关键词和演示配置。
- `scripts/`：生成模拟数据、验证 `Okt` 分词和完整 pipeline。
- `docs/`：沉淀开源复用分析、Git 方案、hooks 方案和学习记录。

## 实施顺序

1. 先用模拟韩语评论验证分词和情感标注。
2. 再将韩语能力挂到现有 pipeline，不改变中文默认行为。
3. 补需求词和停用词，让主题/需求分析至少具备可运行原型。
4. 最后用 hooks 和日志体系把迭代流程固化。

## 风险与降级

- 若 `KoNLPy` 不可用，自动退回 regex 分词，保证流程不中断。
- 若 `Mecab` 环境不可用，优先使用 `Okt`。
- 韩语情感当前为词典原型，后续可替换成标注数据训练模型。
