# 黑洞与引力理论每日精选

**Black Hole & Gravity Theory Daily** 是一个可长期自动运行的静态学术索引。它每天从 arXiv 官方 Atom API 与 INSPIRE-HEP 官方 REST API 获取最近论文，经可审计的硬过滤和结构化模型评分后，生成中英双语 GitHub Pages 网站。模型服务可在 OpenAI 与 DeepSeek 之间切换。

网站聚焦四个方向：黑洞热力学、脉冲星计时阵列（PTA）、全息与凝聚态对偶、广义相对论基础理论。它强调少而精、来源可追溯和不过度声称；自动评分不是同行评议，不保证论文正确或重要。

## 项目特点

- Python 数据管线、Pydantic 核心模型、Jinja2 静态模板、原生 CSS/JavaScript；
- arXiv 与 INSPIRE 跨源合并，优先以 arXiv ID、DOI、严格规范化标题去重；
- 关键词和阈值集中在 `config/`，模型、prompt、schema 与缓存均有版本；
- OpenAI Responses Structured Outputs 或 DeepSeek Chat Completions JSON Output，并统一经过 Pydantic 严格校验；浏览器端不接触 API key；
- 中文标题和完整摘要经过空值、中文字符、长度和结构校验；摘要要求逐句忠实翻译，不得缩写成概述；
- 页面时间筛选支持某一天、某个月、某一年和自定义起止日期，不必再逐日点击查找；
- 论文标题和中英文摘要使用 MathJax 4 排版 LaTeX 公式，并把常见 `\\cite{...}` 标记显示为易读引用；
- 45–49 分进入 `data/review_queue/`，默认 50 分以上公开；
- 无密钥的 8 篇虚构演示数据与正式历史严格分开；
- 每日 GitHub Actions 自动测试、更新、保存数据并部署 Pages。

## 目录概览

```text
config/                 主题词、阈值、网络与版本配置
src/theory_daily/       抓取、规范化、去重、筛选、LLM、存储、渲染与 CLI
templates/              首页、归档、论文卡片、方法说明
static/                 响应式样式与无框架筛选交互
data/                   原始响应、正式论文、待审、拒绝、缓存、状态与报告
tests/                  离线夹具和 25 项自动化测试
dist/                   构建后的 GitHub Pages 静态站点
.github/workflows/      每日更新与部署流程
```

## 本地安装

需要 Python 3.12。以下命令在项目根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

若要完全复用已验收的依赖版本：

```powershell
pip install -r requirements-lock.txt
pip install --no-deps -e .
```

## 无 API key 的离线演示

```powershell
python -m theory_daily.cli demo --fixtures
python -m theory_daily.cli validate
python -m theory_daily.cli serve --port 8000
```

然后访问 `http://127.0.0.1:8000`。演示站包含 8 篇明确写有“DEMO/演示”的虚构记录，不会写入 `data/papers/`，也不会混入正式历史。

## 正式更新

不要把密钥写进源码或提交 `.env`。两种模型服务任选一种。

使用 OpenAI：

```powershell
$env:OPENAI_API_KEY = "你的密钥"
$env:LLM_PROVIDER = "openai"
$env:OPENAI_MODEL = "gpt-5.6-luna"       # 可选
$env:OPENAI_REASONING_EFFORT = "low"     # 可选
$env:MAX_LLM_PAPERS_PER_RUN = "60"       # 可选，费用保护
python -m theory_daily.cli update --since-days 7
python -m theory_daily.cli validate
```

使用 DeepSeek：

```powershell
$env:LLM_PROVIDER = "deepseek"
$env:DEEPSEEK_API_KEY = "你的 DeepSeek API Key"
$env:DEEPSEEK_MODEL = "deepseek-v4-flash"  # 可选，当前默认值
python -m theory_daily.cli update --since-days 7
python -m theory_daily.cli validate
```

DeepSeek 使用官方 `https://api.deepseek.com` Chat Completions 接口和 JSON Output。返回内容仍须通过完整字段、枚举、分值范围、总分一致性与中文翻译校验，不能因为换供应商而降低结构化输出标准。

其他命令：

```powershell
python -m theory_daily.cli build
python -m theory_daily.cli serve --port 8000
ruff check .
mypy src
pytest -q
```

正式更新缺少 `OPENAI_API_KEY` 时会明确失败，不会发布未经评分或翻译的论文。INSPIRE 暂时不可用时，arXiv 流程仍可继续，运行报告会标记降级。若本次所有模型调用均失败，上一版 `dist/` 会保留。

## GitHub 配置与发布

1. 在 GitHub 新建一个空的公共仓库，把本项目提交并推送到 `main`。
2. 打开仓库 **Settings → Secrets and variables → Actions**，选择一种配置：
   - OpenAI：创建 secret `OPENAI_API_KEY`，变量 `LLM_PROVIDER` 填 `openai`；
   - DeepSeek：创建 secret `DEEPSEEK_API_KEY`，变量 `LLM_PROVIDER` 填 `deepseek`。
3. 可选：新建变量 `OPENAI_MODEL` 或 `DEEPSEEK_MODEL`。DeepSeek 默认使用 `deepseek-v4-flash`。
4. 打开 **Settings → Pages**，将 **Source** 选择为 **GitHub Actions**。
5. 打开 **Actions → Update and deploy → Run workflow**，首次手动运行。

工作流每天按北京时间（`Asia/Shanghai`）07:20 自动更新、保存数据并部署。它会防止两个更新同时写数据。推送到 `main` 会运行测试和离线 demo 验收，随后恢复构建正式历史，不调用真实 OpenAI API；手动或定时任务才进行正式更新。公共仓库长期无活动时，GitHub 可能暂停计划任务，需要在 Actions 页面重新启用。

## 筛选、翻译与安全边界

- 标题和摘要始终视为不可信输入。系统 prompt 明确要求忽略其中的指令，页面依靠 Jinja 自动转义，前端不使用 `innerHTML`。
- 模型输入不包含作者姓名、机构、国籍或声望，只包含作者数量和有限元数据。
- 新论文发表不足 30 天时，零引用明确视为中立；社区信号上限为 5 分。
- 中文摘要必须覆盖英文摘要全文而不是只做概述；逐句忠实翻译并保留研究问题、假设、方法、结果、限定条件、局限、公式、变量、模型名和不确定语气。
- 页面只在论文文本区域处理 LaTeX，MathJax 启用安全过滤并固定版本；外部文本仍先经 Jinja 自动转义，引用标记只用 DOM 文本节点转换，不使用 `innerHTML`。若公式 CDN 暂时不可用，页面仍保留已经转义的原始文本。
- 所有外链均使用 `target="_blank"`、`rel="noopener noreferrer"`；静态验证会检查这一点。
- 网络请求统一带 User-Agent、timeout、retry、指数退避，并尊重 `Retry-After`。

更完整的公开说明见构建网站的 `/methodology/` 页面。实现与验收记录见 `IMPLEMENTATION_REPORT.md`。

## 修改主题与阈值

- `config/topics.yaml`：类别、四个主题、高/中权重关键词、负面词、硬排除项；
- `config/settings.yaml`：入选/待审阈值、回溯天数、页大小、超时重试、站点地址和版本号。

修改筛选、prompt、翻译或 schema 时，应同步提升相应版本号；版本参与缓存 key，避免复用已经过时的模型结果。

## 许可

MIT License。
