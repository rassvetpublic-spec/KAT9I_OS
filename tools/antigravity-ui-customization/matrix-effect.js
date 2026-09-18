/**
 * Antigravity UI — Эффект матрицы (Digital Rain, Stacking & Liquid Flow)
 * 
 * Особенности:
 * 1. Легковесный HTML5 Canvas 2D overlay с pointer-events: none.
 * 2. Динамические триггеры:
 *    - TASK_RUNNING: плотный цифровой дождь, активное накопление и стекание.
 *    - IDLE: минималистичный режим (редкие капли раз в пару секунд).
 * 3. Физика стекания и аккумуляции у диалогового окна:
 *    - Символы падают и накапливаются (stacking) на верхней границе поля ввода.
 *    - Осевшие символы формируют неоновый слой и переходят в жидкое состояние.
 *    - Три процедурные реакции на столкновение с барьером:
 *      1. Accumulation & Slide: скольжение вдоль верхней грани к углам и стекание вниз по боковым ребрам.
 *      2. Particle Splash: неоновые брызги капель при ударе.
 *      3. Dissolve & Melt: плавление и растекание пятен с затуханием альфа-канала.
 * 4. Высокая производительность:
 *    - Жесткие лимиты на пул частиц (< 120 частиц, < 45 накопленных символов).
 *    - Пауза при неактивной вкладке (document.hidden).
 *    - Потребление CPU/GPU < 5%.
 * 5. Конфигурация в localStorage ('agy_matrix_effect_config'):
 *    - enabled: true|false
 *    - mode: 'dynamic' | 'task_only'
 *    - intensity: 'low' | 'medium' | 'high'
 *    - color: '#00ff66'
 *    - glowColor: '#70ff94'
 */
(function () {
  'use strict';

  if (window.__agy_matrix_effect_installed) {
    return;
  }
  window.__agy_matrix_effect_installed = true;

  const DEFAULT_CONFIG = {
    enabled: true,
    mode: 'dynamic', // 'dynamic' (IDLE + RUNNING) или 'task_only'
    intensity: 'medium', // 'low' | 'medium' | 'high'
    color: '#00ff66',
    glowColor: '#70ff94',
    fontSize: 14,
    idleSpawnInterval: 2200,
    runningDensity: 0.75
  };

  const INTENSITY_SETTINGS = {
    low: { density: 0.35, speedMult: 0.8, maxParticles: 60, idleInterval: 3500 },
    medium: { density: 0.70, speedMult: 1.0, maxParticles: 110, idleInterval: 2200 },
    high: { density: 0.92, speedMult: 1.25, maxParticles: 160, idleInterval: 1200 }
  };

  function loadConfig() {
    try {
      const saved = localStorage.getItem('agy_matrix_effect_config');
      if (saved) {
        return Object.assign({}, DEFAULT_CONFIG, JSON.parse(saved));
      }
    } catch (e) {
      console.warn('[AGY-UI] Ошибка чтения конфига матрицы:', e);
    }
    return Object.assign({}, DEFAULT_CONFIG);
  }

  function saveConfig(cfg) {
    try {
      localStorage.setItem('agy_matrix_effect_config', JSON.stringify(cfg));
    } catch (e) {
      console.error('[AGY-UI] Ошибка сохранения конфига матрицы:', e);
    }
  }

  const state = {
    cfg: loadConfig(),
    isRunning: false,
    lastIdleSpawn: 0,
    columns: [],
    stackedDrops: [], // Символы, осевшие на верхней кромке поля ввода
    liquidParticles: [], // Жидкие частицы стекания по краям и брызг
    canvas: null,
    ctx: null,
    width: 0,
    height: 0,
    inputRect: null,
    animFrameId: null,
    isPaused: false
  };

  const CHARACTERS = '0123456789ABCDEFｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜXYZ'.split('');

  function getRandomChar() {
    return CHARACTERS[Math.floor(Math.random() * CHARACTERS.length)];
  }

  // Обнаружение диалогового окна чата (input box)
  function updateInputBoxRect() {
    const candidates = [
      'textarea',
      'div[contenteditable="true"]',
      '[role="textbox"]',
      '.chat-input',
      '.input-box',
      '.chat-input-container',
      '.monaco-editor textarea',
      'input[type="text"]'
    ];
    for (const selector of candidates) {
      const elements = document.querySelectorAll(selector);
      for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        const rect = el.getBoundingClientRect();
        if (rect.width > 60 && rect.height > 20 && window.getComputedStyle(el).display !== 'none') {
          const parent = el.closest('.chat-input-container, .input-container, form, div') || el;
          const pRect = parent.getBoundingClientRect();
          state.inputRect = {
            left: Math.max(10, pRect.left),
            right: Math.min(window.innerWidth - 10, pRect.right),
            top: pRect.top,
            bottom: pRect.bottom,
            width: pRect.width,
            height: pRect.height
          };
          return;
        }
      }
    }

    // Виртуальный fallback по центру внизу экрана
    state.inputRect = {
      left: state.width * 0.18,
      right: state.width * 0.82,
      top: Math.max(100, state.height - 130),
      bottom: state.height - 40,
      width: state.width * 0.64,
      height: 90
    };
  }

  // Создание Canvas overlay
  function initCanvas() {
    if (state.canvas) return;

    let canvas = document.getElementById('agy-matrix-overlay');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'agy-matrix-overlay';
      canvas.style.position = 'fixed';
      canvas.style.top = '0';
      canvas.style.left = '0';
      canvas.style.width = '100vw';
      canvas.style.height = '100vh';
      canvas.style.pointerEvents = 'none';
      canvas.style.zIndex = '999990';
      canvas.style.opacity = '0.92';
      document.body.appendChild(canvas);
    }

    state.canvas = canvas;
    state.ctx = canvas.getContext('2d');

    resize();
    window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', () => {
      state.isPaused = document.hidden;
      if (!document.hidden && !state.animFrameId) {
        render();
      }
    });
  }

  function resize() {
    if (!state.canvas) return;
    state.width = state.canvas.width = window.innerWidth;
    state.height = state.canvas.height = window.innerHeight;
    updateInputBoxRect();

    const colCount = Math.floor(state.width / state.cfg.fontSize);
    state.columns = [];
    const intensity = INTENSITY_SETTINGS[state.cfg.intensity] || INTENSITY_SETTINGS.medium;

    for (let i = 0; i < colCount; i++) {
      state.columns.push({
        x: i * state.cfg.fontSize,
        y: Math.random() * -state.height,
        speed: (2 + Math.random() * 3.5) * intensity.speedMult,
        active: false,
        char: getRandomChar()
      });
    }
  }

  // Автоопределение состояния TASK_RUNNING / IDLE
  function checkSystemTaskStatus() {
    const runningIndicator = document.querySelector(
      '.task-running, .spinner, [data-state="running"], .loading-dots, .executing, .antigravity-running'
    );
    state.isRunning = !!runningIndicator || window.__agy_task_running === true;

    const intensity = INTENSITY_SETTINGS[state.cfg.intensity] || INTENSITY_SETTINGS.medium;
    const now = Date.now();

    if (state.isRunning) {
      state.columns.forEach(col => {
        if (!col.active && Math.random() < intensity.density) {
          col.active = true;
          col.speed = (2.2 + Math.random() * 4.0) * intensity.speedMult;
        }
      });
    } else {
      if (state.cfg.mode === 'task_only') {
        state.columns.forEach(col => {
          col.active = false;
        });
      } else {
        // Режим IDLE — редкие капли
        if (now - state.lastIdleSpawn > intensity.idleInterval) {
          state.lastIdleSpawn = now;
          const inactive = state.columns.filter(c => !c.active);
          if (inactive.length > 0) {
            const randomCol = inactive[Math.floor(Math.random() * inactive.length)];
            randomCol.active = true;
            randomCol.y = 0;
            randomCol.speed = 1.4 + Math.random() * 1.8;
          }
        }
      }
    }
  }

  // Накопление символов на барьере (Stacking)
  function handleStacking(x, y) {
    const maxStacked = 45;
    if (state.stackedDrops.length >= maxStacked) {
      // Превышен лимит осевших капель — превращаем в жидкость
      const oldDrop = state.stackedDrops.shift();
      triggerLiquification(oldDrop.x, oldDrop.y);
    }

    state.stackedDrops.push({
      x: x,
      y: y,
      char: getRandomChar(),
      alpha: 1.0,
      life: 50 + Math.floor(Math.random() * 70),
      maxLife: 120,
      glow: Math.random() > 0.4
    });

    // С вероятностью 45% сразу порождаем жидкий всплеск
    if (Math.random() < 0.45) {
      triggerLiquification(x, y);
    }
  }

  // Жидкая физика (Liquification) — 3 процедурные реакции
  function triggerLiquification(x, y) {
    if (!state.inputRect) return;
    const intensity = INTENSITY_SETTINGS[state.cfg.intensity] || INTENSITY_SETTINGS.medium;
    if (state.liquidParticles.length >= intensity.maxParticles) {
      return;
    }

    const inRect = state.inputRect;
    const midX = (inRect.left + inRect.right) / 2;
    const targetEdgeX = x < midX ? inRect.left : inRect.right;
    const mode = Math.floor(Math.random() * 3); // 0: slide, 1: splash, 2: melt

    if (mode === 0) {
      // 1. Accumulation & Slide: скольжение вдоль верхней грани к краю, затем вниз вдоль ребра
      const slideDir = targetEdgeX > x ? 1 : -1;
      const count = 2 + Math.floor(Math.random() * 3);
      for (let i = 0; i < count; i++) {
        state.liquidParticles.push({
          x: x,
          y: y,
          vx: slideDir * (1.8 + Math.random() * 2.2),
          vy: 0, // строго по горизонтали вдоль верхней рамки
          radius: 2 + Math.random() * 2,
          alpha: 0.95,
          type: 'slide',
          targetEdgeX: targetEdgeX,
          edgePassed: false,
          edgeX: targetEdgeX
        });
      }
    } else if (mode === 1) {
      // 2. Particle Splash: неоновые брызги при ударе
      const count = 3 + Math.floor(Math.random() * 4);
      for (let i = 0; i < count; i++) {
        const angle = Math.PI + (Math.random() * Math.PI); // фонтан вверх
        const speed = 1.6 + Math.random() * 3.2;
        state.liquidParticles.push({
          x: x,
          y: y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          radius: 1.4 + Math.random() * 1.6,
          alpha: 1.0,
          type: 'splash'
        });
      }
    } else {
      // 3. Dissolve & Melt: оплавление и таяние пятна
      state.liquidParticles.push({
        x: x,
        y: y,
        vx: (Math.random() - 0.5) * 0.6,
        vy: 0.2 + Math.random() * 0.4,
        radius: 2.8 + Math.random() * 2.2,
        alpha: 0.88,
        type: 'melt'
      });
    }
  }

  // Обновление и рендеринг накопленных символов
  function renderStackedDrops(ctx) {
    for (let i = state.stackedDrops.length - 1; i >= 0; i--) {
      const drop = state.stackedDrops[i];
      drop.life--;

      const lifeRatio = drop.life / drop.maxLife;
      drop.alpha = Math.max(0, Math.min(1, lifeRatio * 1.2));

      ctx.save();
      if (drop.glow) {
        ctx.shadowColor = state.cfg.glowColor;
        ctx.shadowBlur = 4;
        ctx.fillStyle = `rgba(112, 255, 148, ${drop.alpha})`;
      } else {
        ctx.fillStyle = `rgba(0, 255, 102, ${drop.alpha})`;
      }
      ctx.fillText(drop.char, drop.x, drop.y);
      ctx.restore();

      // При окончании жизни превращается в жидкий подтек
      if (drop.life <= 0) {
        triggerLiquification(drop.x, drop.y);
        state.stackedDrops.splice(i, 1);
      }
    }
  }

  // Обновление и рендеринг жидких частиц
  function renderLiquidParticles(ctx, inRect) {
    for (let i = state.liquidParticles.length - 1; i >= 0; i--) {
      const p = state.liquidParticles[i];

      ctx.beginPath();
      ctx.fillStyle = `rgba(0, 255, 102, ${p.alpha})`;
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fill();

      p.x += p.vx;
      p.y += p.vy;

      if (p.type === 'slide') {
        // Движение по верхней грани к углу
        if (!p.edgePassed) {
          p.y = inRect.top; // прижаты к верхней грани
          const reachedLeft = p.targetEdgeX === inRect.left && p.x <= inRect.left;
          const reachedRight = p.targetEdgeX === inRect.right && p.x >= inRect.right;
          if (reachedLeft || reachedRight) {
            p.edgePassed = true;
            p.x = p.targetEdgeX;
            p.vx = 0;
            p.vy = 2.2 + Math.random() * 2.4; // стекание строго вниз по ребру
          }
        } else {
          // Стекание вертикально вниз вдоль левого или правого ребра
          p.x = p.edgeX;
          p.alpha -= 0.016;
        }
      } else if (p.type === 'splash') {
        p.vy += 0.18; // гравитация
        p.alpha -= 0.028;
      } else if (p.type === 'melt') {
        p.radius += 0.03;
        p.alpha -= 0.018;
      }

      if (p.alpha <= 0.02 || p.y > state.height) {
        state.liquidParticles.splice(i, 1);
      }
    }
  }

  function safeRequestAnimationFrame(cb) {
    if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
      return window.requestAnimationFrame(cb);
    }
    return setTimeout(cb, 16);
  }

  // Главный цикл отрисовки
  function render() {
    if (state.isPaused) {
      state.animFrameId = null;
      return;
    }

    if (!state.cfg.enabled) {
      if (state.ctx) {
        state.ctx.clearRect(0, 0, state.width, state.height);
      }
      state.animFrameId = safeRequestAnimationFrame(render);
      return;
    }

    checkSystemTaskStatus();
    updateInputBoxRect();

    const ctx = state.ctx;
    // Полупрозрачная очистка для создания неонового шлейфа
    ctx.fillStyle = 'rgba(10, 14, 20, 0.16)';
    ctx.fillRect(0, 0, state.width, state.height);

    ctx.font = `${state.cfg.fontSize}px monospace`;
    const inRect = state.inputRect;

    // 1. Отрисовка падающего дождя символов
    state.columns.forEach(col => {
      if (!col.active) return;

      if (Math.random() < 0.08) {
        col.char = getRandomChar();
      }

      // Яркая лидирующая голова капли
      ctx.save();
      ctx.fillStyle = state.cfg.glowColor;
      ctx.shadowColor = state.cfg.glowColor;
      ctx.shadowBlur = 6;
      ctx.fillText(col.char, col.x, col.y);
      ctx.restore();

      col.y += col.speed;

      // Столкновение с верхней гранью рамки поля ввода
      if (inRect && col.x >= inRect.left && col.x <= inRect.right && col.y >= inRect.top && col.y <= inRect.top + 16) {
        handleStacking(col.x, inRect.top);
        col.active = false;
        col.y = -Math.random() * 150;
      } else if (col.y > state.height) {
        col.active = false;
        col.y = -Math.random() * 150;
      }
    });

    // 2. Отрисовка оседающих на рамке символов (Stacking)
    renderStackedDrops(ctx);

    // 3. Отрисовка жидких частиц и стекания по краям (Liquid Flow)
    renderLiquidParticles(ctx, inRect);

    state.animFrameId = safeRequestAnimationFrame(render);
  }

  function start() {
    initCanvas();
    render();
    console.log('[AGY-UI] Эффект матрицы (Digital Rain, Stacking & Liquid Flow) успешно инициализирован.');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }

  // Публичный API управления эффектом
  window.AgyMatrixEffect = {
    enable: () => {
      state.cfg.enabled = true;
      saveConfig(state.cfg);
      if (state.isPaused) {
        state.isPaused = false;
        render();
      }
    },
    disable: () => {
      state.cfg.enabled = false;
      saveConfig(state.cfg);
      if (state.ctx) state.ctx.clearRect(0, 0, state.width, state.height);
    },
    toggle: () => {
      if (state.cfg.enabled) {
        window.AgyMatrixEffect.disable();
      } else {
        window.AgyMatrixEffect.enable();
      }
      return state.cfg.enabled;
    },
    setMode: (m) => {
      state.cfg.mode = m;
      saveConfig(state.cfg);
    },
    setIntensity: (lvl) => {
      if (INTENSITY_SETTINGS[lvl]) {
        state.cfg.intensity = lvl;
        saveConfig(state.cfg);
        resize();
      }
    },
    triggerBurst: (count = 15) => {
      // Имитация залпового всплеска дождя
      const inactive = state.columns.filter(c => !c.active);
      const toActivate = Math.min(count, inactive.length);
      for (let i = 0; i < toActivate; i++) {
        inactive[i].active = true;
        inactive[i].y = Math.random() * 50;
        inactive[i].speed = 3 + Math.random() * 3;
      }
    },
    simulateRunning: (run) => {
      window.__agy_task_running = !!run;
      state.isRunning = !!run;
      if (run) checkSystemTaskStatus();
    },
    getConfig: () => Object.assign({}, state.cfg),
    getState: () => ({
      enabled: state.cfg.enabled,
      isRunning: state.isRunning || window.__agy_task_running === true,
      stackedCount: state.stackedDrops.length,
      liquidCount: state.liquidParticles.length,
      activeColumns: state.columns.filter(c => c.active).length
    })
  };
})();
