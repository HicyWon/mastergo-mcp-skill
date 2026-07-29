# Image to UI Skill

将 AI 生成的 UI 图片、界面截图或设计草图，转换为可编辑的源级 UI 结构。这个 skill 会先锁定唯一视觉参考，再以逐项拆解和用户确认作为审批节点，最后从同一份 canonical UI IR 与真实资产包生成自包含 HTML 预览，或交给 MasterGo、Figma 等画布适配器继续生成可编辑画布。

## 适用场景

- 从 AI 生成的界面图恢复可编辑的 UI 结构
- 从高保真截图分析布局、组件、文本、图标和图片资产
- 将草图或文字 brief 补全为一张待确认的视觉参考图
- 生成带 `ui-ir.json` 的自包含 HTML 预览
- 将同一份 UI 结构同步到 MasterGo、Figma 或其他画布
- 对复杂视觉区域进行保真资产边界管理，避免重复绘制或错误拆层

## 核心能力

### 先确认视觉参考

skill 会区分高保真 UI 参考图与低保真草图。对于草图或纯文字 brief，可先生成一张完整的视觉参考图；生成后只保留一张锁定参考，并要求用户确认，避免在后续拆解过程中悄悄改变视觉方向。

### 逐项拆解并同步 UI IR

确认参考图后，按固定格式列出屏幕元数据和组件级五列表格，覆盖所有可见文本、控件、图标、重复项、图片和重要装饰。表格会同步生成 `ui-ir.json` 草稿，保持展示行、结构节点、资产和目标适配之间的可追溯关系。

### 以保真为前提划分资产

复杂的主体、投影、反射、光照、氛围和纹理如果分离后会产生明显漂移，会被保留为一个完整的“参考保真视觉底图”。文本、按钮、卡片、图标和其他真正需要编辑的 UI 节点则独立重建，避免把一张完整截图误当成可编辑图层。

### 同一份 canonical UI IR 适配多个目标

HTML、MasterGo 和 Figma 输出共享同一份平台无关 UI IR。平台差异被限制在 `targets.<adapter>` 映射中；每个图像资产、图标和结构节点都需要明确表示方式、来源、路径、尺寸、透明度和目标端预期节点类型。

### 交付前确定性校验

内置校验脚本会检查树结构、展示行血缘、资产文件、数据 URL、自包含 HTML、画布比例、图标元数据、目标映射和视觉证据。校验失败时不会报告为已完成。

## 标准工作流

```text
参考图或 brief
    ↓
锁定唯一视觉参考并确认
    ↓
逐项组件拆解 + draft ui-ir.json
    ↓
用户确认拆解与输出目标
    ↓
确定 canonical UI IR 与资产包
    ↓
生成自包含 HTML 或目标画布
    ↓
结构回读 + 截图检查 + 确定性校验
```

## 安装

使用 Codex skill installer：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/HicyWon/mastergo-mcp-skill \
  --path image-to-ui
```

也可以将 `image-to-ui/` 目录整体复制到目标 Agent 客户端的 skills 目录。

运行完整校验时需要 Python 3；使用图标解析脚本时需要 Node.js。具体画布写入能力取决于当前客户端和目标平台的适配器与连接状态。

## 使用示例

```text
使用 $image-to-ui 分析这张 UI 截图，先锁定视觉参考，再给我逐项拆解表和 draft ui-ir.json；确认后生成自包含 HTML 预览。
```

```text
使用 $image-to-ui 将这张 AI UI 图恢复成可编辑结构。确认拆解后，把同一份 canonical UI IR 适配到 MasterGo，并完成结构回读与校验。
```

## 关键约束

- 未确认视觉参考前不进入拆解阶段。
- 未确认拆解和输出目标前，不生成 HTML 或写入画布。
- 不使用完整 UI 截图冒充可编辑的独立图片资产。
- 不用 Emoji、字符或图标字体替代非语义视觉图形。
- 不因平台限制静默丢失节点、重复资产或改变视觉锚点。
- 不添加产品行为、导航、动画或交互，除非用户明确要求。

## 目录结构

```text
image-to-ui/
├── SKILL.md
├── README.md
├── agents/openai.yaml
├── references/            # 拆解、保真、确认、图标和验证规则
├── scripts/               # 图标解析与交付校验脚本
└── assets/icons/lucide/   # 本地 Lucide 图标缓存
```

## 许可

本 skill 随仓库使用 MIT License。内置 Lucide 图标资源遵循其目录中的许可证文件。
