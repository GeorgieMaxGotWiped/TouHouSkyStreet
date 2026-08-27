/* 物品图鉴：加载 items.json 并按罕见度/类型筛选渲染 */
(function () {
  var state = { rarity: "all", type: "all", items: [], meta: null };

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function buildFilterBar(containerId, values, key, label) {
    var bar = document.getElementById(containerId);
    bar.innerHTML = "";
    var all = el("button", "filter-btn active", label);
    all.dataset.value = "all";
    all.addEventListener("click", function () { setFilter(key, "all"); });
    bar.appendChild(all);
    values.forEach(function (v) {
      var b = el("button", "filter-btn", v.label);
      b.dataset.value = v.id;
      b.addEventListener("click", function () { setFilter(key, v.id); });
      bar.appendChild(b);
    });
  }

  function setFilter(key, value) {
    state[key] = value;
    render();
  }

  function rarityHex(r) {
    var m = state.meta.rarities.find(function (x) { return x.id === r; });
    return m ? m.color : "#888888";
  }

  function fmtStats(item) {
    var keys = Object.keys(item.stats || {});
    if (!keys.length) return "";
    return keys.map(function (k) { return k + " " + item.stats[k]; }).join("  ·  ");
  }

  function fmtEffects(item) {
    var keys = Object.keys(item.effects || {});
    if (!keys.length) return "";
    return keys.map(function (k) { return k + ": " + item.effects[k]; }).join("  ·  ");
  }

  function card(item) {
    var div = el("div", "item-card");
    var rarity = el("div", "rarity", item.rarity_label.toUpperCase());
    rarity.style.color = rarityHex(item.rarity);
    div.appendChild(rarity);
    div.appendChild(el("h4", null, item.name));
    var type = item.type_label + (item.slot ? " · " + item.slot_label : "");
    div.appendChild(el("div", "type", type));
    var stats = fmtStats(item) || fmtEffects(item);
    if (stats) div.appendChild(el("div", "stats", stats));
    if (item.lore && item.lore.length) {
      var lore = document.createElement("div");
      lore.className = "lore";
      item.lore.forEach(function (line) {
        var p = document.createElement("div");
        p.textContent = line;
        lore.appendChild(p);
      });
      div.appendChild(lore);
    }
    return div;
  }

  function render() {
    var grid = document.getElementById("items-grid");
    grid.innerHTML = "";
    var list = state.items.filter(function (it) {
      if (state.rarity !== "all" && it.rarity !== state.rarity) return false;
      if (state.type !== "all" && it.item_type !== state.type) return false;
      return true;
    });
    list.forEach(function (it) { grid.appendChild(card(it)); });

    document.getElementById("count-line").textContent =
      "当前显示 " + list.length + " / " + state.items.length + " 件";

    document.querySelectorAll(".filter-btn").forEach(function (btn) {
      var active = false;
      if (btn.closest("#filter-rarity") && btn.dataset.value === state.rarity) active = true;
      if (btn.closest("#filter-type") && btn.dataset.value === state.type) active = true;
      btn.classList.toggle("active", active);
    });
  }

  fetch("data/items.json")
    .then(function (r) { if (!r.ok) throw new Error("加载失败"); return r.json(); })
    .then(function (data) {
      state.items = data.items;
      state.meta = data.meta;
      document.getElementById("total").textContent = data.meta.count;
      buildFilterBar("filter-rarity", data.meta.rarities, "rarity", "全部罕见度");
      buildFilterBar("filter-type", data.meta.types, "type", "全部类型");
      render();
    })
    .catch(function (err) {
      document.getElementById("count-line").textContent =
        "未能加载物品数据（" + err.message + "）。请通过 HTTP 服务访问本站，例如：python -m http.server。";
    });
})();
