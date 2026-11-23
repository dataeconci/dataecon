(function () {
  'use strict';
  var openMenu = null;
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function closeAll() { if (openMenu) { openMenu.classList.remove('open'); var dd = openMenu.querySelector('.ac-dd'); if (dd) dd.remove(); openMenu = null; } }
  document.addEventListener('click', function (e) { if (openMenu && !openMenu.contains(e.target)) closeAll(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeAll(); });

  function build(item, close) {
    if (item.sep) { var s = document.createElement('div'); s.className = 'ac-sep'; return s; }
    var d = document.createElement('div'); d.className = 'ac-it';
    var dis = typeof item.dis === 'function' ? item.dis() : !!item.dis;
    var chk = typeof item.chk === 'function' ? item.chk() : null;
    if (dis) d.classList.add('dis');
    d.innerHTML = '<span class="ac-ck">' + (chk ? '&#10003;' : '') + '</span><span class="ac-l">' + esc(item.l) + '</span><span class="ac-k">' + esc(item.k || (item.sub ? '▸' : '')) + '</span>';
    if (item.sub) {
      d.classList.add('has-sub');
      var sub = document.createElement('div'); sub.className = 'ac-dd ac-subdd';
      item.sub.forEach(function (it) { sub.appendChild(build(it, close)); });
      d.appendChild(sub);
    } else if (!dis) {
      d.addEventListener('click', function (e) { e.stopPropagation(); close(); if (item.f) item.f(); });
    }
    return d;
  }

  function menubar(el, defs) {
    el.innerHTML = '';
    el.classList.add('ac-bar');
    Object.keys(defs).forEach(function (label) {
      var m = document.createElement('span'); m.className = 'ac-m'; m.textContent = label;
      function show() {
        closeAll();
        var items = typeof defs[label] === 'function' ? defs[label]() : defs[label];
        var dd = document.createElement('div'); dd.className = 'ac-dd';
        items.forEach(function (it) { dd.appendChild(build(it, closeAll)); });
        m.appendChild(dd); m.classList.add('open'); openMenu = m;
      }
      m.addEventListener('click', function (e) {
        if (e.target.closest('.ac-dd')) return;
        if (openMenu === m) closeAll(); else show();
      });
      m.addEventListener('mouseenter', function () { if (openMenu && openMenu !== m) show(); });
      el.appendChild(m);
    });
  }

  function modal(o) {
    var ov = document.createElement('div'); ov.className = 'ac-ov';
    var w = document.createElement('div'); w.className = 'ac-modal' + (o.wide ? ' wide' : '');
    w.innerHTML = '<div class="ac-mh"><span>' + esc(o.title || '') + '</span><button type="button" class="ac-x">&#10005;</button></div><div class="ac-mb">' + (o.html || '') + '</div><div class="ac-mf"></div>';
    ov.appendChild(w); document.body.appendChild(ov);
    function close() { ov.remove(); }
    w.querySelector('.ac-x').onclick = close;
    ov.addEventListener('mousedown', function (e) { if (e.target === ov) close(); });
    var foot = w.querySelector('.ac-mf');
    (o.buttons || [{ t: 'Fermer' }]).forEach(function (b) {
      var bt = document.createElement('button'); bt.type = 'button'; bt.textContent = b.t; bt.className = b.primary ? 'ac-btn pri' : 'ac-btn';
      bt.onclick = function () { var keep = b.f ? b.f(w) : null; if (keep !== false) close(); };
      foot.appendChild(bt);
    });
    return { el: w, close: close };
  }

  function toast(msg) {
    var t = document.createElement('div'); t.className = 'ac-toast'; t.textContent = msg; document.body.appendChild(t);
    setTimeout(function () { t.classList.add('out'); }, 2200); setTimeout(function () { t.remove(); }, 2700);
  }

  function download(name, text, mime) {
    var b = new Blob([text], { type: mime || 'text/plain;charset=utf-8' });
    var a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = name; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  function pick(accept, cb, asText) {
    var i = document.createElement('input'); i.type = 'file'; i.accept = accept || '';
    i.onchange = function () {
      var f = i.files[0]; if (!f) return; var r = new FileReader();
      r.onload = function () { cb(r.result, f.name); }; r.readAsText(f);
    };
    i.click();
  }

  function csvParse(text) {
    var rows = [], row = [], cur = '', q = false, sep = (text.split('\n')[0].split(';').length > text.split('\n')[0].split(',').length) ? ';' : ',';
    for (var i = 0; i < text.length; i++) {
      var c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
      else if (c === '"') q = true;
      else if (c === sep) { row.push(cur); cur = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cur); cur = ''; if (row.length > 1 || row[0] !== '') rows.push(row); row = []; }
      else cur += c;
    }
    if (cur !== '' || row.length) { row.push(cur); rows.push(row); }
    return rows;
  }

  window.AppChrome = { menubar: menubar, modal: modal, toast: toast, download: download, pick: pick, csvParse: csvParse, esc: esc, closeAll: closeAll };
})();
