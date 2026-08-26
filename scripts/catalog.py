#!/usr/bin/env python3
"""Scan local Agent Skills directories and emit a deduplicated inventory (no classification)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

HOME = Path.home()

DEFAULT_SOURCES: list[dict[str, str]] = [
    {
        "id": "claude",
        "label": "Claude Skills",
        "root": str(HOME / ".claude" / "skills"),
        "mode": "direct",
    },
    {
        "id": "agents",
        "label": "Agents Skills",
        "root": str(HOME / ".agents" / "skills"),
        "mode": "direct",
    },
    {
        "id": "cursor",
        "label": "Cursor Skills",
        "root": str(HOME / ".cursor" / "skills"),
        "mode": "direct",
    },
    {
        "id": "claude-plugin-cache",
        "label": "Claude 插件缓存",
        "root": str(HOME / ".claude" / "plugins" / "cache"),
        "mode": "plugin_cache",
    },
    {
        "id": "cursor-builtin",
        "label": "Cursor 内置",
        "root": str(HOME / ".cursor" / "skills-cursor"),
        "mode": "direct",
        "builtin": "true",
    },
]

# Lower = preferred when deduplicating the same skill name.
SOURCE_PRIORITY = {
    "agents": 0,
    "claude": 1,
    "cursor": 2,
    "claude-plugin-cache": 3,
    "cursor-builtin": 4,
}

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass
class SkillRecord:
    name: str
    folder_name: str
    description: str
    path: str
    source_id: str
    source_label: str
    builtin: bool = False
    display_name: str = ""
    version: str = ""
    triggers: list[str] = field(default_factory=list)
    mtime: float = 0.0
    plugin_package: str = ""
    plugin_hash: str = ""
    all_locations: list[dict[str, str]] = field(default_factory=list)

    def to_public(self) -> dict[str, Any]:
        data = asdict(self)
        data["mtime_iso"] = (
            datetime.fromtimestamp(self.mtime, tz=timezone.utc).isoformat()
            if self.mtime
            else ""
        )
        # Placeholders for the agent to fill (semantic classify + translate).
        data["category"] = ""
        data["description_zh"] = ""
        return data


def parse_frontmatter(text: str) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    raw = match.group(1)
    if yaml is not None:
        try:
            data = yaml.safe_load(raw) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            pass
    result: dict[str, Any] = {}
    name_m = re.search(r"^name:\s*[\"']?([^\"'\n]+)[\"']?\s*$", raw, re.M)
    if name_m:
        result["name"] = name_m.group(1).strip()
    desc_block = re.search(
        r"^description:\s*\|\s*\n((?:[ \t]+.*\n?)*)",
        raw,
        re.M,
    )
    if desc_block:
        lines = [ln.strip() for ln in desc_block.group(1).splitlines() if ln.strip()]
        result["description"] = " ".join(lines)
    else:
        desc_m = re.search(r"^description:\s*[\"']?(.*?)[\"']?\s*$", raw, re.M)
        if desc_m:
            result["description"] = desc_m.group(1).strip()
    return result


def extract_triggers(meta: dict[str, Any], description: str) -> list[str]:
    triggers: list[str] = []
    raw = meta.get("trigger") or meta.get("triggers")
    if isinstance(raw, list):
        triggers.extend(str(x).strip() for x in raw if str(x).strip())
    elif isinstance(raw, str) and raw.strip():
        triggers.append(raw.strip())

    # Common pattern in descriptions: 触发词：a、b、c
    m = re.search(
        r"(?:触发词|触发语|Triggers?)[:：]\s*(.+?)(?:\n|$)",
        description,
        re.I,
    )
    if m:
        chunk = m.group(1)
        parts = re.split(r"[,，、;/|]|或", chunk)
        for p in parts:
            p = p.strip(" `\"'")
            if p and len(p) <= 40:
                triggers.append(p)

    # Dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in triggers:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out[:12]


def discover_direct(source: dict[str, str]) -> list[SkillRecord]:
    root = Path(source["root"]).expanduser()
    if not root.is_dir():
        return []
    return [load_skill(p, source) for p in sorted(root.glob("*/SKILL.md"))]


def discover_plugin_cache(source: dict[str, str]) -> list[SkillRecord]:
    root = Path(source["root"]).expanduser()
    if not root.is_dir():
        return []
    records: list[SkillRecord] = []
    for skill_md in sorted(root.glob("*/*/*/skills/*/SKILL.md")):
        if skill_md.parent.name in {"template", "_template"}:
            continue
        rec = load_skill(skill_md, source)
        parts = skill_md.parts
        try:
            cache_idx = parts.index("cache")
            rec.plugin_package = parts[cache_idx + 2]
            rec.plugin_hash = parts[cache_idx + 3]
        except (ValueError, IndexError):
            pass
        records.append(rec)
    return records


def load_skill(skill_md: Path, source: dict[str, str]) -> SkillRecord:
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    meta = parse_frontmatter(text)
    folder_name = skill_md.parent.name
    name = str(meta.get("name") or folder_name).strip() or folder_name

    description = ""
    for key in ("description", "summary", "summary_zh", "description_zh", "description_en"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            description = val.strip()
            break
    # Prefer explicit description field when present (even if other summaries exist).
    if isinstance(meta.get("description"), str) and meta["description"].strip():
        description = meta["description"].strip()

    display_name = str(
        meta.get("displayName") or meta.get("display_name") or name
    ).strip()
    version = str(meta.get("version") or "").strip()
    try:
        mtime = skill_md.stat().st_mtime
    except OSError:
        mtime = 0.0

    return SkillRecord(
        name=name,
        folder_name=folder_name,
        description=description,
        path=str(skill_md.resolve()),
        source_id=source["id"],
        source_label=source["label"],
        builtin=source.get("builtin") == "true",
        display_name=display_name,
        version=version,
        triggers=extract_triggers(meta, description),
        mtime=mtime,
    )


def source_rank(source_id: str) -> int:
    return SOURCE_PRIORITY.get(source_id, 50)


def dedupe(records: list[SkillRecord]) -> list[SkillRecord]:
    buckets: dict[str, list[SkillRecord]] = {}
    for rec in records:
        key = rec.name.strip().lower() or Path(rec.path).parent.name.lower()
        buckets.setdefault(key, []).append(rec)

    winners: list[SkillRecord] = []
    for group in buckets.values():
        group_sorted = sorted(
            group,
            key=lambda r: (source_rank(r.source_id), -r.mtime),
        )
        winner = group_sorted[0]
        if winner.source_id == "claude-plugin-cache":
            cache_only = [r for r in group if r.source_id == "claude-plugin-cache"]
            winner = max(cache_only, key=lambda r: r.mtime)

        seen_paths: set[str] = set()
        locations: list[dict[str, str]] = []
        for r in sorted(group, key=lambda x: (source_rank(x.source_id), -x.mtime)):
            if r.path in seen_paths:
                continue
            seen_paths.add(r.path)
            locations.append(
                {
                    "source_id": r.source_id,
                    "source_label": r.source_label,
                    "path": r.path,
                    "plugin_package": r.plugin_package,
                    "plugin_hash": r.plugin_hash,
                }
            )
        winner.all_locations = locations
        winners.append(winner)

    winners.sort(key=lambda r: r.name.lower())
    return winners


def scan(sources: list[dict[str, str]] | None = None) -> dict[str, Any]:
    sources = sources or DEFAULT_SOURCES
    raw: list[SkillRecord] = []
    source_stats: list[dict[str, Any]] = []
    for source in sources:
        if source.get("mode") == "plugin_cache":
            found = discover_plugin_cache(source)
        else:
            found = discover_direct(source)
        raw.extend(found)
        source_stats.append(
            {
                "id": source["id"],
                "label": source["label"],
                "root": str(Path(source["root"]).expanduser()),
                "exists": Path(source["root"]).expanduser().is_dir(),
                "count": len(found),
            }
        )
    skills = dedupe(raw)
    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total_raw": len(raw),
        "total_unique": len(skills),
        "sources": source_stats,
        "skills": [s.to_public() for s in skills],
        "note": (
            "category / description_zh 由 Agent 按语义填写；"
            "本脚本只扫描、解析、去重，不修改任何 SKILL.md。"
        ),
    }


def render_inventory_markdown(catalog: dict[str, Any]) -> str:
    """Raw inventory for debugging; final Chinese table is produced by the agent."""
    roots = "、".join(
        f"`{s['root']}`" for s in catalog["sources"] if s.get("exists")
    )
    lines = [
        "# 本地 Skill 扫描清单（原始）",
        "",
        f"> 扫描来源：{roots or '（无有效目录）'}",
        f"> 生成时间（UTC）：{catalog['generated_at']}",
        f"> 命中 {catalog['total_raw']} 个文件，去重后 {catalog['total_unique']} 个技能",
        "",
        "| 技能名称 | 原始描述 | 本地文件路径 | 来源 |",
        "|---|---|---|---|",
    ]
    for item in catalog["skills"]:
        desc = (item.get("description") or "").replace("\n", " ").replace("|", "\\|").strip()
        if len(desc) > 120:
            desc = desc[:117] + "..."
        if not desc:
            desc = "【无描述】"
        name = str(item["name"]).replace("|", "\\|")
        path = str(item["path"]).replace("|", "\\|")
        source = str(item["source_label"]).replace("|", "\\|")
        lines.append(f"| {name} | {desc} | `{path}` | {source} |")
    lines.append("")
    lines.append(
        "> 最终中文分类表由 Agent 语义翻译后输出，勿把本表当作最终交付物。"
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan local Agent Skills (read-only). Classification is done by the agent."
    )
    parser.add_argument(
        "--format",
        choices=("json", "md", "both"),
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Write output to file. For both, path without extension.",
    )
    parser.add_argument(
        "--no-builtin",
        action="store_true",
        help="Skip Cursor built-in skills (~/.cursor/skills-cursor). Included by default.",
    )
    parser.add_argument(
        "--include-builtin",
        action="store_true",
        help="Deprecated no-op: built-in skills are included by default.",
    )
    parser.add_argument(
        "--no-cursor",
        action="store_true",
        help="Skip ~/.cursor/skills.",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Filter by name/description substring (case-insensitive).",
    )
    args = parser.parse_args(argv)

    sources = []
    for src in DEFAULT_SOURCES:
        if src["id"] == "cursor-builtin" and args.no_builtin:
            continue
        if src["id"] == "cursor" and args.no_cursor:
            continue
        sources.append(src)

    catalog = scan(sources)

    if args.query:
        q = args.query.lower()
        filtered = [
            s
            for s in catalog["skills"]
            if q in s["name"].lower()
            or q in (s.get("description") or "").lower()
            or q in (s.get("display_name") or "").lower()
            or q in (s.get("folder_name") or "").lower()
        ]
        catalog["skills"] = filtered
        catalog["total_unique"] = len(filtered)

    out_json = json.dumps(catalog, ensure_ascii=False, indent=2)
    out_md = render_inventory_markdown(catalog)

    if args.out:
        out_path = Path(args.out).expanduser()
        if args.format == "json":
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(out_json + "\n", encoding="utf-8")
            print(str(out_path.resolve()), file=sys.stderr)
        elif args.format == "md":
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(out_md, encoding="utf-8")
            print(str(out_path.resolve()), file=sys.stderr)
        else:
            base = out_path
            if base.suffix in {".json", ".md"}:
                json_path = base.with_suffix(".json")
                md_path = base.with_suffix(".md")
            else:
                json_path = Path(str(base) + ".json")
                md_path = Path(str(base) + ".md")
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(out_json + "\n", encoding="utf-8")
            md_path.write_text(out_md, encoding="utf-8")
            print(str(json_path.resolve()), file=sys.stderr)
            print(str(md_path.resolve()), file=sys.stderr)
        return 0

    if args.format == "json":
        print(out_json)
    elif args.format == "md":
        print(out_md)
    else:
        print(out_json)
        print("\n---\n")
        print(out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
