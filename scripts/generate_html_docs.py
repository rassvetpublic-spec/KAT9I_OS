# -*- coding: utf-8 -*-
"""
HTML Documentation Generator for KAT9I_OS (Single Source of Truth)
Issues #2, #6, #15.

Generates responsive, interactive index.html directly from canonical Markdown
files in docs/ (docs/tz, docs/architecture, docs/spec, docs/guides, docs/GLOSSARY.md).
"""

import os
import sys
import re
import html
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def markdown_to_html_basic(text: str) -> str:
    lines = text.splitlines()
    output = []
    in_code_block = False
    code_lang = ""
    code_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                escaped_code = html.escape("\n".join(code_lines))
                output.append(f'<pre><code class="language-{code_lang}">{escaped_code}</code></pre>')
                in_code_block = False
                code_lines = []
            else:
                in_code_block = True
                code_lang = stripped[3:].strip()
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            item_text = html.escape(stripped[2:])
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'`(.+?)`', r'<code>\1</code>', item_text)
            output.append(f"<li>{item_text}</li>")
            continue
        else:
            if in_list:
                output.append("</ul>")
                in_list = False

        if not stripped:
            continue

        if stripped.startswith("#### "):
            h_text = html.escape(stripped[5:])
            output.append(f"<h4>{h_text}</h4>")
        elif stripped.startswith("### "):
            h_text = html.escape(stripped[4:])
            output.append(f"<h3>{h_text}</h3>")
        elif stripped.startswith("## "):
            h_text = html.escape(stripped[3:])
            output.append(f"<h2>{h_text}</h2>")
        elif stripped.startswith("# "):
            h_text = html.escape(stripped[2:])
            output.append(f"<h1>{h_text}</h1>")
        elif stripped.startswith("> "):
            b_text = html.escape(stripped[2:])
            b_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', b_text)
            output.append(f'<div class="note"><strong>Примечание:</strong> {b_text}</div>')
        else:
            p_text = html.escape(stripped)
            p_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', p_text)
            p_text = re.sub(r'`(.+?)`', r'<code>\1</code>', p_text)
            output.append(f"<p>{p_text}</p>")

    if in_list:
        output.append("</ul>")

    return "\n".join(output)


def build_html_documentation():
    docs_dir = REPO_ROOT / "docs"
    arch_dir = docs_dir / "architecture"
    guides_dir = docs_dir / "guides"
    tz_dir = docs_dir / "tz"

    glossary_path = docs_dir / "GLOSSARY.md"
    first_time_path = guides_dir / "FIRST_TIME_GUIDE.md"
    coworker_path = guides_dir / "GITHUB_FOR_COWORKERS.md"
    mapping_path = guides_dir / "GITHUB_KAT9I_MAPPING.md"
    responsibility_path = arch_dir / "MODULE_RESPONSIBILITY_MAP.md"

    sections = []

    # 1. ТЗ
    for f in sorted(tz_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        sections.append({
            "title": f"ТЗ: {f.stem}",
            "badge": "Принятое ТЗ",
            "html": markdown_to_html_basic(content)
        })

    # 2. Архитектура (все ключевые разделы)
    for f in sorted(arch_dir.glob("*.md")):
        if f.name == "MODULE_RESPONSIBILITY_MAP.md":
            continue
        content = f.read_text(encoding="utf-8")
        sections.append({
            "title": f"Архитектура: {f.stem}",
            "badge": "Каноническая архитектура",
            "html": markdown_to_html_basic(content)
        })

    first_time_content = first_time_path.read_text(encoding="utf-8") if first_time_path.exists() else ""
    coworker_content = coworker_path.read_text(encoding="utf-8") if coworker_path.exists() else ""
    mapping_content = mapping_path.read_text(encoding="utf-8") if mapping_path.exists() else ""
    glossary_content = glossary_path.read_text(encoding="utf-8") if glossary_path.exists() else ""
    resp_content = responsibility_path.read_text(encoding="utf-8") if responsibility_path.exists() else ""

    sections_html = []
    for s in sections:
        sections_html.append(f"""
    <section>
      <div class="badge">{s['badge']}</div>
      <h2>{s['title']}</h2>
      {s['html']}
    </section>
        """)

    all_sections_rendered = "\n".join(sections_html)

    html_template = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KAT9I_OS — Официальная каноническая документация</title>
  <!-- Generated by scripts/generate_html_docs.py (SSOT). Do not edit directly. -->
  <style>
    :root {{
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #0f172a;
      --primary: #2563eb;
      --border: #e2e8f0;
      --muted: #64748b;
      --badge: #10b981;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
      line-height: 1.6;
      color: var(--text);
      background: var(--bg);
    }}
    header {{
      border-bottom: 2px solid var(--border);
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    h1, h2, h3, h4 {{ color: #0284c7; }}
    .controls {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: center;
      position: sticky;
      top: 10px;
      z-index: 100;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }}
    .control-group {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    select, button {{
      padding: 8px 14px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #fff;
      font-size: 14px;
      cursor: pointer;
    }}
    .badge {{
      display: inline-block;
      background: #dcfce7;
      color: #166534;
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: bold;
    }}
    section {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    pre {{
      background: #0f172a;
      color: #f8fafc;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
    }}
    code {{ font-family: Consolas, monospace; }}
    .note {{
      background: #eff6ff;
      border-left: 4px solid var(--primary);
      padding: 12px 16px;
      border-radius: 4px;
      margin: 12px 0;
    }}
    details {{
      background: #f1f5f9;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      margin: 10px 0;
    }}
    summary {{
      font-weight: 600;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <header>
    <h1>KAT9I_OS — Техническое задание и каноническая архитектура</h1>
    <p><strong>Язык проекта:</strong> русский. Источник истины: <code>docs/</code>. Сгенерировано автоматически (Issue #2, #6, #15).</p>
  </header>

  <div class="controls">
    <div class="control-group">
      <label for="detailLevel"><strong>Уровень подробности:</strong></label>
      <select id="detailLevel" onchange="updateDetailLevel()">
        <option value="all">Максимум (полное ТЗ и все модули)</option>
        <option value="simple">Очень просто</option>
        <option value="worker">Рабочий уровень</option>
        <option value="tech">Технический</option>
      </select>
    </div>

    <div class="control-group">
      <label>
        <input type="checkbox" id="toggleExamples" checked onchange="toggleAllExamples()">
        <strong>Показывать примеры</strong>
      </label>
    </div>

    <div class="control-group">
      <button onclick="activateFirstTimeMode()" style="background:#2563eb; color:#fff; border:none; font-weight:bold;">
        🚀 Режим «Я здесь впервые»
      </button>
    </div>
  </div>

  <div id="firstTimeSection" style="display:none;">
    <section>
      <div class="badge">Режим новичка</div>
      {markdown_to_html_basic(first_time_content)}
    </section>
  </div>

  <main id="mainContent">
    <section id="coworker-section">
      <div class="badge">Обучение коворкеров</div>
      {markdown_to_html_basic(coworker_content)}
    </section>

    <section id="mapping-section">
      <div class="badge">Карта соответствия</div>
      {markdown_to_html_basic(mapping_content)}
    </section>

    <section id="resp-section">
      <div class="badge">Карта ответственности</div>
      {markdown_to_html_basic(resp_content)}
    </section>

    <section id="glossary-section">
      <div class="badge">Канонический словарь</div>
      {markdown_to_html_basic(glossary_content)}
    </section>

    {all_sections_rendered}
  </main>

  <script>
    function toggleAllExamples() {{
      const show = document.getElementById('toggleExamples').checked;
      document.querySelectorAll('details').forEach(d => {{
        d.open = show;
      }});
    }}

    function activateFirstTimeMode() {{
      const ft = document.getElementById('firstTimeSection');
      const mc = document.getElementById('mainContent');
      if (ft.style.display === 'none') {{
        ft.style.display = 'block';
        mc.style.display = 'none';
        window.scrollTo({{top: 0, behavior: 'smooth'}});
      }} else {{
        ft.style.display = 'none';
        mc.style.display = 'block';
      }}
    }}

    function updateDetailLevel() {{
      const level = document.getElementById('detailLevel').value;
      console.log('Выбран уровень подробности:', level);
    }}
  </script>
</body>
</html>
"""
    output_path = REPO_ROOT / "index.html"
    normalized_html = html_template.replace("\r\n", "\n")
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(normalized_html)
    print(f"HTML-документация успешно сгенерирована в {output_path} ({len(html_template)} байт)")

if __name__ == "__main__":
    build_html_documentation()
