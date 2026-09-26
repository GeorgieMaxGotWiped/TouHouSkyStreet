/* ============================================================================
   首页标题画面的菜单 —— 与游戏主菜单同一套操作：
   上下键移动（鼠标悬停也会切换）、Enter / Z / 空格确认、数字键直选。
   ========================================================================== */
(function () {
  'use strict';

  var menu = document.querySelector('.title-menu');
  if (!menu) return;

  var rows = [].slice.call(menu.querySelectorAll('.menu-row'));
  if (!rows.length) return;

  var idx = 0;

  rows.forEach(function (row, i) {
    row.style.setProperty('--i', i);
    row.addEventListener('mouseenter', function () { select(i); });
    row.addEventListener('focus', function () { select(i); });
  });

  function select(i) {
    idx = (i + rows.length) % rows.length;
    rows.forEach(function (row, k) {
      row.classList.toggle('is-selected', k === idx);
    });
  }

  function activate(i) {
    var row = rows[i];
    if (!row) return;
    if (row.tagName === 'A' && row.href) row.click();
    else row.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  }

  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var key = e.key;

    if (key === 'ArrowDown' || key === 'ArrowUp') {
      e.preventDefault();
      select(idx + (key === 'ArrowDown' ? 1 : -1));
      return;
    }
    if (key === 'Enter' || key === ' ' || key === 'z' || key === 'Z') {
      e.preventDefault();
      activate(idx);
      return;
    }
    if (key >= '1' && key <= '9') {
      var n = parseInt(key, 10) - 1;
      if (n < rows.length) {
        e.preventDefault();
        select(n);
        activate(n);
      }
    }
  });

  select(0);

  // 入场：逐行错位淡入（对应 CSS 里的 --i 延时）
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      menu.classList.add('is-ready');
    });
  });
})();