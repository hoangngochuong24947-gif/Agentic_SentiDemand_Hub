# 四个开源项目分析报告

## 1. PyKoSpacing

- 仓库位置：`external/PyKoSpacing`
- 核心模块：`pykospacing/kospacing.py`
- 关键能力：基于深度学习模型恢复韩语空格，对 SNS / 短评这类不规范文本很有价值。
- 可复用结论：适合作为“韩语清洗前置器”，先纠正空格，再交给 `Okt` 或 `Mecab` 分词。
- 协议风险：GPL v3，不建议直接混入当前 MIT 项目源码，宜保持“可选外部工具”方式接入。

## 2. KoNLPy

- 仓库位置：`external/konlpy`
- 核心模块：`konlpy/tag/_okt.py`、`konlpy/tag/_mecab.py`
- 关键能力：提供 `Okt`、`Mecab`、`Komoran` 等韩语形态分析器，并统一成 Python 接口。
- 可复用结论：最适合当前项目的直接接入点，用于韩语评论分词和名词抽取。
- 工程提醒：`Okt` 需要 JVM，`Mecab` 还依赖字典安装，因此必须准备回退策略。

## 3. ECommerceCrawlers

- 仓库位置：`external/ECommerceCrawlers`
- 重点目录：`TaobaoCrawler/`
- 关键能力：登录态维护、Cookie 获取、队列式抓取、mitmproxy 注入与异常重试。
- 可复用结论：适合学习“状态管理”和“反爬下的容错模式”，不适合直接复制进当前系统。
- 合规提醒：其中部分实现以绕过检测为目标，只能做研究样本，生产抓取需重新评估站点条款与法律边界。

## 4. Crawlee

- 仓库位置：`external/crawlee-ref`
- 核心结构：`packages/core`、`packages/http-crawler`、`packages/playwright-crawler`
- 关键能力：请求队列、会话池、代理、浏览器自动化、hooks、可观测性。
- 可复用结论：最值得复用的是“架构”，未来做 Naver/Gmarket/11st 抓取时可参考其任务路由和重试机制。
- 接入建议：若后续要补爬虫，建议把 Crawlee 风格的抓取层做成独立子模块或外部服务。

## 对当前项目的具体启发

- 韩语 NLP：优先 `KoNLPy(Okt)`，可选叠加 `PyKoSpacing`。
- 爬虫层：不在当前回合硬接入真实站点，先用模拟数据完成韩语分析原型。
- 工程层：借鉴 Crawlee 的 hook、日志与任务分层思路，把迭代流程自动化。
