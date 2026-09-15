import os
import ast
import re
from pathlib import Path

SCRIPTS_DIR = Path(r"C:\GIT\KAT9I_OS\scripts")
CATALOG_FILE = SCRIPTS_DIR / "CATALOG.md"

def extract_python_doc(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Попытка достать docstring через ast
        module = ast.parse(content)
        doc = ast.get_docstring(module)
        if doc:
            return doc.strip().split('\n')[0] # Берем первую строку
            
        # Если нет docstring, ищем первые комментарии
        lines = content.split('\n')
        comments = []
        for line in lines:
            if line.strip().startswith('#') and not line.strip().startswith('#!'):
                comments.append(line.strip().lstrip('#').strip())
            elif line.strip():
                break
        if comments:
            return " ".join(comments[:2]) # Берем первые две строки комментариев
            
    except Exception:
        pass
    return "_Описание отсутствует_"

def extract_ps1_doc(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Ищем блок <# ... #>
        match = re.search(r'<#\s*(.*?)\s*#>', content, re.DOTALL)
        if match:
            doc = match.group(1).strip()
            # Убираем синтаксис PowerShell справки вроде .SYNOPSIS
            doc = re.sub(r'\.(SYNOPSIS|DESCRIPTION)', '', doc).strip()
            return doc.split('\n')[0]
            
        # Ищем первые комментарии
        lines = content.split('\n')
        comments = []
        for line in lines:
            if line.strip().startswith('#'):
                comments.append(line.strip().lstrip('#').strip())
            elif line.strip():
                break
        if comments:
            return " ".join(comments[:2])
    except Exception:
        pass
    return "_Описание отсутствует_"

def generate_catalog():
    documented_lines = [
        "## ✅ Оформленные скрипты",
        "",
        "| Имя файла | Тип | Описание |",
        "|---|---|---|"
    ]
    
    undocumented_lines = [
        "## ⚠️ Проверить новое (требуется описание)",
        "> *Эти скрипты были созданы недавно и пока не имеют `docstring`. Пожалуйста, добавьте описание в первую строку файла.*",
        "",
        "| Имя файла | Тип |",
        "|---|---|"
    ]
    
    files = list(SCRIPTS_DIR.glob("*.*"))
    files.sort(key=lambda x: x.name.lower())
    
    has_undocumented = False
    
    for f in files:
        if f.name == "CATALOG.md" or f.name == "generate_catalog.py":
            continue
            
        desc = "_Описание отсутствует_"
        type_str = ""
        
        if f.suffix == '.py':
            desc = extract_python_doc(f)
            type_str = "🐍 Python"
        elif f.suffix == '.ps1':
            desc = extract_ps1_doc(f)
            type_str = "⚙️ PowerShell"
        else:
            continue
            
        if desc == "_Описание отсутствует_":
            has_undocumented = True
            undocumented_lines.append(f"| `{f.name}` | {type_str} |")
        else:
            documented_lines.append(f"| `{f.name}` | {type_str} | {desc} |")

    catalog_lines = [
        "# 📚 Каталог скриптов (Script Registry)",
        "> *Этот файл генерируется автоматически скриптом `generate_catalog.py`*",
        ""
    ]
    
    if has_undocumented:
        catalog_lines.extend(undocumented_lines)
        catalog_lines.append("")
        
    catalog_lines.extend(documented_lines)

    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(catalog_lines))
        
    print(f"Каталог успешно сгенерирован: {CATALOG_FILE}")

if __name__ == "__main__":
    generate_catalog()
