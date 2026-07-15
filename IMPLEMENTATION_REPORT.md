# 实施报告

## 完成范围

项目按任务书实现为“Python 数据管线 + Jinja2 静态页面 + 原生 CSS/JavaScript + GitHub Actions + GitHub Pages”。代码不需要数据库服务器、前端框架、Docker 或浏览器端 API 调用。

每日任务明确使用北京时间（`Asia/Shanghai`）07:20 调度；所有持久化时间仍为 UTC，页面按北京时间显示。

核心模块包括：

- `models.py`：版本化 Pydantic 模型；
- `fetch_arxiv.py` / `fetch_inspire.py`：官方 API、超时、重试、退避与原始响应保存；
- `normalize.py` / `deduplicate.py`：标识符规范化、稳定 key 和跨源保守合并；
- `deterministic_filter.py`：集中配置、可审计的第一阶段筛选；
- `llm_curation.py` / `translation.py`：OpenAI Responses Structured Outputs、DeepSeek Chat Completions JSON Output、提示注入边界、评分、翻译校验与跨供应商隔离缓存；
- `storage.py` / `pipeline.py`：原子 JSON、状态、队列、报告和失败安全构建；
- `render.py` / `health.py`：自动转义的静态网站、Atom、公开 JSON 与输出验证；
- `cli.py`：update、build、validate、demo、serve 五类命令。

## 关键权衡

1. 去重只合并相同 arXiv ID、DOI 或严格规范化后完全相同的标题，不做模糊标题匹配，优先避免误合并。
2. INSPIRE 失败被视为可见的数据源降级；arXiv 仍能继续。所有 LLM 调用失败则停止构建，保护上一版站点。
3. 社区信号上限 5 分，模型输入明确标记新论文零引用中立；作者姓名完全不进入模型输入。
4. demo 直接由离线工厂生成并写入 `data/demo/`，正式读取只扫描 `data/papers/`。
5. 页面主体依赖系统字体和少量原生 JavaScript，无大图或运行时后端；论文公式由固定版本的 MathJax 4 按需从 CDN 排版。
6. 模型服务由 `LLM_PROVIDER` 切换；DeepSeek 默认使用 `deepseek-v4-flash`，其 JSON Output 仍交由相同的 Pydantic schema 做二次严格验证。
7. 为提高召回率，滚动窗口扩为 7 天、公开阈值调整为 50 分、待审阈值调整为 45 分；硬筛选继续要求明确的主题语境，不采用作者声望等指标。
8. 主题匹配同时扫描标题和完整英文摘要，并统一连字符形式；PTA 等方向加入毫秒脉冲星、共同红噪声、空间/四极相关、计时噪声、星历误差等上下文词组。
9. 中文摘要改为全文忠实翻译而非摘要概述；翻译版本升级并增加中英文长度比例校验，使旧的过短缓存不会继续发布。
10. 首页时间筛选扩展为某一天、某个月、某一年和自定义日期范围，并保留一键重置。
11. 论文标题、中英文摘要和入选理由支持 LaTeX 数学排版；MathJax 只扫描明确标记的论文区域，并启用 `ui/safe` 过滤。常见引用命令通过安全 DOM 文本节点转换为易读标记，前端仍不使用 `innerHTML`。
12. INSPIRE 日期兼容 `YYYY-MM-DD`、`YYYY-MM`、`YYYY` 和完整时间戳；缺少普通作者时回退到合作组署名，作者与合作组都缺失的异常记录会逐条跳过，不再中断整次每日更新。

## 测试与运行结果

验收环境：Python 3.12.10，Windows x64。2026-07-13 实际运行：

```text
ruff check .       通过
mypy src           通过（18 个源码文件，无问题）
pytest -q          通过（25 passed）
demo --fixtures    通过（8 篇虚构示例）
validate           通过
```

自动化测试覆盖 arXiv 正常/缺字段、INSPIRE 正常/429、两源合并、相似标题防误合并、版本更新、撤稿与公告、holographic display、holographic superconductor、PTA 缩写歧义、新论文零引用中立、非法结构化输出、异常短翻译、HTML 转义、静态文件完整性、缺 key 报错、demo 和第二次运行缓存命中。

## 安全自审

- 仓库未写入 API key；`.env` 已忽略，只有空的 `.env.example`。
- 模型不接收作者姓名和机构；系统提示把论文文本界定为不可信数据。
- Jinja 开启自动转义；前端不使用 `innerHTML`；外链安全属性由构建测试检查。
- 所有持久化 JSON 写入 `schema_version`；模型、prompt、翻译、筛选配置均有版本。
- 正式运行没有 API key 时清楚失败；demo 完全离线。

## 剩余限制

- 首次正式运行需要用户在 GitHub 中配置 `OPENAI_API_KEY` 和 Pages，并手动触发一次工作流。
- 本地验收没有调用真实 arXiv、INSPIRE 或 OpenAI API；在线可用性和实际调用费用由正式工作流决定。
- `config/settings.yaml` 的 `site.base_url` 初始为示例地址，发布前应改为真实 GitHub Pages URL，以便 Atom feed 使用正确的站点绝对地址。
- GitHub 公共仓库长时间无活动时，计划任务可能被暂停，需要手动重新启用。
