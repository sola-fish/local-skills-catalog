---
name: local-skills-catalog
description: 扫描本机已安装的 Agent Skills，将英文 description 译成自然中文，并按语义自动分类，输出中文 Markdown 目录表。触发语：列出全部 skill 中文清单、skill 中文目录、整理我本地所有 skills、本地 skills 整理、skills 清单、skill-manager 生成目录。覆盖 ~/.claude/skills、~/.agents/skills、~/.cursor/skills、~/.cursor/skills-cursor、~/.claude/plugins/cache。只读 SKILL.md，绝不修改源文件。
---

# Skill-Manager：本地技能中文整理

扫描本地 skills → 提取 description → **语义翻译成中文** → **按用途语义分类** → 输出 Markdown 总表。

## 触发指令

以下任一说法都应启用本 skill：

- 列出全部 skill 中文清单
- skill 中文目录
- 整理我本地所有 skills
- skill-manager 生成目录
- 本地有哪些 skill / skills 清单

## 硬约束

1. **只读**各目录下的 `SKILL.md`，**禁止修改**任何源文件；只做读取、翻译、汇总输出
2. 损坏或无 YAML frontmatter 的文件跳过，并在末尾简要说明跳过数量
3. 没有 `description` 时，中文栏标注 **【无描述】**
4. 翻译拒绝机翻腔，符合国内程序员阅读习惯；专有名词可保留英文
5. 输出完成后必须告诉用户：以后直接说「列出全部 skill 中文清单」即可再次调用
6. 分类看 **description 语义**，不要用英文关键词机械匹配（规则见 [references/categories.md](references/categories.md)）

## 执行步骤

```
进度：
- [ ] 1. 扫描并解析（脚本）
- [ ] 2. 逐条语义翻译 + 分类（Agent）
- [ ] 3. 按强制表格格式输出
- [ ] 4. 询问是否保存到 ~/skill-catalog-zh.md
- [ ] 5. 提醒触发语
```

### 1. 扫描（只读）

在本 skill 目录执行：

```bash
python3 <skill-dir>/scripts/catalog.py --format json
```

默认扫描：

| 来源 | 路径模式 |
| --- | --- |
| Claude | `~/.claude/skills/*/SKILL.md` |
| Agents | `~/.agents/skills/*/SKILL.md` |
| Cursor | `~/.cursor/skills/*/SKILL.md` |
| Cursor 内置 | `~/.cursor/skills-cursor/*/SKILL.md`（默认包含） |
| Claude 插件缓存 | `~/.claude/plugins/cache/**/skills/*/SKILL.md` |

可选：`--no-builtin` 跳过内置；`--no-cursor` 跳过 `~/.cursor/skills`；`--query 关键词` 过滤；`--out path` 写原始 JSON。

脚本会：解析 frontmatter 的 `name` / `description`、去重、附带路径与来源。  
脚本**不会**写分类、**不会**改源文件。`category` / `description_zh` 字段留给你填写。

### 2. 翻译与语义分类

对 JSON 中每个 skill：

1. 读 `description`（可参考 `display_name`、`triggers`）
2. 写成 1–2 句通顺中文 → `description_zh`
3. 按语义归入 [references/categories.md](references/categories.md) 中的一个类目 → `category`
4. 无 description → `description_zh` = `【无描述】`，类目仍尽量根据名称语义判断，实在不行用「其他工具」

### 3. 强制输出格式

```markdown
# 本地全部 Skill 中文目录总览

> 扫描来源：~/.claude/skills、~/.agents/skills、~/.cursor/skills、~/.cursor/skills-cursor、~/.claude/plugins/cache  
> 去重后共 N 个技能（原始命中 M 个 SKILL.md）

| 技能名称 | 分类 | 中文功能说明 | 原始英文描述 | 本地文件路径 |
|---|---|---|---|---|
| name | 分类名 | 中文 1–2 句 | 原文（可截断至约 120 字） | `/abs/path/SKILL.md` |
```

要求：

- 表格按 **分类** 再按技能名排序，便于扫读
- 原始描述过长可截断并加 `…`；路径用绝对路径
- 同名多处安装时，路径列用去重后的主路径；可在表下用一行备注「另有重复缓存/安装」
- 若提取到 `triggers`，可在表后追加「常用触发提示」小节（可选优化，非必须）

### 4. 可选落盘

输出完成后询问用户是否保存。若同意：

- 将最终中文 Markdown 写入 `~/skill-catalog-zh.md`（仅写汇总文件，不动任何 `SKILL.md`）

### 5. 收尾固定句

> 以后想再看，直接说「列出全部 skill 中文清单」即可。

## 职责边界

- 本 skill：整理、中文说明、分类展示
- 不负责：安装 / 卸载 / 发布（交给其它 skill-manager / find-skills）
