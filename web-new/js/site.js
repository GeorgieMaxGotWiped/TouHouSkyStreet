/* ============================================================================
   全站公共脚本
     1. 滚动进场（.reveal -> .is-in）
     2. 站内跳转时的「关卡标题卡」转场
     3. 按当前文件给导航打 aria-current
   ========================================================================== */
(function () {
  'use strict';

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* ---------- 1. 滚动进场 ---------- */
  var reveals = [].slice.call(document.querySelectorAll('.reveal'));
  if (reveals.length) {
    if (!('IntersectionObserver' in window) || reduce.matches) {
      reveals.forEach(function (el) { el.classList.add('is-in'); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        });
      }, { rootMargin: '0px 0px -12% 0px', threshold: 0.05 });
      reveals.forEach(function (el) { io.observe(el); });
    }
  }

  /* ---------- 2. 转场：一张标题卡，跨页接力 ----------
     点击 -> 本页把卡淡入（内容 260ms 落定）-> 存进 sessionStorage -> 跳转
     新页面：<head> 内联脚本先加 html.warp-in 让遮罩从首帧生效，
             js/warp-in.js 紧跟 #warp 把同一张卡填成终态，
             这里只负责把它淡出。
     两页之间卡是连续的，没有「旧页消失 / 新页出现」的跳变。            */
  var doc = document.documentElement;
  var card = document.getElementById('warp');
  var current = location.pathname.split('/').pop() || 'index.html';
  var CARD_MIN_MS = 280;     // 必须 >= 卡面内容动画落定时间（260ms），否则会被硬切
  var CARD_FADE_MS = 240;
  var WARP_KEY = 'warp-card';

  function fillCard(no, cn, en) {
    card.querySelector('.no').textContent = no;
    card.querySelector('.cn').textContent = cn;
    card.querySelector('.en').textContent = en;
  }

  function playCard(link, href) {
    var no = link.dataset.cardNo || '';
    var cn = link.dataset.cardCn || '';
    var en = link.dataset.cardEn || '';

    if (!card || reduce.matches || !cn) { location.href = href; return; }

    fillCard(no, cn, en);
    card.classList.add('is-on');
    card.setAttribute('aria-hidden', 'false');

    try {
      sessionStorage.setItem(WARP_KEY, JSON.stringify({ no: no, cn: cn, en: en, t: Date.now() }));
    } catch (err) { /* 写不了就退化成只在本页闪一下，不影响跳转 */ }

    window.setTimeout(function () { location.href = href; }, CARD_MIN_MS);
  }

  /* 上一页留下的卡（内容由紧跟 #warp 的 js/warp-in.js 在首帧就填好）：接着显示，再淡出 */
  function resumeCard() {
    if (!doc.classList.contains('warp-in')) return;

    // 卡面没接上（脚本被拦、或从外部直接进来）就别把页面盖住
    if (!card || !card.querySelector('.cn').textContent) {
      doc.classList.remove('warp-in');
      return;
    }

    var fade = function () {
      // 等两帧，确认这张卡已经画到屏幕上，再开始淡出
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          var dur = reduce.matches ? 0 : CARD_FADE_MS;
          card.style.transition = 'opacity ' + dur + 'ms linear';
          card.style.opacity = '0';
          window.setTimeout(function () {
            doc.classList.remove('warp-in');
            card.style.transition = '';
            card.style.opacity = '';
          }, dur + 60);
        });
      });
    };

    // 等字体就位再揭幕：字体没到就淡出的话，会看到「卡在淡出、字在变形」叠在一起。
    // 但资源慢时不能让卡一直挂着，350ms 封顶。
    var settled = false;
    var go = function () { if (settled) return; settled = true; fade(); };
    if (document.fonts && document.fonts.ready && document.fonts.ready.then) {
      document.fonts.ready.then(go);
      window.setTimeout(go, 350);
    } else {
      go();
    }
  }

  resumeCard();

  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

    var link = e.target.closest && e.target.closest('a[href]');
    if (!link) return;
    if (link.target && link.target !== '_self') return;
    if (link.hasAttribute('download')) return;

    var href = link.getAttribute('href');
    if (!href || href.charAt(0) === '#') return;
    if (/^[a-z]+:/i.test(href) && href.indexOf(location.protocol) !== 0) return;
    if (!/\.html?($|[?#])/i.test(href)) return;

    var target = href.split('#')[0].split('?')[0];
    if (target === current) {
      e.preventDefault();
      return;
    }

    e.preventDefault();
    playCard(link, href);
  });

  /* 从 bfcache 返回时，别把上一页那张卡留在屏幕上 */
  window.addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    doc.classList.remove('warp-in');
    if (!card) return;
    card.classList.remove('is-on');
    card.style.transition = '';
    card.style.opacity = '';
    card.setAttribute('aria-hidden', 'true');
  });

  /* ---------- 3. 导航当前项 ---------- */
  var here = current.replace(/\.html?$/i, '');
  [].slice.call(document.querySelectorAll('.nav-list a')).forEach(function (a) {
    var href = (a.getAttribute('href') || '').replace(/\.html?$/i, '');
    if (href === here) a.setAttribute('aria-current', 'page');
  });

  /* ---------- 页尾年份 ---------- */
  [].slice.call(document.querySelectorAll('[data-year]')).forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });
})();