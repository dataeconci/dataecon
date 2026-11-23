(function () {
  'use strict';

  const root = document.getElementById('pl');
  const OUTIL = root.dataset.outil;
  const NIVEAU = root.dataset.niveau;
  const KEY = 'dataecon_player_' + OUTIL + '_' + NIVEAU;
  const NOMS = { python: 'Python', r: 'R', sql: 'SQL', tableau: 'Tableau', smartpls: 'SmartPLS', powerbi: 'Power BI' };
  const MODES = { python: 'python', r: 'r', sql: 'text/x-sql', tableau: 'text/plain', smartpls: 'text/plain', powerbi: 'text/plain' };
  const FICHIERS = { python: 'exercice.py', r: 'exercice.R', sql: 'requete.sql', tableau: 'analyse.txt', smartpls: 'interpretation.txt', powerbi: 'reponse_powerbi.txt' };

  let lecon = null;
  let idx = -1;            // -1 = page d'introduction ; lecon.concepts.length = fin
  let etat = load();       // { xp, valides:{id:{xp}}, auto }
  let editor = null;
  let essais = 0, indiceVu = false, solutionVue = false, graphiqueGenere = false;

  function load() {
    try { return Object.assign({ xp: 0, valides: {}, auto: false }, JSON.parse(localStorage.getItem(KEY) || '{}')); }
    catch (e) { return { xp: 0, valides: {}, auto: false }; }
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(etat)); } catch (e) {} }

  const $ = (s, r) => (r || document).querySelector(s);
  const esc = (t) => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function md(t) {
    return esc(t).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>');
  }
  function plain(t) { return String(t).replace(/\*\*/g, '').replace(/`/g, '').replace(/\s+/g, ' ').trim(); }

  function cover(outil) {
    const head = "<svg viewBox='0 0 600 340' xmlns='http://www.w3.org/2000/svg' font-family='Inter,Segoe UI,sans-serif'>" +
      "<defs><linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#0b2a4a'/><stop offset='1' stop-color='#1f5f99'/></linearGradient></defs>" +
      "<rect width='600' height='340' fill='url(#bg)'/><g stroke='#fff' stroke-opacity='.07'>" +
      "<path d='M0 85H600M0 170H600M0 255H600M100 0V340M200 0V340M300 0V340M400 0V340M500 0V340'/></g>";
    const foot = '</svg>';
    const win = (x, y, w, h) => `<rect x='${x}' y='${y}' width='${w}' height='${h}' rx='12' fill='#0f1b2b'/><circle cx='${x + 18}' cy='${y + 16}' r='5' fill='#c2a15a'/><circle cx='${x + 36}' cy='${y + 16}' r='5' fill='#5b9bd5'/><circle cx='${x + 54}' cy='${y + 16}' r='5' fill='#8aa0b5'/>`;
    const lines = (x, y, arr) => arr.map((l, i) => `<rect x='${x + l[0]}' y='${y + i * 22}' width='${l[1]}' height='9' rx='4' fill='${l[2]}'/>`).join('');
    if (outil === 'python') {
      return head + win(60, 60, 300, 220) + lines(84, 104, [[0, 70, '#c2a15a'], [18, 150, '#5b9bd5'], [18, 110, '#8fd3a7'], [0, 90, '#c2a15a'], [18, 170, '#5b9bd5'], [18, 120, '#e6edf5'], [0, 60, '#c2a15a'], [18, 140, '#8fd3a7']]) +
        "<g transform='translate(410 90)'><rect x='0' y='60' width='28' height='70' rx='4' fill='#c2a15a'/><rect x='44' y='30' width='28' height='100' rx='4' fill='#fff'/><rect x='88' y='0' width='28' height='130' rx='4' fill='#5b9bd5'/><text x='58' y='170' text-anchor='middle' fill='#fff' font-size='20' font-weight='700'>Python</text><text x='58' y='194' text-anchor='middle' fill='#c9d8e8' font-size='12'>pandas · numpy · matplotlib</text></g>" + foot;
    }
    if (outil === 'r') {
      return head + win(60, 60, 300, 220) + lines(84, 104, [[0, 130, '#5b9bd5'], [18, 160, '#e6edf5'], [18, 100, '#8fd3a7'], [0, 80, '#c2a15a'], [18, 140, '#5b9bd5'], [18, 90, '#e6edf5'], [0, 110, '#c2a15a']]) +
        "<g transform='translate(400 70)'><circle cx='70' cy='70' r='62' fill='#fff' fill-opacity='.1' stroke='#c2a15a' stroke-width='3'/><text x='70' y='95' text-anchor='middle' fill='#fff' font-size='72' font-weight='800'>R</text><polyline points='0,190 30,170 60,178 90,140 130,120 160,90' fill='none' stroke='#c2a15a' stroke-width='4' stroke-linecap='round'/><text x='80' y='230' text-anchor='middle' fill='#c9d8e8' font-size='12'>tidyverse · ggplot2</text></g>" + foot;
    }
    if (outil === 'sql') {
      const cyl = (y, c) => `<ellipse cx='130' cy='${y}' rx='60' ry='16' fill='${c}'/><rect x='70' y='${y}' width='120' height='42' fill='${c}'/><ellipse cx='130' cy='${y + 42}' rx='60' ry='16' fill='${c}'/><ellipse cx='130' cy='${y}' rx='60' ry='16' fill='#fff' fill-opacity='.18'/>`;
      let t = '';
      for (let r = 0; r < 4; r++) for (let c = 0; c < 3; c++) t += `<rect x='${300 + c * 80}' y='${100 + r * 36}' width='78' height='34' fill='${r === 0 ? '#c2a15a' : (r % 2 ? '#ffffff' : '#e6eef7')}' stroke='#cfd9e6'/>`;
      return head + cyl(80, '#c2a15a') + cyl(130, '#5b9bd5') + cyl(180, '#e6edf5') + t +
        "<text x='420' y='280' text-anchor='middle' fill='#fff' font-size='20' font-weight='700'>SQL</text><text x='420' y='302' text-anchor='middle' fill='#c9d8e8' font-size='12'>SELECT · WHERE · GROUP BY</text>" + foot;
    }
    if (outil === 'powerbi') return '<svg viewBox=\'0 0 600 340\' xmlns=\'http://www.w3.org/2000/svg\' font-family=\'Inter,Segoe UI,sans-serif\'><defs><linearGradient id=\'bg\' x1=\'0\' y1=\'0\' x2=\'1\' y2=\'1\'><stop offset=\'0\' stop-color=\'#0b2a4a\'/><stop offset=\'1\' stop-color=\'#1f5f99\'/></linearGradient></defs><rect width=\'600\' height=\'340\' fill=\'url(#bg)\'/><g stroke=\'#fff\' stroke-opacity=\'.07\'><path d=\'M0 85H600M0 170H600M0 255H600M100 0V340M200 0V340M300 0V340M400 0V340M500 0V340\'/></g><rect x=\'96\' y=\'150\' width=\'56\' height=\'90\' rx=\'3\' fill=\'#fff\' fill-opacity=\'.92\'/><rect x=\'170\' y=\'110\' width=\'56\' height=\'130\' rx=\'3\' fill=\'#c2a15a\'/><rect x=\'244\' y=\'70\' width=\'56\' height=\'170\' rx=\'3\' fill=\'#fff\' fill-opacity=\'.92\'/><rect x=\'318\' y=\'125\' width=\'56\' height=\'115\' rx=\'3\' fill=\'#c2a15a\'/><circle cx=\'470\' cy=\'155\' r=\'62\' fill=\'none\' stroke=\'#fff\' stroke-opacity=\'.25\' stroke-width=\'22\'/><path d=\'M470 93A62 62 0 1 1 410 170\' fill=\'none\' stroke=\'#c2a15a\' stroke-width=\'22\'/><line x1=\'80\' y1=\'240\' x2=\'400\' y2=\'240\' stroke=\'#fff\' stroke-width=\'2\'/><text x=\'300\' y=\'296\' text-anchor=\'middle\' font-size=\'24\' font-weight=\'700\' fill=\'#fff\'>Power BI</text><text x=\'300\' y=\'318\' text-anchor=\'middle\' font-size=\'12\' fill=\'#c9d8e8\'>Power Query · modèle · DAX · rapports</text></svg>';
    if (outil === 'smartpls') return '<svg viewBox=\'0 0 600 340\' xmlns=\'http://www.w3.org/2000/svg\' font-family=\'Inter,Segoe UI,sans-serif\'><defs><linearGradient id=\'bg\' x1=\'0\' y1=\'0\' x2=\'1\' y2=\'1\'><stop offset=\'0\' stop-color=\'#0b2a4a\'/><stop offset=\'1\' stop-color=\'#1f5f99\'/></linearGradient></defs><rect width=\'600\' height=\'340\' fill=\'url(#bg)\'/><g stroke=\'#fff\' stroke-opacity=\'.07\'><path d=\'M0 85H600M0 170H600M0 255H600M100 0V340M200 0V340M300 0V340M400 0V340M500 0V340\'/></g><defs><marker id=\'ar2\' viewBox=\'0 0 10 10\' refX=\'9\' refY=\'5\' markerWidth=\'7\' markerHeight=\'7\' orient=\'auto\'><path d=\'M0 0L10 5L0 10z\' fill=\'#fff\'/></marker></defs><ellipse cx=\'110\' cy=\'130\' rx=\'62\' ry=\'30\' fill=\'#fff\' fill-opacity=\'.95\' stroke=\'#c2a15a\' stroke-width=\'3\'/><text x=\'110\' y=\'134\' text-anchor=\'middle\' font-size=\'13\' font-weight=\'700\' fill=\'#0b2a4a\'>Qualité</text><ellipse cx=\'300\' cy=\'70\' rx=\'70\' ry=\'30\' fill=\'#fff\' fill-opacity=\'.95\' stroke=\'#c2a15a\' stroke-width=\'3\'/><text x=\'300\' y=\'74\' text-anchor=\'middle\' font-size=\'13\' font-weight=\'700\' fill=\'#0b2a4a\'>Satisfaction</text><ellipse cx=\'490\' cy=\'130\' rx=\'62\' ry=\'30\' fill=\'#fff\' fill-opacity=\'.95\' stroke=\'#c2a15a\' stroke-width=\'3\'/><text x=\'490\' y=\'134\' text-anchor=\'middle\' font-size=\'13\' font-weight=\'700\' fill=\'#0b2a4a\'>Fidélité</text><line x1=\'160\' y1=\'112\' x2=\'238\' y2=\'84\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><line x1=\'362\' y1=\'84\' x2=\'442\' y2=\'112\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><line x1=\'174\' y1=\'134\' x2=\'426\' y2=\'134\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><rect x=\'38\' y=\'222\' width=\'44\' height=\'24\' rx=\'3\' fill=\'#c2a15a\'/><line x1=\'60\' y1=\'222\' x2=\'90\' y2=\'160\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><rect x=\'88\' y=\'222\' width=\'44\' height=\'24\' rx=\'3\' fill=\'#c2a15a\'/><line x1=\'110\' y1=\'222\' x2=\'110\' y2=\'160\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><rect x=\'138\' y=\'222\' width=\'44\' height=\'24\' rx=\'3\' fill=\'#c2a15a\'/><line x1=\'160\' y1=\'222\' x2=\'130\' y2=\'160\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><rect x=\'418\' y=\'222\' width=\'44\' height=\'24\' rx=\'3\' fill=\'#c2a15a\'/><line x1=\'440\' y1=\'222\' x2=\'470\' y2=\'160\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><rect x=\'468\' y=\'222\' width=\'44\' height=\'24\' rx=\'3\' fill=\'#c2a15a\'/><line x1=\'490\' y1=\'222\' x2=\'490\' y2=\'160\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><rect x=\'518\' y=\'222\' width=\'44\' height=\'24\' rx=\'3\' fill=\'#c2a15a\'/><line x1=\'540\' y1=\'222\' x2=\'510\' y2=\'160\' stroke=\'#fff\' stroke-width=\'2.5\' marker-end=\'url(#ar2)\'/><text x=\'300\' y=\'296\' text-anchor=\'middle\' font-size=\'24\' font-weight=\'700\' fill=\'#fff\' font-family=\'Inter,Segoe UI,sans-serif\'>SmartPLS</text><text x=\'300\' y=\'318\' text-anchor=\'middle\' font-size=\'12\' fill=\'#c9d8e8\' font-family=\'Inter,Segoe UI,sans-serif\'>PLS-SEM · mesure · bootstrapping · médiation</text></svg>';
    return head + "<rect x='60' y='60' width='480' height='220' rx='14' fill='#fff' fill-opacity='.95'/>" +
      "<g><rect x='90' y='170' width='36' height='80' fill='#c2a15a'/><rect x='136' y='140' width='36' height='110' fill='#1f5f99'/><rect x='182' y='110' width='36' height='140' fill='#0b2a4a'/><rect x='228' y='150' width='36' height='100' fill='#5b9bd5'/></g>" +
      "<circle cx='400' cy='150' r='60' fill='#1f5f99'/><path d='M400 150 L400 90 A60 60 0 0 1 452 180 Z' fill='#c2a15a'/><path d='M400 150 L452 180 A60 60 0 0 1 360 196 Z' fill='#0b2a4a'/>" +
      "<polyline points='300,240 340,220 380,230 430,205 500,215' fill='none' stroke='#c2a15a' stroke-width='3'/><text x='300' y='300' fill='#fff' font-size='20' font-weight='700'>Tableau</text>" + foot;
  }

  const synth = window.speechSynthesis;
  const narrator = {
    queue: [], i: 0, playing: false, paused: false, voice: null, token: 0,
    init() {
      if (!synth) { ['v-play', 'v-pause', 'v-stop'].forEach(id => { $('#' + id).disabled = true; }); $('#v-play').title = 'Voix non supportée par ce navigateur'; return; }
      const pick = () => {
        const v = synth.getVoices();
        this.voice = v.find(x => /^fr[-_]FR/i.test(x.lang) && /female|amelie|marie|denise|julie|google/i.test(x.name)) ||
                     v.find(x => /^fr/i.test(x.lang)) || null;
      };
      pick(); synth.onvoiceschanged = pick;
    },
    collect() {
      const items = [];
      document.querySelectorAll('[data-speak]').forEach(el => {
        const parts = el.dataset.speak.match(/[^.!?:;]+[.!?:;]?/g) || [el.dataset.speak];
        let buf = '';
        parts.forEach(p => { buf += p; if (buf.length > 90) { items.push({ el, text: buf.trim() }); buf = ''; } });
        if (buf.trim()) items.push({ el, text: buf.trim() });
      });
      return items;
    },
    start() {
      if (!synth) return;
      this.stop(true);
      this.queue = this.collect(); this.i = 0; this.playing = true; this.paused = false; this.token++;
      this.ui();
      this.next(this.token);
    },
    next(tk) {
      if (tk !== this.token) return;
      document.querySelectorAll('.speaking').forEach(e => e.classList.remove('speaking'));
      if (this.i >= this.queue.length) { this.playing = false; this.ui(); return; }
      const it = this.queue[this.i++];
      it.el.classList.add('speaking');
      it.el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      const u = new SpeechSynthesisUtterance(it.text);
      u.lang = 'fr-FR'; if (this.voice) u.voice = this.voice;
      u.rate = parseFloat($('#v-rate').value) || 1;
      u.onend = () => this.next(tk);
      u.onerror = () => this.next(tk);
      synth.speak(u);
    },
    toggle() {
      if (!synth || !this.playing) return;
      if (this.paused) { synth.resume(); this.paused = false; } else { synth.pause(); this.paused = true; }
      this.ui();
    },
    stop(silent) {
      if (!synth) return;
      this.token++; this.playing = false; this.paused = false;
      synth.cancel();
      document.querySelectorAll('.speaking').forEach(e => e.classList.remove('speaking'));
      if (!silent) this.ui();
    },
    ui() {
      $('#v-pause').disabled = !this.playing; $('#v-stop').disabled = !this.playing;
      $('#v-pause').innerHTML = this.paused ? '<i class="fas fa-play"></i>' : '<i class="fas fa-pause"></i>';
      $('#v-play').innerHTML = this.playing ? '<i class="fas fa-rotate-right"></i>' : '<i class="fas fa-volume-high"></i>';
    }
  };

  const fichiersCache = {};
  async function fichiersPour(code) {
    const noms = [...new Set((String(code).match(/['"]([\w\-]+\.csv)['"]/g) || []).map(m => m.slice(1, -1)))];
    const res = [];
    for (const n of noms) {
      if (!fichiersCache[n]) {
        const r = await fetch('/static/data/' + n);
        if (!r.ok) throw new Error('Jeu de données introuvable : ' + n);
        fichiersCache[n] = new Uint8Array(await r.arrayBuffer());
      }
      res.push([n, fichiersCache[n]]);
    }
    return res;
  }

  const engines = {
    py: null, r: null, sql: null, chart: null,

    async python(code) {
      if (!this.py) {
        if (!window.loadPyodide) await loadScript('https://cdn.jsdelivr.net/pyodide/v0.26.1/full/pyodide.js');
        this.py = await window.loadPyodide();
      }
      let out = '';
      this.py.setStdout({ batched: s => { out += s + '\n'; } });
      this.py.setStderr({ batched: s => { out += s + '\n'; } });
      await this.py.loadPackagesFromImports(code);
      for (const [n, buf] of await fichiersPour(code)) this.py.FS.writeFile(n, buf);
      if (/matplotlib|pyplot/.test(code)) {
        await this.py.runPythonAsync("import matplotlib\nmatplotlib.use('AGG')");
      }
      const g = this.py.globals.get('dict')();
      let html = '';
      try {
        await this.py.runPythonAsync(code, { globals: g });
        if (/matplotlib|pyplot/.test(code)) {
          const imgs = await this.py.runPythonAsync(
            "import io, base64, matplotlib.pyplot as _plt\n" +
            "_r = []\n" +
            "for _n in _plt.get_fignums():\n" +
            "    _b = io.BytesIO(); _plt.figure(_n).savefig(_b, format='png', dpi=110, bbox_inches='tight'); _r.append(base64.b64encode(_b.getvalue()).decode())\n" +
            "_plt.close('all')\n" +
            "_r");
          const arr = imgs.toJs(); imgs.destroy();
          html = arr.map(b => '<img alt="Graphique" style="max-width:100%;background:#fff;border-radius:8px;margin-top:8px" src="data:image/png;base64,' + b + '">').join('');
        }
      } finally { g.destroy(); }
      return { text: out.trimEnd(), html: html ? ((out.trim() ? '<pre style="margin:0;color:inherit;background:none">' + esc(out.trimEnd()) + '</pre>' : '') + html) : '' };
    },

    async r(code, o) {
      o = o || {};
      if (!this.r_) {
        const { WebR } = await import('https://webr.r-wasm.org/v0.4.2/webr.mjs');
        this.r_ = new WebR({ channelType: 'PostMessage' });
        await this.r_.init();
      }
      for (const [n, buf] of await fichiersPour(code)) await this.r_.FS.writeFile('/home/web_user/' + n, buf);
      const shelter = await new this.r_.Shelter();
      try {
        if (o.fresh !== false || this.rClear) { await shelter.captureR('rm(list=ls())'); this.rClear = false; }
        const res = await shelter.captureR(code, { withAutoprint: true });
        const text = res.output.map(x => x.data).join('\n');
        const err = res.output.some(x => x.type === 'stderr');
        let env = [];
        try {
          const s = await this.r_.evalRString("paste(vapply(ls(), function(n) paste(n, class(get(n))[1], length(get(n)), sep='\\t'), ''), collapse='\\n')");
          env = s ? s.split('\n').map(l => l.split('\t')) : [];
        } catch (e) {}
        return { text: text.trimEnd(), warn: err, env };
      } finally { await shelter.purge(); }
    },

    async sqlOpen() {
      if (!window.initSqlJs) await loadScript('https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.js');
      if (!this.sqlMod) this.sqlMod = await window.initSqlJs({ locateFile: f => 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/' + f });
      if (!this.db) {
        const db = this.db = new this.sqlMod.Database();
        db.run("CREATE TABLE ventes (id INTEGER PRIMARY KEY, date TEXT, produit TEXT, quantite INTEGER, prix_unitaire REAL, ville TEXT);");
        db.run("INSERT INTO ventes VALUES (1,'2024-01-15','Cacao',120,1500.00,'Abidjan'),(2,'2024-01-20','Café',85,1200.00,'Abidjan'),(3,'2024-02-05','Cacao',200,1520.00,'San-Pédro'),(4,'2024-02-12','Anacarde',150,800.00,'Bouaké'),(5,'2024-02-18','Café',60,1180.00,'Daloa'),(6,'2024-03-02','Cacao',180,1550.00,'Abidjan'),(7,'2024-03-10','Anacarde',220,820.00,'Korhogo'),(8,'2024-03-22','Coton',95,950.00,'Bouaké'),(9,'2024-04-05','Cacao',250,1600.00,'San-Pédro'),(10,'2024-04-14','Café',110,1250.00,'Man'),(11,'2024-05-03','Coton',130,980.00,'Korhogo'),(12,'2024-05-19','Anacarde',175,850.00,'Bouaké'),(13,'2024-06-08','Cacao',300,1650.00,'Abidjan'),(14,'2024-06-25','Café',90,1220.00,'Daloa'),(15,'2024-07-11','Coton',140,1000.00,'Korhogo'),(16,'2024-07-28','Cacao',210,1680.00,'San-Pédro'),(17,'2024-08-15','Anacarde',190,870.00,'Bouaké'),(18,'2024-09-02','Café',75,1150.00,'Man'),(19,'2024-09-20','Cacao',280,1700.00,'Abidjan'),(20,'2024-10-05','Coton',160,1020.00,'Bouaké');");
        db.run("CREATE TABLE produits (produit TEXT PRIMARY KEY, categorie TEXT, cout_unitaire REAL);");
        db.run("INSERT INTO produits VALUES ('Cacao','Culture de rente',1100),('Café','Culture de rente',900),('Anacarde','Noix',600),('Coton','Fibre',700),('Hévéa','Latex',500);");
        db.run("CREATE TABLE villes (ville TEXT PRIMARY KEY, region TEXT, habitants INTEGER);");
        db.run("INSERT INTO villes VALUES ('Abidjan','Lagunes',5600000),('San-Pédro','Bas-Sassandra',390000),('Bouaké','Vallée du Bandama',740000),('Daloa','Haut-Sassandra',320000),('Korhogo','Savanes',290000),('Man','Montagnes',190000),('Yamoussoukro','Lacs',360000);");
      }
      return this.db;
    },
    resetSql() { if (this.db) { try { this.db.close(); } catch (e) {} } this.db = null; },
    async sqlSchema() {
      const db = await this.sqlOpen();
      const t = db.exec("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name");
      const names = t.length ? t[0].values.map(v => v[0]) : [];
      return names.map(n => { const i = db.exec('PRAGMA table_info(' + n + ')'); return { name: n, cols: i.length ? i[0].values.map(v => ({ name: v[1], type: v[2] })) : [] }; });
    },
    async sql(code, o) {
      o = o || {};
      if (o.fresh) this.resetSql();
      const db = await this.sqlOpen();
      const res = db.exec(code);
      const mod = db.getRowsModified();
      if (!res.length) return { text: 'Requête exécutée (aucun résultat à afficher).', rows: [], msg: 'Commande(s) exécutée(s) avec succès. ' + mod + ' ligne(s) affectée(s).' };
      const r = res[res.length - 1];
      const html = '<table><thead><tr>' + r.columns.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr></thead><tbody>' +
        r.values.map(row => '<tr>' + row.map(v => '<td>' + (v === null ? 'NULL' : esc(v)) + '</td>').join('') + '</tr>').join('') + '</tbody></table>' +
        '<div class="muted">' + r.values.length + ' ligne(s)</div>';
      return { html, rows: r.values, cols: r.columns, text: JSON.stringify(r.values), msg: '(' + r.values.length + ' ligne(s) retournée(s))' };
    },

    async run(outil, code, o) {
      if (outil === 'python') return this.python(code);
      if (outil === 'r') return this.r(code, o);
      return this.sql(code, o);
    },
    resetSqlPublic() { this.resetSql(); }
  };
  engines.r_ = null;

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = () => rej(new Error('Chargement impossible : ' + src));
      document.head.appendChild(s);
    });
  }
  async function exec(code) {
    return engines.run(OUTIL, code, { fresh: true });
  }

  const body = $('#pl-body');

  function majTop() {
    $('#pl-tool').textContent = NOMS[OUTIL] + ' · ' + ({ debutant: 'Débutant', intermediaire: 'Intermédiaire', avance: 'Avancé' }[NIVEAU]);
    $('#pl-course-title').textContent = lecon.titre;
    $('#pl-xp').textContent = etat.xp;
    const n = lecon.concepts.length, d = Object.keys(etat.valides).length;
    $('#pl-progress-fill').style.width = Math.round(d / n * 100) + '%';
    $('#pl-progress-label').textContent = d + ' / ' + n;
    $('#v-auto').checked = !!etat.auto;
    const steps = $('#pl-steps');
    steps.innerHTML = '';
    lecon.concepts.forEach((c, i) => {
      const prevOk = i === 0 || etat.valides[lecon.concepts[i - 1].id];
      const b = document.createElement('button');
      b.className = 'pl-step' + (i === idx ? ' active' : '') + (etat.valides[c.id] ? ' done' : '') + (!prevOk && !etat.valides[c.id] ? ' locked' : '');
      b.innerHTML = '<span class="n">' + (etat.valides[c.id] ? '<i class="fas fa-check"></i>' : i + 1) + '</span>' + esc(c.titre);
      b.onclick = () => { if (prevOk || etat.valides[c.id]) aller(i); };
      steps.appendChild(b);
    });
  }

  function aller(i) {
    narrator.stop();
    idx = i; essais = 0; indiceVu = false; solutionVue = false; graphiqueGenere = false; studioCfg = null;
    majTop();
    if (idx < 0) return intro();
    if (idx >= lecon.concepts.length) return fin();
    concept();
    window.scrollTo({ top: 0 });
    if (etat.auto) setTimeout(() => narrator.start(), 500);
  }

  function intro() {
    const done = Object.keys(etat.valides).length;
    body.innerHTML =
      '<section class="pl-intro"><div class="cover">' + cover(OUTIL) + '</div><div>' +
      '<span class="pl-chip">Cours interactif</span><h1>' + esc(lecon.titre) + '</h1>' +
      '<p class="lead" data-speak="' + esc(plain(lecon.titre + '. ' + lecon.description + ' Ce cours contient ' + lecon.concepts.length + ' concepts. Pour chacun, vous écoutez une explication, vous testez un exemple, puis vous résolvez un exercice.')) + '">' + esc(lecon.description) + '</p>' +
      '<ol>' + lecon.concepts.map((c, i) => '<li class="' + (etat.valides[c.id] ? 'done' : '') + '"><span class="n">' + (i + 1) + '</span><div><strong>' + esc(c.titre) + '</strong><br><small>' + esc(c.objectif) + '</small></div></li>').join('') + '</ol>' +
      '<button class="pl-cta" id="go"><i class="fas fa-play"></i> ' + (done ? 'Reprendre le cours' : 'Commencer le cours') + '</button></div></section>';
    $('#go').onclick = () => { let k = lecon.concepts.findIndex(c => !etat.valides[c.id]); aller(k < 0 ? 0 : k); };
  }

  function concept() {
    const c = lecon.concepts[idx];
    const ex = c.exercice;
    const paras = c.explication.split(/\n\s*\n/).map(p => '<p class="narr" data-speak="' + esc(plain(p)) + '">' + md(p).replace(/\n/g, '<br>') + '</p>').join('');
    const speakIntro = 'Concept ' + (idx + 1) + ' : ' + c.titre + '. ' + c.objectif + '.';
    const dejaOk = !!etat.valides[c.id];
    const studio = OUTIL === 'tableau';
    const pls = OUTIL === 'smartpls' || OUTIL === 'powerbi';
    const texte = studio || pls;

    body.innerHTML =
      '<div class="pl-split">' +
      '<section class="pl-lesson">' +
        '<div class="pl-illus">' + (c.image_svg || cover(OUTIL)) + '</div>' +
        '<span class="pl-chip">Concept ' + (idx + 1) + ' / ' + lecon.concepts.length + '</span>' +
        '<h2 class="narr" data-speak="' + esc(plain(speakIntro)) + '">' + esc(c.titre) + '</h2>' +
        '<p class="pl-obj">' + esc(c.objectif) + '</p>' + paras +
        (c.code_exemple ? '<div class="pl-example"><header><span>Exemple</span><span><button id="cp-ex">Copier dans l\'éditeur</button>' + (texte ? '' : '<button id="run-ex">Exécuter</button>') + '</span></header><pre>' + esc(c.code_exemple) + '</pre></div>' : '') +
        (c.question_reflexion ? '<div class="pl-think narr" data-speak="' + esc('Question de réflexion. ' + plain(c.question_reflexion)) + '"><strong>À réfléchir :</strong> ' + md(c.question_reflexion) + '</div>' : '') +
        '<div class="pl-ex"><h3>Exercice</h3><div class="pl-ex-text" data-speak="' + esc('Exercice. ' + plain(ex.enonce)) + '">' + md(ex.enonce) + '</div>' +
          '<div class="pl-ex-actions"><button class="pl-link" id="b-hint"><i class="fas fa-lightbulb"></i> Indice</button><button class="pl-link" id="b-sol" disabled><i class="fas fa-eye"></i> Voir la solution</button></div>' +
          '<div id="hint-box"></div><div id="sol-box" class="pl-solution"></div></div>' +
      '</section>' +
      '<section class="pl-work">' +
        '<div class="pl-work-head"><span class="file"><i class="fas fa-file-code"></i> ' + FICHIERS[OUTIL] + '</span><span class="pl-actions">' +
          '<button class="pl-btn ghost" id="b-reset"><i class="fas fa-rotate-left"></i> Réinitialiser</button>' +
          (texte ? '' : '<button class="pl-btn run" id="b-run"><i class="fas fa-play"></i> Exécuter</button>') +
          '<button class="pl-btn submit" id="b-submit"><i class="fas fa-check"></i> Valider ma réponse</button></span></div>' +
        (studio ? studioHTML() : pls ? plsHTML(c) : codeHTML()) +
        '<div class="pl-feedback" id="fb"></div>' +
      '</section></div>' +
      '<div class="pl-nav"><button id="b-prev"><i class="fas fa-arrow-left"></i> Précédent</button><button id="b-next" ' + (dejaOk ? '' : 'disabled') + '>Suivant <i class="fas fa-arrow-right"></i></button></div>';

    if (studio) initStudio(); else if (!pls) initEditor(dejaOk ? ex.solution_attendue : '', c);
    $('#b-prev').onclick = () => aller(idx - 1);
    $('#b-next').onclick = () => aller(idx + 1);
    $('#b-hint').onclick = () => { indiceVu = true; $('#hint-box').innerHTML = '<div class="pl-hint"><i class="fas fa-lightbulb"></i> ' + md(ex.indice || 'Relisez l\'explication.') + '</div>'; };
    $('#b-sol').onclick = () => { solutionVue = true; $('#sol-box').innerHTML = '<pre>' + esc(ex.solution_attendue) + '</pre>'; };
    $('#b-reset').onclick = () => { if (texte) $('#answer').value = ''; else editor.set(starter()); };
    $('#b-submit').onclick = () => soumettre(c);
    const cp = $('#cp-ex'); if (cp) cp.onclick = () => { if (texte) { $('#answer').value = c.code_exemple; } else editor.set(c.code_exemple); };
    const rx = $('#run-ex'); if (rx) rx.onclick = () => { editor.set(c.code_exemple); lancer(); };
    if (!texte) { $('#b-run').onclick = () => lancer(); document.querySelectorAll('.app-run').forEach(b => { b.onclick = () => lancer(); }); }
    majBoutons();
  }


  function plsHTML(c) {
    return '<div class="pl-pls"><div class="pl-pls-head"><i class="fas fa-table"></i> ' + (OUTIL === 'powerbi' ? 'Données et modèle à analyser' : 'Résultats SmartPLS à interpréter') + ' <a href="/formations/' + OUTIL + '" target="_blank" style="float:right;color:#c2a15a;font-weight:600;text-decoration:none">Pratiquer dans le laboratoire</a></div>' +
      '<div class="pl-pls-res">' + (c.resultats || '<p class="pls-note">Appuyez-vous sur le schéma et l\'exemple de la leçon pour répondre.</p>') + '</div></div>' +
      '<textarea class="pl-answer" id="answer" placeholder="Rédigez votre réponse (quelques phrases ou la formule DAX demandée)..."></textarea>';
  }

  function majBoutons() { $('#b-sol').disabled = !(essais >= 2 || solutionVue); }

  /* ===== Éditeurs de code : façade commune ===== */
  const AC = window.AppChrome;
  const COMMENT = { python: '#', r: '#', sql: '--' };
  let fontPx = 13, showLines = true, themeDark = false;

  function mkEd(host, val, keys) {
    let raw;
    const common = {
      comment() {
        const pre = COMMENT[OUTIL] + ' ', [a, b] = this.range();
        const ls = this.getLines(a, b);
        const all = ls.every(l => !l.trim() || l.trim().startsWith(COMMENT[OUTIL]));
        this.setLines(a, b, ls.map(l => all ? l.replace(new RegExp('^(\\s*)' + COMMENT[OUTIL].replace(/[-#]/g, '\\$&') + ' ?'), '$1') : (l.trim() ? l.replace(/^(\s*)/, '$1' + pre) : l)));
      },
      replaceAll(q, r) { const t = this.get(); if (!q || !t.includes(q)) return 0; const n = t.split(q).length - 1; this.set(t.split(q).join(r)); return n; }
    };
    if (window.CodeMirror) {
      const cm = window.CodeMirror(host, { value: val, mode: MODES[OUTIL], lineNumbers: showLines, indentUnit: 4, tabSize: 4, indentWithTabs: false, lineWrapping: true,
        extraKeys: Object.assign({ Tab: c => c.somethingSelected() ? c.indentSelection('add') : c.replaceSelection('    ', 'end') }, keys || {}) });
      raw = Object.assign({ cm,
        get: () => cm.getValue(), set: v => cm.setValue(v), focus: () => cm.focus(),
        undo: () => cm.undo(), redo: () => cm.redo(), sel: () => cm.getSelection(), replaceSel: t => cm.replaceSelection(t, 'around'),
        selectAll: () => { cm.focus(); cm.execCommand('selectAll'); },
        font: px => { cm.getWrapperElement().style.fontSize = px + 'px'; cm.refresh(); },
        lines: on => cm.setOption('lineNumbers', on), refresh: () => cm.refresh(),
        range: () => [cm.getCursor('from').line, cm.getCursor('to').line],
        getLines: (a, b) => { const r = []; for (let i = a; i <= b; i++) r.push(cm.getLine(i)); return r; },
        setLines: (a, b, ls) => cm.replaceRange(ls.join('\n'), { line: a, ch: 0 }, { line: b, ch: cm.getLine(b).length }),
        indent: () => { cm.execCommand('selectAll'); cm.indentSelection('smart'); },
        find(q) {
          if (!q) return false; const t = cm.getValue(); let i = t.indexOf(q, cm.indexFromPos(cm.getCursor('to')));
          if (i < 0) i = t.indexOf(q); if (i < 0) return false;
          cm.setSelection(cm.posFromIndex(i), cm.posFromIndex(i + q.length)); cm.scrollIntoView(null, 80); cm.focus(); return true;
        } }, common);
      cm.getWrapperElement().style.fontSize = fontPx + 'px';
      setTimeout(() => cm.refresh(), 60);
    } else {
      const ta = document.createElement('textarea'); ta.className = 'fallback'; ta.value = val; ta.spellcheck = false; ta.style.fontSize = fontPx + 'px'; host.appendChild(ta);
      const keysMap = keys || {};
      ta.addEventListener('keydown', e => {
        if (e.ctrlKey && e.key === 'Enter' && (keysMap['Ctrl-Enter'])) { e.preventDefault(); keysMap['Ctrl-Enter'](); }
        if (e.shiftKey && e.key === 'Enter' && keysMap['Shift-Enter']) { e.preventDefault(); keysMap['Shift-Enter'](); }
        if (e.key === 'Tab') { e.preventDefault(); const s = ta.selectionStart; ta.setRangeText('    ', s, ta.selectionEnd, 'end'); }
      });
      const lineOf = pos => ta.value.slice(0, pos).split('\n').length - 1;
      raw = Object.assign({ ta,
        get: () => ta.value, set: v => { ta.value = v; }, focus: () => ta.focus(),
        undo: () => { ta.focus(); document.execCommand('undo'); }, redo: () => { ta.focus(); document.execCommand('redo'); },
        sel: () => ta.value.slice(ta.selectionStart, ta.selectionEnd), replaceSel: t => { ta.focus(); ta.setRangeText(t, ta.selectionStart, ta.selectionEnd, 'select'); },
        selectAll: () => { ta.focus(); ta.select(); }, font: px => { ta.style.fontSize = px + 'px'; }, lines: () => {}, refresh: () => {},
        range: () => [lineOf(ta.selectionStart), lineOf(ta.selectionEnd)],
        getLines: (a, b) => ta.value.split('\n').slice(a, b + 1),
        setLines: (a, b, ls) => { const all = ta.value.split('\n'); all.splice(a, b - a + 1, ...ls); ta.value = all.join('\n'); },
        indent: () => {},
        find(q) {
          if (!q) return false; let i = ta.value.indexOf(q, ta.selectionEnd); if (i < 0) i = ta.value.indexOf(q); if (i < 0) return false;
          ta.focus(); ta.setSelectionRange(i, i + q.length); return true;
        } }, common);
    }
    return raw;
  }

  function findDialog(E, replace) {
    const m = AC.modal({ title: replace ? 'Rechercher et remplacer' : 'Rechercher', html: '<label>Rechercher</label><input type="text" id="fd-q">' + (replace ? '<label>Remplacer par</label><input type="text" id="fd-r">' : '') + '<div id="fd-msg" style="margin-top:.6rem;color:#52606d"></div>',
      buttons: [{ t: 'Suivant', primary: true, f: w => { const ok = E().find(w.querySelector('#fd-q').value); w.querySelector('#fd-msg').textContent = ok ? 'Occurrence trouvée.' : 'Aucune occurrence.'; return false; } }]
        .concat(replace ? [{ t: 'Remplacer tout', f: w => { const n = E().replaceAll(w.querySelector('#fd-q').value, w.querySelector('#fd-r').value); w.querySelector('#fd-msg').textContent = n + ' remplacement(s).'; return false; } }] : [])
        .concat([{ t: 'Fermer' }]) });
    setTimeout(() => { const i = m.el.querySelector('#fd-q'); if (i) i.focus(); }, 30);
  }
  function optionsDialog(onApply) {
    AC.modal({ title: 'Options', html: '<label>Taille de la police de l\'éditeur (px)</label><input type="number" id="op-f" min="10" max="26" value="' + fontPx + '"><label>Numéros de ligne</label><select id="op-l"><option value="1">Affichés</option><option value="0"' + (showLines ? '' : ' selected') + '>Masqués</option></select><label>Thème</label><select id="op-t"><option value="0">Clair</option><option value="1"' + (themeDark ? ' selected' : '') + '>Sombre</option></select>',
      buttons: [{ t: 'Appliquer', primary: true, f: w => { fontPx = Math.max(10, Math.min(26, +w.querySelector('#op-f').value || 13)); showLines = w.querySelector('#op-l').value === '1'; themeDark = w.querySelector('#op-t').value === '1'; onApply(); } }, { t: 'Annuler' }] });
  }
  function applyTheme() { const app = document.querySelector('.pl-app'); if (app) app.classList.toggle('dark', themeDark); }
  function ref(title, html) { AC.modal({ title, html, wide: true }); }
  const quitter = () => { location.href = '/formations'; };
  async function clip(E, cut) { const s = E().sel(); try { await navigator.clipboard.writeText(s); } catch (e) {} if (cut && s) E().replaceSel(''); }
  async function paste(E) { try { const t = await navigator.clipboard.readText(); E().replaceSel(t); } catch (e) { AC.toast('Collez avec Ctrl + V (le presse-papiers est protégé par le navigateur).'); } }
  const zoom = (E, d) => { fontPx = Math.max(10, Math.min(26, fontPx + d)); E().font(fontPx); };

  const R_CHEAT = '<h4>Bases</h4><table><tr><th>Objectif</th><th>Commande</th></tr><tr><td>Affecter</td><td><code>x &lt;- 5</code></td></tr><tr><td>Vecteur</td><td><code>c(1, 2, 3)</code></td></tr><tr><td>Importer un CSV</td><td><code>read.csv("fichier.csv")</code></td></tr><tr><td>Résumé</td><td><code>summary(df)</code>, <code>str(df)</code>, <code>head(df)</code></td></tr><tr><td>Moyenne, écart-type</td><td><code>mean(x)</code>, <code>sd(x)</code></td></tr><tr><td>Régression</td><td><code>lm(y ~ x, data = df)</code></td></tr><tr><td>Graphique</td><td><code>plot(x, y)</code>, <code>hist(x)</code></td></tr></table>';
  const SQL_CHEAT = '<table><tr><th>Objectif</th><th>Syntaxe</th></tr><tr><td>Sélectionner</td><td><code>SELECT col FROM table WHERE condition</code></td></tr><tr><td>Trier / limiter</td><td><code>ORDER BY col DESC LIMIT 5</code></td></tr><tr><td>Agréger</td><td><code>SELECT col, SUM(x) FROM t GROUP BY col HAVING SUM(x) &gt; 100</code></td></tr><tr><td>Joindre</td><td><code>FROM a JOIN b ON a.k = b.k</code></td></tr><tr><td>Insérer</td><td><code>INSERT INTO t VALUES (...)</code></td></tr><tr><td>Fenêtre</td><td><code>SUM(x) OVER (PARTITION BY c ORDER BY d)</code></td></tr><tr><td>CTE</td><td><code>WITH s AS (SELECT ...) SELECT * FROM s</code></td></tr></table>';
  const PY_HELP = '<h4>Raccourcis</h4><table><tr><td><b>Maj + Entrée</b></td><td>Exécuter la cellule et passer à la suivante</td></tr><tr><td><b>Ctrl + Entrée</b></td><td>Exécuter la cellule</td></tr><tr><td><b>Alt + Entrée</b></td><td>Exécuter et insérer une cellule dessous</td></tr><tr><td><b>Échap</b></td><td>Mode commande ; ensuite <b>A</b> / <b>B</b> (insérer au-dessus / en dessous), <b>D D</b> (supprimer), <b>M</b> (Markdown), <b>Y</b> (Code), <b>Entrée</b> (éditer)</td></tr></table>';
  const SNIPPETS = {
    sql: [['Sélection simple', "SELECT ville, SUM(quantite) AS total\nFROM ventes\nGROUP BY ville\nORDER BY total DESC;"], ['Jointure', "SELECT v.ville, p.categorie, SUM(v.quantite) AS total\nFROM ventes v\nJOIN produits p ON p.produit = v.produit\nGROUP BY v.ville, p.categorie;"], ['Fonction de fenêtre', "SELECT id, ville, quantite,\n       SUM(quantite) OVER (PARTITION BY ville ORDER BY date) AS cumul\nFROM ventes;"], ['Expression de table (CTE)', "WITH t AS (\n  SELECT produit, SUM(quantite) AS q FROM ventes GROUP BY produit\n)\nSELECT * FROM t WHERE q > 100;"]]
  };

  /* ===== Applications : RStudio, Jupyter, éditeur SQL ===== */
  let docs = [], activeDoc = 0, ed = null, lastCode = '', nb = null;

  function codeHTML() {
    if (OUTIL === 'python') {
      return '<div class="pl-app app-python"><div class="nb-head"><b>jupyter</b><span class="nb-name">exercice</span><span class="nb-saved" id="nbsaved">Non enregistré</span></div>' +
        '<div class="app-menu" id="appmenu"></div>' +
        '<div class="app-tool"><button class="tb" id="nb-add" title="Insérer une cellule dessous"><i class="fas fa-plus"></i></button><button class="tb" id="nb-cut" title="Couper la cellule"><i class="fas fa-scissors"></i></button><button class="tb" id="nb-copy" title="Copier la cellule"><i class="far fa-copy"></i></button><button class="tb" id="nb-paste" title="Coller dessous"><i class="far fa-paste"></i></button><span class="spx"></span>' +
        '<button class="tb" id="nb-run" title="Exécuter (Maj+Entrée)"><i class="fas fa-play"></i> Exécuter</button><button class="tb" id="nb-stop" title="Interrompre"><i class="fas fa-stop"></i></button><button class="tb" id="nb-restart" title="Redémarrer le noyau"><i class="fas fa-rotate-right"></i></button><button class="tb" id="nb-runall" title="Tout exécuter"><i class="fas fa-forward"></i></button>' +
        '<select id="nb-type"><option value="code">Code</option><option value="md">Markdown</option></select><span class="app-hint">Python 3 (ipykernel) <i class="fas fa-circle" style="color:#2f8f6b;font-size:.55rem"></i> <span id="status"></span></span></div>' +
        '<div class="nb-cells" id="nbcells"></div></div>';
    }
    const out = '<div class="pl-console-out" id="out"><span class="muted">Exécutez votre code pour voir le résultat.</span></div>';
    if (OUTIL === 'r') {
      return '<div class="pl-app app-r"><div class="app-menu" id="appmenu"></div>' +
        '<div class="app-tool"><button class="tb" id="r-new" title="Nouveau script"><i class="far fa-file"></i></button><button class="tb" id="r-save" title="Enregistrer"><i class="far fa-floppy-disk"></i></button><span class="spx"></span><button class="tb" id="r-line" title="Exécuter la ligne ou la sélection (Ctrl+Entrée)"><i class="fas fa-play"></i> Run</button><button class="tb" id="r-src" title="Source (Ctrl+Maj+S)"><i class="fas fa-arrow-right-to-bracket"></i> Source</button><span class="app-hint">Ctrl + Entrée : ligne ou sélection</span></div>' +
        '<div class="app-tabs" id="doctabs"></div><div class="pl-editor" id="editor"></div>' +
        '<div class="pl-console"><div class="app-ctabs" id="ctabs"><span class="on" data-p="out">Console</span><span data-p="env">Environment</span><span data-p="term">Terminal</span><span data-p="jobs">Background Jobs</span><span class="sp"></span><span id="status"></span></div>' +
        '<div class="r-path">R 4.4 · ~/</div><div class="cpane on" id="p-out">' + out + '</div><div class="cpane" id="p-env"><div class="pl-console-out" id="envbox"><span class="muted">Environnement vide.</span></div></div>' +
        '<div class="cpane" id="p-term"><div class="pl-console-out term" id="termout">$ Terminal prêt. Tapez help.</div><div class="term-in"><span>$</span><input id="termin" spellcheck="false" autocomplete="off"></div></div>' +
        '<div class="cpane" id="p-jobs"><div class="pl-console-out"><span class="muted">Aucune tâche en arrière-plan.</span></div></div></div></div>';
    }
    if (OUTIL === 'sql') {
      return '<div class="pl-app app-sql"><div class="app-menu" id="appmenu"></div>' +
        '<div class="app-tool"><button class="tb" id="q-new" title="Nouvelle requête"><i class="far fa-file"></i></button><button class="tb" id="q-save" title="Enregistrer"><i class="far fa-floppy-disk"></i></button><span class="spx"></span><button class="tb" id="q-run" title="Exécuter (F5)"><i class="fas fa-play"></i> Exécuter</button><button class="tb" id="q-plan" title="Plan d\'exécution"><i class="fas fa-sitemap"></i> Plan</button><button class="tb" id="q-fmt" title="Formater"><i class="fas fa-align-left"></i></button><select id="q-db"><option>ventes.db</option></select><span class="app-hint">F5 ou Ctrl+Entrée : exécuter (la sélection si elle existe)</span></div>' +
        '<div class="sql-body"><aside class="sql-obj" id="objexp"></aside><div class="sql-main"><div class="app-tabs" id="doctabs"></div><div class="pl-editor" id="editor"></div>' +
        '<div class="pl-console"><div class="app-ctabs" id="ctabs"><span class="on" data-p="out">Résultats</span><span data-p="msg">Messages</span><span class="sp"></span><span id="status"></span></div>' +
        '<div class="cpane on" id="p-out">' + out + '</div><div class="cpane" id="p-msg"><div class="pl-console-out" id="msgbox"><span class="muted">Aucun message.</span></div></div></div></div></div></div>';
    }
    return '<div class="pl-editor" id="editor"></div><div class="pl-console"><div class="pl-console-head"><span>Console</span><span id="status"></span></div>' + out + '</div>';
  }

  function paneTabs() {
    document.querySelectorAll('#ctabs span[data-p]').forEach(t => t.onclick = () => showPane(t.dataset.p));
  }
  function showPane(p) {
    document.querySelectorAll('#ctabs span[data-p]').forEach(x => x.classList.toggle('on', x.dataset.p === p));
    document.querySelectorAll('.cpane').forEach(x => x.classList.toggle('on', x.id === 'p-' + p));
    if (p === 'term') { const i = $('#termin'); if (i) i.focus(); }
  }

  /* --- documents (onglets de scripts) pour R et SQL --- */
  function renderDocTabs() {
    const el = $('#doctabs'); if (!el) return;
    el.innerHTML = docs.map((d, i) => '<span class="' + (i === activeDoc ? 'on' : '') + '" data-i="' + i + '"><i class="fas ' + (OUTIL === 'sql' ? 'fa-database' : 'fa-file-code') + '"></i> ' + esc(d.name) + (docs.length > 1 ? ' <b class="dx" data-x="' + i + '" title="Fermer">&times;</b>' : '') + '</span>').join('') + '<span class="dadd" id="dadd" title="Nouveau">+</span>';
    el.querySelectorAll('span[data-i]').forEach(s => s.onclick = e => { if (e.target.dataset.x !== undefined) { closeDoc(+e.target.dataset.x); return; } switchDoc(+s.dataset.i); });
    $('#dadd').onclick = () => newDoc();
  }
  function switchDoc(i) { docs[activeDoc].src = ed.get(); activeDoc = i; ed.set(docs[i].src); renderDocTabs(); ed.focus(); }
  function newDoc(src) {
    docs[activeDoc] && (docs[activeDoc].src = ed.get());
    const n = docs.length + 1;
    docs.push({ name: OUTIL === 'sql' ? 'Requete' + n + '.sql' : 'Untitled' + n, src: src === undefined ? starter() : src });
    activeDoc = docs.length - 1; ed.set(docs[activeDoc].src); renderDocTabs(); ed.focus();
  }
  function closeDoc(i) {
    if (docs.length < 2) return;
    docs.splice(i, 1); activeDoc = Math.min(activeDoc, docs.length - 1); if (i < activeDoc) activeDoc = Math.max(0, activeDoc - 1);
    ed.set(docs[activeDoc].src); renderDocTabs();
  }
  const saveDoc = () => { docs[activeDoc].src = ed.get(); AC.download(docs[activeDoc].name, ed.get()); AC.toast('Fichier enregistré : ' + docs[activeDoc].name); };
  const openDoc = () => AC.pick(OUTIL === 'sql' ? '.sql,.txt' : '.R,.r,.txt', (t, n) => { newDoc(t); docs[activeDoc].name = n; renderDocTabs(); });

  function termCmd(line) {
    const out = $('#termout'); const a = line.trim().split(/\s+/), c = a[0];
    out.textContent += '\n$ ' + line;
    const say = t => { out.textContent += '\n' + t; };
    if (!c) return;
    if (c === 'clear') out.textContent = '';
    else if (c === 'pwd') say('/home/web_user');
    else if (c === 'whoami') say('web_user');
    else if (c === 'date') say(new Date().toString());
    else if (c === 'echo') say(a.slice(1).join(' '));
    else if (c === 'ls') say(['exercice.R', 'donnees'].concat(docs.map(d => d.name)).filter((v, i, s) => s.indexOf(v) === i).join('  '));
    else if (c === 'R' || c === 'Rscript') say('Utilisez la console R de l\'onglet Console.');
    else if (c === 'help') say('Commandes disponibles : pwd, ls, echo, date, whoami, clear, help');
    else say('bash: ' + c + ': commande introuvable');
    out.scrollTop = out.scrollHeight;
  }

  /* --- menus R --- */
  function menusR() {
    const E = () => ed;
    return {
      File: [{ l: 'New File > R Script', k: 'Ctrl+Maj+N', f: () => newDoc() }, { l: 'Open File...', k: 'Ctrl+O', f: openDoc }, { sep: 1 }, { l: 'Save', k: 'Ctrl+S', f: saveDoc }, { l: 'Save As...', f: () => { const n = prompt('Nom du fichier', docs[activeDoc].name); if (n) { docs[activeDoc].name = n; renderDocTabs(); saveDoc(); } } }, { sep: 1 }, { l: 'Close', k: 'Ctrl+W', dis: () => docs.length < 2, f: () => closeDoc(activeDoc) }, { l: 'Quit Session...', k: 'Ctrl+Q', f: quitter }],
      Edit: [{ l: 'Undo', k: 'Ctrl+Z', f: () => E().undo() }, { l: 'Redo', k: 'Ctrl+Maj+Z', f: () => E().redo() }, { sep: 1 }, { l: 'Cut', k: 'Ctrl+X', f: () => clip(E, true) }, { l: 'Copy', k: 'Ctrl+C', f: () => clip(E) }, { l: 'Paste', k: 'Ctrl+V', f: () => paste(E) }, { l: 'Select All', k: 'Ctrl+A', f: () => E().selectAll() }, { sep: 1 }, { l: 'Find...', k: 'Ctrl+F', f: () => findDialog(E) }, { l: 'Replace and Find...', f: () => findDialog(E, true) }, { sep: 1 }, { l: 'Clear Console', k: 'Ctrl+L', f: () => { $('#out').innerHTML = '<span class="muted">Console effacée.</span>'; } }],
      Code: [{ l: 'Run Selected Line(s)', k: 'Ctrl+Entrée', f: () => runR('line') }, { l: 'Re-Run Previous', k: 'Ctrl+Alt+P', dis: () => !lastCode, f: () => runR('prev') }, { l: 'Source', k: 'Ctrl+Maj+S', f: () => runR('all') }, { sep: 1 }, { l: 'Comment/Uncomment Lines', k: 'Ctrl+Maj+C', f: () => E().comment() }, { l: 'Reindent Lines', k: 'Ctrl+I', f: () => E().indent() }, { sep: 1 }, { l: 'Insert Section', k: 'Ctrl+Maj+R', f: () => E().replaceSel('# Section ----\n') }, { l: 'Insert Pipe Operator', k: 'Ctrl+Maj+M', f: () => E().replaceSel(' |> ') }, { l: 'Insert Assignment Operator', k: 'Alt+-', f: () => E().replaceSel(' <- ') }],
      View: [{ l: 'Zoom In', k: 'Ctrl++', f: () => zoom(E, 1) }, { l: 'Zoom Out', k: 'Ctrl+-', f: () => zoom(E, -1) }, { sep: 1 }, { l: 'Show Line Numbers', chk: () => showLines, f: () => { showLines = !showLines; E().lines(showLines); } }, { sep: 1 }, { l: 'Move Focus to Source', f: () => E().focus() }, { l: 'Show Console', f: () => showPane('out') }, { l: 'Show Environment', f: () => showPane('env') }, { l: 'Show Terminal', f: () => showPane('term') }, { l: 'Show Background Jobs', f: () => showPane('jobs') }],
      Session: [{ l: 'Restart R', k: 'Ctrl+Maj+F10', f: () => { $('#out').innerHTML = '<span class="muted">R redémarré : espace de travail vidé.</span>'; $('#envbox').innerHTML = '<span class="muted">Environnement vide.</span>'; engines.rClear = true; } }, { l: 'Clear Workspace...', f: () => { engines.rClear = true; $('#envbox').innerHTML = '<span class="muted">Environnement vide.</span>'; AC.toast('Espace de travail vidé.'); } }, { sep: 1 }, { l: 'Set Working Directory', sub: [{ l: 'To Source File Location', f: () => AC.toast('Répertoire de travail : ~/') }, { l: 'Choose Directory...', f: () => AC.toast('Le répertoire est fixé à ~/ dans le laboratoire.') }] }, { l: 'Interrupt R', k: 'Échap', dis: () => !running, f: () => AC.toast('Interruption demandée.') }],
      Tools: [{ l: 'Install Packages...', f: installPkgs }, { sep: 1 }, { l: 'Global Options...', f: () => optionsDialog(() => { E().font(fontPx); E().lines(showLines); applyTheme(); }) }],
      Help: [{ l: 'R Help', f: () => ref('Aide R', R_CHEAT) }, { l: 'Cheat Sheet : bases de R', f: () => ref('Aide-mémoire R', R_CHEAT) }, { l: 'Keyboard Shortcuts Help', k: 'Alt+Maj+K', f: () => ref('Raccourcis clavier', '<table><tr><td><b>Ctrl + Entrée</b></td><td>Exécuter la ligne ou la sélection</td></tr><tr><td><b>Ctrl + Maj + S</b></td><td>Exécuter tout le script (Source)</td></tr><tr><td><b>Ctrl + Maj + C</b></td><td>Commenter / décommenter</td></tr><tr><td><b>Ctrl + I</b></td><td>Réindenter</td></tr></table>') }, { sep: 1 }, { l: 'About RStudio', f: () => ref('À propos', '<p>Environnement d\'exercice DataEcon.Ci reproduisant l\'organisation de RStudio (R 4.4 exécuté dans le navigateur).</p>') }]
    };
  }
  let running = false;
  function installPkgs() {
    AC.modal({ title: 'Install Packages', html: '<label>Packages (séparés par des espaces ou des virgules)</label><input type="text" id="pk" placeholder="ex. dplyr ggplot2">', buttons: [{ t: 'Install', primary: true, f: w => { const p = w.querySelector('#pk').value.split(/[\s,]+/).filter(Boolean); if (p.length) { showPane('out'); runR('code', 'webr::install(c(' + p.map(x => '"' + x.replace(/[^\w.]/g, '') + '"').join(',') + '))'); } } }, { t: 'Cancel' }] });
  }
  async function runR(mode, code) {
    ed.get; let c;
    if (mode === 'code') c = code;
    else if (mode === 'prev') c = lastCode;
    else if (mode === 'line') {
      c = ed.sel(); if (!c) { const [a] = ed.range(); c = ed.getLines(a, a)[0]; }
    } else c = ed.get();
    if (!c || !c.trim()) { AC.toast('Rien à exécuter.'); return null; }
    lastCode = c; showPane('out');
    return lancer(c, { fresh: mode === 'all', echo: mode !== 'all' });
  }

  /* --- menus SQL --- */
  function menusSQL() {
    const E = () => ed;
    const ins = t => { E().replaceSel(t); E().focus(); };
    return {
      Fichier: [{ l: 'Nouvelle requête', k: 'Ctrl+N', f: () => newDoc() }, { l: 'Ouvrir un fichier...', k: 'Ctrl+O', f: openDoc }, { l: 'Enregistrer', k: 'Ctrl+S', f: saveDoc }, { sep: 1 }, { l: 'Exporter les résultats (CSV)', dis: () => !lastRes, f: exportCsv }, { l: 'Réinitialiser la base de données', f: () => { engines.resetSql(); refreshExplorer(); AC.toast('Base de données réinitialisée.'); } }, { sep: 1 }, { l: 'Fermer l\'onglet', dis: () => docs.length < 2, f: () => closeDoc(activeDoc) }, { l: 'Quitter', f: quitter }],
      Édition: [{ l: 'Annuler', k: 'Ctrl+Z', f: () => E().undo() }, { l: 'Rétablir', k: 'Ctrl+Y', f: () => E().redo() }, { sep: 1 }, { l: 'Couper', k: 'Ctrl+X', f: () => clip(E, true) }, { l: 'Copier', k: 'Ctrl+C', f: () => clip(E) }, { l: 'Coller', k: 'Ctrl+V', f: () => paste(E) }, { l: 'Sélectionner tout', k: 'Ctrl+A', f: () => E().selectAll() }, { sep: 1 }, { l: 'Rechercher...', k: 'Ctrl+F', f: () => findDialog(E) }, { l: 'Remplacer...', k: 'Ctrl+H', f: () => findDialog(E, true) }, { sep: 1 }, { l: 'Commenter la sélection', k: 'Ctrl+K, C', f: () => E().comment() }, { l: 'Mettre en majuscules', k: 'Ctrl+Maj+U', f: () => { const s = E().sel(); if (s) E().replaceSel(s.toUpperCase()); else AC.toast('Sélectionnez du texte.'); } }],
      Affichage: [{ l: 'Explorateur d\'objets', k: 'F8', chk: () => !$('#objexp').classList.contains('hide'), f: () => $('#objexp').classList.toggle('hide') }, { l: 'Résultats', f: () => showPane('out') }, { l: 'Messages', f: () => showPane('msg') }, { sep: 1 }, { l: 'Agrandir le texte', f: () => zoom(E, 1) }, { l: 'Réduire le texte', f: () => zoom(E, -1) }, { l: 'Numéros de ligne', chk: () => showLines, f: () => { showLines = !showLines; E().lines(showLines); } }],
      Requête: [{ l: 'Exécuter', k: 'F5', f: () => runSQL() }, { l: 'Exécuter la sélection uniquement', f: () => { const s = E().sel(); if (!s) AC.toast('Aucune sélection.'); else runSQL(s); } }, { l: 'Afficher le plan d\'exécution estimé', k: 'Ctrl+L', f: planSQL }, { sep: 1 }, { l: 'Inclure la durée d\'exécution', chk: () => showTime, f: () => { showTime = !showTime; } }, { l: 'Effacer les résultats', f: () => { $('#out').innerHTML = '<span class="muted">Résultats effacés.</span>'; lastRes = null; } }],
      Outils: [{ l: 'Modèles de requêtes', sub: SNIPPETS.sql.map(s => ({ l: s[0], f: () => ins(s[1] + '\n') })) }, { l: 'Formater la requête', k: 'Ctrl+K, D', f: fmtSQL }, { sep: 1 }, { l: 'Options...', f: () => optionsDialog(() => { E().font(fontPx); E().lines(showLines); applyTheme(); }) }],
      Fenêtre: [{ l: 'Nouvelle fenêtre de requête', f: () => newDoc() }, { sep: 1 }].concat([]).concat([{ l: 'Fermer la fenêtre active', dis: () => docs.length < 2, f: () => closeDoc(activeDoc) }]),
      Aide: [{ l: 'Référence SQL', f: () => ref('Référence SQL', SQL_CHEAT) }, { l: 'Schéma de la base', f: () => ref('Schéma de la base', schemaHTML()) }, { l: 'À propos', f: () => ref('À propos', '<p>Éditeur de requêtes DataEcon.Ci (moteur SQLite exécuté dans le navigateur, base d\'exemple ventes.db).</p>') }]
    };
  }
  let showTime = true, lastRes = null, schemaCache = [];
  function schemaHTML() { return schemaCache.map(t => '<h4>' + esc(t.name) + '</h4><table><tr><th>Colonne</th><th>Type</th></tr>' + t.cols.map(c => '<tr><td>' + esc(c.name) + '</td><td>' + esc(c.type || '') + '</td></tr>').join('') + '</table>').join('') || '<p>Exécutez une première requête pour charger le schéma.</p>'; }
  async function refreshExplorer() {
    const el = $('#objexp'); if (!el) return;
    try { schemaCache = await engines.sqlSchema(); } catch (e) { schemaCache = []; }
    el.innerHTML = '<div class="obj-h">Explorateur d\'objets</div><div class="obj-n db">ventes.db</div><div class="obj-n g">Tables</div>' +
      schemaCache.map(t => '<div class="obj-t" data-t="' + esc(t.name) + '"><i class="fas fa-table"></i> ' + esc(t.name) + '</div><div class="obj-c hide">' + t.cols.map(c => '<div data-c="' + esc(c.name) + '">' + esc(c.name) + ' <small>' + esc(c.type || '') + '</small></div>').join('') + '</div>').join('') + '<div class="obj-n g">Vues</div><div class="obj-n g">Index</div>';
    el.querySelectorAll('.obj-t').forEach(t => { t.onclick = () => t.nextElementSibling.classList.toggle('hide'); t.ondblclick = () => { ed.replaceSel('SELECT * FROM ' + t.dataset.t + ';'); ed.focus(); }; });
    el.querySelectorAll('.obj-c div').forEach(c => c.onclick = () => { ed.replaceSel(c.dataset.c); ed.focus(); });
  }
  function exportCsv() { if (!lastRes) return; const q = v => '"' + String(v === null ? '' : v).replace(/"/g, '""') + '"'; AC.download('resultats.csv', '﻿' + [lastRes.columns.map(q).join(',')].concat(lastRes.values.map(r => r.map(q).join(','))).join('\n'), 'text/csv;charset=utf-8'); }
  function fmtSQL() {
    let t = ed.get(); const kw = ['select', 'from', 'where', 'group by', 'order by', 'having', 'join', 'left join', 'inner join', 'limit', 'union', 'and', 'or', 'on', 'as', 'in', 'not', 'null', 'is', 'like', 'between', 'distinct', 'desc', 'asc', 'case', 'when', 'then', 'else', 'end', 'with', 'over', 'partition by', 'insert into', 'values', 'update', 'set', 'delete', 'create table'];
    kw.sort((a, b) => b.length - a.length).forEach(k => { t = t.replace(new RegExp('\\b' + k.replace(' ', '\\s+') + '\\b', 'gi'), k.toUpperCase()); });
    t = t.replace(/\s+(FROM|WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|LEFT JOIN|INNER JOIN|JOIN|UNION)\b/g, '\n$1');
    ed.set(t); AC.toast('Requête formatée.');
  }
  async function runSQL(code) {
    const s = code || ed.sel() || ed.get();
    return lancer(s, { sql: true });
  }
  async function planSQL() {
    const s = (ed.sel() || ed.get()).trim().replace(/;+\s*$/, ''); if (!s) return;
    return lancer('EXPLAIN QUERY PLAN ' + s, { sql: true, plan: true });
  }

  /* --- Jupyter : cellules --- */
  function nbCell(type, src) {
    const c = { type: type || 'code', n: null, rendered: false };
    const div = document.createElement('div'); div.className = 'nb-c'; div.tabIndex = 0;
    div.innerHTML = '<span class="nb-in"></span><div class="nb-body"><div class="nb-ed"></div><div class="nb-md hide"></div><div class="nb-out hide"><span class="nb-ol"></span><div class="nbo"></div></div></div>';
    c.div = div; c.edHost = div.querySelector('.nb-ed'); c.mdEl = div.querySelector('.nb-md'); c.outEl = div.querySelector('.nb-out'); c.inEl = div.querySelector('.nb-in');
    c.ed = mkEd(c.edHost, src || '', { 'Shift-Enter': () => nbRun(c, 'next'), 'Ctrl-Enter': () => nbRun(c, 'stay'), 'Alt-Enter': () => nbRun(c, 'below'), Esc: () => div.focus() });
    div.addEventListener('mousedown', () => nbSelect(c));
    div.addEventListener('dblclick', () => { if (c.type === 'md') { c.rendered = false; nbDraw(c); c.ed.focus(); } });
    div.addEventListener('keydown', e => nbKey(e, c));
    nbDraw(c); return c;
  }
  function nbDraw(c) {
    const md_ = c.type === 'md';
    c.edHost.classList.toggle('hide', md_ && c.rendered);
    c.mdEl.classList.toggle('hide', !(md_ && c.rendered));
    if (md_ && c.rendered) c.mdEl.innerHTML = md(c.ed.get()).replace(/\n/g, '<br>');
    c.inEl.textContent = md_ ? '' : 'In [' + (c.n === null ? ' ' : c.n) + ']:';
    c.div.classList.toggle('md', md_);
  }
  function nbSelect(c) { nb.cur = nb.cells.indexOf(c); nb.cells.forEach(x => x.div.classList.toggle('sel', x === c)); $('#nb-type').value = c.type; }
  function nbAdd(at, type, src) { const c = nbCell(type, src); nb.cells.splice(at, 0, c); const host = $('#nbcells'); host.insertBefore(c.div, host.children[at] || null); nbSelect(c); setTimeout(() => c.ed.refresh(), 30); return c; }
  function nbCur() { return nb.cells[nb.cur] || nb.cells[0]; }
  function nbDel(i) { if (nb.cells.length === 1) { nb.cells[0].ed.set(''); nb.cells[0].outEl.classList.add('hide'); return; } const c = nb.cells.splice(i, 1)[0]; c.div.remove(); nbSelect(nb.cells[Math.min(i, nb.cells.length - 1)]); }
  function nbKey(e, c) {
    if (e.target !== c.div) return; const i = nb.cells.indexOf(c);
    const k = e.key.toLowerCase();
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (c.type === 'md') { c.rendered = false; nbDraw(c); } c.ed.focus(); }
    else if (e.key === 'Enter' && e.shiftKey) { e.preventDefault(); nbRun(c, 'next'); }
    else if (k === 'a') { nbAdd(i, 'code'); c.div.previousSibling && 0; }
    else if (k === 'b') nbAdd(i + 1, 'code');
    else if (k === 'm') { c.type = 'md'; c.rendered = true; nbDraw(c); }
    else if (k === 'y') { c.type = 'code'; c.rendered = false; nbDraw(c); }
    else if (k === 'd') { if (nb.dd) { nbDel(i); nb.dd = false; } else { nb.dd = true; setTimeout(() => { nb.dd = false; }, 700); } }
    else if (e.key === 'ArrowUp' && i > 0) { nb.cells[i - 1].div.focus(); nbSelect(nb.cells[i - 1]); }
    else if (e.key === 'ArrowDown' && i < nb.cells.length - 1) { nb.cells[i + 1].div.focus(); nbSelect(nb.cells[i + 1]); }
  }
  const SEP = '␞';
  async function nbRun(c, then) {
    const i = nb.cells.indexOf(c);
    if (c.type === 'md') { c.rendered = true; nbDraw(c); } else await nbExecUpTo(i, i);
    if (then === 'next') { if (i === nb.cells.length - 1) nbAdd(i + 1, 'code'); else nbSelect(nb.cells[i + 1]); const t = nbCur(); if (t.type === 'code') t.ed.focus(); }
    else if (then === 'below') { nbAdd(i + 1, 'code').ed.focus(); }
  }
  async function nbExecUpTo(upTo, from) {
    const codeCells = nb.cells.map((c, i) => ({ c, i })).filter(x => x.c.type === 'code' && x.i <= upTo);
    if (!codeCells.length) return null;
    const src = codeCells.map(x => x.c.ed.get()).join('\nprint("' + SEP + '")\n');
    const st = $('#status'); st.textContent = 'Exécution... (le premier lancement charge Python)'; const t0 = performance.now();
    codeCells.forEach(x => { if (x.i >= from) x.c.inEl.textContent = 'In [*]:'; });
    let r = null, err = null;
    try { r = await exec(src); } catch (e) { err = e.message || String(e); }
    const segs = r ? r.text.split(SEP + '\n').map(s => s.replace(/\n$/, '')) : [];
    const imgs = r && r.html ? (r.html.match(/<img[^>]*>/g) || []) : [];
    nb.count += 1;
    codeCells.forEach((x, k) => {
      if (x.i < from) return;
      x.c.n = nb.count; x.c.inEl.textContent = 'In [' + nb.count + ']:';
      const last = k === codeCells.length - 1;
      let out = '';
      if (err && last) out = '<span class="err">' + esc(err) + '</span>';
      else { const t = (segs[k] || '').trim(); if (t) out += '<pre>' + esc(t) + '</pre>'; if (last) out += imgs.join(''); }
      x.c.outEl.classList.toggle('hide', !out);
      x.c.outEl.querySelector('.nb-ol').textContent = out && !err ? 'Out[' + nb.count + ']:' : '';
      x.c.outEl.querySelector('.nbo').innerHTML = out; x.c.raw = out ? (segs[k] || '') : '';
    });
    st.textContent = err ? 'Erreur' : ((performance.now() - t0) / 1000).toFixed(2) + ' s';
    if (err) return null;
    return { text: segs.join('\n').trim(), html: imgs.length ? imgs.join('') : '' };
  }
  async function nbRunAll() { return nbExecUpTo(nb.cells.length - 1, 0); }
  function nbClear() { nb.cells.forEach(c => { c.outEl.classList.add('hide'); c.outEl.querySelector('.nbo').innerHTML = ''; c.n = null; nbDraw(c); }); nb.count = 0; }
  function nbIpynb() {
    return JSON.stringify({ nbformat: 4, nbformat_minor: 5, metadata: { kernelspec: { display_name: 'Python 3', language: 'python', name: 'python3' }, language_info: { name: 'python' } },
      cells: nb.cells.map(c => c.type === 'md' ? { cell_type: 'markdown', metadata: {}, source: c.ed.get().split(/(?<=\n)/) } : { cell_type: 'code', metadata: {}, execution_count: c.n, source: c.ed.get().split(/(?<=\n)/), outputs: c.raw ? [{ output_type: 'stream', name: 'stdout', text: (c.raw + '\n').split(/(?<=\n)/) }] : [] }) }, null, 1);
  }
  function nbLoad(text, name) {
    let cells;
    if (/\.ipynb$/i.test(name)) { try { cells = JSON.parse(text).cells.map(c => ({ type: c.cell_type === 'markdown' ? 'md' : 'code', src: [].concat(c.source).join('') })); } catch (e) { AC.toast('Fichier .ipynb invalide.'); return; } }
    else cells = [{ type: 'code', src: text }];
    $('#nbcells').innerHTML = ''; nb.cells = []; cells.forEach((c, k) => { const x = nbAdd(k, c.type, c.src); if (c.type === 'md') { x.rendered = true; nbDraw(x); } }); nb.count = 0;
  }
  const nbClip = { cell: null };
  function menusPy() {
    const cur = () => nbCur(), E = () => cur().ed, idx = () => nb.cells.indexOf(cur());
    return {
      Fichier: [{ l: 'Nouveau notebook', f: () => { $('#nbcells').innerHTML = ''; nb.cells = []; nb.count = 0; nbAdd(0, 'code', starter()); } }, { l: 'Ouvrir...', k: '.py / .ipynb', f: () => AC.pick('.py,.ipynb,.txt', nbLoad) }, { sep: 1 }, { l: 'Enregistrer le notebook', k: 'Ctrl+S', f: () => { AC.download('exercice.ipynb', nbIpynb(), 'application/json'); $('#nbsaved').textContent = 'Enregistré à ' + new Date().toLocaleTimeString('fr-FR'); } }, { l: 'Télécharger au format .py', f: () => AC.download('exercice.py', nb.cells.map(c => c.type === 'md' ? c.ed.get().split('\n').map(l => '# ' + l).join('\n') : c.ed.get()).join('\n\n')) }, { l: 'Imprimer', f: () => window.print() }, { sep: 1 }, { l: 'Fermer et arrêter', f: quitter }],
      Édition: [{ l: 'Annuler', f: () => E().undo() }, { l: 'Rétablir', f: () => E().redo() }, { sep: 1 }, { l: 'Couper la cellule', f: () => { nbClip.cell = { type: cur().type, src: E().get() }; nbDel(idx()); } }, { l: 'Copier la cellule', f: () => { nbClip.cell = { type: cur().type, src: E().get() }; AC.toast('Cellule copiée.'); } }, { l: 'Coller la cellule dessous', dis: () => !nbClip.cell, f: () => { const c = nbAdd(idx() + 1, nbClip.cell.type, nbClip.cell.src); if (c.type === 'md') { c.rendered = true; nbDraw(c); } } }, { l: 'Supprimer la cellule', f: () => nbDel(idx()) }, { sep: 1 }, { l: 'Fusionner avec la cellule suivante', dis: () => idx() >= nb.cells.length - 1, f: () => { const i = idx(); nb.cells[i].ed.set(nb.cells[i].ed.get() + '\n' + nb.cells[i + 1].ed.get()); nbDel(i + 1); nbSelect(nb.cells[i]); } }, { l: 'Monter la cellule', dis: () => idx() < 1, f: () => { const i = idx(), c = nb.cells.splice(i, 1)[0]; nb.cells.splice(i - 1, 0, c); $('#nbcells').insertBefore(c.div, $('#nbcells').children[i - 1]); } }, { l: 'Descendre la cellule', dis: () => idx() >= nb.cells.length - 1, f: () => { const i = idx(), c = nb.cells.splice(i, 1)[0]; nb.cells.splice(i + 1, 0, c); $('#nbcells').insertBefore(c.div, $('#nbcells').children[i + 1] || null); } }, { sep: 1 }, { l: 'Rechercher...', f: () => findDialog(E) }, { l: 'Rechercher et remplacer...', f: () => findDialog(E, true) }],
      Affichage: [{ l: 'Afficher / masquer l\'en-tête', f: () => document.querySelector('.nb-head').classList.toggle('hide') }, { l: 'Afficher / masquer la barre d\'outils', f: () => document.querySelector('.app-tool').classList.toggle('hide') }, { l: 'Numéros de ligne', chk: () => showLines, f: () => { showLines = !showLines; nb.cells.forEach(c => c.ed.lines(showLines)); } }, { sep: 1 }, { l: 'Agrandir le texte', f: () => { fontPx = Math.min(26, fontPx + 1); nb.cells.forEach(c => c.ed.font(fontPx)); } }, { l: 'Réduire le texte', f: () => { fontPx = Math.max(10, fontPx - 1); nb.cells.forEach(c => c.ed.font(fontPx)); } }],
      Insertion: [{ l: 'Insérer une cellule au-dessus', f: () => nbAdd(idx(), 'code') }, { l: 'Insérer une cellule en dessous', f: () => nbAdd(idx() + 1, 'code') }],
      Cellule: [{ l: 'Exécuter les cellules', k: 'Ctrl+Entrée', f: () => nbRun(cur(), 'stay') }, { l: 'Exécuter et sélectionner la suivante', k: 'Maj+Entrée', f: () => nbRun(cur(), 'next') }, { l: 'Exécuter et insérer dessous', k: 'Alt+Entrée', f: () => nbRun(cur(), 'below') }, { sep: 1 }, { l: 'Tout exécuter', f: nbRunAll }, { l: 'Exécuter les cellules au-dessus', f: () => idx() > 0 && nbExecUpTo(idx() - 1, 0) }, { l: 'Exécuter la cellule et celles en dessous', f: () => nbExecUpTo(nb.cells.length - 1, idx()) }, { sep: 1 }, { l: 'Type de cellule', sub: [{ l: 'Code', chk: () => cur().type === 'code', f: () => { cur().type = 'code'; cur().rendered = false; nbDraw(cur()); $('#nb-type').value = 'code'; } }, { l: 'Markdown', chk: () => cur().type === 'md', f: () => { cur().type = 'md'; nbDraw(cur()); $('#nb-type').value = 'md'; } }] }, { l: 'Sorties actuelles', sub: [{ l: 'Effacer', f: () => { cur().outEl.classList.add('hide'); } }, { l: 'Tout effacer', f: nbClear }] }],
      Noyau: [{ l: 'Interrompre', f: () => AC.toast('Aucune exécution en cours.') }, { l: 'Redémarrer', f: () => { nbClear(); AC.toast('Noyau redémarré : les variables sont réinitialisées.'); } }, { l: 'Redémarrer et effacer les sorties', f: nbClear }, { l: 'Redémarrer et tout exécuter', f: () => { nbClear(); nbRunAll(); } }, { sep: 1 }, { l: 'Changer de noyau', sub: [{ l: 'Python 3 (ipykernel)', chk: () => true, f: () => {} }] }],
      Aide: [{ l: 'Aide du notebook', f: () => ref('Aide', PY_HELP) }, { l: 'Raccourcis clavier', f: () => ref('Raccourcis clavier', PY_HELP) }, { l: 'Référence Markdown', f: () => ref('Markdown', '<table><tr><td><code># Titre</code></td><td>Titre</td></tr><tr><td><code>**gras**</code></td><td><b>gras</b></td></tr><tr><td><code>`code`</code></td><td>code en ligne</td></tr><tr><td><code>- élément</code></td><td>liste</td></tr></table>') }, { l: 'À propos', f: () => ref('À propos', '<p>Notebook DataEcon.Ci reproduisant Jupyter (Python 3 exécuté dans le navigateur).</p>') }]
    };
  }

  function starter() { return OUTIL === 'sql' ? '-- Écrivez votre requête ici\n' : '# Écrivez votre code ici\n'; }

  function initEditor(initial) {
    const val = initial || starter();
    docs = []; activeDoc = 0; lastRes = null; lastCode = '';
    if (OUTIL === 'python') {
      nb = { cells: [], cur: 0, count: 0 };
      const first = nbAdd(0, 'code', val);
      editor = { get: () => nb.cells.filter(c => c.type === 'code').map(c => c.ed.get()).join('\n\n'), set: v => { $('#nbcells').innerHTML = ''; nb.cells = []; nb.count = 0; nbAdd(0, 'code', v); }, focus: () => nbCur().ed.focus() };
      menuInit(menusPy());
      $('#nb-add').onclick = () => nbAdd(nb.cur + 1, 'code'); $('#nb-cut').onclick = () => { nbClip.cell = { type: nbCur().type, src: nbCur().ed.get() }; nbDel(nb.cur); };
      $('#nb-copy').onclick = () => { nbClip.cell = { type: nbCur().type, src: nbCur().ed.get() }; AC.toast('Cellule copiée.'); };
      $('#nb-paste').onclick = () => { if (nbClip.cell) nbAdd(nb.cur + 1, nbClip.cell.type, nbClip.cell.src); };
      $('#nb-run').onclick = () => nbRun(nbCur(), 'next'); $('#nb-stop').onclick = () => AC.toast('Aucune exécution en cours.');
      $('#nb-restart').onclick = () => { nbClear(); AC.toast('Noyau redémarré.'); }; $('#nb-runall').onclick = nbRunAll;
      $('#nb-type').onchange = e => { const c = nbCur(); c.type = e.target.value; c.rendered = c.type === 'md'; nbDraw(c); };
      return;
    }
    const host = $('#editor');
    const keys = OUTIL === 'r' ? { 'Ctrl-Enter': () => runR('line'), 'Cmd-Enter': () => runR('line'), 'Shift-Ctrl-S': () => runR('all'), 'Shift-Ctrl-C': () => ed.comment(), 'Ctrl-S': () => saveDoc() }
      : { F5: () => runSQL(), 'Ctrl-Enter': () => runSQL(), 'Cmd-Enter': () => runSQL(), 'Ctrl-S': () => saveDoc() };
    ed = mkEd(host, val, keys);
    docs = [{ name: FICHIERS[OUTIL], src: val }]; renderDocTabs();
    editor = { get: () => ed.get(), set: v => { ed.set(v); docs[activeDoc].src = v; }, focus: () => ed.focus() };
    paneTabs();
    if (OUTIL === 'r') {
      menuInit(menusR());
      $('#r-new').onclick = () => newDoc(); $('#r-save').onclick = saveDoc; $('#r-line').onclick = () => runR('line'); $('#r-src').onclick = () => runR('all');
      const ti = $('#termin'); ti.addEventListener('keydown', e => { if (e.key === 'Enter') { termCmd(ti.value); ti.value = ''; } });
    } else if (OUTIL === 'sql') {
      menuInit(menusSQL());
      $('#q-new').onclick = () => newDoc(); $('#q-save').onclick = saveDoc; $('#q-run').onclick = () => runSQL(); $('#q-plan').onclick = planSQL; $('#q-fmt').onclick = fmtSQL;
      refreshExplorer();
    }
  }
  function menuInit(defs) { AC.menubar($('#appmenu'), defs); }

  async function lancer(override, opts) {
    opts = opts || {};
    if (OUTIL === 'python' && override === undefined) return nbRunAll();
    const code = (override !== undefined ? override : editor.get()).trim();
    const out = $('#out'), st = $('#status'), btn = $('#b-run');
    if (!code) { out.innerHTML = '<span class="err">Écrivez du code avant d\'exécuter.</span>'; return null; }
    if (btn) btn.disabled = true; running = true; st.textContent = 'Exécution... (le premier lancement charge le moteur ' + NOMS[OUTIL] + ')';
    const t0 = performance.now();
    try {
      if (OUTIL === 'sql' && opts.fresh) engines.resetSql();
      const r = await engines.run(OUTIL, code, opts);
      const dt = ((performance.now() - t0) / 1000);
      if (OUTIL === 'sql') {
        lastRes = r.cols ? { columns: r.cols, values: r.rows } : lastRes;
        const mb = $('#msgbox'); if (mb) mb.innerHTML = '<div>' + esc(r.msg || 'Commandes exécutées.') + '</div>' + (showTime ? '<div class="muted">Durée d\'exécution : ' + dt.toFixed(3) + ' s</div>' : '');
        refreshExplorer();
      }
      if (OUTIL === 'r' && r.env) { const eb = $('#envbox'); if (eb) eb.innerHTML = r.env.length ? '<table><tr><th>Nom</th><th>Classe</th><th>Longueur</th></tr>' + r.env.map(x => '<tr><td>' + esc(x[0]) + '</td><td>' + esc(x[1]) + '</td><td>' + esc(x[2]) + '</td></tr>').join('') + '</table>' : '<span class="muted">Environnement vide.</span>'; }
      out.innerHTML = r.html || (r.text ? '<pre style="margin:0;color:inherit;background:none">' + esc(r.text) + '</pre>' : '<span class="muted">Le code s\'est exécuté sans rien afficher.</span>');
      st.textContent = dt.toFixed(2) + ' s';
      return r;
    } catch (e) {
      out.innerHTML = '<span class="err">' + esc(e.message || e) + '</span>';
      if (OUTIL === 'sql') { const mb = $('#msgbox'); if (mb) mb.innerHTML = '<div class="err">Msg : ' + esc(e.message || e) + '</div>'; if ($('#ctabs')) showPane('out'); }
      st.textContent = 'Erreur';
      return null;
    } finally { if (btn) btn.disabled = false; running = false; }
  }

  const DONNEES = [
    ['Abidjan', 'Cacao', '2024-01', 120, 1500], ['Abidjan', 'Café', '2024-01', 85, 1200], ['San-Pédro', 'Cacao', '2024-02', 200, 1520], ['Bouaké', 'Anacarde', '2024-02', 150, 800],
    ['Daloa', 'Café', '2024-02', 60, 1180], ['Abidjan', 'Cacao', '2024-03', 180, 1550], ['Korhogo', 'Anacarde', '2024-03', 220, 820], ['Bouaké', 'Coton', '2024-03', 95, 950],
    ['San-Pédro', 'Cacao', '2024-04', 250, 1600], ['Man', 'Café', '2024-04', 110, 1250], ['Korhogo', 'Coton', '2024-05', 130, 980], ['Bouaké', 'Anacarde', '2024-05', 175, 850],
    ['Abidjan', 'Cacao', '2024-06', 300, 1650], ['Daloa', 'Café', '2024-06', 90, 1220], ['Korhogo', 'Coton', '2024-07', 140, 1000]
  ].map(r => ({ ville: r[0], produit: r[1], date: r[2], quantite: r[3], ca: r[3] * r[4] }));

  const PRODUITS = ['Cacao', 'Café', 'Anacarde', 'Coton'];
  const VILLES = ['Abidjan', 'Bouaké', 'Daloa', 'Korhogo', 'Man', 'San-Pédro'];
  let studioCfg = null;
  const opt = (arr, all) => '<option value="">' + all + '</option>' + arr.map(v => '<option value="' + v + '">' + v + '</option>').join('');

  function studioHTML() {
    return '<div class="tb-app">' +
      '<div class="tb-title"><span class="tb-logo">+</span> Classeur1 - Tableau Public</div>' +
      '<div class="tb-menu" id="tbmenu"></div>' +
      '<div class="tb-body">' +
        '<aside class="tb-data"><div class="tb-h">Données</div><div class="tb-src"><i class="fas fa-database"></i> Ventes (échantillon)</div>' +
          '<div class="tb-sub">Tables</div><ul><li><i class="fas fa-table"></i> Ventes</li></ul>' +
          '<div class="tb-sub">Dimensions</div><ul class="dim"><li draggable="true" data-f="date"><i class="fas fa-calendar"></i> Date</li><li draggable="true" data-f="produit"><i>Abc</i> Produit</li><li draggable="true" data-f="ville"><i>Abc</i> Ville</li></ul>' +
          '<div class="tb-sub">Mesures</div><ul class="mes"><li draggable="true" data-f="quantite"><i>#</i> Quantité</li><li draggable="true" data-f="ca"><i>#</i> Chiffre d\'affaires</li><li draggable="true" data-f="nb"><i>#</i> Nombre de ventes</li></ul></aside>' +
        '<section class="tb-main">' +
          '<div class="tb-shelf" data-drop="dim"><span>Colonnes<br><small>Dimension</small></span><div class="tb-pill dim"><select id="s-dim"><option value="ville">Ville</option><option value="produit">Produit</option><option value="date">Mois</option></select></div></div>' +
          '<div class="tb-shelf" data-drop="mes"><span>Lignes<br><small>Mesure</small></span><div class="tb-pill mes"><select id="s-mes"><option value="quantite">Quantité totale</option><option value="ca">Chiffre d\'affaires</option><option value="nb">Nombre de ventes</option><option value="prix">Prix moyen (FCFA)</option></select></div></div>' +
          '<div class="pl-chartbox"><canvas id="chart"></canvas></div>' +
        '</section>' +
        '<aside class="tb-right">' +
          '<div class="tb-card"><div class="tb-h">Filtres</div>' +
            '<label>Produit<select id="s-fp">' + opt(PRODUITS, 'Tous') + '</select></label>' +
            '<label>Ville<select id="s-fv">' + opt(VILLES, 'Toutes') + '</select></label>' +
            '<label>Période<select id="s-per"><option value="">Toute l\'année</option><option value="T1">1er trimestre</option><option value="T2">2e trimestre</option><option value="T3">3e trimestre</option></select></label></div>' +
          '<div class="tb-card"><div class="tb-h">Repères</div>' +
            '<label>Graphique (type de marque)<select id="s-type"><option value="bar">Barres</option><option value="barh">Barres horizontales</option><option value="pie">Camembert</option><option value="line">Lignes</option><option value="area">Aires</option></select></label>' +
            '<label>Tri<select id="s-tri"><option value="">Aucun</option><option value="desc">Décroissant</option><option value="asc">Croissant</option></select></label>' +
            '<label>Afficher<select id="s-top"><option value="0">Tout</option><option value="3">Top 3</option><option value="5">Top 5</option></select></label></div>' +
          '<button class="pl-btn run" id="s-go"><i class="fas fa-chart-column"></i> Générer</button>' +
        '</aside>' +
      '</div>' +
      '<div class="tb-sheets" id="tbsheets"></div></div>' +
      '<textarea class="pl-answer" id="answer" placeholder="Décrivez ce que vous observez (une ou deux phrases)..."></textarea>';
  }
  const tbDrop = (f, kind) => { const isDim = ['date', 'produit', 'ville'].indexOf(f) >= 0; if (kind && (kind === 'dim') !== isDim) { AC.toast(isDim ? 'Une dimension se place sur Colonnes.' : 'Une mesure se place sur Lignes.'); return; } $('#' + (isDim ? 's-dim' : 's-mes')).value = f; };
  const PALS = { 'Classique': ['#0b2a4a', '#1f5f99', '#c2a15a', '#5b9bd5', '#8aa0b5', '#a8873f', '#123a63'], 'Vive': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#17becf'], 'Sobre': ['#4d4d4d', '#7f7f7f', '#a6a6a6', '#c2a15a', '#8aa0b5', '#5b6770', '#333333'] };
  const tbOpt = { labels: false, avg: false, legend: false, pal: 'Classique' };
  let tbRows = [], tbMes = '';
  const TB_IDS = ['s-dim', 's-mes', 's-fp', 's-fv', 's-per', 's-type', 's-tri', 's-top'];
  let tbSheets = [{ name: 'Feuille 1', vals: null, gen: false }], tbCur = 0;
  function tbVals() { const o = {}; TB_IDS.forEach(i => { o[i] = $('#' + i).value; }); return o; }
  function tbSet(o) { TB_IDS.forEach(i => { if (o && o[i] !== undefined) $('#' + i).value = o[i]; }); }
  function tbReset() { TB_IDS.forEach(i => { const e = $('#' + i); e.selectedIndex = 0; }); if (engines.chart) { engines.chart.destroy(); engines.chart = null; } graphiqueGenere = false; studioCfg = null; tbRows = []; }
  function tbSheetsDraw() {
    const el = $('#tbsheets'); if (!el) return;
    el.innerHTML = tbSheets.map((t, i) => '<span class="' + (i === tbCur ? 'on' : '') + '" data-i="' + i + '">' + esc(t.name) + (tbSheets.length > 1 && i === tbCur ? ' <b class="tbx" title="Supprimer la feuille">&times;</b>' : '') + '</span>').join('') + '<span class="add" id="tbadd" title="Nouvelle feuille">+</span>';
    el.querySelectorAll('span[data-i]').forEach(sp => { sp.onclick = e => { if (e.target.classList.contains('tbx')) { tbDel(); return; } tbSwitch(+sp.dataset.i); }; sp.ondblclick = () => { const n = prompt('Nom de la feuille', tbSheets[+sp.dataset.i].name); if (n) { tbSheets[+sp.dataset.i].name = n.slice(0, 30); tbSheetsDraw(); } }; });
    $('#tbadd').onclick = () => tbNew();
  }
  function tbSave() { tbSheets[tbCur].vals = tbVals(); tbSheets[tbCur].gen = graphiqueGenere; }
  function tbSwitch(i) { tbSave(); tbCur = i; const t = tbSheets[i]; tbReset(); if (t.vals) tbSet(t.vals); tbSheetsDraw(); if (t.gen) $('#s-go').click(); }
  function tbNew(dup) { tbSave(); const n = 'Feuille ' + (tbSheets.length + 1); tbSheets.push({ name: n, vals: dup ? tbVals() : null, gen: !!dup && graphiqueGenere }); tbSwitch(tbSheets.length - 1); }
  function tbDel() { if (tbSheets.length < 2) return; tbSheets.splice(tbCur, 1); tbCur = Math.max(0, tbCur - 1); const t = tbSheets[tbCur]; tbReset(); if (t.vals) tbSet(t.vals); tbSheetsDraw(); if (t.gen) $('#s-go').click(); }
  function tbCsv() { if (!tbRows.length) { AC.toast('Générez d\'abord un graphique.'); return; } AC.download('tableau.csv', '\ufeff' + [['Catégorie', tbMes].join(';')].concat(tbRows.map(r => r.join(';'))).join('\n'), 'text/csv;charset=utf-8'); }
  function tbMenus() {
    const regen = () => { if (graphiqueGenere) $('#s-go').click(); };
    const na = t => () => AC.modal({ title: t, html: '<p>Cette fonction n\'est pas disponible dans le laboratoire (version simplifiée axée sur la création de feuilles de calcul).</p>' });
    return {
      'Fichier': [{ l: 'Nouveau classeur', f: () => { tbSheets = [{ name: 'Feuille 1', vals: null, gen: false }]; tbCur = 0; tbReset(); tbSheetsDraw(); } }, { sep: 1 }, { l: 'Exporter l\'image...', dis: () => !engines.chart, f: () => { const a = document.createElement('canvas'), c = $('#chart'); a.width = c.width; a.height = c.height; const x = a.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, a.width, a.height); x.drawImage(c, 0, 0); const l = document.createElement('a'); l.href = a.toDataURL('image/png'); l.download = 'graphique.png'; l.click(); } }, { l: 'Exporter les données (CSV)', f: tbCsv }, { l: 'Imprimer', f: () => window.print() }, { sep: 1 }, { l: 'Quitter', f: () => { location.href = '/formations'; } }],
      'Données': [{ l: 'Afficher les données', f: () => AC.modal({ title: 'Afficher les données : Ventes', wide: true, html: '<div style="max-height:340px;overflow:auto"><table><tr><th>Ville</th><th>Produit</th><th>Date</th><th>Quantité</th><th>Chiffre d\'affaires</th></tr>' + DONNEES.map(d => '<tr><td>' + d.ville + '</td><td>' + d.produit + '</td><td>' + d.date + '</td><td>' + d.quantite + '</td><td>' + d.ca.toLocaleString('fr-FR') + '</td></tr>').join('') + '</table></div>' }) }, { l: 'Actualiser la source de données', k: 'F5', f: () => { regen(); AC.toast('Source actualisée.'); } }, { l: 'Modifier la source de données...', f: na('Source de données') }],
      'Feuille de calcul': [{ l: 'Nouvelle feuille de calcul', f: () => tbNew() }, { l: 'Dupliquer', f: () => tbNew(true) }, { l: 'Effacer la feuille', f: () => { tbReset(); } }, { sep: 1 }, { l: 'Afficher les étiquettes de marque', chk: () => tbOpt.labels, f: () => { tbOpt.labels = !tbOpt.labels; regen(); } }, { l: 'Afficher la légende', chk: () => tbOpt.legend, f: () => { tbOpt.legend = !tbOpt.legend; regen(); } }, { sep: 1 }, { l: 'Supprimer la feuille', dis: () => tbSheets.length < 2, f: tbDel }],
      'Tableau de bord': [{ l: 'Nouveau tableau de bord', f: na('Tableau de bord') }],
      'Histoire': [{ l: 'Nouvelle histoire', f: na('Histoire') }],
      'Analyse': [{ l: 'Ligne de moyenne', chk: () => tbOpt.avg, f: () => { tbOpt.avg = !tbOpt.avg; regen(); } }, { l: 'Totaux', dis: () => !tbRows.length, f: () => AC.modal({ title: 'Totaux', html: '<p>' + esc(tbMes) + ' : <b>' + tbRows.reduce((a, r) => a + r[1], 0).toLocaleString('fr-FR') + '</b> sur ' + tbRows.length + ' catégorie(s).</p>' }) }, { l: 'Moyenne par catégorie', dis: () => !tbRows.length, f: () => AC.modal({ title: 'Moyenne', html: '<p>' + esc(tbMes) + ' moyen : <b>' + Math.round(tbRows.reduce((a, r) => a + r[1], 0) / tbRows.length).toLocaleString('fr-FR') + '</b></p>' }) }],
      'Carte': [{ l: 'Cartes géographiques', f: na('Carte') }],
      'Format': [{ l: 'Palette de couleurs', sub: Object.keys(PALS).map(n => ({ l: n, chk: () => tbOpt.pal === n, f: () => { tbOpt.pal = n; regen(); } })) }],
      'Fenêtre': [{ l: 'Présenter', k: 'F7', f: () => { const e = document.querySelector('.tb-app'); if (e.requestFullscreen) e.requestFullscreen(); } }, { l: 'Réinitialiser les volets', f: () => { document.querySelectorAll('.tb-data,.tb-right').forEach(x => x.classList.remove('hide')); } }, { l: 'Volet Données', chk: () => !document.querySelector('.tb-data').classList.contains('hide'), f: () => document.querySelector('.tb-data').classList.toggle('hide') }, { l: 'Volet Filtres et repères', chk: () => !document.querySelector('.tb-right').classList.contains('hide'), f: () => document.querySelector('.tb-right').classList.toggle('hide') }],
      'Aide': [{ l: 'Guide de la feuille de calcul', f: () => AC.modal({ title: 'Guide', wide: true, html: '<ol><li>Glissez une dimension (Ville, Produit, Date) vers <b>Colonnes</b>, ou choisissez-la dans la liste.</li><li>Glissez une mesure vers <b>Lignes</b>.</li><li>Réglez les filtres et le type de graphique, puis cliquez sur <b>Générer</b>.</li><li>Ajoutez des feuilles avec le bouton +.</li></ol>' }) }, { l: 'À propos', f: () => AC.modal({ title: 'À propos', html: '<p>Environnement d\'entraînement DataEcon.Ci inspiré de l\'organisation de Tableau.</p>' }) }]
    };
  }
  async function initStudio() {
    AC.menubar($('#tbmenu'), tbMenus()); tbSheetsDraw();
    document.querySelectorAll('.tb-data li[data-f]').forEach(li => {
      li.addEventListener('dragstart', e => { e.dataTransfer.setData('text/plain', li.dataset.f); });
      li.addEventListener('dblclick', () => tbDrop(li.dataset.f));
    });
    document.querySelectorAll('.tb-shelf[data-drop]').forEach(sh => { sh.addEventListener('dragover', e => e.preventDefault()); sh.addEventListener('drop', e => { e.preventDefault(); tbDrop(e.dataTransfer.getData('text/plain'), sh.dataset.drop); }); });
    if (!window.Chart) { try { await loadScript('https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js'); } catch (e) {} }
    $('#s-go').onclick = () => {
      if (!window.Chart) { feedback(false, 'Le module de graphiques n\'a pas pu se charger. Vérifiez votre connexion.'); return; }
      const cfg = { dim: $('#s-dim').value, mes: $('#s-mes').value, type: $('#s-type').value, produit: $('#s-fp').value, ville: $('#s-fv').value, periode: $('#s-per').value, tri: $('#s-tri').value, top: $('#s-top').value };
      const inPer = d => !cfg.periode || (cfg.periode === 'T1' ? d <= '2024-03' : cfg.periode === 'T2' ? (d >= '2024-04' && d <= '2024-06') : d >= '2024-07');
      const rows = DONNEES.filter(d => (!cfg.produit || d.produit === cfg.produit) && (!cfg.ville || d.ville === cfg.ville) && inPer(d.date));
      if (!rows.length) { feedback(false, 'Aucune donnée ne correspond à ces filtres. Modifiez-les puis regénérez.'); return; }
      const agg = {};
      rows.forEach(d => { const k = d[cfg.dim]; const a = agg[k] || (agg[k] = { q: 0, ca: 0, nb: 0 }); a.q += d.quantite; a.ca += d.ca; a.nb += 1; });
      const val = a => cfg.mes === 'quantite' ? a.q : cfg.mes === 'ca' ? a.ca : cfg.mes === 'nb' ? a.nb : Math.round(a.ca / a.q);
      let items = Object.keys(agg).sort().map(k => [k, val(agg[k])]);
      if (cfg.tri === 'desc') items.sort((x, y) => y[1] - x[1]); else if (cfg.tri === 'asc') items.sort((x, y) => x[1] - y[1]);
      if (+cfg.top) items = items.slice(0, +cfg.top);
      const labels = items.map(i => i[0]), data = items.map(i => i[1]);
      const nomMes = { quantite: 'Quantité', ca: 'Chiffre d\'affaires (FCFA)', nb: 'Nombre de ventes', prix: 'Prix moyen (FCFA)' }[cfg.mes];
      const pal = PALS[tbOpt.pal];
      const isLine = cfg.type === 'line' || cfg.type === 'area';
      if (engines.chart) engines.chart.destroy();
      engines.chart = new window.Chart($('#chart'), { type: cfg.type === 'barh' ? 'bar' : (cfg.type === 'area' ? 'line' : cfg.type),
        data: { labels, datasets: [{ label: nomMes, data, backgroundColor: isLine ? 'rgba(31,95,153,.18)' : pal, borderColor: '#1f5f99', borderWidth: 2, fill: cfg.type === 'area', tension: .3 }] },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: cfg.type === 'barh' ? 'y' : 'x', plugins: { legend: { display: cfg.type === 'pie' || tbOpt.legend } } },
        plugins: [{ id: 'lbl', afterDatasetsDraw(c) { if (!tbOpt.labels) return; const x = c.ctx; x.save(); x.font = '12px sans-serif'; x.fillStyle = '#0b2a4a'; x.textAlign = 'center'; c.getDatasetMeta(0).data.forEach((el, i) => { const v = c.data.datasets[0].data[i]; x.fillText(Number(v).toLocaleString('fr-FR'), el.x + (c.options.indexAxis === 'y' ? 28 : 0), el.y - (c.options.indexAxis === 'y' ? 0 : 6)); }); x.restore(); } }] });
      if (tbOpt.avg && cfg.type !== 'pie' && cfg.type !== 'barh') { const m = data.reduce((a, b) => a + b, 0) / data.length; engines.chart.data.datasets.push({ type: 'line', label: 'Moyenne', data: data.map(() => m), borderColor: '#c2a15a', borderDash: [6, 4], pointRadius: 0, fill: false }); engines.chart.update(); }
      tbRows = items.map(i => [i[0], i[1]]); tbMes = nomMes;
      studioCfg = cfg; graphiqueGenere = true;
      const fb = $('#fb'); fb.className = 'pl-feedback'; fb.innerHTML = '';
    };
  }

  const norm = s => String(s).replace(/\r/g, '').split('\n').map(l => l.trim()).filter(Boolean).join('\n').replace(/\s+/g, ' ').toLowerCase();

  async function soumettre(c) {
    const ex = c.exercice, fb = $('#fb'), btn = $('#b-submit');
    const code = (OUTIL === 'tableau' || OUTIL === 'smartpls' || OUTIL === 'powerbi') ? $('#answer').value.trim() : editor.get().trim();
    if (!code || /^(#|--)[^\n]*$/.test(code)) { feedback(false, 'Écrivez d\'abord votre réponse.'); return; }
    btn.disabled = true;
    let ok = false, msg = '';
    try {
      if (OUTIL === 'smartpls' || OUTIL === 'powerbi') {
        const t = code.toLowerCase().replace(/\s+/g, ' ');
        const mots = ex.mots_cles || [];
        const test = (m) => m.split('|').some(a => { try { return new RegExp(a.toLowerCase()).test(t); } catch (e) { return t.includes(a.toLowerCase()); } });
        const trouves = mots.filter(test).length;
        if (code.length < 25) msg = 'Votre interprétation est trop courte. Rédigez une ou deux phrases en citant les éléments demandés.';
        else if (mots.length && trouves < Math.max(1, Math.ceil(mots.length * 0.6))) msg = 'Votre réponse est incomplète : reprenez les éléments de l\'énoncé (valeurs, fonctions, étapes), justifiez et concluez (un indice est disponible).';
        else ok = true;
      } else if (OUTIL === 'tableau') {
        const mots = [...new Set((ex.mots_cles || []).map(m => m.toLowerCase()))];
        const t = code.toLowerCase();
        const trouves = mots.filter(m => m.split('|').some(a => t.includes(a))).length;
        const noms = { dim: 'la dimension', mes: 'la mesure', type: 'le type de graphique', produit: 'le filtre Produit', ville: 'le filtre Ville', periode: 'le filtre Période', tri: 'le tri', top: 'l\'option Afficher' };
        const faux = (!ex.attendu || !studioCfg) ? [] : Object.keys(ex.attendu).filter(k => String(studioCfg[k]) !== String(ex.attendu[k]));
        if (!graphiqueGenere) msg = 'Générez d\'abord le graphique demandé avec le bouton « Générer ».';
        else if (faux.length) msg = 'Vérifiez ' + faux.map(k => noms[k] || k).join(', ') + ' : le graphique généré ne correspond pas à la consigne.';
        else if (mots.length && trouves < Math.max(1, Math.ceil(mots.length * 0.5))) msg = 'Le graphique est correct, mais votre description est incomplète. Citez ce que vous observez (un indice est disponible).';
        else ok = true;
      } else {
        const r = await lancer(undefined, { fresh: true });
        if (!r) { msg = 'Votre code contient une erreur. Lisez le message dans la console.'; }
        else {
          let ref = null;
          try { ref = await exec(ex.solution_attendue); } catch (e) { ref = null; }
          if (ref) {
            let same;
            if (OUTIL === 'sql') {
              const a = r.rows.map(x => JSON.stringify(x)), b = ref.rows.map(x => JSON.stringify(x));
              same = /order\s+by/i.test(ex.solution_attendue) ? a.join('|') === b.join('|') : a.slice().sort().join('|') === b.slice().sort().join('|');
            } else same = norm(r.text) === norm(ref.text);
            if (same) ok = true;
          }
          if (!ok) {
            const low = code.toLowerCase();
            const manque = (ex.mots_cles || []).filter(m => !low.includes(String(m).toLowerCase()));
            if (!manque.length && r.text !== undefined && ref === null) ok = true;
            else msg = OUTIL === 'sql' ? 'Le résultat de votre requête ne correspond pas à celui attendu. Vérifiez les colonnes, les conditions et l\'ordre.' : 'Le résultat affiché ne correspond pas à celui attendu. Comparez avec l\'énoncé.';
          }
        }
      }
    } catch (e) { msg = 'Erreur : ' + (e.message || e); }
    btn.disabled = false;
    if (ok) {
      if (!etat.valides[c.id]) {
        const gain = solutionVue ? 20 : (indiceVu ? 35 : 50);
        etat.xp += gain; etat.valides[c.id] = { xp: gain }; save();
        feedback(true, 'Bravo ! +' + gain + ' XP');
      } else feedback(true, 'Réponse correcte (déjà validée).');
      majTop(); $('#b-next').disabled = false;
    } else { essais++; majBoutons(); feedback(false, msg || 'Pas tout à fait. Réessayez.'); }
  }

  function feedback(ok, text) {
    const fb = $('#fb');
    fb.className = 'pl-feedback ' + (ok ? 'ok' : 'bad');
    fb.innerHTML = '<i class="fas ' + (ok ? 'fa-circle-check' : 'fa-circle-xmark') + '"></i> ' + esc(text) +
      (ok ? '<button class="next" id="fb-next">' + (idx + 1 >= lecon.concepts.length ? 'Terminer' : 'Concept suivant') + ' <i class="fas fa-arrow-right"></i></button>' : '');
    const n = $('#fb-next'); if (n) n.onclick = () => aller(idx + 1);
  }

  function fin() {
    const total = lecon.concepts.length, ok = Object.keys(etat.valides).length;
    body.innerHTML = '<section class="pl-end"><div class="medal"><i class="fas fa-trophy"></i></div><h2>Cours terminé</h2>' +
      '<p data-speak="' + esc('Félicitations ! Vous avez terminé le cours ' + lecon.titre + '. Vous avez gagné ' + etat.xp + ' points.') + '">Vous avez terminé « ' + esc(lecon.titre) + ' ».</p>' +
      '<div class="stats"><div class="stat"><strong>' + ok + ' / ' + total + '</strong>exercices réussis</div><div class="stat"><strong>' + etat.xp + '</strong>points XP</div></div>' +
      '<a class="pl-cta" href="/certification/' + OUTIL + '/' + NIVEAU + '" style="text-decoration:none"><i class="fas fa-certificate"></i> Passer l\'examen et obtenir le certificat</a> ' +
      '<a class="pl-link" href="/formations" style="margin-left:8px;text-decoration:none">Choisir un autre cours</a> ' +
      '<button class="pl-link" id="redo" style="margin-left:8px">Refaire le cours</button></section>';
    $('#redo').onclick = () => { etat = { xp: 0, valides: {}, auto: etat.auto }; save(); aller(-1); };
  }

  function tutor() {
    const panel = $('#tutor'), msgs = $('#tutor-msgs');
    $('#tutor-fab').onclick = () => { panel.hidden = !panel.hidden; if (!panel.hidden) $('#tutor-input').focus(); };
    $('#tutor-close').onclick = () => { panel.hidden = true; };
    $('#tutor-form').onsubmit = async e => {
      e.preventDefault();
      const inp = $('#tutor-input'), q = inp.value.trim(); if (!q) return;
      inp.value = '';
      add('me', q);
      const wait = add('bot', '...');
      const c = idx >= 0 && idx < lecon.concepts.length ? lecon.concepts[idx] : null;
      try {
        const r = await fetch('/api/tutor', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: q, outil: OUTIL, niveau: NIVEAU, concept: c ? { titre: c.titre, objectif: c.objectif, explication: c.explication, exercice: c.exercice.enonce, solution: c.exercice.solution_attendue, indice: c.exercice.indice } : null }) });
        const j = await r.json();
        wait.textContent = j.reponse || 'Pas de réponse.';
      } catch (err) { wait.textContent = 'Instructeur indisponible pour le moment.'; }
      msgs.scrollTop = msgs.scrollHeight;
    };
    function add(cls, t) { const d = document.createElement('div'); d.className = 'msg ' + cls; d.textContent = t; msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; return d; }
  }

  async function init() {
    narrator.init();
    $('#v-play').onclick = () => narrator.start();
    $('#v-pause').onclick = () => narrator.toggle();
    $('#v-stop').onclick = () => narrator.stop();
    $('#v-auto').onchange = e => { etat.auto = e.target.checked; save(); };
    window.addEventListener('beforeunload', () => narrator.stop(true));
    try {
      const r = await fetch('/api/lesson/' + OUTIL + '/' + NIVEAU);
      if (!r.ok) throw new Error('indisponible');
      lecon = await r.json();
    } catch (e) {
      $('#pl-course-title').textContent = NOMS[OUTIL];
      body.innerHTML = '<div class="pl-loading"><i class="fas fa-hourglass-half"></i><br><br>Ce cours (' + NOMS[OUTIL] + ', ' + NIVEAU + ') sera bientôt disponible.<br><br><a href="/formations" class="pl-cta" style="text-decoration:none">Retour aux formations</a></div>';
      return;
    }
    tutor();
    aller(-1);
  }
  init();
})();
