# MasterGo MCP Skill

用于在 Codex 中连接并操作 MasterGo Vibe MCP 画布的 skill。

[GitHub 仓库](https://github.com/HicyWon/mastergo-mcp-skill) · [MasterGo MCP 官方文档](https://mastergo.com/help/MG/MCP)

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

这个 skill 可以帮助 Codex：

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

支持 MasterGo Vibe MCP，也支持私域 MasterGo 环境，例如 `mastergo.dongfeng-nissan.com.cn`。

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

脚本会更新：

```text
~/.codex/config.toml
~/.codex/.mcp.json
```

脚本会保留其他 MCP 配置，并在修改前创建带时间戳的备份。配置完成后，需要完全退出并重新启动 Codex。

## 使用方法

### 检查连接

```text
检查 MasterGo MCP 是否连接正常。
```

也可以检查版本：

```text
获取当前 MasterGo MCP 版本。
```

### 生成页面

1. 打开 MasterGo 文件或画布。
2. 确认 MasterGo MCP 已连接。
3. 描述页面需求。
4. 生成后用图层读取或截图能力进行复核。

示例：

```text
在当前 MasterGo 画布中生成一个新能源汽车设置页，包含车辆状态、续航信息、充电入口和底部导航。
```

### 读取和修改图层

读取当前选中图层：

```text
读取当前选中的 MasterGo 图层结构。
```

修改图层：

```text
将当前选中卡片的标题改为“车辆状态”，把内边距调整为 16px，圆角调整为 8px。
```

导出前端代码：

```text
导出当前选中图层的前端代码，使用 HTML 格式。
```

如果使用管道兜底模式，`get_selection_node` 和 `get_frontend_code` 必须提供 `projectDir`。

## 连接模式

### 原生 MCP 模式（推荐）

当 Codex 已加载 `mcp__mastergo` 工具时，优先使用原生模式。该模式下页面生成、组件创建、设计同步和画布写入能力最完整、最可靠。

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

### 找不到 `mcp__mastergo` 工具

可能原因是 Codex 没有加载 MCP 配置，或配置后没有重启。

处理步骤：

1. 检查 `~/.codex/config.toml` 是否存在 `[mcp_servers.mastergo]`。
2. 确认 `@mastergo/vibe-mcp` 配置正确。
3. 完全退出并重新打开 Codex。
4. 使用 `tool_search("mastergo")` 或 `mcp__mastergo__get_version` 验证。

### `list_mcp_resources` 返回 `Method not found`

这不一定是故障。MasterGo Vibe MCP 可能不提供 `resources/list` 方法。只要 `mcp__mastergo__get_version` 或其他 `mcp__mastergo__...` 工具可用，就可以继续使用。

### `npx` 不存在

安装 Node.js 18 或更高版本：

```bash
brew install node
```

也可以从 [Node.js 官网](https://nodejs.org/) 下载。此 skill 不会自动安装 Node.js。

### `mgmcp` 没有运行

先打开 MasterGo 客户端或连接的 Chrome 中的目标文件，然后检查：

```bash
lsof -i :50678
```

如果没有监听，重新打开 MasterGo 文件并等待连接建立。

### 工具调用成功，但画布没有变化

可能是 `mgmcp` 长时间运行后状态异常。检查并重启进程：

```bash
lsof -i :50678 | grep mgmcp
kill <mgmcp_PID>
```

然后完全退出并重新打开 MasterGo 客户端，再重启 Codex。仅刷新浏览器页面通常不会重启 `mgmcp`。

### `NoSelection`

说明当前没有选中图层。请在 MasterGo 中选中一个图层或根节点，也可以直接提供目标节点 ID：

```text
读取节点 19:361 的结构。
```

### `no online mg canvas`

说明 MCP 已启动，但没有连接到在线 MasterGo 画布。请确认：

- 目标文件已在 MasterGo 客户端中打开
- 文件处于可编辑状态
- 使用的是 MCP 支持的 MasterGo 客户端或 Chrome 环境
- 必要时重启 MasterGo 和 `mgmcp`

仅在 Codex 内置浏览器中看到页面，不一定代表 `mgmcp` 已连接到该画布。

### 前端代码导出失败

请确认当前已选中图层、目标节点 ID 正确，并且在管道模式下传入了 `projectDir`。

## 安全与操作原则

涉及以下操作时，应先确认再执行：

- 修改 `~/.codex/config.toml` 或 `.mcp.json`
- 安装 npm 包或 Homebrew 软件
- 终止 `mgmcp` 进程
- 修改或删除画布变量
- 对画布执行写入操作

遇到配置、安装或调用异常时，优先参考 [MasterGo MCP 官方文档](https://mastergo.com/help/MG/MCP)，并明确说明信息来源。

## 项目结构

```text
.
├── mastergo-mcp/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   └── scripts/setup-mastergo-mcp.sh
├── README.md
├── LICENSE
└── .gitignore
```

## 许可

本项目采用 MIT License，详见 [LICENSE](LICENSE)。
