---
name: mastergo-mcp
description: >
  MasterGo Vibe MCP 集成。当用户要求在 MasterGo 画布上设计、绘制、
  生成页面、读取图层代码、修改组件、管理变量时使用。自动检测 MCP
  连接状态，未配置时引导一键安装，配置完成后提供完整的工具调用能力。
  支持私域版 MasterGo（如 mastergo.private.example.com）。
---

# MasterGo Vibe MCP Skill

此 skill 封装了 MasterGo Vibe MCP（@mastergo/vibe-mcp v1.0.18）的完整配置和调用流程。

默认示例以 Codex 为 Agent 客户端，但本 skill 的 MCP 工作流也适用于 Claude Code 及其他支持 MCP 的 Agent 客户端。具体配置入口以客户端的 MCP 配置方式为准；本 skill 自带的 Codex 配置脚本主要面向 Codex Desktop，并同时提供通用 MCP JSON 配置。

> Skill 版本：**1.1** (2026-07-10T14:30:00+08:00)

## 操作原则

1. **官方文档先行**：本 skill 以 MasterGo MCP 官方文档（https://mastergo.com/help/MG/MCP/VIBE）为第一参考源。当遇到配置、安装、使用问题或工具调用异常时，优先从官方文档查询方法，并告诉用户信息来自官方文档。
2. **信息来源透明**：所有操作建议应说明信息是通过官方文档直接获取、从 skill 经验中得出、还是通过浏览器/API 主动查询得到的。不准确认的信息不提。
3. **风险操作前确认**：涉及写文件（如修改 `~/.codex/config.toml`、`.mcp.json`）、杀进程（`kill <PID>`）、安装包（`brew install`、`npm install`）等可能影响用户环境稳定性的操作，需先告知意图、预期效果和潜在风险，等待用户确认后执行。
4. **稳定优先，标准为桥**：优先使用当前 Agent 客户端的原生 MCP、官方 npm 包、标准配置文件路径等官方或业界通用的方式完成任务。非标准绕过手段（如管道 JSON-RPC 调用）仅在标准路径受阻且无修复手段时作为临时兜底，并告知用户局限性。
5. **报告来源与兜底**：如果某种方法从官方文档学到但实际执行未生效，诚实告知用户"官方文档说明此方法，但当前环境未能生效"，再切换为非标准的替代方案。

## 何时触发

当以下任一条件满足时激活（避免用户未意图使用 MasterGo 时误触发）：

**条件 A — 用户明确提到 MasterGo 相关的关键词：**
- 包含"MasterGo"、"mgmcp"这些词
- 明确说"在 MasterGo 上画 / 设计 / 生成..."
- 明确说"使用 MasterGo MCP / Vibe MCP..."
- 明确要求"获取画布图层代码 / 把画布内容导出为前端代码"

**条件 B — 上下文已确认在使用 MasterGo（如正在操作画布）：**
- 前序对话已经在操作 MasterGo 画布
- 用户说"接着改"、"继续设计"、"再调整一下"等与画布任务连续的语境

**不触发的情况（以下场景不要激活 skill）：**
- 用户只说"设计一个页面 / 给我画个界面"而没有提及 MasterGo 相关词
- 用户只说"获取前端代码"而没有提及画布或 MasterGo
- 上下文无任何 MasterGo 关联

## 工作流

### 阶段 0：环境自检（每次对话首轮必做）

```
1. 检查原生 MCP 工具是否已暴露：
   - 优先调用 tool_search("mastergo")，查看是否出现 `mcp__mastergo` 工具命名空间
   - 或直接尝试 `mcp__mastergo__get_version`
   - 如果原生工具可用，跳到阶段 3（走原生 MCP，所有工具可用）

2. 辅助检查 MCP server 注册状态：
   - 可以调用 list_mcp_resources(server="mastergo")
   - 如果返回 `unknown MCP server`，说明当前 Agent 会话没有加载 mastergo server
   - 如果返回 `Method not found`，不代表故障；MasterGo Vibe MCP 不实现 resources/list，但原生工具可能已正常暴露

3. 如果原生工具未暴露：
   - 检查 npx 是否可用：which npx
   - 检查 mgmcp 是否运行：lsof -i :50678
     特别检查 mgmcp PID 是否已运行过久（同一 PID 运行超 30 分钟可能导致状态腐化）
   - 检查 ~/.codex/config.toml 是否存在 `[mcp_servers.mastergo]`
   - 检查 ~/.codex/.mcp.json 是否存在（通用 IDE / Cursor 风格配置，Codex Desktop 不一定只读这个入口）
```

### 阶段 1：配置修复（写入前需用户确认）

**如果 npx 不可用** → 告诉用户安装 Node.js，不要自动安装：
```
brew install node
# 如果 brew 也没有，去 https://nodejs.org/ 下载
```

**如果 mgmcp 未运行** → 告诉用户:
```
请先安装并启动 MasterGo 桌面客户端，先建立本地 MCP 服务。服务建立后，可以在 MasterGo Web 客户端中打开目标文件，并确认页面显示“MCP 服务端启动并已连接”。
```

根据当前环境的实测经验，首次建立 Vibe MCP 连接需要 MasterGo 桌面客户端生成 `http://localhost:50678`；建立本地服务后，不需要再在桌面客户端中打开目标文件，可以继续使用 MasterGo Web 客户端。桌面客户端、Web 客户端和本地服务之间的具体生命周期机制尚未由官方文档完整说明，连接异常时建议重新启动桌面客户端进行初始化。

**如果 Codex Desktop 原生配置或通用 `.mcp.json` 缺失/错误** → 使用本 skill 的安装脚本。先向用户说明将修改的路径、保留现有配置且会创建备份，并说明首次启动时 `npx -y` 可能下载 `@mastergo/vibe-mcp`，得到明确确认后再执行：

```bash
bash scripts/setup-mastergo-mcp.sh --yes
```

- `--yes` 只表示用户已经在对话中明确批准写入；未确认时不要传此参数，也不要执行写入。
- 脚本默认更新 `${CODEX_HOME:-$HOME/.codex}/config.toml` 中的 `[mcp_servers.mastergo]`，并更新同目录 `.mcp.json` 中的 `mcpServers.mastergo`；不会覆盖其他 server。
- 只修复 Codex Desktop 时传 `--codex-only`；只修复通用 JSON 时传 `--json-only`；端口变化时传 `--port <port>`。
- 脚本只检查 Node.js/npx，不自动运行 `brew install` 或全局 `npm install`。缺少依赖时向用户解释并另行请求安装许可。
- 脚本对变更文件创建时间戳备份并原子写入；无变化时不创建备份。

写入后需要完全退出并重启对应的 Agent 客户端才能生效。

**配置完成后，必须让对应的 Agent 客户端重新加载 MCP 配置**：通常需要完全退出并重启客户端。重启后用 `tool_search("mastergo")` 或 `mcp__mastergo__get_version` 验证原生 MCP 工具是否暴露；不要把 `list_mcp_resources(server="mastergo")` 的 `Method not found` 当成失败。

#### 官方 MCP 类型区分

- **Vibe MCP**：`@mastergo/vibe-mcp`，连接本机 `http://localhost:50678`，不需要个人令牌，用于 Vibe Design / 画布读取、生成、修改、同步、变量和组件操作。本 skill 默认使用 Vibe MCP。
- **Magic MCP**：`@mastergo/magic-mcp`，需要个人令牌，用于原 DSL / D2C 数据场景。除非用户明确要求 Magic MCP / DSL / D2C，否则不要把本 skill 切到 Magic MCP。

### 阶段 2：管道调用工具（自动修复失败时的后备方案）

仅当当前 Agent 客户端的原生 MCP 工具没有暴露（`tool_search("mastergo")` 找不到 `mcp__mastergo` 命名空间，或 `mcp__mastergo__get_version` 不可调用）时，才使用管道直接调用。每次调用都是一个独立的 exec_command：

```bash
export PATH="/opt/homebrew/bin:$PATH"
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"codex","version":"1.0"}},"id":1}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","method":"tools/call","params":{工具参数},"id":2}' \
  | npx -y @mastergo/vibe-mcp --url=http://localhost:50678 2>/dev/null
```

**四条红线**:
- `--url` 必须带 `http://` 前缀
- `get_selection_node` 和 `get_frontend_code` 必须传 `projectDir`
- 输出是 ndjson 格式，用 `python3` 或 `grep` 解析
- 首次 npx 下载需要 `require_escalated` + `prefix_rule: ["npx","-y","@mastergo/vibe-mcp"]`

### 阶段 3：执行用户任务

#### 原生 MCP 优先策略

如果阶段 0 确认 `mcp__mastergo` 工具命名空间已暴露，则直接使用原生 MCP 工具完成任务（如 `mcp__mastergo__design_page`、`mcp__mastergo__get_selection_node` 等），不走管道模式。
注意：`list_mcp_resources(server="mastergo")` 返回 `Method not found` 是正常现象，因为 Vibe MCP 不提供 resources/list；只要 `mcp__mastergo__...` 工具能调用，就视为原生 MCP 可用。

#### 管道模式 vs 原生 MCP 的工具可靠性

以下表格仅适用于 **原生 MCP 不可用、必须走管道模式兜底** 时参考。如果原生 MCP 已暴露，直接使用 `mcp__mastergo__...` 工具即可，不存在管道模式的已知 bug。

@mastergo/vibe-mcp v1.0.18 在管道模式（stdin 串行发送 JSON-RPC）下有已知 bug：**所有自动加载 page-generate/component-generate 规则的写工具，均会吞掉实际返回结果，仅返回规则文本**。此 bug 在 Codex 原生 MCP 模式下不存在。

**管道模式下建议放弃的工具**：`design_page`(带code参数)、`submit_page_to_canvas`、`agent_create_component`、`agent_sync_design`

| 可靠性 | 工具 | 管道模式 | 原生 MCP |
|--------|------|----------|----------|
| ✅ 稳定 | get_version, tools/list | 可用 | 可用 |
| ✅ 稳定 | get_selection_node | 可用 | 可用 |
| ✅ 稳定 | agent_update_node | 局部修改首选；完整子树需复核 | 可用 |
| ⚠️ 有条件 | get_frontend_code, get_screenshot | 可用 | 可用 |
| ⚠️ 有条件 | agent_replace_node, agent_remove_node | 图片替换/结构替换兜底 | 可用 |
| ⚠️ 有条件 | design_page(无code参) | 仅创建占位层 | 完整可用 |
| ❌ 不可靠 | design_page(有code参) | 管道模式只返回规则文本 | 完整可用 |
| ❌ 不可靠 | submit_page_to_canvas | 管道模式只返回规则文本 | 完整可用 |
| ❌ 不可靠 | agent_create_component | 返回成功但不创建 | 完整可用 |
| ❌ 不可靠 | agent_sync_design | 返回成功但不同步 | 完整可用 |

#### 推荐任务执行路径（按已验证的可靠性排序）

**任务1：在画布放置内容（已验证可跑通）**

原生 MCP 可用时：直接调用 `mcp__mastergo__design_page` 完成页面生成和提交；后续用 `mcp__mastergo__get_selection_node` 或 `mcp__mastergo__get_screenshot` 复核。

管道模式兜底时：
```
1. design_page(requirement, designSource="free-draw", userConfirmedDesignSource=true, projectDir)
   → 提取返回信息中的 placeholderNodeId（如 19:361）
2. agent_update_node(targetNodeId="19:361", code=包含 data-node-id 的完整HTML)
   → 写入成功，画布可见
```
`agent_update_node` 是管道模式下已验证可用的局部修改首选路径；写入完整根节点子树后必须用 `get_selection_node` 拉取复核。

**任务2：读取并修改已有图层（已验证）**
```
1. get_selection_node(projectDir) → 获取节点代码
2. agent_update_node(code=修改后的HTML片段) → 局部修改
```

**任务3：将组件库作为画布内容放置（有限可用）**
```
1. design_page(无code) → 创建占位层
2. agent_update_node → 用完整HTML填入所有组件
```
注意：组件不会被创建为 MasterGo 原生母版组件，仅以图层组形式呈现在画布上。

**任务3b：完整子树写入异常的兜底（已观察到）**
```
1. agent_update_node 写入完整根节点子树后
2. get_selection_node(targetNodeId=根节点ID, projectDir) → 拉取基准 HTML
3. 检查根节点直接子节点 data-name 顺序是否与预期一致
4. 若顺序反转、局部样式 accepted 但未生效、或完整子树未变化，停止重复 agent_update_node
5. agent_replace_node(targetNodeId=根节点ID, code=正常顺序完整HTML, projectDir) → 强制替换结构
```
注意：管道模式下曾观察到 `agent_update_node` 重建已有根节点完整子树时返回 accepted，但顶层子节点顺序与预期相反；仅更新父容器样式（如 `flex-direction: column-reverse`）也可能返回 accepted 但画布不变。

**任务4：导出前端代码**
```
get_frontend_code(projectDir, targetNodeId) → 导出选中图层HTML
```

#### mgmcp 守护进程健康管理

mgmcp 长期运行后会积累连接状态腐化，表现特征：
- `get_version` / `tools/list` 正常
- 所有写工具返回 `isError=false` 但画布无变化
- 所有工具调用超时

**检查方法**：
```bash
lsof -i :50678 | grep mgmcp
# 查看 PID 和运行时长
```

**修复方法**（告诉用户操作）：
```bash
# 1. 查看 mgmcp PID
lsof -i :50678 | grep mgmcp
# 2. 杀掉 mgmcp 进程
kill <mgmcp_PID>
# 3. 完全退出并重新打开 MasterGo 桌面客户端
#    刷新浏览器页面不会重启 mgmcp！
```

## 完整工具参考

### 页面/设计
| 工具 | 管道可用 | 用途 | 关键参数 |
|------|----------|------|----------|
| get_guidelines | ✅ | 加载生成规则 | scope: ["page-generate"] |
| design_page | ⚠️ 仅无code | 创建占位层（拿到placeholderNodeId） | requirement, designSource, userConfirmedDesignSource, projectDir |
| submit_page_to_canvas | ❌ | 管道模式不生效，优先用 agent_update_node；完整子树异常时用 agent_replace_node | code, projectDir |

### 图层操作
| 工具 | 管道可用 | 用途 | 关键参数 |
|------|----------|------|----------|
| get_selection_node | ✅ | 读取图层快照 | **projectDir(必填)**, targetNodeId |
| agent_update_node | ✅ **局部修改首选** | 文本/样式/小范围结构修改；完整子树写入后必须复核 | code(HTML片段,必须含data-node-id), targetNodeId |
| agent_replace_node | ⚠️ | 替换图标/图片；当完整子树顺序异常或 update accepted 但无变化时强制替换结构 | code, targetNodeId |
| agent_remove_node | ⚠️ | 删除节点 | targetNodeId 或选中图层 |

### 导出/读取
| 工具 | 管道可用 | 用途 | 关键参数 |
|------|----------|------|----------|
| get_frontend_code | ⚠️ | 导出 HTML | **projectDir(必填)**, outputFormat |
| get_screenshot | ⚠️ | 导出预览图 | projectDir, targetNodeId |

### 组件/变量/库
| 工具 | 管道可用 | 用途 |
|------|----------|------|
| agent_create_component | ❌ | 管道模式只返回成功不创建 |
| get_component_info | ⚠️ | 获取团队库/本地组件信息 |
| get_variables | ✅ | 读取文件变量 |
| update_variables | ⚠️ | 创建/修改/排序变量 |
| agent_remove_variable | ⚠️ | 删除变量（高危） |
| get_library_list | ✅ | 列出已订阅团队库 |
| get_design_diff | ⚠️ | 对比本地与画布差异 |
| agent_sync_design | ❌ | 管道模式返回成功但不同步 |

### 基础
| 工具 | 管道可用 | 用途 |
|------|----------|------|
| get_version | ✅ | 获取 MCP 版本 |

## 故障速查

| 症状 | 原因 | 动作 |
|------|------|------|
| unknown MCP server | Codex 当前会话未加载 mastergo server；或只写了通用 .mcp.json，Codex Desktop 未读到 | 优先检查并写入 `~/.codex/config.toml` 的 `[mcp_servers.mastergo]`，重启 Codex 后重试；仅当当前无法重启且必须完成操作时才临时走管道调用 |
| list_mcp_resources 返回 Method not found | MasterGo Vibe MCP 不实现 resources/list | 不算失败；用 `tool_search("mastergo")` 或 `mcp__mastergo__get_version` 验证原生工具 |
| tool_search 能看到 mcp__mastergo 但 get_selection_node 返回 NoSelection | 画布在线，但当前没有选中图层 | 让用户在 MasterGo 画布中选中一个图层/根节点后重试，或传 targetNodeId |
| no online mg canvas | mgmcp 未连接到在线 MasterGo 画布；可能尚未完成首次桌面客户端初始化，或 Web 文件尚未显示已连接 | 首次使用时启动 MasterGo 桌面客户端建立 `http://localhost:50678`；之后在 MasterGo Web 客户端打开文件，并确认页面显示“MCP 服务端启动并已连接” |
| in-app browser 能看到文件但 MCP 报 no online mg canvas | Agent 内置浏览器看到文件，不代表 mgmcp 已连接到该画布 | 优先在 MasterGo Web 客户端打开同一文件并确认“MCP 服务端启动并已连接”；首次连接异常时重新启动 MasterGo 桌面客户端 |
| `Unsupported protocol localhost:` | --url 缺 http:// | 改为 `--url=http://localhost:50678` |
| 50678 端口无 mgmcp 监听 | MasterGo 本地服务未启动，或端口自动切换 | 首次使用时启动 MasterGo 桌面客户端初始化本地服务；若实际端口变化，更新 `--url=http://localhost:<port>` |
| get_selection_node 报缺参数 | projectDir 必填 | 传工作区绝对路径 |
| ERR_MODULE_NOT_FOUND: zod | pnpm/npm 冲突 | rm node_modules && npm install |
| 写工具返回 isError=false 但画布无变化 | 管道模式工具 bug | 改用 agent_update_node 写入 |
| agent_update_node 返回 accepted 但父容器样式未变化 | 管道模式局部样式合并未生效 | 拉取 get_selection_node 验证；若是根节点结构问题，改用 agent_replace_node |
| 完整页面写入后顶栏/底栏上下颠倒 | agent_update_node 重建已有根节点完整子树时可能出现直接子节点顺序异常 | 用 get_selection_node 检查根节点直接子节点 data-name 顺序；用 agent_replace_node + 正常顺序完整 HTML 替换 |
| 本地图片路径导致写入失败 | HTML 引用了不存在的 ./asset/... 文件 | 确保图片真实存在于 projectDir 内，或先生成/复制到 asset/images 后再传 projectDir |
| submit_page_to_canvas 返回规则文本 | 管道模式 auto-load 吞结果 | 用 agent_update_node 替代，或重启 Codex 走原生 MCP |
| design_page 报"占位层启动失败" | mgmcp 守护进程状态腐化 | 杀掉 mgmcp 进程后重新打开 MasterGo 桌面客户端进行初始化，再在 Web 客户端打开目标文件 |
| mgmcp 在但写工具全部超时 | mgmcp 连接泄漏/卡死 | `kill <mgmcp_PID>` → 重新打开 MasterGo 桌面客户端进行初始化，再在 Web 客户端恢复目标文件连接 |
| 创建组件后 Assets 面板看不到 | agent_create_component 在管道模式不生效 | 改用 agent_update_node 在画布放置，或重启 Codex 走原生 MCP |

## 已知限制

- **@mastergo/vibe-mcp v1.0.18 管道模式 bug**：所有自动加载规则的写工具（design_page, submit_page_to_canvas, agent_create_component, agent_sync_design）在 stdin 串行模式下的返回结果被规则文本覆盖。这些工具仅在 Codex 原生 MCP（Codex Desktop 建议通过 `~/.codex/config.toml` 的 `[mcp_servers.mastergo]` 加载；通用 IDE 可用 `.mcp.json`/`mcp.json`）模式下完整可用
- **无文档级页面创建能力**：@mastergo/vibe-mcp 不具备创建 MasterGo 文档页面标签（底部"页面1/页面2"）的能力，只能操作当前画布内的节点
- mgmcp 通过 HTML+Tailwind 转译操作画布，不能直接操控 MasterGo 原生工具栏控件（矩形/星形/钢笔工具等）
- **mgmcp 守护进程长期运行会腐化**：连接泄漏导致写工具失效。建议单次对话中定期检查 PID，异常时杀掉重启
- 私域版 MasterGo 的 URL 与官方版不同，但 mgmcp 通过 Chrome 扩展连接，无需额外配置
- agent_create_component 创建的不是画布可视化图层，而是 Assets 面板中的母版组件，需要通过 MasterGo 的 Assets 面板查看

## 版本

- mgmcp daemon: v1.1.9（自动更新）
- @mastergo/vibe-mcp: v1.0.18（npm 包）
