# Confirmation Controls

Use this reference only at the visual-reference confirmation gate and the decomposition-confirmation gate. It adds an in-conversation convenience layer; it never changes the canonical workflow, files, UI IR, assets, target adapters, validators, or delivered HTML.

## Common rules

- Always present a complete plain-text fallback first. A user can reply with an option number plus optional text; natural-language replies remain valid.
- In Codex when the active `visualize` skill is available, always create exactly one compact confirmation fragment in the thread-scoped visualization directory and emit `::codex-inline-vis{file="<title>.html"}` after the plain-text choices. Do not merely describe a panel. Follow the active `visualize` skill's fragment, accessibility, and styling rules.
- The fragment must use visible labeled native buttons for choices 1–3, a labeled text input or textarea plus submit button for choice 4, and `window.openai.sendFollowUpMessage({ prompt, title })` for every submitted action. Its prompt must include the current `stage`, immutable `revision`, normalized `intent`, and any entered text. The panel itself has no persistent state beyond the input value.
- When `visualize` is unavailable or compatibility is uncertain, omit the fragment and directive and continue with text alone. Do not emit an unsupported control directive.
- Include the current `stage` and immutable reference or draft `revision` in every control-generated instruction. Reject a stale instruction without side effects and re-present the current choices.
- Treat duplicate instructions for the same stage and revision idempotently: do not regenerate, decompose, or submit twice.
- Keep only one current-stage panel. Do not create a persistent control surface, store a second state model, or add controls to delivered HTML or canvas output.
- Keep the panel lightweight: no reference-image duplication, asset extraction, IR rendering, target inspection, or validation occurs until the selected existing workflow step requires it.

## Visual-reference confirmation

After showing the candidate visual reference, show these plain-text choices. The visible labels are the user contract.

```text
请选择下一步：
1. 这版通过，开始拆解 UI
2. 换一个全新的风格
3. 丰富界面内容
4. 其他：请直接描述
```

Map them to these normalized intents:

| Choice | Intent | Required behavior |
| --- | --- | --- |
| 1 | `accept-and-decompose` | Confirm this visual reference and begin the existing decomposition and synchronized draft UI IR workflow. |
| 2 | `regenerate-style` | Treat the request as explicit design exploration. Collect or infer only the requested style direction, preserve the user's product intent, supplied text, and clear structural anchors, then generate one replacement candidate visual reference. Do not decompose or create a draft UI IR. Return to this same confirmation gate. |
| 3 | `enrich-ui` | Generate one replacement candidate visual reference with additional context-appropriate supporting UI detail. Preserve product intent, supplied text, main functions, and clear structural anchors. Add no new business workflow, destination, or unrelated feature; do not mirror, duplicate, or merely repeat existing elements. Suitable additions include non-duplicative Dock/navigation items, complementary controls inside an existing composite component, meaningful information hierarchy, or restrained background texture. Do not decompose or create a draft UI IR. Return to this same confirmation gate. |
| 4 | `other` | Send the user's free-form instruction with the current stage and revision. Interpret it under the normal skill rules; ask only when it materially changes intent or is ambiguous. |

Do not describe the normalized intent, hidden prompt, or implementation details to the user. A style or enrichment replacement becomes a candidate reference; it becomes locked only if the user subsequently selects choice 1. If a prior decomposition exists because the user explicitly returned to this gate, a materially replaced reference invalidates that prior decomposition under the normal reference-revision rule.

## Decomposition confirmation and target selection

Use this gate only after presenting the fixed decomposition tables and a synchronized draft `ui-ir.json` with status `awaiting-user-confirmation`. Always show all four choices, even if HTML, MasterGo, or Figma was named earlier. Treat the earlier target as a suggested default only; a current explicit choice overrides it.

Show:

```text
请选择下一步：
1. 认可拆解方案，生成本地 HTML 预览
2. 认可拆解方案，直接绘制到 MasterGo 画布
3. 认可拆解方案，直接绘制到 Figma 画布
4. 其他：请直接描述
```

Map them to these normalized intents:

| Choice | Intent | Required behavior |
| --- | --- | --- |
| 1 | `accept-and-generate-html` | Confirm the current table and draft together, finalize the canonical UI IR, then enter the existing static self-contained HTML workflow. |
| 2 | `accept-and-submit-mastergo` | Confirm the current table and draft together, finalize the canonical UI IR, then enter the existing MasterGo adapter workflow. |
| 3 | `accept-and-submit-figma` | Confirm the current table and draft together, finalize the canonical UI IR, then enter the existing Figma adapter boundary. Figma transport, readback, and verification are not assumed to be available; report unsupported, blocked, or `submitted-unverified` honestly until that workflow is verified. |
| 4 | `other` | Send the user's free-form instruction with the current stage and draft revision. Keep the draft in `awaiting-user-confirmation` unless the instruction explicitly confirms it. |

Do not let any choice generate HTML or call a canvas adapter from an unconfirmed draft. The normal canonical UI IR, asset package, target preflight, deterministic validator, structural readback, and visual-evidence rules remain mandatory.
