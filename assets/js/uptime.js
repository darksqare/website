/* Uptime counter in the header line. Change START to when your server went up. */
(function () {
  var START = new Date("2026-10-19T00:00:00Z");
  var el = document.getElementById("uptime");
  if (!el) return;
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function tick() {
    var s = Math.max(0, Math.floor((Date.now() - START.getTime()) / 1000));
    var d = Math.floor(s / 86400);
    var h = Math.floor((s % 86400) / 3600);
    var m = Math.floor((s % 3600) / 60);
    el.textContent = d + "d " + pad(h) + ":" + pad(m) + ":" + pad(s % 60);
  }
  tick();
  setInterval(tick, 1000);
})();
