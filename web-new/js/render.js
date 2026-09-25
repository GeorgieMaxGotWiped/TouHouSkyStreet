/* ============================================================================
   数据页渲染：关卡 / 人物 / 曲目
   数据源放在 data/*.json，页面只留骨架；Boss 介绍在 data/bosses.json，按 id 并进来。
   注意：这些页需要经由本地 HTTP 服务访问（python web-new/serve.py）。
   ========================================================================== */
(function () {
  'use strict';

  var page = document.body.getAttribute('data-page');
  if (!page) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function load(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function fail(target, err) {
    if (!target) return;
    target.innerHTML =
      '<div class="wrap"><div class="panel">' +
      '<h3>数据没能加载</h3>' +
      '<p style="margin-top:12px;color:var(--ink-dim)">' + esc(err.message) + '</p>' +
      '<p style="margin-top:12px;color:var(--ink-dim)">本页用 fetch 读取 <code>data/*.json</code>，' +
      '需要经由本地 HTTP 服务访问。请在项目根目录执行 <code>python web-new/serve.py</code>，' +
      '再打开 <code>http://127.0.0.1:8100</code>。</p>' +
      '</div></div>';
  }

  /* ---------------------------------------------------------------- 关卡 */
  /* Boss 介绍单独成文（data/bosses.json），按 id 合进来：
     同一个 Boss 会在多面出现（The Watcher 三面与五面各一次），写进 stages.json 会重复。 */
  function introMap(bossData) {
    var map = {};
    ((bossData && bossData.bosses) || []).forEach(function (b) { map[b.id] = b.intro; });
    return map;
  }

  function renderStages(data, bossData) {
    var list = document.getElementById('stageList');
    var nav = document.getElementById('stageNav');
    var stages = data.stages || [];
    var introById = introMap(bossData);

    if (nav) {
      nav.innerHTML = stages.map(function (s) {
        return '<a class="chip" href="#stage-' + esc(s.key) + '">STAGE ' + esc(s.no) +
               '<span class="cn">' + esc(s.cn) + '</span></a>';
      }).join('');
    }
    if (!list) return;

    list.innerHTML = stages.map(function (s) {
      var bosses = (s.bosses || []).map(function (b) {
        var intro = introById[b.id];
        return '<li class="boss">' +
          '<div class="art"><img src="' + esc(b.art) + '" alt="' + esc(b.name) + '" loading="lazy"></div>' +
          '<div>' +
            '<div class="role">' + esc(b.role) + '</div>' +
            '<h3>' + esc(b.name) + '</h3>' +
            '<div class="title">' + esc(b.title) + ' &middot; ' + esc(b.en) + '</div>' +
            (intro ? '<p class="intro">' + esc(intro) + '</p>' : '') +
          '</div>' +
        '</li>';
      }).join('');

      var spells = (s.spells || []).map(function (sp) {
        return '<li><span class="where">' + esc(sp.where) + '</span>' +
               '<span>' + esc(sp.name) + '</span>' +
               '<span class="by">' + esc(sp.by) + '</span></li>';
      }).join('');

      return '<article class="stage" id="stage-' + esc(s.key) + '">' +
        '<div class="wrap"><div class="stage-grid">' +
          '<aside class="stage-id">' +
            '<div class="no">' + esc(s.no) + '</div>' +
            '<h2>' + esc(s.cn) + '</h2>' +
            '<div class="en">' + esc(s.en) + '</div>' +
            '<div class="music">' +
              '<div><span class="k">道中</span>' + esc(s.music.route) + '</div>' +
              '<div><span class="k">关底</span>' + esc(s.music.boss) + '</div>' +
            '</div>' +
          '</aside>' +
          '<div class="stage-body">' +
            '<div class="stage-open"><img src="' + esc(s.art) + '" alt="' + esc(s.cn) + ' 关卡标题卡" loading="lazy"></div>' +
            '<p class="desc">' + esc(s.desc) + '</p>' +
            '<ul class="boss-list">' + bosses + '</ul>' +
            '<div class="spells"><h4>Spell Cards</h4><ul>' + spells + '</ul></div>' +
          '</div>' +
        '</div></div>' +
      '</article>';
    }).join('');
  }

  /* -------------------------------------------- 人物页 1/3：自机 */
  function renderCharaList(data) {
    var list = document.getElementById('charaList');
    if (!list) return;
    var chars = data.characters || [];
    var total = chars.length;

    list.innerHTML = chars.map(function (c, i) {
      var poem = (c.intro || []).map(function (line) { return '<span>' + esc(line) + '</span>'; }).join('');
      return '<article class="chara-full" id="chara-' + esc(c.key) + '" style="--chara-color:' + esc(c.color) + '">' +
        '<div class="wrap"><div class="inner">' +
          '<div class="art"><img src="' + esc(c.portrait) + '" alt="' + esc(c.label) + ' 立绘" loading="lazy"></div>' +
          '<div>' +
            '<div class="idx">' + String(i + 1).padStart(2, '0') + ' / ' + String(total).padStart(2, '0') + '</div>' +
            '<h2>' + esc(c.en) + '</h2>' +
            '<div class="cn">' + esc(c.cn) + '</div>' +
            '<div class="poem">' + poem + '</div>' +
            '<dl class="spec">' +
              '<dt>自机弹</dt><dd>' + esc(c.shot) + '</dd>' +
              '<dt>特点</dt><dd>' + esc(c.shot_tag) + '</dd>' +
              '<dt>战斗形象</dt><dd><div class="fight"><img src="' + esc(c.fight) + '" alt="' + esc(c.label) + ' 战斗形象" loading="lazy"></div></dd>' +
            '</dl>' +
          '</div>' +
        '</div></div>' +
      '</article>';
    }).join('');
  }

  /* ---------------------------------------------------------------- 曲目 */
  function renderTracks(data) {
    var list = document.getElementById('trackList');
    var note = document.getElementById('trackNote');
    if (note && data.note) note.textContent = data.note;
    if (!list) return;
    var groups = data.groups || [];

    list.innerHTML = groups.map(function (g) {
      var rows = (g.tracks || []).map(function (t, i) {
        return '<li class="track">' +
          '<span class="idx">' + String(i + 1).padStart(2, '0') + '</span>' +
          '<span class="cn">' + esc(t.cn) + '</span>' +
          '<span class="en">' + esc(t.en) + '</span>' +
          '<span class="kind">' + esc(t.kind) + '</span>' +
        '</li>';
      }).join('');
      return '<div class="track-group">' +
        '<div class="who">' +
          '<div class="no">STAGE ' + esc(g.no) + '</div>' +
          '<h3>' + esc(g.cn) + '</h3>' +
          '<div class="en">' + esc(g.en) + '</div>' +
        '</div>' +
        '<ul>' + rows + '</ul>' +
      '</div>';
    }).join('');
  }

  /* -------------------------------------------- 人物页 2/3：页内跳转 */
  function renderCastNav(stagesData) {
    var nav = document.getElementById('castNav');
    if (!nav) return;
    var chips = ['<a class="chip" href="#cast-players">Players' +
                 '<span class="cn">四位自机</span></a>'];
    (stagesData.stages || []).forEach(function (s) {
      chips.push('<a class="chip" href="#cast-' + esc(s.key) + '">STAGE ' + esc(s.no) +
                 '<span class="cn">' + esc(s.cn) + '</span></a>');
    });
    nav.innerHTML = chips.join('');
  }

  /* -------------------------------------------- 人物页 3/3：对手名单 */
  /* 一位一行，按第一次登场的面分组。同一位在多面出现时只占一行：
     The Watcher 三面是道中、五面是开场，这里只立一张，另一处写进脚注。 */
  function renderBossGallery(stagesData, bossData) {
    var host = document.getElementById('bossList');
    if (!host) return;
    var intros = introMap(bossData);

    var order = [];
    var byId = {};
    (stagesData.stages || []).forEach(function (s) {
      (s.bosses || []).forEach(function (b) {
        var rec = byId[b.id];
        if (rec) {
          rec.also.push({ no: s.no, role: b.role });
          return;
        }
        rec = byId[b.id] = { boss: b, stage: s, role: b.role, also: [] };
        order.push(rec);
      });
    });

    var groups = [];
    order.forEach(function (rec) {
      var g = groups[groups.length - 1];
      if (!g || g.key !== rec.stage.key) {
        g = { key: rec.stage.key, stage: rec.stage, items: [] };
        groups.push(g);
      }
      g.items.push(rec);
    });

    var total = order.length;
    var n = 0;

    host.innerHTML = groups.map(function (g) {
      var rows = g.items.map(function (rec) {
        n += 1;
        var b = rec.boss;
        var intro = intros[b.id];
        var also = rec.also.map(function (a) {
          return '同一人在 STAGE ' + esc(a.no) + ' 还会以「' + esc(a.role) + '」再登场一次。';
        }).join(' ');

        return '<li class="boss-row">' +
          '<div class="art"><img src="' + esc(b.art) + '" alt="' + esc(b.name) +
            ' 立绘" loading="lazy"></div>' +
          '<div>' +
            '<div class="idx">' + String(n).padStart(2, '0') + ' / ' +
              String(total).padStart(2, '0') + '</div>' +
            '<div class="role">' + esc(rec.role) + '</div>' +
            '<h3>' + esc(b.name) + '</h3>' +
            '<div class="title">' + esc(b.title) + ' &middot; ' + esc(b.en) + '</div>' +
            (intro ? '<p class="intro">' + esc(intro) + '</p>' : '') +
            (also ? '<p class="also">' + esc(also) + '</p>' : '') +
          '</div>' +
        '</li>';
      }).join('');

      return '<div class="boss-group" id="cast-' + esc(g.key) + '">' +
        '<div class="group-head">' +
          '<span class="no">STAGE ' + esc(g.stage.no) + '</span>' +
          '<h3>' + esc(g.stage.cn) + '</h3>' +
          '<span class="en">' + esc(g.stage.en) + '</span>' +
        '</div>' +
        '<ul class="boss-rows">' + rows + '</ul>' +
      '</div>';
    }).join('');
  }

  /* ------------------------------------------------- 人物页：自机 + 对手 */
  function renderCharacters(charaData, stagesData, bossData) {
    renderCharaList(charaData);
    renderCastNav(stagesData);
    renderBossGallery(stagesData, bossData);
  }

  var PAGES = {
    stages: {
      urls: ['data/stages.json', 'data/bosses.json'],
      run: function (r) { renderStages(r[0], r[1]); },
      target: function () { return document.getElementById('stageList'); }
    },
    characters: {
      urls: ['data/chara.json', 'data/stages.json', 'data/bosses.json'],
      run: function (r) { renderCharacters(r[0], r[1], r[2]); },
      target: function () { return document.getElementById('charaList'); }
    },
    music: {
      urls: ['data/tracks.json'],
      run: function (r) { renderTracks(r[0]); },
      target: function () { return document.getElementById('trackList'); }
    }
  };

  var conf = PAGES[page];
  if (!conf) return;

  Promise.all(conf.urls.map(load))
    .then(conf.run)
    .catch(function (err) { fail(conf.target(), err); });
})();