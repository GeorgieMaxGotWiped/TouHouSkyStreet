/* 画廊：加载 gallery.json，按分类筛选 + 点击放大 */
(function () {
  var state = { cat: "all", items: [], meta: null };
  var grid = document.getElementById("gallery-grid");
  var filterBar = document.getElementById("filter-cat");

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function buildFilters(cats) {
    filterBar.innerHTML = "";
    var mk = function (id, label) {
      var b = el("button", "filter-btn", label);
      b.dataset.value = id;
      b.addEventListener("click", function () { state.cat = id; render(); });
      filterBar.appendChild(b);
    };
    mk("all", "全部");
    cats.forEach(function (c) { mk(c.id, c.label); });
  }

  function render() {
    grid.innerHTML = "";
    var list = state.items.filter(function (it) { return state.cat === "all" || it.category === state.cat; });
    list.forEach(function (it) {
      var card = el("figure", "gallery-card");
      var img = document.createElement("img");
      img.src = it.image; img.alt = it.name; img.loading = "lazy";
      var cap = el("figcaption", "", it.name);
      card.appendChild(img);
      card.appendChild(cap);
      card.addEventListener("click", function () { openLightbox(it); });
      grid.appendChild(card);
    });
    document.querySelectorAll(".filter-btn").forEach(function (b) {
      b.classList.toggle("active", b.dataset.value === state.cat);
    });
  }

  function openLightbox(it) {
    var lb = document.getElementById("lightbox");
    document.getElementById("lightbox-img").src = it.image;
    document.getElementById("lightbox-img").alt = it.name;
    document.getElementById("lightbox-cap").textContent = it.name;
    lb.hidden = false;
  }
  function closeLightbox() { document.getElementById("lightbox").hidden = true; }

  document.getElementById("lightbox-close").addEventListener("click", closeLightbox);
  document.getElementById("lightbox").addEventListener("click", function (e) {
    if (e.target.id === "lightbox") closeLightbox();
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeLightbox(); });

  fetch("data/gallery.json")
    .then(function (r) { if (!r.ok) throw new Error("load"); return r.json(); })
    .then(function (data) {
      state.items = data.items;
      state.meta = data;
      document.getElementById("total").textContent = data.items.length;
      buildFilters(data.categories || []);
      render();
    })
    .catch(function () {
      grid.innerHTML = "<p style='color:var(--c-text-dim);'>画廊数据加载失败，请通过 HTTP 服务访问本站。</p>";
    });
})();
