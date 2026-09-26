/* ============================================================================
   物品图鉴：读取 data/items.json，按稀有度 / 类型 / 关键词筛选。
   悬停提示框模仿游戏里 SkyBlock GUI 的暗色提示框。
   ========================================================================== */
(function () {
  'use strict';

  var grid = document.getElementById('itemGrid');
  if (!grid) return;

  var chipsBox = document.getElementById('itemFilters');
  var countBox = document.getElementById('itemCount');
  var searchBox = document.getElementById('itemSearch');

  var STAT_LABELS = {
    damage: '伤害', strength: '力量', crit_chance: '暴击率', crit_damage: '暴击伤害',
    health: '生命', defense: '防御', speed: '速度', intelligence: '智力',
    mana: '魔力', max_mana: '最大魔力', ferocity: '凶暴', ability_damage: '技能伤害',
    true_defense: '真实防御', attack_speed: '攻速', bonus_attack_speed: '攻速加成',
    magic_find: '魔法寻宝', pet_luck: '宠物幸运', health_regen: '生命回复',
    sea_creature_chance: '海怪几率', true_damage: '真实伤害', vitality: '活力'
  };

  var state = { rarity: '*', type: '*', q: '' };
  var all = [];
  var meta = null;

  function statLabel(key) {
    if (STAT_LABELS[key]) return STAT_LABELS[key];
    return key.replace(/_/g, ' ').replace(/\b\w/g, function (m) { return m.toUpperCase(); });
  }

  function money(n) {
    if (!n) return null;
    if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
    return String(n);
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function tipHTML(it) {
    var h = '<div class="name" style="color:' + esc(it.rarity_color) + '">' + esc(it.name) + '</div>';
    h += '<div class="rar" style="color:' + esc(it.rarity_color) + '">' + esc(it.rarity_label) + ' ' + esc(it.type_label) + '</div>';
    var stats = Object.keys(it.stats || {});
    if (stats.length) {
      h += '<ul>';
      stats.forEach(function (k) {
        var v = it.stats[k];
        var txt = typeof v === 'number' ? (v >= 0 ? '+' + v : String(v)) : String(v);
        var suffix = /chance|crit|find|luck|chance_/.test(k) ? '%' : '';
        h += '<li>' + esc(statLabel(k)) + ' ' + esc(txt) + suffix + '</li>';
      });
      h += '</ul>';
    }
    if (it.lore && it.lore.length) {
      h += '<div class="lore">' + it.lore.map(esc).join('<br>') + '</div>';
    }
    var prices = [];
    if (it.buy_price) prices.push('买入 ' + money(it.buy_price));
    if (it.sell_price) prices.push('卖出 ' + money(it.sell_price));
    if (it.reforgeable) prices.push('可重铸');
    if (prices.length) h += '<div class="price">' + esc(prices.join('　')) + '</div>';
    return h;
  }

  function render() {
    var q = state.q.trim().toLowerCase();
    var list = all.filter(function (it) {
      if (state.rarity !== '*' && it.rarity !== state.rarity) return false;
      if (state.type !== '*' && it.type !== state.type) return false;
      if (q && it.name.toLowerCase().indexOf(q) < 0 && it.id.indexOf(q) < 0) return false;
      return true;
    });

    if (countBox) countBox.textContent = list.length + ' / ' + all.length;

    if (!list.length) {
      grid.innerHTML = '<div class="item" style="grid-column:1/-1;padding:40px;color:var(--ink-mute)">没有符合条件的物品。</div>';
      return;
    }

    grid.innerHTML = list.map(function (it) {
      return '<figure class="item">' +
        '<img src="' + esc(it.icon) + '" alt="" loading="lazy">' +
        '<figcaption class="n" style="color:' + esc(it.rarity_color) + '">' + esc(it.name) + '</figcaption>' +
        '<div class="r" style="color:' + esc(it.rarity_color) + '">' + esc(it.rarity_label) + '</div>' +
        '<div class="t">' + esc(it.type_label) + (it.slot_label && it.slot_label !== it.type_label ? ' · ' + esc(it.slot_label) : '') + '</div>' +
        '<div class="tip">' + tipHTML(it) + '</div>' +
        '</figure>';
    }).join('');
  }

  function chips() {
    if (!chipsBox) return;
    var html = '<button class="chip is-on" data-kind="rarity" data-value="*">全部<span class="cn">稀有度</span></button>';
    meta.rarities.forEach(function (r) {
      var n = all.filter(function (it) { return it.rarity === r.id; }).length;
      if (!n) return;
      html += '<button class="chip" data-kind="rarity" data-value="' + esc(r.id) + '" ' +
        'style="--c:' + esc(r.color) + '">' + esc(r.label) + '</button>';
    });
    html += '<button class="chip is-on" data-kind="type" data-value="*">全部<span class="cn">类型</span></button>';
    meta.types.forEach(function (t) {
      var n = all.filter(function (it) { return it.type === t.id; }).length;
      if (!n) return;
      html += '<button class="chip" data-kind="type" data-value="' + esc(t.id) + '">' + esc(t.label) + '</button>';
    });
    html += '<span class="count" id="itemCount"></span>';
    chipsBox.innerHTML = html;
    countBox = document.getElementById('itemCount');

    chipsBox.addEventListener('click', function (e) {
      var btn = e.target.closest('.chip');
      if (!btn) return;
      var kind = btn.dataset.kind;
      var value = btn.dataset.value;
      state[kind] = value;
      [].slice.call(chipsBox.querySelectorAll('.chip[data-kind="' + kind + '"]')).forEach(function (b) {
        b.classList.toggle('is-on', b === btn);
      });
      render();
    });
  }

  if (searchBox) {
    searchBox.addEventListener('input', function () {
      state.q = searchBox.value;
      render();
    });
  }

  fetch('data/items.json')
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (data) {
      all = data.items || [];
      meta = data.meta || { rarities: [], types: [] };
      chips();
      render();
    })
    .catch(function (err) {
      grid.innerHTML = '<div class="item" style="grid-column:1/-1;padding:40px;color:var(--ink-mute)">' +
        '图鉴数据加载失败（' + esc(err.message) + '）。<br>' +
        '图鉴需要经由本地 HTTP 服务访问：在项目根目录执行 <code>python web/serve.py</code>，' +
        '然后打开 <code>http://127.0.0.1:8100</code>。</div>';
    });
})();
