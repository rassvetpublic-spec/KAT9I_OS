"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Preload script — runs in every BrowserWindow before the page loads.
 * Exposes a minimal, secure API via contextBridge so the renderer can
 * communicate with the main-process auto-updater without nodeIntegration.
 */
const electron_1 = require("electron");
const updaterAPI = {
    onStateChanged: (callback) => {
        const handler = (_event, state) => {
            callback(state);
        };
        electron_1.ipcRenderer.on('updater:state-changed', handler);
        // Return unsubscribe function
        return () => {
            electron_1.ipcRenderer.removeListener('updater:state-changed', handler);
        };
    },
    applyUpdate: () => electron_1.ipcRenderer.invoke('updater:apply'),
    quitAndInstall: () => electron_1.ipcRenderer.invoke('updater:quit-and-install'),
    checkForUpdates: () => electron_1.ipcRenderer.invoke('updater:check-for-updates'),
    getState: () => electron_1.ipcRenderer.invoke('updater:get-state'),
};
const dialogAPI = {
    showOpenDialog: () => electron_1.ipcRenderer.invoke('dialog:open-workspace'),
    showOpenMultipleFolderDialog: () => electron_1.ipcRenderer.invoke('dialog:open-workspaces'),
};
const notificationAPI = {
    send: (options) => electron_1.ipcRenderer.invoke('notification:send', options),
    openSystemPreferences: () => electron_1.ipcRenderer.invoke('notification:open-system-preferences'),
    onClicked: (callback) => {
        const handler = (_event, payload) => {
            callback(payload);
        };
        electron_1.ipcRenderer.on('notification:clicked', handler);
        return () => {
            electron_1.ipcRenderer.removeListener('notification:clicked', handler);
        };
    },
};
const storageAPI = {
    getItems: () => electron_1.ipcRenderer.invoke('storage:get-items'),
    updateItems: (changes) => electron_1.ipcRenderer.invoke('storage:update-items', changes),
    onChanged: (callback) => {
        const handler = (_event, changes) => {
            callback(changes);
        };
        electron_1.ipcRenderer.on('storage:changed', handler);
        return () => {
            electron_1.ipcRenderer.removeListener('storage:changed', handler);
        };
    },
};
const logsAPI = {
    getElectronLogs: () => electron_1.ipcRenderer.invoke('logs:electron'),
};
const extensionsAPI = {
    sendAuthorities: (authoritiesMap) => electron_1.ipcRenderer.invoke('extensions:send-authorities', authoritiesMap),
};
const deepLinkAPI = {
    onDeepLink: (callback) => {
        const handler = (_event, url) => {
            callback(url);
        };
        electron_1.ipcRenderer.on('deep-link', handler);
        return () => {
            electron_1.ipcRenderer.removeListener('deep-link', handler);
        };
    },
    getStoredDeepLink: () => electron_1.ipcRenderer.invoke('deep-link:get-stored'),
};
const agentAPI = {
    updateActiveAgentCount: (count) => electron_1.ipcRenderer.invoke('agent:update-active-count', count),
};
const electronNativeAPI = {
    getZoomLevel: () => electron_1.webFrame.getZoomFactor(),
    setTitleBarOverlay: (options) => electron_1.ipcRenderer.invoke('window:set-title-bar-overlay', options),
    minimize: () => electron_1.ipcRenderer.invoke('window:minimize'),
    maximize: () => electron_1.ipcRenderer.invoke('window:maximize'),
    unmaximize: () => electron_1.ipcRenderer.invoke('window:unmaximize'),
    isMaximized: () => electron_1.ipcRenderer.invoke('window:is-maximized'),
    close: () => electron_1.ipcRenderer.invoke('window:close'),
    toggleDevTools: () => electron_1.ipcRenderer.invoke('window:toggle-devtools'),
    zoomIn: () => {
        void electron_1.ipcRenderer.invoke('window:zoom-in');
    },
    zoomOut: () => {
        void electron_1.ipcRenderer.invoke('window:zoom-out');
    },
    resetZoom: () => {
        void electron_1.ipcRenderer.invoke('window:reset-zoom');
    },
    openExternal: (url) => electron_1.ipcRenderer.invoke('shell:open-external', url),
    revealInFilePicker: (path) => electron_1.ipcRenderer.invoke('shell:reveal-in-file-picker', path),
};
const ideAPI = {
    isInstalled: () => electron_1.ipcRenderer.invoke('ide:is-installed'),
};
electron_1.contextBridge.exposeInMainWorld('electronUpdater', updaterAPI);
electron_1.contextBridge.exposeInMainWorld('dialog', dialogAPI);
electron_1.contextBridge.exposeInMainWorld('nativeNotifications', notificationAPI);
electron_1.contextBridge.exposeInMainWorld('nativeStorage', storageAPI);
electron_1.contextBridge.exposeInMainWorld('logs', logsAPI);
electron_1.contextBridge.exposeInMainWorld('extensions', extensionsAPI);
electron_1.contextBridge.exposeInMainWorld('deepLink', deepLinkAPI);
electron_1.contextBridge.exposeInMainWorld('agent', agentAPI);
electron_1.contextBridge.exposeInMainWorld('electronNative', electronNativeAPI);
electron_1.contextBridge.exposeInMainWorld('ide', ideAPI);

// === AGY_UI_CUSTOMIZATION_START ===
(function() {
  function __agy_inject_css() {
    try {
      if (!document.getElementById('agy-context-menu-style')) {
        const style = document.createElement('style');
        style.id = 'agy-context-menu-style';
        style.textContent = "/* Context Menu & Settings Modal Styles for Antigravity Standalone */\n\n#agy-context-menu {\n  position: fixed;\n  display: none;\n  min-width: 230px;\n  max-width: 320px;\n  background: rgba(24, 26, 32, 0.95);\n  backdrop-filter: blur(16px);\n  -webkit-backdrop-filter: blur(16px);\n  border: 1px solid rgba(255, 255, 255, 0.14);\n  border-radius: 12px;\n  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.06);\n  padding: 6px;\n  z-index: 2147483647;\n  font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif;\n  font-size: 13px;\n  color: #e4e6eb;\n  user-select: none;\n  opacity: 0;\n  transform: scale(0.96);\n  transition: opacity 0.12s cubic-bezier(0.16, 1, 0.3, 1), transform 0.12s cubic-bezier(0.16, 1, 0.3, 1);\n  pointer-events: none;\n}\n\n#agy-context-menu.agy-visible {\n  display: block;\n  opacity: 1;\n  transform: scale(1);\n  pointer-events: auto;\n}\n\n.agy-menu-item {\n  display: flex;\n  align-items: center;\n  justify-content: space-between;\n  padding: 8px 12px;\n  border-radius: 8px;\n  cursor: pointer;\n  transition: background-color 0.1s ease, color 0.1s ease;\n  position: relative;\n}\n\n.agy-menu-item:hover {\n  background-color: rgba(255, 255, 255, 0.1);\n  color: #ffffff;\n}\n\n.agy-menu-item.agy-disabled {\n  opacity: 0.45;\n  cursor: not-allowed;\n  pointer-events: none;\n}\n\n.agy-menu-item-left {\n  display: flex;\n  align-items: center;\n  gap: 10px;\n}\n\n.agy-menu-icon {\n  font-size: 14px;\n  width: 18px;\n  text-align: center;\n  display: inline-block;\n}\n\n.agy-menu-label {\n  font-weight: 500;\n}\n\n.agy-menu-shortcut {\n  font-size: 11px;\n  color: #9ba1a6;\n  margin-left: 12px;\n}\n\n.agy-menu-arrow {\n  font-size: 10px;\n  color: #9ba1a6;\n}\n\n.agy-menu-separator {\n  height: 1px;\n  background-color: rgba(255, 255, 255, 0.1);\n  margin: 5px 2px;\n}\n\n/* Submenu */\n.agy-has-submenu:hover > .agy-submenu {\n  display: block;\n  opacity: 1;\n  transform: scale(1);\n}\n\n.agy-submenu {\n  position: absolute;\n  top: -6px;\n  left: 100%;\n  display: none;\n  min-width: 210px;\n  background: rgba(24, 26, 32, 0.97);\n  backdrop-filter: blur(16px);\n  -webkit-backdrop-filter: blur(16px);\n  border: 1px solid rgba(255, 255, 255, 0.14);\n  border-radius: 12px;\n  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.6);\n  padding: 6px;\n  opacity: 0;\n  transform: scale(0.96);\n  transition: opacity 0.12s cubic-bezier(0.16, 1, 0.3, 1), transform 0.12s cubic-bezier(0.16, 1, 0.3, 1);\n  margin-left: 4px;\n}\n\n/* Settings Modal */\n#agy-settings-modal {\n  position: fixed;\n  top: 0;\n  left: 0;\n  width: 100vw;\n  height: 100vh;\n  background: rgba(0, 0, 0, 0.65);\n  backdrop-filter: blur(8px);\n  display: none;\n  align-items: center;\n  justify-content: center;\n  z-index: 2147483647;\n  font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif;\n  color: #e4e6eb;\n}\n\n#agy-settings-modal.agy-modal-open {\n  display: flex;\n}\n\n.agy-modal-card {\n  width: 520px;\n  max-width: 90vw;\n  max-height: 85vh;\n  background: #1c1e26;\n  border: 1px solid rgba(255, 255, 255, 0.14);\n  border-radius: 16px;\n  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);\n  display: flex;\n  flex-direction: column;\n  overflow: hidden;\n}\n\n.agy-modal-header {\n  padding: 18px 24px;\n  border-bottom: 1px solid rgba(255, 255, 255, 0.1);\n  display: flex;\n  align-items: center;\n  justify-content: space-between;\n}\n\n.agy-modal-title {\n  font-size: 16px;\n  font-weight: 600;\n  display: flex;\n  align-items: center;\n  gap: 8px;\n}\n\n.agy-modal-close {\n  background: transparent;\n  border: none;\n  color: #9ba1a6;\n  font-size: 20px;\n  cursor: pointer;\n  padding: 4px 8px;\n  border-radius: 6px;\n  transition: background-color 0.1s ease;\n}\n\n.agy-modal-close:hover {\n  background: rgba(255, 255, 255, 0.1);\n  color: #fff;\n}\n\n.agy-modal-body {\n  padding: 20px 24px;\n  overflow-y: auto;\n  flex: 1;\n}\n\n.agy-section-desc {\n  font-size: 12px;\n  color: #9ba1a6;\n  margin-bottom: 14px;\n  line-height: 1.5;\n}\n\n.agy-skills-list {\n  display: flex;\n  flex-direction: column;\n  gap: 8px;\n  margin-bottom: 16px;\n}\n\n.agy-skill-row {\n  display: flex;\n  gap: 10px;\n  align-items: center;\n}\n\n.agy-skill-row input {\n  background: rgba(255, 255, 255, 0.06);\n  border: 1px solid rgba(255, 255, 255, 0.12);\n  border-radius: 8px;\n  padding: 7px 12px;\n  color: #fff;\n  font-size: 13px;\n  outline: none;\n}\n\n.agy-skill-row input:focus {\n  border-color: #60a5fa;\n  background: rgba(255, 255, 255, 0.1);\n}\n\n.agy-skill-name {\n  flex: 1;\n}\n\n.agy-skill-cmd {\n  flex: 1.5;\n}\n\n.agy-btn-del {\n  background: rgba(239, 68, 68, 0.15);\n  border: 1px solid rgba(239, 68, 68, 0.3);\n  color: #f87171;\n  border-radius: 8px;\n  padding: 7px 12px;\n  cursor: pointer;\n  transition: background-color 0.1s ease;\n}\n\n.agy-btn-del:hover {\n  background: rgba(239, 68, 68, 0.3);\n}\n\n.agy-modal-footer {\n  padding: 16px 24px;\n  border-top: 1px solid rgba(255, 255, 255, 0.1);\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n}\n\n.agy-btn-add {\n  background: rgba(255, 255, 255, 0.08);\n  border: 1px solid rgba(255, 255, 255, 0.15);\n  color: #fff;\n  border-radius: 8px;\n  padding: 8px 14px;\n  cursor: pointer;\n  font-size: 13px;\n  transition: background-color 0.1s ease;\n}\n\n.agy-btn-add:hover {\n  background: rgba(255, 255, 255, 0.15);\n}\n\n.agy-btn-save {\n  background: #3b82f6;\n  border: none;\n  color: #fff;\n  font-weight: 500;\n  border-radius: 8px;\n  padding: 8px 18px;\n  cursor: pointer;\n  font-size: 13px;\n  transition: background-color 0.1s ease;\n}\n\n.agy-btn-save:hover {\n  background: #2563eb;\n}\n";
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

  // Logic:
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

      // Добавляем шапку с именем воркера, если ее нет
      let header = document.getElementById('agy-menu-worker-header');
      if (!header) {
        header = document.createElement('div');
        header.id = 'agy-menu-worker-header';
        header.style.cssText = 'padding: 4px 12px 8px; font-weight: 800; font-size: 14px; color: #BD93F9; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 5px; text-align: center; letter-spacing: 1px;';
        
        let workerName = "WORKER";
        if (typeof process !== 'undefined' && process.argv) {
          const match = process.argv.join(' ').match(/Worker_(\d)/);
          if (match) workerName = "WORKER " + match[1];
        }
        header.innerText = workerName;
        menu.insertBefore(header, menu.firstChild);
      }

      // Сначала делаем меню видимым невидимо, чтобы измерить его реальные размеры
      menu.style.visibility = 'hidden';
      menu.style.display = 'block';
      const actualWidth = menu.offsetWidth;
      const actualHeight = menu.offsetHeight;
      menu.style.display = '';
      menu.style.visibility = '';

      // Позиционирование с проверкой границ окна
      let x = e.clientX;
      let y = e.clientY;

      if (x + actualWidth > window.innerWidth) {
        x = window.innerWidth - actualWidth - 10;
      }
      if (y + actualHeight > window.innerHeight) {
        y = y - actualHeight; // Раскрываем вверх!
        if (y < 10) y = 10; // Защита от выхода за верхний край
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

})();
// === AGY_UI_CUSTOMIZATION_END ===
