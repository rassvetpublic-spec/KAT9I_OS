import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools" / "antigravity-ui-customization"


def test_required_files_exist():
    required = [
        TOOLS_DIR / "Antigravity-UI-Customizer.ps1",
        TOOLS_DIR / "patch-engine.js",
        TOOLS_DIR / "context-menu.js",
        TOOLS_DIR / "context-menu.css",
        TOOLS_DIR / "context-menu-config.json",
        TOOLS_DIR / "README.md",
    ]
    for p in required:
        assert p.exists(), f"Missing required file: {p}"


def test_config_structure_and_skills():
    config_path = TOOLS_DIR / "context-menu-config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "skills" in data
    assert isinstance(data["skills"], list)
    assert len(data["skills"]) >= 5

    commands = [s["command"] for s in data["skills"]]
    assert "/interview-me" in commands
    assert "/agy-customizations" in commands
    assert "/antigravity-guide" in commands
    assert "/grill-me" in commands


def test_javascript_syntax_and_symbols():
    js_path = TOOLS_DIR / "context-menu.js"
    res = subprocess.run(["node", "-c", str(js_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax error in {js_path}: {res.stderr}"

    content = js_path.read_text(encoding="utf-8")
    assert "__agy_context_menu_installed" in content
    assert "findChatInput" in content
    assert "insertTextIntoChat" in content
    assert "renderSkillsSubmenu" in content
    assert "createSettingsModalDOM" in content


def test_readme_integration():
    readme_path = ROOT / "README.md"
    readme_content = readme_path.read_text(encoding="utf-8")
    assert "tools/antigravity-ui-customization/README.md" in readme_content
    assert "Antigravity Standalone" in readme_content
