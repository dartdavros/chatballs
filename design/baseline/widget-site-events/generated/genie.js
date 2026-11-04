window.EventGenie=function(shell,btn){
  var frame=shell.firstElementChild,appearance={rgb:[15,155,142]},panelRadius=()=>shell.parentElement.clientWidth<=480?0:24,launcherRadius=()=>28;
    // Эффект джина: окно втягивается в кнопку, вытягивая горловину, — как в
  // доке macOS. Аффинными трансформациями такое не получить: там изгиб, а не
  // масштаб. Поэтому силуэт рисуется контуром SVG и перестраивается на каждом
  // кадре. Сам iframe в анимации не участвует — менять его размеры покадрово
  // нельзя, внутри переворачивалась бы вёрстка.
  var GENIE_OPEN_MS = 300;
  var GENIE_CLOSE_MS = 240;
  var SVG_NS = "http://www.w3.org/2000/svg";
  var genieSvg = null, geniePath = null, genieRaf = 0;

  function ensureGenie() {
    if (genieSvg) return;
    genieSvg = document.createElementNS(SVG_NS, "svg");
    genieSvg.style.cssText = "position:fixed;left:0;top:0;width:100%;height:100%;z-index:2147482999;pointer-events:none;display:none;overflow:visible;";
    geniePath = document.createElementNS(SVG_NS, "path");
    geniePath.style.filter = "drop-shadow(0 12px 40px rgba(0,0,0,0.18))";
    genieSvg.appendChild(geniePath);
    document.body.appendChild(genieSvg);
  }

  function smooth(x) {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    return x * x * (3 - 2 * x);
  }

  function mix(a, b, k) { return a + (b - a) * k; }

  function shapeAt(p, panel, icon) {
    // Низ втягивается раньше верха — из-за этого и появляется горловина.
    var pb = smooth(Math.min(1, p * 1.7));
    var pt = smooth(Math.max(0, (p - 0.3) / 0.7));

    var topY = mix(panel.top, icon.top, pt);
    var topHalf = mix(panel.half, icon.half, pt);
    var topCx = mix(panel.cx, icon.cx, pt);
    var topR = Math.min(mix(panel.radius, icon.radius, pt), topHalf);

    var bottomY = mix(panel.bottom, icon.bottom, pb);
    var bottomHalf = mix(panel.half, icon.half, pb);
    var bottomCx = mix(panel.cx, icon.cx, pb);
    var bottomR = Math.min(mix(panel.radius, icon.radius, pb), bottomHalf);

    return {
      topY: topY, topL: topCx - topHalf, topRt: topCx + topHalf, topR: topR,
      bottomY: bottomY, bottomL: bottomCx - bottomHalf, bottomRt: bottomCx + bottomHalf, bottomR: bottomR,
      // Плечо кривой: чем длиннее горловина, тем мягче изгиб.
      k: Math.max(0, (bottomY - topY) * 0.45),
      fill: pt
    };
  }

  function pathOf(g, dx, dy) {
    var tl = g.topL - dx, tr = g.topRt - dx, ty = g.topY - dy;
    var bl = g.bottomL - dx, br = g.bottomRt - dx, by = g.bottomY - dy;
    return "M" + (tl + g.topR) + "," + ty +
      "H" + (tr - g.topR) +
      "Q" + tr + "," + ty + " " + tr + "," + (ty + g.topR) +
      "C" + tr + "," + (ty + g.k) + " " + br + "," + (by - g.k) + " " + br + "," + (by - g.bottomR) +
      "Q" + br + "," + by + " " + (br - g.bottomR) + "," + by +
      "H" + (bl + g.bottomR) +
      "Q" + bl + "," + by + " " + bl + "," + (by - g.bottomR) +
      "C" + bl + "," + (by - g.k) + " " + tl + "," + (ty + g.k) + " " + tl + "," + (ty + g.topR) +
      "Q" + tl + "," + ty + " " + (tl + g.topR) + "," + ty + "Z";
  }

  function paintGenie(p, panel, icon) {
    var g = shapeAt(p, panel, icon);
    geniePath.setAttribute("d", pathOf(g, 0, 0));
    geniePath.setAttribute(
      "fill",
      "rgb(" + Math.round(mix(255, appearance.rgb[0], g.fill)) + "," +
        Math.round(mix(255, appearance.rgb[1], g.fill)) + "," +
        Math.round(mix(255, appearance.rgb[2], g.fill)) + ")"
    );
    // Контур режет контейнер. Его собственная геометрия не меняется, поэтому
    // координаты контура честно переводятся в его систему простым сдвигом.
    var box = shell.getBoundingClientRect();
    shell.style.clipPath = "path('" + pathOf(g, box.left, box.top) + "')";

    // Окно внутри повторяет форму: ширина идёт за горловиной, высота — за
    // длиной силуэта, наклон — за уходом центра к кнопке. Содержимое из-за
    // этого сжимается и заваливается вместе с окном, а не стоит на месте.
    var width = Math.max(1, box.width);
    var height = Math.max(1, box.height);
    var sx = Math.max(0.001, (g.topRt - g.topL) / width);
    var sy = Math.max(0.001, (g.bottomY - g.topY) / height);
    var lean = ((g.bottomL + g.bottomRt) / 2 - (g.topL + g.topRt) / 2) /
      Math.max(1, g.bottomY - g.topY);
    var skew = Math.atan((sy / sx) * lean) * 180 / Math.PI;
    frame.style.transform = "translate(" + (g.topL - box.left) + "px," + (g.topY - box.top) + "px)" +
      " scale(" + sx + "," + sy + ") skewX(" + skew + "deg)";
    frame.style.borderRadius = Math.round(mix(panelRadius(), icon.radius, g.fill)) + "px";
  }

  function restPanel() {
    shell.style.clipPath = "none";
    frame.style.transform = "none";
    frame.style.borderRadius = panelRadius() + "px";
  }

  function playGenie(from, to, duration, panel, icon, done) {
    ensureGenie();
    genieSvg.style.display = "block";
    var started = 0;
    window.cancelAnimationFrame(genieRaf);
    function step(now) {
      if (!started) started = now;
      var linear = Math.min(1, (now - started) / duration);
      // Мягкий вход и выход: резкий старт читается как рывок.
      var eased = linear < 0.5 ? 2 * linear * linear : 1 - Math.pow(-2 * linear + 2, 2) / 2;
      paintGenie(mix(from, to, eased), panel, icon);
      if (linear < 1) genieRaf = window.requestAnimationFrame(step);
      else done();
    }
    genieRaf = window.requestAnimationFrame(step);
  }

  function panelRect() {
    var box = shell.getBoundingClientRect();
    return {
      top: box.top,
      bottom: box.bottom,
      cx: box.left + box.width / 2,
      half: box.width / 2,
      radius: panelRadius()
    };
  }

  function iconRect() {
    var box = btn.getBoundingClientRect();
    return {
      top: box.top,
      bottom: box.bottom,
      cx: box.left + box.width / 2,
      half: box.width / 2,
      radius: launcherRadius()
    };
  }

  return {play:function(open,done){ensureGenie();btn.style.opacity='0';btn.style.pointerEvents='none';
    if(open)paintGenie(1,panelRect(),iconRect());
    playGenie(open?1:0,open?0:1,open?GENIE_OPEN_MS:GENIE_CLOSE_MS,panelRect(),iconRect(),function(){
      genieSvg.style.display='none';restPanel();btn.style.opacity='';btn.style.pointerEvents='';done();});},
    dispose:function(){window.cancelAnimationFrame(genieRaf);if(genieSvg)genieSvg.remove();}};
};