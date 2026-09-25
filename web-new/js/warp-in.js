/* ============================================================================
   跨页接力：把上一页的标题卡在本页首帧原样立起来。
   ----------------------------------------------------------------------------
   必须紧跟在 #warp 之后同步加载。它在解析到卡片的那一刻就把内容填好，
   于是首帧画出来就是完整的一张卡（内容已是终态，不重播入场动画），
   之后交给 js/site.js 淡出。整段转场因此是一张连续的卡，而不是两次跳变。
   <head> 里的内联脚本负责更早一步加上 html.warp-in，让遮罩从首帧就生效。
   ========================================================================== */
(function () {
  'use strict';

  var stored = null;
  try {
    stored = JSON.parse(sessionStorage.getItem('warp-card') || 'null');
    sessionStorage.removeItem('warp-card');
  } catch (err) { return; }

  if (!stored || !stored.cn) return;
  // 隔太久（比如用户在新标签页里翻回来）就别再放这张卡了
  if (typeof stored.t !== 'number' || Date.now() - stored.t > 12000) return;

  var card = document.getElementById('warp');
  if (!card) return;

  card.querySelector('.no').textContent = stored.no || '';
  card.querySelector('.cn').textContent = stored.cn || '';
  card.querySelector('.en').textContent = stored.en || '';
})();