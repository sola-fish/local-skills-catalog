# local-skills-catalog

扫描本机已安装的 Agent Skills，把英文 `description` 译成自然中文，按用途语义分类，输出一份可扫读的 **中文 Markdown 目录表**。

本 skill **只读**各处的 `SKILL.md`，不修改任何源文件；安装 / 卸载 / 发布请用其它 skill-manager / find-skills。

## 你能得到什么

对 Agent 说「列出全部 skill 中文清单」后，会得到类似：

```markdown
# 本地全部 Skill 中文目录总览

> 去重后共 N 个技能（原始命中 M 个 SKILL.md）

| 技能名称 | 分类 | 中文功能说明 | 原始英文描述 | 本地文件路径 |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |
```

可选落盘到 `~/skill-catalog-zh.md`（仅写汇总，不动任何 `SKILL.md`）。

## 触发语

以下任一说法即可启用：

- 列出全部 skill 中文清单
- skill 中文目录
- 整理我本地所有 skills / 本地 skills 整理
- skills 清单
- skill-manager 生成目录
- 本地有哪些 skill

## 扫描范围

| 来源 | 路径 |
| --- | --- |
| Claude | `~/.claude/skills/*/SKILL.md` |
| Agents | `~/.agents/skills/*/SKILL.md` |
| Cursor | `~/.cursor/skills/*/SKILL.md` |
| Cursor 内置 | `~/.cursor/skills-cursor/*/SKILL.md`（默认包含） |
| Claude 插件缓存 | `~/.claude/plugins/cache/**/skills/*/SKILL.md` |

同名多处安装时会去重；主路径优先顺序大致为：Agents → Claude → Cursor → 插件缓存 → Cursor 内置。

## 工作方式

```
扫描脚本(catalog.py) → JSON 清单
        ↓
Agent 语义翻译 + 分类（见 references/categories.md）
        ↓
中文 Markdown 总表 →（可选）~/skill-catalog-zh.md
```

- **脚本只负责**：解析 frontmatter 的 `name` / `description`、去重、附带来源与路径
- **Agent 负责**：写 `description_zh`、按语义归类（不做英文关键词机械匹配）

## 目录结构

```
local-skills-catalog/
├── SKILL.md                 # Agent 执行说明（必读）
├── README.md                # 本文件
├── references/
│   └── categories.md        # 语义分类类目与中文写法
└── scripts/
    ├── catalog.py           # 只读扫描 / 去重
    └── install.sh           # 软链安装到本机 skill 目录
```

## 安装

在本仓库根目录执行：

```bash
bash scripts/install.sh
```

会把本目录软链到：

- `~/.agents/skills/local-skills-catalog`
- `~/.claude/skills/local-skills-catalog`
- `~/.cursor/skills/local-skills-catalog`

若目标已是真实目录（非软链），会跳过以免覆盖。

依赖：`python3`；有 `PyYAML` 时解析更稳，没有则用内置简易 frontmatter 解析。

## 单独跑扫描脚本

```bash
# JSON（给 Agent 用）
python3 scripts/catalog.py --format json

# Markdown 骨架（无中文分类，仅清单）
python3 scripts/catalog.py --format md

# 跳过 Cursor 内置
python3 scripts/catalog.py --no-builtin --format json

# 跳过 ~/.cursor/skills
python3 scripts/catalog.py --no-cursor --format json

# 关键词过滤
python3 scripts/catalog.py --query pdf --format json

# 写出原始 JSON
python3 scripts/catalog.py --format json --out /tmp/skills.json
```

## 分类类目

详见 [references/categories.md](references/categories.md)，包括：文档办公、设计创意、图表可视化、浏览器与测试、内容媒体、写作与沟通、开发工程、代码审查、Git 与协作流、调试排错、前端开发、后端 / DevOps、Prompt / 工作流、协作知识、技能元工具、Cursor / IDE、其他工具。

## 硬约束摘要

1. 只读 `SKILL.md`，禁止改源文件  
2. 损坏或无 YAML frontmatter 的文件跳过，并在结果末尾说明跳过数量  
3. 无 `description` 时中文栏标 **【无描述】**  
4. 中文说明避免机翻腔；专有名词可保留英文（PDF、MCP、PPT、OCR、PR 等）  
5. 分类看 description **语义**，不看英文关键词是否命中  

## 职责边界

| 做 | 不做 |
| --- | --- |
| 扫描、翻译、分类、目录展示 | 安装 / 卸载 / 发布技能 |
| 可选写出 `~/skill-catalog-zh.md` | 修改任何已安装 skill 的源文件 |
