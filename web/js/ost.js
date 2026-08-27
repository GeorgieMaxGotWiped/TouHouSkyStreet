/* OST：加载 music.json 渲染曲目列表。当前曲目为空，显示占位。 */
(function () {
  var listEl = document.getElementById("track-list");

  function render(tracks) {
    if (!tracks || !tracks.length) return; // 保留页面上的占位文案
    listEl.innerHTML = "";
    tracks.forEach(function (t) {
      var row = document.createElement("div");
      row.className = "track-row";
      var idx = document.createElement("span");
      idx.className = "track-idx";
      idx.textContent = t.idx != null ? String(t.idx).padStart(2, "0") : "";
      var info = document.createElement("div");
      info.className = "track-info";
      var title = document.createElement("div");
      title.className = "track-title";
      title.textContent = t.title;
      var sub = document.createElement("div");
      sub.className = "track-sub";
      sub.textContent = t.subtitle || t.album || "";
      info.appendChild(title);
      info.appendChild(sub);
      var play = document.createElement("button");
      play.className = "ctrl";
      play.textContent = "▶";
      if (t.src) { play.removeAttribute("disabled"); }
      else { play.setAttribute("disabled", ""); play.title = "音源整理中"; }
      row.appendChild(idx);
      row.appendChild(info);
      row.appendChild(play);
      listEl.appendChild(row);
    });
  }

  fetch("data/music.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      document.querySelector(".player-track").textContent =
        (data.tracks && data.tracks.length) ? data.tracks[0].title : "曲目整理中";
      document.querySelector(".player-sub").textContent =
        (data.tracks && data.tracks.length) ? ("共 " + data.tracks.length + " 首") : "暂无上线曲目";
      render(data.tracks);
    })
    .catch(function () { /* 保持占位 */ });
})();
