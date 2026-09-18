const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

function getSha256(filePath) {
  if (!fs.existsSync(filePath)) return null;
  const buffer = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function findAntigravityTarget(customTarget) {
  if (customTarget && fs.existsSync(customTarget)) {
    return path.resolve(customTarget);
  }

  if (process.env.ANTIGRAVITY_APP_ASAR && fs.existsSync(process.env.ANTIGRAVITY_APP_ASAR)) {
    return path.resolve(process.env.ANTIGRAVITY_APP_ASAR);
  }

  // 1. Поиск через активный процесс Antigravity
  try {
    const out = execSync('powershell -NoProfile -Command "(Get-Process -Name Antigravity -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Path)"', { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] }).trim();
    if (out && fs.existsSync(out)) {
      const asarFromProc = path.join(path.dirname(out), 'resources', 'app.asar');
      if (fs.existsSync(asarFromProc)) {
        return asarFromProc;
      }
    }
  } catch (e) {}

  // 2. Стандартные переменные среды
  const localAppData = process.env.LOCALAPPDATA || '';
  const programFiles = process.env.ProgramFiles || 'C:\\Program Files';
  const programFilesX86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';

  const candidates = [
    path.join(localAppData, 'Programs', 'antigravity', 'resources', 'app.asar'),
    'C:\\Antigravity\\Standalone\\App\\resources\\app.asar',
    path.join(programFiles, 'Antigravity', 'resources', 'app.asar'),
    path.join(programFilesX86, 'Antigravity', 'resources', 'app.asar')
  ];

  for (const c of candidates) {
    if (c && fs.existsSync(c)) {
      return c;
    }
  }

  // 3. Поиск по профилям C:\Users\*
  const usersDir = 'C:\\Users';
  if (fs.existsSync(usersDir)) {
    try {
      const users = fs.readdirSync(usersDir);
      for (const u of users) {
        const candidate = path.join(usersDir, u, 'AppData', 'Local', 'Programs', 'antigravity', 'resources', 'app.asar');
        if (fs.existsSync(candidate)) {
          return candidate;
        }
      }
    } catch (e) {}
  }

  return null;
}

function getStatus(targetAsar) {
  console.log('==================================================');
  console.log('  ANTIGRAVITY STANDALONE UI CUSTOMIZER — STATUS   ');
  console.log('==================================================');

  if (!targetAsar) {
    console.error('[ERROR] app.asar не найден в путях Antigravity.');
    process.exit(20);
  }

  const backupPath = targetAsar + '.bak';
  const asarSha = getSha256(targetAsar);
  const backupSha = getSha256(backupPath);

  console.log(`[INFO] Целевой файл: ${targetAsar}`);
  console.log(`[INFO] SHA-256 app.asar: ${asarSha}`);

  if (fs.existsSync(backupPath)) {
    console.log(`[OK] Резервная копия существует: ${backupPath}`);
    console.log(`[INFO] SHA-256 бэкапа: ${backupSha}`);
  } else {
    console.log('[WARN] Резервная копия еще не создана (оригинальное состояние).');
  }

  const tmpDir = path.join(process.env.TEMP || '.', `agy_check_${Date.now()}`);
  try {
    fs.mkdirSync(tmpDir, { recursive: true });
    execSync(`npx --yes @electron/asar extract-file "${targetAsar}" "dist/preload.js"`, { cwd: tmpDir, stdio: 'pipe' });
    const extractedPreload = path.join(tmpDir, 'preload.js');
    if (fs.existsSync(extractedPreload)) {
      const content = fs.readFileSync(extractedPreload, 'utf8');
      if (content.includes('__agy_context_menu_installed')) {
        const hasMatrix = content.includes('__agy_matrix_effect_installed');
        console.log(`[OK] Состояние: ПАТЧ УСТАНОВЛЕН (PATCHED)${hasMatrix ? ' [+MATRIX_EFFECT]' : ''}`);
        process.exit(0);
      }
    }
    console.log('[INFO] Состояние: ОРИГИНАЛЬНЫЙ (NOT_PATCHED)');
    process.exit(0);
  } catch (err) {
    console.warn('[WARN] Не удалось проверить статус инъекции: ' + err.message);
    process.exit(1);
  } finally {
    if (fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  }
}

function installCustomization(targetAsar) {
  console.log('==================================================');
  console.log('  ANTIGRAVITY STANDALONE UI CUSTOMIZER — INSTALL  ');
  console.log('==================================================');

  if (!targetAsar) {
    console.error('[ERROR] Целевой app.asar не найден.');
    process.exit(20);
  }

  const scriptDir = __dirname;
  const cssPath = path.join(scriptDir, 'context-menu.css');
  const jsPath = path.join(scriptDir, 'context-menu.js');
  const matrixPath = path.join(scriptDir, 'matrix-effect.js');

  if (!fs.existsSync(cssPath) || !fs.existsSync(jsPath)) {
    console.error('[ERROR] context-menu.css или context-menu.js не найдены.');
    process.exit(1);
  }

  const backupPath = targetAsar + '.bak';
  if (!fs.existsSync(backupPath)) {
    console.log(`[INFO] Создание резервной копии в ${backupPath}...`);
    fs.copyFileSync(targetAsar, backupPath);
    console.log(`[OK] Резервная копия создана. SHA-256: ${getSha256(backupPath)}`);
  } else {
    console.log(`[INFO] Существующий бэкап сохранен: ${backupPath}`);
  }

  const workDir = path.join(process.env.TEMP || '.', `agy_work_${Date.now()}`);
  try {
    fs.mkdirSync(workDir, { recursive: true });
    console.log('[INFO] Распаковка app.asar во временный каталог...');
    execSync(`npx --yes @electron/asar extract "${targetAsar}" "${workDir}"`, { stdio: 'inherit' });

    const preloadPath = path.join(workDir, 'dist', 'preload.js');
    if (!fs.existsSync(preloadPath)) {
      throw new Error('dist/preload.js не найден в распакованном app.asar.');
    }

    let preloadContent = fs.readFileSync(preloadPath, 'utf8');

    // Очистка предыдущей инъекции если была
    const markerStart = '// === AGY_UI_CUSTOMIZATION_START ===';
    const markerEnd = '// === AGY_UI_CUSTOMIZATION_END ===';
    const idxStart = preloadContent.indexOf(markerStart);
    const idxEnd = preloadContent.indexOf(markerEnd);
    if (idxStart !== -1 && idxEnd !== -1) {
      console.log('[INFO] Обновление существующей инъекции...');
      preloadContent = preloadContent.substring(0, idxStart) + preloadContent.substring(idxEnd + markerEnd.length);
    }

    const cssContent = fs.readFileSync(cssPath, 'utf8');
    const jsContent = fs.readFileSync(jsPath, 'utf8');
    const matrixContent = fs.existsSync(matrixPath) ? fs.readFileSync(matrixPath, 'utf8') : '';

    const injection = `
${markerStart}
(function() {
  function __agy_inject_css() {
    try {
      if (!document.getElementById('agy-context-menu-style')) {
        const style = document.createElement('style');
        style.id = 'agy-context-menu-style';
        style.textContent = ${JSON.stringify(cssContent)};
        (document.head || document.documentElement).appendChild(style);
      }
    } catch(e) {
      console.warn('[AGY-UI] Error injecting CSS:', e);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', __agy_inject_css);
  } else {
    __agy_inject_css();
  }

  // Matrix Visual Effect (Digital Rain, Stacking & Fluid Flow):
  ${matrixContent}

  // Context Menu & Customization Logic:
  ${jsContent}
})();
${markerEnd}
`;

    const newPreload = preloadContent.trimEnd() + '\n' + injection;
    fs.writeFileSync(preloadPath, newPreload, 'utf8');
    console.log('[OK] Инъекция (контекстное меню + эффект матрицы) в dist/preload.js успешно сформирована.');

    console.log('[INFO] Упаковка обновленного app.asar...');
    const tmpAsar = path.join(process.env.TEMP || '.', `app_patched_${Date.now()}.asar`);
    execSync(`npx --yes @electron/asar pack "${workDir}" "${tmpAsar}"`, { stdio: 'inherit' });

    fs.copyFileSync(tmpAsar, targetAsar);
    fs.unlinkSync(tmpAsar);

    console.log(`[OK] Antigravity Standalone успешно модифицирован!`);
    console.log(`[INFO] Новый SHA-256 app.asar: ${getSha256(targetAsar)}`);
    console.log(`[INFO] Перезапустите Antigravity для активации контекстного меню.`);
    process.exit(0);
  } catch (err) {
    console.error('[ERROR] Ошибка установки патча: ' + err.message);
    process.exit(1);
  } finally {
    if (fs.existsSync(workDir)) {
      fs.rmSync(workDir, { recursive: true, force: true });
    }
  }
}

function restoreOriginal(targetAsar) {
  console.log('==================================================');
  console.log('  ANTIGRAVITY STANDALONE UI CUSTOMIZER — RESTORE  ');
  console.log('==================================================');

  if (!targetAsar) {
    console.error('[ERROR] app.asar не найден.');
    process.exit(20);
  }

  const backupPath = targetAsar + '.bak';
  if (!fs.existsSync(backupPath)) {
    console.error(`[ERROR] Файл бэкапа не найден: ${backupPath}`);
    process.exit(10);
  }

  console.log(`[INFO] Восстановление из ${backupPath}...`);
  fs.copyFileSync(backupPath, targetAsar);
  console.log(`[OK] Оригинальное состояние успешно восстановлено!`);
  console.log(`[INFO] SHA-256 app.asar: ${getSha256(targetAsar)}`);
  process.exit(0);
}

const args = process.argv.slice(2);
const command = args[0] || 'status';
let customTarget = null;
const targetIdx = args.indexOf('--target');
if (targetIdx !== -1 && args[targetIdx + 1]) {
  customTarget = args[targetIdx + 1];
}

const target = findAntigravityTarget(customTarget);

switch (command) {
  case 'status':
    getStatus(target);
    break;
  case 'install':
    installCustomization(target);
    break;
  case 'restore':
    restoreOriginal(target);
    break;
  default:
    console.log(`Использование: node patch-engine.js [status|install|restore] [--target <path>]`);
    process.exit(1);
}
