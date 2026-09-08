# -*- coding: utf-8 -*-
"""
HTML Documentation Generator for KAT9I_OS (Single Source of Truth)
Issues #2, #6, #15, #36, #55.

Generates responsive, interactive index.html directly from canonical Markdown
files in docs/ (docs/tz, docs/architecture, docs/spec, docs/guides, docs/GLOSSARY.md).
"""

import os
import sys
import re
import html
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def format_inline_markdown(text: str) -> str:
    """Форматирует ссылки, жирный шрифт, курсив и код внутри инлайнового текста."""
    # Сохраняем ссылки [text](url)
    def replace_link(m):
        link_text = m.group(1)
        url = m.group(2)
        return f'<a href="{url}">{link_text}</a>'

    # Регулярка для ссылок: [текст](url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', replace_link, text)
    # Жирный шрифт
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Код
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def markdown_to_html_enhanced(text: str) -> str:
    """
    Полноценный конвертер Markdown -> HTML.
    Поддерживает:
    - Заголовки с ID и якорями (#, ##, ###, ####)
    - Блоки кода с подсветкой синтаксиса (```lang ... ```)
    - Маркированные и нумерованные списки
    - Таблицы Markdown (| col | col |)
    - GitHub-стиль блоков цитат и заметок (> [!NOTE], > [!IMPORTANT] и обычные >)
    - Исходные теги <details> и <summary>
    - Разметку уровней подробности (Очень просто, Просто, Рабочий, Технический, Максимум)
    """
    lines = text.splitlines()
    output = []
    in_code_block = False
    code_lang = ""
    code_lines = []
    in_list = False
    list_type = "ul"
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Блоки кода
        if stripped.startswith("```"):
            if in_code_block:
                escaped_code = html.escape("\n".join(code_lines))
                output.append(f'<pre><code class="language-{code_lang}">{escaped_code}</code></pre>')
                in_code_block = False
                code_lines = []
            else:
                if in_list:
                    output.append(f"</{list_type}>")
                    in_list = False
                in_code_block = True
                code_lang = stripped[3:].strip()
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Таблицы Markdown
        if stripped.startswith("|") and stripped.endswith("|") and i + 1 < len(lines):
            next_stripped = lines[i + 1].strip()
            if next_stripped.startswith("|") and re.match(r'^\|[\s\-:|]+\|$', next_stripped):
                if in_list:
                    output.append(f"</{list_type}>")
                    in_list = False

                # Считываем заголовок таблицы
                headers = [c.strip() for c in stripped.strip("|").split("|")]
                table_html = ['<div class="table-container"><table class="doc-table"><thead><tr>']
                for h in headers:
                    table_html.append(f'<th>{format_inline_markdown(html.escape(h))}</th>')
                table_html.append('</tr></thead><tbody>')

                i += 2  # Пропускаем строку-разделитель

                while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    row_cells = [c.strip() for c in lines[i].strip("|").split("|")]
                    table_html.append('<tr>')
                    for c in row_cells:
                        table_html.append(f'<td>{format_inline_markdown(html.escape(c))}</td>')
                    table_html.append('</tr>')
                    i += 1

                table_html.append('</tbody></table></div>')
                output.append("".join(table_html))
                continue

        # Теги <details>, <summary>, </details>
        if stripped.startswith("<details") or stripped.startswith("</details>") or stripped.startswith("<summary") or stripped.startswith("</summary>"):
            if in_list:
                output.append(f"</{list_type}>")
                in_list = False
            output.append(line)
            i += 1
            continue

        # Маркированные списки
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list or list_type != "ul":
                if in_list:
                    output.append(f"</{list_type}>")
                output.append("<ul>")
                in_list = True
                list_type = "ul"
            item_text = html.escape(stripped[2:])
            formatted_item = format_inline_markdown(item_text)

            # Определение уровня подробности для элементов списков
            level_attr = ""
            if "Очень просто:" in item_text:
                level_attr = ' data-detail-level="simple"'
            elif "Просто:" in item_text:
                level_attr = ' data-detail-level="basic"'
            elif "Рабочий уровень:" in item_text or "Рабочее объяснение:" in item_text:
                level_attr = ' data-detail-level="worker"'
            elif "Технический уровень:" in item_text or "Технически:" in item_text:
                level_attr = ' data-detail-level="tech"'
            elif "Максимум:" in item_text or "Крайние случаи:" in item_text:
                level_attr = ' data-detail-level="all"'

            output.append(f'<li{level_attr}>{formatted_item}</li>')
            i += 1
            continue
        elif re.match(r'^\d+\.\s+', stripped):
            match = re.match(r'^\d+\.\s+', stripped)
            prefix_len = len(match.group(0))
            if not in_list or list_type != "ol":
                if in_list:
                    output.append(f"</{list_type}>")
                output.append("<ol>")
                in_list = True
                list_type = "ol"
            item_text = html.escape(stripped[prefix_len:])
            formatted_item = format_inline_markdown(item_text)
            output.append(f'<li>{formatted_item}</li>')
            i += 1
            continue
        else:
            if in_list:
                output.append(f"</{list_type}>")
                in_list = False

        if not stripped:
            i += 1
            continue

        # Заголовки
        if stripped.startswith("#### "):
            h_text = html.escape(stripped[5:])
            h_id = re.sub(r'[^a-zA-Z0-9_\u0400-\u04FF]+', '-', h_text.lower()).strip('-')
            output.append(f'<h4 id="{h_id}">{format_inline_markdown(h_text)}</h4>')
        elif stripped.startswith("### "):
            h_text = html.escape(stripped[4:])
            h_id = re.sub(r'[^a-zA-Z0-9_\u0400-\u04FF]+', '-', h_text.lower()).strip('-')
            output.append(f'<h3 id="{h_id}">{format_inline_markdown(h_text)}</h3>')
        elif stripped.startswith("## "):
            h_text = html.escape(stripped[3:])
            h_id = re.sub(r'[^a-zA-Z0-9_\u0400-\u04FF]+', '-', h_text.lower()).strip('-')
            output.append(f'<h2 id="{h_id}">{format_inline_markdown(h_text)}</h2>')
        elif stripped.startswith("# "):
            h_text = html.escape(stripped[2:])
            h_id = re.sub(r'[^a-zA-Z0-9_\u0400-\u04FF]+', '-', h_text.lower()).strip('-')
            output.append(f'<h1 id="{h_id}">{format_inline_markdown(h_text)}</h1>')
        elif stripped.startswith("> "):
            b_text = html.escape(stripped[2:])
            b_formatted = format_inline_markdown(b_text)
            alert_class = "note"
            alert_title = "Примечание"
            if "[!IMPORTANT]" in b_text:
                alert_class = "alert-important"
                alert_title = "Важно"
                b_formatted = b_formatted.replace("[!IMPORTANT]", "").strip()
            elif "[!WARNING]" in b_text or "[!CAUTION]" in b_text:
                alert_class = "alert-warning"
                alert_title = "Внимание"
                b_formatted = b_formatted.replace("[!WARNING]", "").replace("[!CAUTION]", "").strip()
            elif "[!TIP]" in b_text:
                alert_class = "alert-tip"
                alert_title = "Совет"
                b_formatted = b_formatted.replace("[!TIP]", "").strip()

            output.append(f'<div class="{alert_class}"><strong>{alert_title}:</strong> {b_formatted}</div>')
        elif stripped == "---":
            output.append("<hr>")
        else:
            p_text = html.escape(stripped)
            formatted_p = format_inline_markdown(p_text)

            level_attr = ""
            if formatted_p.startswith("<strong>Очень просто:</strong>"):
                level_attr = ' data-detail-level="simple"'
            elif formatted_p.startswith("<strong>Просто:</strong>"):
                level_attr = ' data-detail-level="basic"'
            elif formatted_p.startswith("<strong>Рабочее объяснение:</strong>") or formatted_p.startswith("<strong>Рабочий уровень:</strong>"):
                level_attr = ' data-detail-level="worker"'
            elif formatted_p.startswith("<strong>Технически:</strong>") or formatted_p.startswith("<strong>Технический уровень:</strong>"):
                level_attr = ' data-detail-level="tech"'
            elif formatted_p.startswith("<strong>Максимум:</strong>") or formatted_p.startswith("<strong>Крайние случаи:</strong>"):
                level_attr = ' data-detail-level="all"'

            output.append(f'<p{level_attr}>{formatted_p}</p>')

        i += 1

    if in_list:
        output.append(f"</{list_type}>")

    return "\n".join(output)


def build_html_documentation():
    docs_dir = REPO_ROOT / "docs"
    tz_dir = docs_dir / "tz"
    arch_dir = docs_dir / "architecture"
    spec_dir = docs_dir / "spec"
    guides_dir = docs_dir / "guides"

    glossary_path = docs_dir / "GLOSSARY.md"
    first_time_path = guides_dir / "FIRST_TIME_GUIDE.md"
    coworker_path = guides_dir / "GITHUB_FOR_COWORKERS.md"
    mapping_path = guides_dir / "GITHUB_KAT9I_MAPPING.md"
    responsibility_path = arch_dir / "MODULE_RESPONSIBILITY_MAP.md"

    sections = []

    # 1. ТЗ (docs/tz/*.md)
    if tz_dir.exists():
        for f in sorted(tz_dir.glob("*.md"), key=lambda p: p.name):
            content = f.read_text(encoding="utf-8")
            sections.append({
                "id": f"tz-{f.stem.lower()}",
                "title": f"ТЗ: {f.stem}",
                "badge": "Принятое ТЗ",
                "level": "basic",
                "html": markdown_to_html_enhanced(content)
            })

    # 2. Спецификации (docs/spec/*.md) — устраняет выпадение спецификаций (#36, #55)
    if spec_dir.exists():
        for f in sorted(spec_dir.glob("*.md"), key=lambda p: p.name):
            content = f.read_text(encoding="utf-8")
            sections.append({
                "id": f"spec-{f.stem.lower()}",
                "title": f"Спецификация: {f.stem}",
                "badge": "Каноническая спецификация",
                "level": "tech",
                "html": markdown_to_html_enhanced(content)
            })

    # 3. Архитектура (все разделы docs/architecture/*.md кроме навигационной карты)
    if arch_dir.exists():
        for f in sorted(arch_dir.glob("*.md"), key=lambda p: p.name):
            if f.name == "MODULE_RESPONSIBILITY_MAP.md":
                continue
            content = f.read_text(encoding="utf-8")
            sections.append({
                "id": f"arch-{f.stem.lower()}",
                "title": f"Архитектура: {f.stem}",
                "badge": "Каноническая архитектура",
                "level": "all",
                "html": markdown_to_html_enhanced(content)
            })

    # 4. Руководства (остальные руководства из docs/guides/*.md)
    if guides_dir.exists():
        for f in sorted(guides_dir.glob("*.md"), key=lambda p: p.name):
            if f.name in ["FIRST_TIME_GUIDE.md", "GITHUB_FOR_COWORKERS.md", "GITHUB_KAT9I_MAPPING.md"]:
                continue
            content = f.read_text(encoding="utf-8")
            sections.append({
                "id": f"guide-{f.stem.lower()}",
                "title": f"Руководство: {f.stem}",
                "badge": "Руководство коворкера",
                "level": "worker",
                "html": markdown_to_html_enhanced(content)
            })

    first_time_content = first_time_path.read_text(encoding="utf-8") if first_time_path.exists() else ""
    coworker_content = coworker_path.read_text(encoding="utf-8") if coworker_path.exists() else ""
    mapping_content = mapping_path.read_text(encoding="utf-8") if mapping_path.exists() else ""
    glossary_content = glossary_path.read_text(encoding="utf-8") if glossary_path.exists() else ""
    resp_content = responsibility_path.read_text(encoding="utf-8") if responsibility_path.exists() else ""

    sections_html = []
    nav_links = []

    for s in sections:
        nav_links.append(f'<a href="#{s["id"]}" data-target-id="{s["id"]}">{s["title"]}</a>')
        sections_html.append(f"""
    <section id="{s['id']}" data-section-level="{s.get('level', 'all')}">
      <div class="badge">{s['badge']}</div>
      {s['html']}
    </section>
        """)

    all_sections_rendered = "\n".join(sections_html)
    all_nav_rendered = "\n".join(nav_links)

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
    h1, h2, h3, h4 {{ color: #0284c7; scroll-margin-top: 80px; }}
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
      scroll-margin-top: 80px;
    }}
    pre {{
      background: #0f172a;
      color: #f8fafc;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
    }}
    code {{ font-family: Consolas, monospace; background: #e2e8f0; padding: 2px 4px; border-radius: 4px; }}
    pre code {{ background: transparent; padding: 0; }}
    .note {{
      background: #eff6ff;
      border-left: 4px solid var(--primary);
      padding: 12px 16px;
      border-radius: 4px;
      margin: 12px 0;
    }}
    .alert-important {{
      background: #fef2f2;
      border-left: 4px solid #ef4444;
      padding: 12px 16px;
      border-radius: 4px;
      margin: 12px 0;
    }}
    .alert-warning {{
      background: #fffbeb;
      border-left: 4px solid #f59e0b;
      padding: 12px 16px;
      border-radius: 4px;
      margin: 12px 0;
    }}
    .alert-tip {{
      background: #f0fdf4;
      border-left: 4px solid #10b981;
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
    .table-container {{
      overflow-x: auto;
      margin: 16px 0;
    }}
    table.doc-table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }}
    table.doc-table th, table.doc-table td {{
      border: 1px solid var(--border);
      padding: 8px 12px;
    }}
    table.doc-table th {{
      background: #f1f5f9;
      font-weight: 600;
    }}
    nav.quick-nav {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    nav.quick-nav a {{
      color: var(--primary);
      text-decoration: none;
      font-size: 13px;
      background: #eff6ff;
      padding: 4px 8px;
      border-radius: 6px;
    }}
    nav.quick-nav a:hover {{
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <header>
    <h1>KAT9I_OS — Техническое задание и каноническая архитектура</h1>
    <p><strong>Язык проекта:</strong> русский. Источник истины: <code>docs/</code>. Сгенерировано автоматически (Issue #2, #6, #15, #36, #55).</p>
  </header>

  <div class="controls">
    <div class="control-group">
      <label for="detailLevel"><strong>Уровень подробности:</strong></label>
      <select id="detailLevel" onchange="updateDetailLevel()">
        <option value="all">5. Максимум (всё ТЗ, архитектура и крайние случаи)</option>
        <option value="tech">4. Технический (контракты, состояния, инварианты)</option>
        <option value="worker">3. Рабочий (правила и интерфейсы коворкера)</option>
        <option value="basic">2. Просто (что это такое и зачем нужно)</option>
        <option value="simple">1. Очень просто (детское/вводное объяснение)</option>
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

  <nav class="quick-nav">
    <strong>Быстрая навигация:</strong>
    <a href="#coworker-section" data-target-id="coworker-section">Коворкерам</a>
    <a href="#mapping-section" data-target-id="mapping-section">Карта терминов</a>
    <a href="#resp-section" data-target-id="resp-section">Карта ответственности</a>
    <a href="#glossary-section" data-target-id="glossary-section">Словарь</a>
    {all_nav_rendered}
  </nav>

  <div id="firstTimeSection" style="display:none;">
    <section data-section-level="simple">
      <div class="badge">Режим новичка</div>
      {markdown_to_html_enhanced(first_time_content)}
    </section>
  </div>

  <main id="mainContent">
    <section id="coworker-section" data-section-level="worker">
      <div class="badge">Обучение коворкеров</div>
      {markdown_to_html_enhanced(coworker_content)}
    </section>

    <section id="mapping-section" data-section-level="worker">
      <div class="badge">Карта соответствия</div>
      {markdown_to_html_enhanced(mapping_content)}
    </section>

    <section id="resp-section" data-section-level="worker">
      <div class="badge">Карта ответственности</div>
      {markdown_to_html_enhanced(resp_content)}
    </section>

    <section id="glossary-section" data-section-level="simple">
      <div class="badge">Канонический словарь</div>
      {markdown_to_html_enhanced(glossary_content)}
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

      // Иерархия уровней: simple (1) -> basic (2) -> worker (3) -> tech (4) -> all (5)
      const levelRank = {{
        'simple': 1,
        'basic': 2,
        'worker': 3,
        'tech': 4,
        'all': 5
      }};

      const currentRank = levelRank[level] || 5;

      // 1. Фильтрация секций по data-section-level
      const sections = document.querySelectorAll('section[data-section-level]');
      sections.forEach(sec => {{
        const secLevel = sec.getAttribute('data-section-level');
        const secRank = levelRank[secLevel] || 5;
        const isVisible = (secRank <= currentRank);
        sec.style.display = isVisible ? '' : 'none';

        const secId = sec.getAttribute('id');
        if (secId) {{
          const navLink = document.querySelector(`nav.quick-nav a[data-target-id="${{secId}}"]`);
          if (navLink) {{
            navLink.style.display = isVisible ? '' : 'none';
          }}
        }}
      }});

      // 2. Внутрисекционная фильтрация по data-detail-level
      const elementsWithLevel = document.querySelectorAll('[data-detail-level]');
      elementsWithLevel.forEach(el => {{
        const elLevel = el.getAttribute('data-detail-level');
        const elRank = levelRank[elLevel] || 5;

        if (level === 'simple') {{
          el.style.display = (elLevel === 'simple') ? '' : 'none';
        }} else if (level === 'basic') {{
          el.style.display = (elRank <= 2) ? '' : 'none';
        }} else if (level === 'worker') {{
          el.style.display = (elRank <= 3) ? '' : 'none';
        }} else if (level === 'tech') {{
          el.style.display = (elRank <= 4) ? '' : 'none';
        }} else {{
          el.style.display = '';
        }}
      }});
    }}
  </script>
</body>
</html>
"""
    output_path = REPO_ROOT / "index.html"
    normalized_html = html_template.replace("\r\n", "\n")
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(normalized_html)
    print(f"HTML-документация успешно сгенерирована в {output_path} ({len(normalized_html)} байт)")

if __name__ == "__main__":
    build_html_documentation()