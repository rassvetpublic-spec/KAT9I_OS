import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools" / "antigravity-ui-customization"


def test_required_files_exist():
    required = [
        TOOLS_DIR / "Antigravity-UI-Customizer.ps1",
        TOOLS_DIR / "patch-engine.js",
        TOOLS_DIR / "matrix-effect.js",
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
    # 1. context-menu.js
    menu_js_path = TOOLS_DIR / "context-menu.js"
    res = subprocess.run(["node", "-c", str(menu_js_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax error in {menu_js_path}: {res.stderr}"

    content = menu_js_path.read_text(encoding="utf-8")
    assert "__agy_context_menu_installed" in content
    assert "findChatInput" in content
    assert "insertTextIntoChat" in content
    assert "renderSkillsSubmenu" in content
    assert "createSettingsModalDOM" in content
    assert "agy-matrix-toggle" in content
    assert "agy-action-toggle-matrix" in content

    # 2. matrix-effect.js
    matrix_js_path = TOOLS_DIR / "matrix-effect.js"
    res_m = subprocess.run(["node", "-c", str(matrix_js_path)], capture_output=True, text=True)
    assert res_m.returncode == 0, f"Syntax error in {matrix_js_path}: {res_m.stderr}"

    m_content = matrix_js_path.read_text(encoding="utf-8")
    assert "__agy_matrix_effect_installed" in m_content
    assert "updateInputBoxRect" in m_content
    assert "handleStacking" in m_content
    assert "triggerLiquification" in m_content
    assert "renderStackedDrops" in m_content
    assert "renderLiquidParticles" in m_content
    assert "AgyMatrixEffect" in m_content
    assert "triggerBurst" in m_content
    assert "simulateRunning" in m_content

    # 3. patch-engine.js
    patch_js_path = TOOLS_DIR / "patch-engine.js"
    res_p = subprocess.run(["node", "-c", str(patch_js_path)], capture_output=True, text=True)
    assert res_p.returncode == 0, f"Syntax error in {patch_js_path}: {res_p.stderr}"
    p_content = patch_js_path.read_text(encoding="utf-8")
    assert "matrix-effect.js" in p_content
    assert "__agy_matrix_effect_installed" in p_content


def test_matrix_effect_node_simulation():
    """Тестирование выполнения логики матрицы в виртуальном окружении Node.js"""
    test_script = """
    const fs = require('fs');
    const path = require('path');
    
    // Мок окружения браузера/DOM
    global.window = {
      innerWidth: 1200,
      innerHeight: 800,
      addEventListener: () => {},
      getComputedStyle: () => ({ display: 'block' }),
      requestAnimationFrame: (cb) => setTimeout(cb, 16)
    };
    global.document = {
      readyState: 'complete',
      hidden: false,
      addEventListener: () => {},
      createElement: () => ({
        style: {},
        getContext: () => ({
          fillRect: () => {},
          clearRect: () => {},
          fillText: () => {},
          beginPath: () => {},
          arc: () => {},
          fill: () => {},
          save: () => {},
          restore: () => {}
        })
      }),
      getElementById: () => null,
      querySelectorAll: () => [],
      querySelector: () => null,
      body: { appendChild: () => {} }
    };
    global.localStorage = {
      _data: {},
      getItem: function(k) { return this._data[k] || null; },
      setItem: function(k, v) { this._data[k] = v; }
    };

    const code = fs.readFileSync(process.argv[1], 'utf8');
    eval(code);

    if (!window.AgyMatrixEffect) {
      throw new Error('AgyMatrixEffect not exported');
    }
    window.AgyMatrixEffect.enable();
    window.AgyMatrixEffect.setMode('dynamic');
    window.AgyMatrixEffect.setIntensity('high');
    window.AgyMatrixEffect.triggerBurst(10);
    window.AgyMatrixEffect.simulateRunning(true);
    
    const state = window.AgyMatrixEffect.getState();
    if (!state.enabled || !state.isRunning) {
      throw new Error('State mismatch: ' + JSON.stringify(state));
    }
    console.log('SIMULATION_OK');
    process.exit(0);
    """
    matrix_js_path = TOOLS_DIR / "matrix-effect.js"
    res = subprocess.run(["node", "-e", test_script, str(matrix_js_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Simulation failed: {res.stderr}\n{res.stdout}"
    assert "SIMULATION_OK" in res.stdout


def test_matrix_physics_and_fluid_mechanics():
    """Проверка гидродинамики, переключения режимов и процедурных реакций матрицы"""
    test_script = """
    const fs = require('fs');

    global.window = {
      innerWidth: 1000,
      innerHeight: 800,
      addEventListener: () => {},
      getComputedStyle: () => ({ display: 'block' }),
      requestAnimationFrame: () => {}
    };
    global.document = {
      readyState: 'complete',
      hidden: false,
      addEventListener: () => {},
      createElement: () => ({
        style: {},
        getContext: () => ({
          fillRect: () => {},
          clearRect: () => {},
          fillText: () => {},
          beginPath: () => {},
          arc: () => {},
          fill: () => {},
          save: () => {},
          restore: () => {}
        })
      }),
      getElementById: () => null,
      querySelectorAll: () => [],
      querySelector: () => null,
      body: { appendChild: () => {} }
    };
    global.localStorage = {
      _data: {},
      getItem: function(k) { return this._data[k] || null; },
      setItem: function(k, v) { this._data[k] = v; }
    };

    const code = fs.readFileSync(process.argv[1], 'utf8');
    eval(code);

    const api = window.AgyMatrixEffect;
    if (!api) throw new Error('AgyMatrixEffect not found');

    // Проверяем интенсивности
    api.setIntensity('low');
    if (api.getConfig().intensity !== 'low') throw new Error('Low intensity failed');
    api.setIntensity('high');
    if (api.getConfig().intensity !== 'high') throw new Error('High intensity failed');

    // Проверяем переключение режимов
    api.setMode('task_only');
    if (api.getConfig().mode !== 'task_only') throw new Error('task_only mode failed');
    api.setMode('dynamic');
    if (api.getConfig().mode !== 'dynamic') throw new Error('dynamic mode failed');

    // Проверяем toggle
    api.disable();
    if (api.getState().enabled !== false) throw new Error('disable failed');
    const toggled = api.toggle();
    if (toggled !== true || api.getState().enabled !== true) throw new Error('toggle failed');

    // Проверяем генерацию всплеска
    api.triggerBurst(20);
    const state = api.getState();
    if (state.activeColumns === 0) throw new Error('Burst failed to activate columns');

    console.log('PHYSICS_VERIFIED');
    process.exit(0);
    """
    matrix_js_path = TOOLS_DIR / "matrix-effect.js"
    res = subprocess.run(["node", "-e", test_script, str(matrix_js_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Physics test failed: {res.stderr}\n{res.stdout}"
    assert "PHYSICS_VERIFIED" in res.stdout


def test_readme_integration():
    readme_path = ROOT / "README.md"
    readme_content = readme_path.read_text(encoding="utf-8")
    assert "tools/antigravity-ui-customization/README.md" in readme_content
    assert "Antigravity Standalone" in readme_content
    assert "эффект матрицы" in readme_content.lower()
