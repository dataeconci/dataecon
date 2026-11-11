/* ===== Lecteur de cours interactif DataEcon.Ci ===== */
(function () {
  'use strict';

  const root = document.getElementById('pl');
  const OUTIL = root.dataset.outil;
  const NIVEAU = root.dataset.niveau;
  const KEY = 'dataecon_player_' + OUTIL + '_' + NIVEAU;
  const NOMS = { python: 'Python', r: 'R', sql: 'SQL', tableau: 'Tableau' };
  const MODES = { python: 'python', r: 'r', sql: 'text/x-sql', tableau: 'text/plain' };
  const FICHIERS = { python: 'exercice.py', r: 'exercice.R', sql: 'requete.sql', tableau: 'analyse.txt' };

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

  /* ---------- Illustrations de couverture par outil ---------- */
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
    return head + "<rect x='60' y='60' width='480' height='220' rx='14' fill='#fff' fill-opacity='.95'/>" +
      "<g><rect x='90' y='170' width='36' height='80' fill='#c2a15a'/><rect x='136' y='140' width='36' height='110' fill='#1f5f99'/><rect x='182' y='110' width='36' height='140' fill='#0b2a4a'/><rect x='228' y='150' width='36' height='100' fill='#5b9bd5'/></g>" +
      "<circle cx='400' cy='150' r='60' fill='#1f5f99'/><path d='M400 150 L400 90 A60 60 0 0 1 452 180 Z' fill='#c2a15a'/><path d='M400 150 L452 180 A60 60 0 0 1 360 196 Z' fill='#0b2a4a'/>" +
      "<polyline points='300,240 340,220 380,230 430,205 500,215' fill='none' stroke='#c2a15a' stroke-width='3'/><text x='300' y='300' fill='#fff' font-size='20' font-weight='700'>Tableau</text>" + foot;
  }

  /* ---------- Narration vocale (Web Speech API) ---------- */
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

  /* ---------- Jeux de données du cours (static/data) ---------- */
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

  /* ---------- Moteurs d'exécution ---------- */
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
      // Charger automatiquement les paquets importés (pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib)
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

    async r(code) {
      if (!this.r_) {
        const { WebR } = await import('https://webr.r-wasm.org/v0.4.2/webr.mjs');
        this.r_ = new WebR({ channelType: 'PostMessage' });
        await this.r_.init();
      }
      for (const [n, buf] of await fichiersPour(code)) await this.r_.FS.writeFile('/home/web_user/' + n, buf);
      const shelter = await new this.r_.Shelter();
      try {
        await shelter.captureR('rm(list=ls())');
        const res = await shelter.captureR(code, { withAutoprint: true });
        const text = res.output.map(o => o.data).join('\n');
        const err = res.output.some(o => o.type === 'stderr');
        return { text: text.trimEnd(), warn: err };
      } finally { await shelter.purge(); }
    },

    async sql(code) {
      if (!window.initSqlJs) await loadScript('https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.js');
      if (!this.sqlMod) this.sqlMod = await window.initSqlJs({ locateFile: f => 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/' + f });
      const db = new this.sqlMod.Database();
      try {
        db.run("CREATE TABLE ventes (id INTEGER PRIMARY KEY, date TEXT, produit TEXT, quantite INTEGER, prix_unitaire REAL, ville TEXT);");
        db.run("INSERT INTO ventes VALUES (1,'2024-01-15','Cacao',120,1500.00,'Abidjan'),(2,'2024-01-20','Café',85,1200.00,'Abidjan'),(3,'2024-02-05','Cacao',200,1520.00,'San-Pédro'),(4,'2024-02-12','Anacarde',150,800.00,'Bouaké'),(5,'2024-02-18','Café',60,1180.00,'Daloa'),(6,'2024-03-02','Cacao',180,1550.00,'Abidjan'),(7,'2024-03-10','Anacarde',220,820.00,'Korhogo'),(8,'2024-03-22','Coton',95,950.00,'Bouaké'),(9,'2024-04-05','Cacao',250,1600.00,'San-Pédro'),(10,'2024-04-14','Café',110,1250.00,'Man'),(11,'2024-05-03','Coton',130,980.00,'Korhogo'),(12,'2024-05-19','Anacarde',175,850.00,'Bouaké'),(13,'2024-06-08','Cacao',300,1650.00,'Abidjan'),(14,'2024-06-25','Café',90,1220.00,'Daloa'),(15,'2024-07-11','Coton',140,1000.00,'Korhogo'),(16,'2024-07-28','Cacao',210,1680.00,'San-Pédro'),(17,'2024-08-15','Anacarde',190,870.00,'Bouaké'),(18,'2024-09-02','Café',75,1150.00,'Man'),(19,'2024-09-20','Cacao',280,1700.00,'Abidjan'),(20,'2024-10-05','Coton',160,1020.00,'Bouaké');");
        db.run("CREATE TABLE produits (produit TEXT PRIMARY KEY, categorie TEXT, cout_unitaire REAL);");
        db.run("INSERT INTO produits VALUES ('Cacao','Culture de rente',1100),('Café','Culture de rente',900),('Anacarde','Noix',600),('Coton','Fibre',700),('Hévéa','Latex',500);");
        db.run("CREATE TABLE villes (ville TEXT PRIMARY KEY, region TEXT, habitants INTEGER);");
        db.run("INSERT INTO villes VALUES ('Abidjan','Lagunes',5600000),('San-Pédro','Bas-Sassandra',390000),('Bouaké','Vallée du Bandama',740000),('Daloa','Haut-Sassandra',320000),('Korhogo','Savanes',290000),('Man','Montagnes',190000),('Yamoussoukro','Lacs',360000);");
        const res = db.exec(code);
        if (!res.length) return { text: 'Requête exécutée (aucun résultat à afficher).', rows: [] };
        const r = res[res.length - 1];
        let html = '<table><thead><tr>' + r.columns.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr></thead><tbody>' +
          r.values.map(row => '<tr>' + row.map(v => '<td>' + (v === null ? 'NULL' : esc(v)) + '</td>').join('') + '</tr>').join('') + '</tbody></table>' +
          '<div class="muted">' + r.values.length + ' ligne(s)</div>';
        return { html, rows: r.values, text: JSON.stringify(r.values) };
      } finally { db.close(); }
    }
  };
  engines.r_ = null;

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = () => rej(new Error('Chargement impossible : ' + src));
      document.head.appendChild(s);
    });
  }
  async function exec(code) {
    if (OUTIL === 'python') return engines.python(code);
    if (OUTIL === 'r') return engines.r(code);
    return engines.sql(code);
  }

  /* ---------- Rendu ---------- */
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

    body.innerHTML =
      '<div class="pl-split">' +
      '<section class="pl-lesson">' +
        '<div class="pl-illus">' + (c.image_svg || cover(OUTIL)) + '</div>' +
        '<span class="pl-chip">Concept ' + (idx + 1) + ' / ' + lecon.concepts.length + '</span>' +
        '<h2 class="narr" data-speak="' + esc(plain(speakIntro)) + '">' + esc(c.titre) + '</h2>' +
        '<p class="pl-obj">' + esc(c.objectif) + '</p>' + paras +
        (c.code_exemple ? '<div class="pl-example"><header><span>Exemple</span><span><button id="cp-ex">Copier dans l\'éditeur</button>' + (studio ? '' : '<button id="run-ex">Exécuter</button>') + '</span></header><pre>' + esc(c.code_exemple) + '</pre></div>' : '') +
        (c.question_reflexion ? '<div class="pl-think narr" data-speak="' + esc('Question de réflexion. ' + plain(c.question_reflexion)) + '"><strong>À réfléchir :</strong> ' + md(c.question_reflexion) + '</div>' : '') +
        '<div class="pl-ex"><h3>Exercice</h3><div class="pl-ex-text" data-speak="' + esc('Exercice. ' + plain(ex.enonce)) + '">' + md(ex.enonce) + '</div>' +
          '<div class="pl-ex-actions"><button class="pl-link" id="b-hint"><i class="fas fa-lightbulb"></i> Indice</button><button class="pl-link" id="b-sol" disabled><i class="fas fa-eye"></i> Voir la solution</button></div>' +
          '<div id="hint-box"></div><div id="sol-box" class="pl-solution"></div></div>' +
      '</section>' +
      '<section class="pl-work">' +
        '<div class="pl-work-head"><span class="file"><i class="fas fa-file-code"></i> ' + FICHIERS[OUTIL] + '</span><span class="pl-actions">' +
          '<button class="pl-btn ghost" id="b-reset"><i class="fas fa-rotate-left"></i> Réinitialiser</button>' +
          (studio ? '' : '<button class="pl-btn run" id="b-run"><i class="fas fa-play"></i> Exécuter</button>') +
          '<button class="pl-btn submit" id="b-submit"><i class="fas fa-check"></i> Valider ma réponse</button></span></div>' +
        (studio ? studioHTML() : '<div class="pl-editor" id="editor"></div><div class="pl-console"><div class="pl-console-head"><span>Console</span><span id="status"></span></div><div class="pl-console-out" id="out"><span class="muted">Exécutez votre code pour voir le résultat. Raccourci : Ctrl + Entrée.</span></div></div>') +
        '<div class="pl-feedback" id="fb"></div>' +
      '</section></div>' +
      '<div class="pl-nav"><button id="b-prev"><i class="fas fa-arrow-left"></i> Précédent</button><button id="b-next" ' + (dejaOk ? '' : 'disabled') + '>Suivant <i class="fas fa-arrow-right"></i></button></div>';

    if (studio) initStudio(); else initEditor(dejaOk ? ex.solution_attendue : '', c);
    $('#b-prev').onclick = () => aller(idx - 1);
    $('#b-next').onclick = () => aller(idx + 1);
    $('#b-hint').onclick = () => { indiceVu = true; $('#hint-box').innerHTML = '<div class="pl-hint"><i class="fas fa-lightbulb"></i> ' + md(ex.indice || 'Relisez l\'explication.') + '</div>'; };
    $('#b-sol').onclick = () => { solutionVue = true; $('#sol-box').innerHTML = '<pre>' + esc(ex.solution_attendue) + '</pre>'; };
    $('#b-reset').onclick = () => { if (studio) $('#answer').value = ''; else editor.set(starter()); };
    $('#b-submit').onclick = () => soumettre(c);
    const cp = $('#cp-ex'); if (cp) cp.onclick = () => { if (studio) { $('#answer').value = c.code_exemple; } else editor.set(c.code_exemple); };
    const rx = $('#run-ex'); if (rx) rx.onclick = () => { editor.set(c.code_exemple); lancer(); };
    if (!studio) { $('#b-run').onclick = lancer; }
    majBoutons();
  }

  function starter() { return OUTIL === 'sql' ? '-- Écrivez votre requête ici\n' : (OUTIL === 'python' ? '# Écrivez votre code ici\n' : '# Écrivez votre code ici\n'); }

  function initEditor(initial) {
    const host = $('#editor');
    const val = initial || starter();
    if (window.CodeMirror) {
      const cm = window.CodeMirror(host, { value: val, mode: MODES[OUTIL], lineNumbers: true, indentUnit: 4, tabSize: 4, indentWithTabs: false, lineWrapping: true,
        extraKeys: { 'Ctrl-Enter': lancer, 'Cmd-Enter': lancer, Tab: c => c.somethingSelected() ? c.indentSelection('add') : c.replaceSelection('    ', 'end') } });
      editor = { get: () => cm.getValue(), set: v => cm.setValue(v) };
      setTimeout(() => cm.refresh(), 50);
    } else {
      const ta = document.createElement('textarea'); ta.className = 'fallback'; ta.value = val; host.appendChild(ta);
      ta.addEventListener('keydown', e => { if (e.ctrlKey && e.key === 'Enter') lancer(); });
      editor = { get: () => ta.value, set: v => { ta.value = v; } };
    }
  }

  function majBoutons() { $('#b-sol').disabled = !(essais >= 2 || solutionVue); }

  async function lancer() {
    const code = editor.get().trim();
    const out = $('#out'), st = $('#status'), btn = $('#b-run');
    if (!code) { out.innerHTML = '<span class="err">Écrivez du code avant d\'exécuter.</span>'; return null; }
    btn.disabled = true; st.textContent = 'Exécution... (le premier lancement charge le moteur ' + NOMS[OUTIL] + ')';
    const t0 = performance.now();
    try {
      const r = await exec(code);
      out.innerHTML = r.html || (r.text ? '<pre style="margin:0;color:inherit;background:none">' + esc(r.text) + '</pre>' : '<span class="muted">Le code s\'est exécuté sans rien afficher. Pensez à utiliser print().</span>');
      st.textContent = ((performance.now() - t0) / 1000).toFixed(2) + ' s';
      return r;
    } catch (e) {
      out.innerHTML = '<span class="err">' + esc(e.message || e) + '</span>';
      st.textContent = 'Erreur';
      return null;
    } finally { btn.disabled = false; }
  }

  /* ---------- Studio Tableau ---------- */
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
    return '<div class="pl-studio">' +
      '<label>Dimension<select id="s-dim"><option value="ville">Ville</option><option value="produit">Produit</option><option value="date">Mois</option></select></label>' +
      '<label>Mesure<select id="s-mes"><option value="quantite">Quantité totale</option><option value="ca">Chiffre d\'affaires</option><option value="nb">Nombre de ventes</option><option value="prix">Prix moyen (FCFA)</option></select></label>' +
      '<label>Graphique<select id="s-type"><option value="bar">Barres</option><option value="barh">Barres horizontales</option><option value="pie">Camembert</option><option value="line">Lignes</option><option value="area">Aires</option></select></label>' +
      '<label>Produit<select id="s-fp">' + opt(PRODUITS, 'Tous') + '</select></label>' +
      '<label>Ville<select id="s-fv">' + opt(VILLES, 'Toutes') + '</select></label>' +
      '<label>Période<select id="s-per"><option value="">Toute l\'année</option><option value="T1">1er trimestre</option><option value="T2">2e trimestre</option><option value="T3">3e trimestre</option></select></label>' +
      '<label>Tri<select id="s-tri"><option value="">Aucun</option><option value="desc">Décroissant</option><option value="asc">Croissant</option></select></label>' +
      '<label>Afficher<select id="s-top"><option value="0">Tout</option><option value="3">Top 3</option><option value="5">Top 5</option></select></label>' +
      '<button class="pl-btn run" id="s-go"><i class="fas fa-chart-column"></i> Générer</button></div>' +
      '<div class="pl-chartbox"><canvas id="chart"></canvas></div>' +
      '<textarea class="pl-answer" id="answer" placeholder="Décrivez ce que vous observez (une ou deux phrases)..."></textarea>';
  }
  async function initStudio() {
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
      const pal = ['#0b2a4a', '#1f5f99', '#c2a15a', '#5b9bd5', '#8aa0b5', '#a8873f', '#123a63'];
      const isLine = cfg.type === 'line' || cfg.type === 'area';
      if (engines.chart) engines.chart.destroy();
      engines.chart = new window.Chart($('#chart'), { type: cfg.type === 'barh' ? 'bar' : (cfg.type === 'area' ? 'line' : cfg.type),
        data: { labels, datasets: [{ label: nomMes, data, backgroundColor: isLine ? 'rgba(31,95,153,.18)' : pal, borderColor: '#1f5f99', borderWidth: 2, fill: cfg.type === 'area', tension: .3 }] },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: cfg.type === 'barh' ? 'y' : 'x' } });
      studioCfg = cfg; graphiqueGenere = true;
      const fb = $('#fb'); fb.className = 'pl-feedback'; fb.innerHTML = '';
    };
  }

  /* ---------- Validation ---------- */
  const norm = s => String(s).replace(/\r/g, '').split('\n').map(l => l.trim()).filter(Boolean).join('\n').replace(/\s+/g, ' ').toLowerCase();

  async function soumettre(c) {
    const ex = c.exercice, fb = $('#fb'), btn = $('#b-submit');
    const code = OUTIL === 'tableau' ? $('#answer').value.trim() : editor.get().trim();
    if (!code || /^(#|--)[^\n]*$/.test(code)) { feedback(false, 'Écrivez d\'abord votre réponse.'); return; }
    btn.disabled = true;
    let ok = false, msg = '';
    try {
      if (OUTIL === 'tableau') {
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
        const r = await lancer();
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

  /* ---------- Instructeur IA ---------- */
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

  /* ---------- Démarrage ---------- */
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
