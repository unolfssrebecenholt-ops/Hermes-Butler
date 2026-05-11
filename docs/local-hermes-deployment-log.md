# Hermes 本地部署与改动日志

这份文档用于记录这台机器上的 Hermes 本地部署状态，以及后续所有本地变更。

适用范围：
- 增加或移除 `MCP`
- 安装或调整 `Skills`
- 修改 Hermes 原生源码
- 修改 `~/.hermes/.env`、`~/.hermes/config.yaml` 等配置
- 调整网关、服务、消息平台接入方式

约定：
- 只记录“做了什么、改了哪里、为什么这样改、如何复现”
- 不记录任何真实密钥、令牌、Cookie 明文
- 凡是涉及密钥，只记录变量名、配置位置和用途
- 以后每次再做本地变更，都继续追加到这份文档

## 0. 文档建立记录

### 2026-04-18：建立统一本地变更日志

目标：
- 把这台机器上与 Hermes 相关的所有本地改动集中记录到一个文档里
- 方便后续排查、迁移和二次部署

执行规则：
- 后续凡是新增 `MCP`、安装/修改 `Skills`、修改 Hermes 原生源码、调整 `~/.hermes/.env`、`~/.hermes/config.yaml`、消息平台配置或服务托管方式，都继续追加到本文件
- 涉及密钥时，只记录变量名、用途、文件位置，不记录真实明文

## 1. 机器上的关键路径

- Hermes 源码目录：`/Users/zhanglongsheng/Documents/hermes-agent`
- Hermes Home：`/Users/zhanglongsheng/.hermes`
- Hermes 环境变量文件：`/Users/zhanglongsheng/.hermes/.env`
- Hermes 主配置文件：`/Users/zhanglongsheng/.hermes/config.yaml`
- Feishu 网关 launchd 服务：`/Users/zhanglongsheng/Library/LaunchAgents/ai.hermes.gateway.plist`
- 本地技能目录：`/Users/zhanglongsheng/.hermes/skills`

## 2. 当前本地运行摘要

### 2.1 模型与 Provider

- 主模型已切换为 `MiniMax-M2.7`
- Provider 已切换为 `minimax-cn`
- Base URL 使用 `https://api.minimaxi.com/anthropic`
- 密钥存放位置：`~/.hermes/.env`
- 相关变量名：
  - `MINIMAX_CN_API_KEY`

### 2.2 搜索能力

- 已启用 Tavily + Firecrawl 方案
- 密钥存放位置：`~/.hermes/.env`
- 相关变量名：
  - `TAVILY_API_KEY`
  - `FIRECRAWL_API_KEY`

### 2.3 本地 Skills

- 已安装本地 skill：`xhs-apis`
- 安装来源：`XhsSkills` 仓库中的 `skills/xhs-apis`
- 最终落地路径：`/Users/zhanglongsheng/.hermes/skills/xhs-apis`
- 说明：
  - 这是 `local skill`
  - 当前不是 Hermes Hub 托管安装
  - 后续更新需要手动维护，不走 Hub 自动更新链路

### 2.4 飞书网关

- 平台：`Feishu`
- 域：`feishu`
- 连接模式：`websocket`
- home channel 已设置为当前飞书聊天
- 当前策略：
  - `FEISHU_ALLOW_ALL_USERS=true`
  - `FEISHU_GROUP_POLICY=open`
  - `group_sessions_per_user: true`
- 说明：
  - 群里所有成员都可以使用机器人
  - 但每个人在群里的上下文是独立的

### 2.5 服务托管方式

- 网关运行方式：macOS `launchd` 用户级 `LaunchAgent`
- 当前服务标签：`ai.hermes.gateway`
- 启动方式：登录当前 macOS 用户后自动拉起
- 注意：
  - 锁屏通常不影响
  - 睡眠、注销、关机、重启未登录会导致机器人离线

## 3. 源码补丁记录

### 2026-04-18：补齐 Feishu Excel/文档附件发送链路

目标：
- 让 Hermes 在飞书聊天场景下，能把 `.xlsx` 等本地文档作为附件发出去

问题根因：
- Feishu 适配器本身支持 `send_document`
- 但 Hermes 上层的 `send_message` 路径会把 Feishu 附件省略
- 同时自动识别本地附件的规则默认不识别 `.xlsx` 等文档类型

本次修改文件：
- `tools/send_message_tool.py`
- `gateway/platforms/base.py`
- `tests/tools/test_send_message_tool.py`
- `tests/gateway/test_platform_base.py`
- `tests/gateway/test_extract_local_files.py`

具体修改：

1. `tools/send_message_tool.py`
- 在 `send_message` 的 `message` 字段说明中补充 `MEDIA:/absolute/path.ext` 用法
- 为 `Platform.FEISHU` 增加“带附件时走原生发送 helper”的分支
- 这样 Feishu 在 `send_message` 场景下不再丢弃文档附件
- 同时允许“只有附件、没有正文”的发送

2. `gateway/platforms/base.py`
- 扩展 `extract_media()` 可识别的附件扩展名
- 新增文档类型支持：
  - `.pdf`
  - `.doc`
  - `.docx`
  - `.xls`
  - `.xlsx`
  - `.ppt`
  - `.pptx`
  - `.csv`
  - `.tsv`
- 扩展 `extract_local_files()` 的本地文件自动识别范围，让模型只输出本地 `.xlsx` 路径时，也能被网关识别并作为文档发送

3. 测试补充
- 增加 `MEDIA:/tmp/report.xlsx` 提取测试
- 增加 `.xlsx/.pdf/.csv` 等本地文档路径识别测试
- 增加 Feishu `send_message` 场景下的文档附件发送测试

效果：
- Hermes 直接回复一个本地 `.xlsx` 路径时，网关现在可以把它当文档附件发往飞书
- Hermes 使用 `send_message` 工具并附带 `MEDIA:/absolute/path.xlsx` 时，Feishu 路径也不再丢附件

## 4. 配置变更记录

### 2026-05-11：OpenAI-compatible 中转站切换规范

目标：
- 让 Hermes 可以随时切换自定义 OpenAI-compatible 中转站
- 避免再次因为中转站风控规则误判为模型或密钥失效

当前推荐配置位置：
- `~/.hermes/config.yaml`
- `~/.hermes/.env`

推荐 `config.yaml` 结构：

```yaml
model:
  default: gpt-5.5
  provider: relay
  base_url: https://<relay-host>/v1

providers:
  relay:
    name: Relay
    base_url: https://<relay-host>/v1
    key_env: RELAY_API_KEY
    default_model: gpt-5.5
```

推荐 `.env` 结构：

```bash
RELAY_API_KEY=sk-...
```

注意：
- 不要把真实中转站 key 写入文档或提交到仓库
- `relay` 是用户自定义 provider 名称，运行时应解析为 `custom` OpenAI-compatible client
- 如果出现 `Unknown provider 'relay'`，说明某条路径没有正确处理自定义 provider
- 如果 `/v1/models` 成功，但聊天请求报 `HTTP 403: Your request was blocked`，优先检查中转站是否拦截 OpenAI Python SDK 默认 `User-Agent`
- 2026-05-11 已在源码中补丁：普通自定义 OpenAI-compatible 中转站统一使用 `User-Agent: HermesAgent/1.0`
- 保留特殊 provider 的专用 headers：OpenRouter、Kimi、Qwen Portal、Copilot、Gemini

切换中转站后的标准操作：
1. 修改 `~/.hermes/config.yaml` 的 `model.base_url` 和 `providers.<name>.base_url`
2. 修改 `~/.hermes/.env` 中对应 `key_env` 的密钥值
3. 确认模型名存在于中转站 `/v1/models`
4. 重启网关：
   `source venv/bin/activate && python -m hermes_cli.main gateway restart`
5. 发送一条极短消息测试，例如 `你好`

验证命令示例：

```bash
source venv/bin/activate
python - <<'PY'
from hermes_cli.env_loader import load_hermes_dotenv
load_hermes_dotenv()
from hermes_cli.runtime_provider import resolve_runtime_provider
rt = resolve_runtime_provider()
print(rt["provider"], rt["base_url"], rt["api_mode"], rt.get("requested_provider"))
print("api_key:", "***redacted***" if rt.get("api_key") else "<empty>")
PY
```

### 2026-04-18：MiniMax China 配置

修改位置：
- `~/.hermes/.env`
- `~/.hermes/config.yaml`

结果：
- 主模型改为 `MiniMax-M2.7`
- Provider 改为 `minimax-cn`
- Base URL 改为 `https://api.minimaxi.com/anthropic`

### 2026-04-18：搜索 API 配置

修改位置：
- `~/.hermes/.env`

结果：
- 写入搜索相关密钥变量：
  - `TAVILY_API_KEY`
  - `FIRECRAWL_API_KEY`

### 2026-04-18：飞书 home channel 修正

问题：
- 最初误把 `FEISHU_HOME_CHANNEL` 写成了飞书应用 `App ID`

修正结果：
- 改为真实飞书聊天 `chat_id`（`oc_...`）
- 同步到了：
  - `~/.hermes/.env`
  - `~/.hermes/config.yaml`

### 2026-04-18：飞书群聊开放策略

修改位置：
- `~/.hermes/.env`
- `~/.hermes/config.yaml`

结果：
- `FEISHU_ALLOW_ALL_USERS=true`
- `FEISHU_GROUP_POLICY=open`
- `group_sessions_per_user: true`

## 5. Skills 变更记录

### 2026-04-18：安装 XhsSkills / xhs-apis

变更内容：
- 安装本地 skill：`xhs-apis`
- 技能目录落地到：`/Users/zhanglongsheng/.hermes/skills/xhs-apis`
- Python 依赖已安装到 Hermes venv
- Node 依赖已安装到 skill 自己的 `scripts` 目录

备注：
- 这是本地技能安装，不是 Hub 安装
- 迁移到新机器时，需要重新：
  - 复制技能目录
  - 安装 Python 依赖
  - 安装 Node 依赖

## 6. MCP 变更记录

截至 2026-04-18：
- 暂无额外 MCP 服务安装记录

后续如果新增 MCP，请按下面模板追加：

```md
### YYYY-MM-DD：安装/调整 <MCP 名称>

- 安装位置：
- 配置文件：
- 启动方式：
- 依赖：
- 验证方法：
- 备注：
```

## 7. 迁移到新机器时的建议顺序

1. 克隆 Hermes 源码到新机器
2. 安装 Hermes 依赖与 Python 虚拟环境
3. 恢复 `~/.hermes/config.yaml`
4. 恢复 `~/.hermes/.env` 中的变量名对应值
5. 恢复本地 skills 目录
6. 重新安装本地 skill 的 Python / Node 依赖
7. 检查飞书应用配置与权限
8. 安装并启动 `launchd` / 服务托管
9. 做一次：
   - 模型对话测试

## 8. 运维操作记录

### 2026-04-18：重启 Hermes Gateway 以加载源码补丁

目的：
- 让本次 Feishu 文档附件发送补丁生效

执行命令：
- 在仓库根目录执行：`./venv/bin/hermes gateway restart`

验证结果：
- CLI 返回：`Service restarted`
- `launchctl` 状态：`gui/501/ai.hermes.gateway`
- 当前状态：`running`
   - Web 搜索测试
   - Feishu 对话测试
   - 附件发送测试

## 8. 后续更新规则

从这次开始，后续凡是你让我执行下面这些操作，我都继续更新这份文档：

- 新增或删除 `MCP`
- 安装或调整 `Skills`
- 修改 Hermes 原生源码
- 修改平台配置、模型配置、搜索配置
- 修改服务托管方式
- 增加新的部署依赖或启动脚本
