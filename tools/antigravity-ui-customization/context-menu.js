/**
 * Antigravity Standalone — Кастомное контекстное меню по правой кнопке мыши
 * Модуль внедряет контекстное меню с буфером обмена, действиями чата,
 * вызовом скилов и окном настроек.
 */
(function () {
  'use strict';

  if (window.__agy_context_menu_installed) {
    return;
  }
  window.__agy_context_menu_installed = true;

  const DEFAULT_CONFIG = {
    version: "1.0.0",
    skills: [
      { name: "Interview Me", command: "/interview-me", icon: "🎙️" },
      { name: "AGY Customizations", command: "/agy-customizations", icon: "🛠️" },
      { name: "Antigravity Guide", command: "/antigravity-guide", icon: "📖" },
      { name: "Grill Me", command: "/grill-me", icon: "🔥" },
      { name: "Boost", command: "/boost", icon: "🚀" },
      { name: "Goal", command: "/goal", icon: "🎯" }
    ]
  };

  function loadConfig() {
    try {
      const saved = localStorage.getItem('agy_context_menu_config');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('[AGY-UI] Ошибка чтения конфига из localStorage:', e);
    }
    return JSON.parse(JSON.stringify(DEFAULT_CONFIG));
  }

  function saveConfig(cfg) {
    try {
      localStorage.setItem('agy_context_menu_config', JSON.stringify(cfg));
    } catch (e) {
      console.error('[AGY-UI] Ошибка сохранения конфига:', e);
    }
  }

  let config = loadConfig();
  let selectedText = '';
  let activeTarget = null;

  // Поиск поля ввода чата
  function findChatInput() {
    const candidates = [
      'textarea',
      'div[contenteditable="true"]',
      '[role="textbox"]',
      '.chat-input textarea',
      '.monaco-editor textarea',
      'input[type="text"]'
    ];
    for (const selector of candidates) {
      const elements = document.querySelectorAll(selector);
      for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).display !== 'none') {
          return el;
        }
      }
    }
    return null;
  }

  // Вставка текста в поле ввода чата
  function insertTextIntoChat(text, append = false) {
    const input = findChatInput();
    if (!input) {
      // Fallback через буфер обмена
      navigator.clipboard.writeText(text);
      console.log('[AGY-UI] Поле чата не найдено. Текст скопирован в буфер обмена:', text);
      return;
    }

    input.focus();

    if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {
      const currentVal = input.value || '';
      input.value = append && currentVal ? currentVal + ' ' + text : text;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      input.selectionStart = input.selectionEnd = input.value.length;
    } else if (input.isContentEditable) {
      if (!append) {
        input.innerText = '';
      }
      document.execCommand('insertText', false, text);
    }
  }

  // Создание разметки меню
  function createMenuDOM() {
    let menu = document.getElementById('agy-context-menu');
    if (menu) return menu;

    menu = document.createElement('div');
    menu.id = 'agy-context-menu';
    menu.innerHTML = `
      <div class="agy-menu-item" id="agy-action-copy">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">📋</span>
          <span class="agy-menu-label">Копировать</span>
        </div>
        <span class="agy-menu-shortcut">Ctrl+C</span>
      </div>
      <div class="agy-menu-item" id="agy-action-paste">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">📥</span>
          <span class="agy-menu-label">Вставить</span>
        </div>
        <span class="agy-menu-shortcut">Ctrl+V</span>
      </div>
      <div class="agy-menu-item" id="agy-action-cut">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">✂️</span>
          <span class="agy-menu-label">Вырезать</span>
        </div>
        <span class="agy-menu-shortcut">Ctrl+X</span>
      </div>
      <div class="agy-menu-item" id="agy-action-select-all">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">🔘</span>
          <span class="agy-menu-label">Выделить всё</span>
        </div>
        <span class="agy-menu-shortcut">Ctrl+A</span>
      </div>

      <div class="agy-menu-separator"></div>

      <div class="agy-menu-item" id="agy-action-insert-chat">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">💬</span>
          <span class="agy-menu-label">Вставить в строку чата</span>
        </div>
      </div>
      <div class="agy-menu-item" id="agy-action-clear-chat">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">🧹</span>
          <span class="agy-menu-label">Очистить строку чата</span>
        </div>
      </div>

      <div class="agy-menu-separator"></div>

      <div class="agy-menu-item agy-has-submenu" id="agy-action-skills">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">⚡</span>
          <span class="agy-menu-label">Скилы и команды</span>
        </div>
        <span class="agy-menu-arrow">▶</span>
        <div class="agy-submenu" id="agy-skills-submenu"></div>
      </div>

      <div class="agy-menu-separator"></div>

      <div class="agy-menu-item" id="agy-action-settings">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">⚙️</span>
          <span class="agy-menu-label">Настройки меню</span>
        </div>
      </div>
      <div class="agy-menu-item" id="agy-action-devtools">
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">🔍</span>
          <span class="agy-menu-label">Инспектор элементов</span>
        </div>
        <span class="agy-menu-shortcut">F12</span>
      </div>
    `;

    document.body.appendChild(menu);
    renderSkillsSubmenu();
    bindMenuEvents(menu);
    createSettingsModalDOM();
    return menu;
  }

  // Рендер подменю скилов
  function renderSkillsSubmenu() {
    const submenu = document.getElementById('agy-skills-submenu');
    if (!submenu) return;
    submenu.innerHTML = '';

    if (!config.skills || config.skills.length === 0) {
      submenu.innerHTML = '<div class="agy-menu-item agy-disabled"><span class="agy-menu-label">Нет скилов</span></div>';
      return;
    }

    config.skills.forEach(skill => {
      const item = document.createElement('div');
      item.className = 'agy-menu-item';
      item.innerHTML = `
        <div class="agy-menu-item-left">
          <span class="agy-menu-icon">${skill.icon || '🔹'}</span>
          <span class="agy-menu-label">${skill.name}</span>
        </div>
        <span class="agy-menu-shortcut">${skill.command}</span>
      `;
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        hideMenu();
        const cmd = skill.command;
        const textToInsert = selectedText ? `${cmd} ${selectedText}` : `${cmd} `;
        insertTextIntoChat(textToInsert);
      });
      submenu.appendChild(item);
    });
  }

  // Создание модального окна настроек
  function createSettingsModalDOM() {
    let modal = document.getElementById('agy-settings-modal');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'agy-settings-modal';
    modal.innerHTML = `
      <div class="agy-modal-card">
        <div class="agy-modal-header">
          <div class="agy-modal-title">
            <span>⚙️</span> Настройки контекстного меню Antigravity
          </div>
          <button class="agy-modal-close" id="agy-modal-close-btn">&times;</button>
        </div>
        <div class="agy-modal-body">
          <div class="agy-section-desc">
            Настройте список скилов и команд, отображаемых в подменю. При выборе скила в поле ввода чата подставляется команда с выделенным текстом.
          </div>
          <div class="agy-skills-list" id="agy-modal-skills-list"></div>
          <button class="agy-btn-add" id="agy-btn-add-skill">+ Добавить скил/команду</button>
        </div>
        <div class="agy-modal-footer">
          <button class="agy-btn-add" id="agy-btn-reset-skills">Сбросить по умолчанию</button>
          <button class="agy-btn-save" id="agy-btn-save-skills">Сохранить изменения</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    document.getElementById('agy-modal-close-btn').addEventListener('click', () => {
      modal.classList.remove('agy-modal-open');
    });

    document.getElementById('agy-btn-add-skill').addEventListener('click', () => {
      addSkillRow('', '', '🔹');
    });

    document.getElementById('agy-btn-reset-skills').addEventListener('click', () => {
      config = JSON.parse(JSON.stringify(DEFAULT_CONFIG));
      saveConfig(config);
      renderModalSkills();
      renderSkillsSubmenu();
    });

    document.getElementById('agy-btn-save-skills').addEventListener('click', () => {
      const rows = document.querySelectorAll('.agy-skill-row');
      const updatedSkills = [];
      rows.forEach(row => {
        const name = row.querySelector('.agy-skill-name').value.trim();
        const cmd = row.querySelector('.agy-skill-cmd').value.trim();
        const icon = row.querySelector('.agy-skill-icon').value.trim() || '🔹';
        if (name && cmd) {
          updatedSkills.push({ name, command: cmd, icon });
        }
      });
      config.skills = updatedSkills;
      saveConfig(config);
      renderSkillsSubmenu();
      modal.classList.remove('agy-modal-open');
    });

    return modal;
  }

  function addSkillRow(name = '', cmd = '', icon = '🔹') {
    const list = document.getElementById('agy-modal-skills-list');
    const row = document.createElement('div');
    row.className = 'agy-skill-row';
    row.innerHTML = `
      <input type="text" class="agy-skill-icon" style="width: 45px; text-align: center;" value="${icon}" title="Иконка">
      <input type="text" class="agy-skill-name" placeholder="Название" value="${name}">
      <input type="text" class="agy-skill-cmd" placeholder="/команда" value="${cmd}">
      <button class="agy-btn-del" title="Удалить">✕</button>
    `;
    row.querySelector('.agy-btn-del').addEventListener('click', () => {
      row.remove();
    });
    list.appendChild(row);
  }

  function renderModalSkills() {
    const list = document.getElementById('agy-modal-skills-list');
    if (!list) return;
    list.innerHTML = '';
    (config.skills || []).forEach(skill => {
      addSkillRow(skill.name, skill.command, skill.icon);
    });
  }

  function openSettingsModal() {
    const modal = document.getElementById('agy-settings-modal');
    if (modal) {
      renderModalSkills();
      modal.classList.add('agy-modal-open');
    }
  }

  // Привязка обработчиков пунктов меню
  function bindMenuEvents(menu) {
    // Копировать
    document.getElementById('agy-action-copy').addEventListener('click', async () => {
      hideMenu();
      if (selectedText) {
        try {
          await navigator.clipboard.writeText(selectedText);
        } catch (e) {
          document.execCommand('copy');
        }
      }
    });

    // Вставить
    document.getElementById('agy-action-paste').addEventListener('click', async () => {
      hideMenu();
      try {
        const text = await navigator.clipboard.readText();
        if (activeTarget && (activeTarget.tagName === 'INPUT' || activeTarget.tagName === 'TEXTAREA' || activeTarget.isContentEditable)) {
          if (activeTarget.isContentEditable) {
            activeTarget.focus();
            document.execCommand('insertText', false, text);
          } else {
            const start = activeTarget.selectionStart || 0;
            const end = activeTarget.selectionEnd || 0;
            const val = activeTarget.value || '';
            activeTarget.value = val.substring(0, start) + text + val.substring(end);
            activeTarget.selectionStart = activeTarget.selectionEnd = start + text.length;
            activeTarget.dispatchEvent(new Event('input', { bubbles: true }));
          }
        } else {
          insertTextIntoChat(text, true);
        }
      } catch (e) {
        console.warn('[AGY-UI] Ошибка доступа к буферу обмена:', e);
      }
    });

    // Вырезать
    document.getElementById('agy-action-cut').addEventListener('click', () => {
      hideMenu();
      document.execCommand('cut');
    });

    // Выделить всё
    document.getElementById('agy-action-select-all').addEventListener('click', () => {
      hideMenu();
      if (activeTarget && (activeTarget.tagName === 'INPUT' || activeTarget.tagName === 'TEXTAREA')) {
        activeTarget.select();
      } else {
        document.execCommand('selectAll');
      }
    });

    // Вставить в строку чата
    document.getElementById('agy-action-insert-chat').addEventListener('click', () => {
      hideMenu();
      if (selectedText) {
        insertTextIntoChat(selectedText, false);
      }
    });

    // Очистить строку чата
    document.getElementById('agy-action-clear-chat').addEventListener('click', () => {
      hideMenu();
      const input = findChatInput();
      if (input) {
        if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {
          input.value = '';
          input.dispatchEvent(new Event('input', { bubbles: true }));
        } else if (input.isContentEditable) {
          input.innerText = '';
        }
      }
    });

    // Настройки меню
    document.getElementById('agy-action-settings').addEventListener('click', () => {
      hideMenu();
      openSettingsModal();
    });

    // DevTools
    document.getElementById('agy-action-devtools').addEventListener('click', () => {
      hideMenu();
      if (window.electronNative && typeof window.electronNative.toggleDevTools === 'function') {
        window.electronNative.toggleDevTools();
      } else {
        console.log('[AGY-UI] DevTools trigger');
      }
    });
  }

  function hideMenu() {
    const menu = document.getElementById('agy-context-menu');
    if (menu) {
      menu.classList.remove('agy-visible');
    }
  }

  // Инициализация обработчиков окна
  function init() {
    const menu = createMenuDOM();

    window.addEventListener('contextmenu', (e) => {
      // Игнорируем правый клик внутри самого меню и модалки
      if (e.target.closest('#agy-context-menu') || e.target.closest('#agy-settings-modal')) {
        return;
      }

      e.preventDefault();

      activeTarget = e.target;
      selectedText = window.getSelection().toString().trim();

      const hasSelection = selectedText.length > 0;
      const isEditable = activeTarget && (activeTarget.tagName === 'INPUT' || activeTarget.tagName === 'TEXTAREA' || activeTarget.isContentEditable);

      // Настройка активности пунктов
      const copyItem = document.getElementById('agy-action-copy');
      const cutItem = document.getElementById('agy-action-cut');
      const insertChatItem = document.getElementById('agy-action-insert-chat');

      if (copyItem) copyItem.classList.toggle('agy-disabled', !hasSelection);
      if (cutItem) cutItem.classList.toggle('agy-disabled', !hasSelection || !isEditable);
      if (insertChatItem) insertChatItem.classList.toggle('agy-disabled', !hasSelection);

      // Позиционирование с проверкой границ окна
      const menuWidth = 240;
      const menuHeight = 360;
      let x = e.clientX;
      let y = e.clientY;

      if (x + menuWidth > window.innerWidth) {
        x = Math.max(10, window.innerWidth - menuWidth - 10);
      }
      if (y + menuHeight > window.innerHeight) {
        y = Math.max(10, window.innerHeight - menuHeight - 10);
      }

      menu.style.left = `${x}px`;
      menu.style.top = `${y}px`;
      menu.classList.add('agy-visible');
    });

    window.addEventListener('click', (e) => {
      if (!e.target.closest('#agy-context-menu')) {
        hideMenu();
      }
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        hideMenu();
        const modal = document.getElementById('agy-settings-modal');
        if (modal) modal.classList.remove('agy-modal-open');
      }
    });

    console.log('[AGY-UI] Кастомное контекстное меню Antigravity Standalone успешно активировано.');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
