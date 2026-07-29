# MasterGo MCP Skill

用于在 Codex、Claude Code 以及其他支持 MCP 的 Agent 客户端中连接并操作 MasterGo Vibe MCP 画布的 skill。

[GitHub 仓库](https://github.com/HicyWon/mastergo-mcp-skill) · [MasterGo MCP 官方文档](https://mastergo.com/help/MG/MCP/VIBE)

## 目录

- [功能概览](#功能概览)
- [触发条件](#触发条件)
- [安装与配置](#安装与配置)
- [使用方法](#使用方法)
- [连接模式](#连接模式)
- [常见故障处理](#常见故障处理)
- [项目结构](#项目结构)
- [许可](#许可)

## 功能概览

这个 skill 可以帮助 Codex、Claude Code 以及其他支持 MCP 的 Agent 客户端：

- 检查 MasterGo MCP 连接状态和版本
- 配置 Codex Desktop 的 MasterGo MCP
- 在 MasterGo 画布中生成页面和界面
- 读取当前选中的图层结构
- 修改图层文本、样式和局部结构
- 替换或删除图层
- 获取选中图层的前端代码
- 获取画布截图
- 读取和更新设计变量
- 查询组件信息和团队组件库
- 查看本地设计与画布之间的差异
- 将设计同步到画布

支持 MasterGo Vibe MCP，也支持私域 MasterGo 环境，例如 `mastergo.private.example.com`。

> 本 skill 默认针对 Vibe MCP，不负责 Magic MCP、DSL 或 D2C 场景。

## 触发条件

用户明确提到以下内容时会触发：

- MasterGo、`mgmcp`、MasterGo MCP、Vibe MCP
- 在 MasterGo 上画页面、设计界面或生成页面
- 修改 MasterGo 组件或画布内容
- 获取 MasterGo 图层代码

也可以显式指定：

```text
使用 $mastergo-mcp 检查连接，并读取当前选中图层。
```

仅说“设计一个页面”而没有提到 MasterGo 时，通常不会触发此 skill。

## 安装与配置

### 前置依赖

- Node.js 18 或更高版本
- `npx`
- 已打开的 MasterGo 客户端，或连接的 Chrome 中的 MasterGo 文件

如果尚未安装 Node.js，可以执行：

```bash
brew install node
```

### 自动配置

配置 Codex Desktop 和通用 MCP 客户端：

```bash
bash mastergo-mcp/scripts/setup-mastergo-mcp.sh --yes
```

只配置 Codex Desktop：

```bash
bash mastergo-mcp/scripts/setup-mastergo-mcp.sh --yes --codex-only
```

只配置通用 MCP JSON：

```bash
bash mastergo-mcp/scripts/setup-mastergo-mcp.sh --yes --json-only
```

默认连接地址为：

```text
http://localhost:50678
```

如果端口不同，可以指定：

```bash
bash mastergo-mcp/scripts/setup-mastergo-mcp.sh --yes --port 50678
```

脚本主要面向 Codex Desktop，同时提供通用 MCP JSON 配置。Claude Code 等其他支持 MCP 的客户端可以复用本 skill 的工作流，具体配置入口请以对应客户端的 MCP 配置方式为准。

脚本会更新：

```text
~/.codex/config.toml
~/.codex/.mcp.json
```

脚本会保留其他 MCP 配置，并在修改前创建带时间戳的备份。配置完成后，需要完全退出并重新启动对应的 Agent 客户端。

## 使用方法

使用前请打开 MasterGo 文件或画布，并确认 MCP 已连接。以下示例中的引号内容就是可以直接输入给 Agent 的指令。

| 使用场景 | 可以做什么 | 用户输入示例 |
| --- | --- | --- |
| 检查连接 | 检查 MCP 是否在线、获取版本 | “检查 MasterGo MCP 是否连接正常”<br>“获取当前 MasterGo MCP 版本” |
| 生成页面 | 根据自然语言需求在画布中生成页面 | “在当前 MasterGo 画布中生成一个登录页面，包含手机号输入框、验证码输入框、登录按钮和隐私协议入口” |
| 生成复杂界面 | 创建完整业务页面或车机界面 | “在当前 MasterGo 画布中生成一个新能源汽车设置页，包含车辆状态、续航信息、充电入口和底部导航” |
| 读取图层 | 查看当前选中图层的结构和属性 | “读取当前选中的 MasterGo 图层结构” |
| 修改图层 | 修改文本、样式和局部结构 | “将当前选中卡片的标题改为‘车辆状态’，把内边距调整为 16px，圆角调整为 8px” |
| 替换或删除 | 替换图层内容或删除指定节点 | “把当前选中的图标替换为充电图标”<br>“删除当前选中的辅助说明文本” |
| 导出代码 | 将画布图层转换为前端代码 | “导出当前选中图层的前端代码，使用 HTML 格式” |
| 获取截图 | 获取当前画布或节点的视觉预览 | “获取当前选中图层的截图” |
| 设计变量 | 读取或更新颜色、字号等设计变量 | “读取当前文件的设计变量”<br>“将主色变量更新为 #1677FF” |
| 组件和资源 | 查询组件信息、团队库和设计差异 | “列出当前可用的团队组件库”<br>“对比本地设计与画布之间的差异” |

如果使用管道兜底模式，`get_selection_node` 和 `get_frontend_code` 必须提供 `projectDir`。

## 连接模式

### 原生 MCP 模式（推荐）

当当前 Agent 客户端已加载 `mcp__mastergo` 工具时，优先使用原生模式。该模式下页面生成、组件创建、设计同步和画布写入能力最完整、最可靠。

可以通过以下方式验证：

```text
tool_search("mastergo")
```

或调用：

```text
mcp__mastergo__get_version
```

### 管道兜底模式

只有原生 MCP 工具没有加载时才使用管道模式。管道模式适合检查版本、读取图层、获取截图、局部修改和导出前端代码。

以下写入工具在管道模式下不可靠：

- `design_page`（带 `code` 参数）
- `submit_page_to_canvas`
- `agent_create_component`
- `agent_sync_design`

管道模式下建议先创建占位节点，再使用 `agent_update_node` 写入内容，并用 `get_selection_node` 验证结果。完整子树异常时，可以使用 `agent_replace_node` 强制替换结构。

## 常见故障处理

| 症状 | 常见原因 | 处理方法 |
| --- | --- | --- |
| 找不到 `mcp__mastergo` 工具 | MCP 配置未加载，或配置后没有重启 Agent 客户端 | 检查 `~/.codex/config.toml` 是否存在 `[mcp_servers.mastergo]`；确认 `@mastergo/vibe-mcp` 配置正确；完全重启客户端；使用 `tool_search("mastergo")` 或 `mcp__mastergo__get_version` 验证 |
| `list_mcp_resources` 返回 `Method not found` | Vibe MCP 可能不提供 `resources/list` 方法 | 不一定是故障；只要 `mcp__mastergo__get_version` 或其他 `mcp__mastergo__...` 工具可用，就可以继续使用 |
| `npx` 不存在 | 未安装 Node.js 或 Node.js 未加入 PATH | 安装 Node.js 18+：`brew install node`，或从 [Node.js 官网](https://nodejs.org/) 安装 |
| `mgmcp` 没有运行 | MasterGo 文件未打开，或连接尚未建立 | 打开 MasterGo 客户端或连接的 Chrome 中的目标文件；执行 `lsof -i :50678` 检查端口 |
| 工具调用成功但画布没有变化 | `mgmcp` 长时间运行后状态异常，或使用了管道模式下不可靠的写入工具 | 执行 `lsof -i :50678 \| grep mgmcp` 找到进程，执行 `kill <mgmcp_PID>` 后重启 MasterGo 和 Agent 客户端；优先使用原生 MCP 模式 |
| `NoSelection` | 当前没有选中图层 | 在 MasterGo 中选中图层或根节点，或提供节点 ID，例如“读取节点 19:361 的结构” |
| `no online mg canvas` | MCP 已启动，但没有连接到在线画布 | 确认目标文件已在 MasterGo 客户端中打开且可编辑；确认使用的是 MCP 支持的客户端或 Chrome 环境；必要时重启 MasterGo 和 `mgmcp` |
| 前端代码导出失败 | 未选中图层、节点 ID 错误，或缺少 `projectDir` | 选中目标图层并确认节点 ID；管道模式下为 `get_frontend_code` 传入 `projectDir` |

仅在 Agent 客户端的内置浏览器中看到 MasterGo 页面，不一定代表 `mgmcp` 已连接到该画布。

## 安全与操作原则

涉及以下操作时，应先确认再执行：

- 修改 `~/.codex/config.toml` 或 `.mcp.json`
- 安装 npm 包或 Homebrew 软件
- 终止 `mgmcp` 进程
- 修改或删除画布变量
- 对画布执行写入操作

遇到配置、安装或调用异常时，优先参考 [MasterGo MCP 官方文档](https://mastergo.com/help/MG/MCP/VIBE)，并明确说明信息来源。

## 项目结构

```text
.
├── mastergo-mcp/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── scripts/setup-mastergo-mcp.sh
├── README.md
├── agents.md
├── LICENSE
└── .gitignore
```

## 许可

本项目采用 MIT License，详见 [LICENSE](LICENSE)。
