/* ============================================================================
   弹幕背景 —— 全站的本体视觉
   一个很轻的自制弹幕引擎：环形 / 螺旋 / 自机狙扇形 三种发射器，
   子弹用游戏配色（青 / 金 / 紫），低透明度铺在内容之下。
   首页会在标题菜单所在的区域留空，避免压住文字。
   尊重 prefers-reduced-motion，标签页隐藏时自动停帧。
   ========================================================================== */
(function () {
  'use strict';

  var canvas = document.getElementById('danmaku');
  if (!canvas) return;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var config = window.DANMAKU || {};
  if (reduceMotion.matches || config.enabled === false) {
    canvas.parentNode.removeChild(canvas);
    return;
  }

  var ctx = canvas.getContext('2d', { alpha: true });
  var W = 0, H = 0, DPR = 1;
  var bullets = [];
  var emitters = [];
  var running = true;
  var last = 0;
  var time = 0;
  var aim = { x: 0, y: 0, tx: 0, ty: 0 };

  var COLORS = {
    sky:    [48, 192, 255],
    gold:   [255, 239, 74],
    purple: [192, 64, 255],
    green:  [48, 255, 128],
    white:  [230, 238, 252]
  };

  var MAX_BULLETS = 420;

  // 首页标题菜单所在的区域：这里不生成子弹，保证菜单干净
  var quiet = null;

  function measure() {
    var parent = canvas.parentNode || document.body;
    var rect = parent.getBoundingClientRect();
    W = Math.max(320, rect.width);
    H = Math.max(320, rect.height);
    DPR = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(W * DPR);
    canvas.height = Math.round(H * DPR);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

    aim.x = aim.tx = W * 0.5;
    aim.y = aim.ty = H * 0.72;

    quiet = document.body.classList.contains('is-title')
      ? { x0: W * 0.04, y0: H * 0.30, x1: W * 0.56, y1: H * 0.78 }
      : null;
  }

  function inQuiet(x, y) {
    return !!quiet && x > quiet.x0 && x < quiet.x1 && y > quiet.y0 && y < quiet.y1;
  }

  function addBullet(x, y, angle, speed, size, key, life) {
    if (bullets.length >= MAX_BULLETS) return;
    if (inQuiet(x, y)) return;
    bullets.push({
      x: x, y: y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      r: size,
      c: COLORS[key] || COLORS.sky,
      a: 1,
      age: 0,
      life: life || 6.5
    });
  }

  function spawnRing(em, dt) {
    em.t -= dt;
    if (em.t > 0) return;
    em.t = em.period;
    var n = em.count;
    em.base += 0.32;
    for (var i = 0; i < n; i++) {
      addBullet(em.x, em.y, em.base + (i / n) * Math.PI * 2, em.speed, em.size, em.color, em.life);
    }
  }

  function spawnSpiral(em, dt) {
    em.t -= dt;
    if (em.t > 0) return;
    em.t = em.period;
    em.base += em.step;
    for (var k = 0; k < em.arms; k++) {
      addBullet(em.x, em.y, em.base + (k / em.arms) * Math.PI * 2, em.speed, em.size, em.color, em.life);
    }
  }

  function spawnAimed(em, dt) {
    em.t -= dt;
    if (em.t > 0) return;
    em.t = em.period;
    var base = Math.atan2(aim.y - em.y, aim.x - em.x);
    var spread = em.spread;
    for (var i = 0; i < em.count; i++) {
      var f = em.count === 1 ? 0 : (i / (em.count - 1) - 0.5) * 2;
      addBullet(em.x, em.y, base + f * spread, em.speed * (1 - Math.abs(f) * 0.18),
                em.size, em.color, em.life);
    }
  }

  function makeEmitters() {
    emitters = [
      // 左上螺旋，青
      { kind: 'spiral', x: W * 0.08, y: H * 0.16, base: 0, step: 0.42, arms: 5,
        period: 0.11, t: 0, speed: 78, size: 2.6, color: 'sky', life: 7 },
      // 右上螺旋，金
      { kind: 'spiral', x: W * 0.92, y: H * 0.24, base: Math.PI, step: -0.36, arms: 4,
        period: 0.13, t: 0.05, speed: 66, size: 2.4, color: 'gold', life: 7 },
      // 下方环形，紫
      { kind: 'ring', x: W * 0.5, y: H * 1.02, base: 0, count: 9,
        period: 1.15, t: 0.4, speed: 88, size: 3, color: 'purple', life: 6 },
      // 左侧自机狙扇形，白
      { kind: 'aimed', x: -10, y: H * 0.5, base: 0, count: 3, spread: 0.30,
        period: 0.62, t: 0.2, speed: 120, size: 2.2, color: 'white', life: 6 },
      // 右侧自机狙扇形，青
      { kind: 'aimed', x: W + 10, y: H * 0.62, base: 0, count: 4, spread: 0.40,
        period: 0.78, t: 0.5, speed: 108, size: 2.2, color: 'sky', life: 6 }
    ];
    if (W < 700) {
      emitters = emitters.slice(0, 3);
      emitters.forEach(function (e) { e.speed *= 0.8; });
    }
  }

  function step(dt) {
    time += dt;

    // 虚拟「自机」缓慢漂移，让自机狙有方向变化
    if (time % 3.2 < dt) {
      aim.tx = W * (0.32 + Math.random() * 0.36);
      aim.ty = H * (0.52 + Math.random() * 0.34);
    }
    aim.x += (aim.tx - aim.x) * Math.min(1, dt * 0.9);
    aim.y += (aim.ty - aim.y) * Math.min(1, dt * 0.9);

    for (var i = 0; i < emitters.length; i++) {
      var em = emitters[i];
      em.x = Math.max(-20, Math.min(W + 20, em.x));
      em.y = Math.max(-20, Math.min(H + 20, em.y));
      if (em.kind === 'ring') spawnRing(em, dt);
      else if (em.kind === 'spiral') spawnSpiral(em, dt);
      else spawnAimed(em, dt);
    }

    for (var j = bullets.length - 1; j >= 0; j--) {
      var b = bullets[j];
      b.age += dt;
      b.x += b.vx * dt;
      b.y += b.vy * dt;
      var life = b.age / b.life;
      b.a = life < 0.12 ? life / 0.12 : (life > 0.78 ? Math.max(0, (1 - life) / 0.22) : 1);
      b.a *= 0.85;
      if (b.age > b.life || b.x < -60 || b.x > W + 60 || b.y < -60 || b.y > H + 60) {
        bullets.splice(j, 1);
      }
    }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < bullets.length; i++) {
      var b = bullets[i];
      var c = b.c;
      // 外圈光晕
      ctx.globalAlpha = b.a * 0.28;
      ctx.fillStyle = 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')';
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.r * 2.5, 0, Math.PI * 2);
      ctx.fill();
      // 弹体
      ctx.globalAlpha = b.a * 0.9;
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
      ctx.fill();
      // 高光
      ctx.globalAlpha = b.a * 0.75;
      ctx.fillStyle = 'rgba(255,255,255,.9)';
      ctx.beginPath();
      ctx.arc(b.x - b.r * 0.25, b.y - b.r * 0.25, Math.max(0.6, b.r * 0.42), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function frame(now) {
    if (!running) return;
    var dt = Math.min(0.05, (now - last) / 1000 || 0);
    last = now;
    step(dt);
    draw();
    requestAnimationFrame(frame);
  }

  function start() {
    if (running) return;
    running = true;
    last = performance.now();
    requestAnimationFrame(frame);
  }

  function stop() {
    running = false;
    ctx.clearRect(0, 0, W, H);
  }

  measure();
  makeEmitters();

  var resizeTimer = 0;
  window.addEventListener('resize', function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      measure();
      makeEmitters();
      bullets.length = 0;
    }, 180);
  }, { passive: true });

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stop();
    else start();
  });

  // 首页标题菜单淡出后弹幕变明显一点
  window.addEventListener('load', function () {
    var screen = document.querySelector('.title-screen');
    if (!screen) return;
    window.addEventListener('scroll', function () {
      var p = Math.min(1, window.scrollY / Math.max(1, screen.offsetHeight * 0.9));
      document.body.classList.toggle('is-title', p < 0.35);
    }, { passive: true });
  });

  start();
})();