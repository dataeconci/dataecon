(function(){
var PAL=['#1f5f99','#c2a15a','#0b2a4a','#5b9bd5','#8aa0b5','#a8873f','#2f8f6b','#b03a2e'];
var app=document.getElementById('app'),grid=document.getElementById('grid'),fbox=document.getElementById('filters');
var cols=[],rows=[],cfg=CONFIG,state={filters:{}};
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function fmt(v){if(v==null||isNaN(v))return '-';var a=Math.abs(v);return Number(v).toLocaleString('fr-FR',{maximumFractionDigits:a>=100?0:2});}
function colType(n){for(var i=0;i<cols.length;i++)if(cols[i].name===n)return cols[i].type;return 'text';}
function filtered(){return rows.filter(function(r){for(var k in state.filters){var f=state.filters[k];if(f!==''&&String(r[k])!==f)return false;}return true;});}
function agg(rs,a,field){
  if(a==='count')return rs.length;
  if(a==='distinct'){var s={};rs.forEach(function(r){s[r[field]]=1;});return Object.keys(s).length;}
  var v=rs.map(function(r){return Number(r[field]);}).filter(function(x){return !isNaN(x)&&x!==null;});
  if(!v.length)return null;
  if(a==='sum')return v.reduce(function(x,y){return x+y;},0);
  if(a==='avg')return v.reduce(function(x,y){return x+y;},0)/v.length;
  if(a==='min')return Math.min.apply(null,v);return Math.max.apply(null,v);}
function groups(w){var rs=filtered(),m={},order=[];
  rs.forEach(function(r){var k=r[w.group]==null||r[w.group]===''?'(vide)':String(r[w.group]);if(!(k in m)){m[k]=[];order.push(k);}m[k].push(r);});
  var out=order.map(function(k){return [k,agg(m[k],w.agg,w.field)];});
  if(colType(w.group)==='date'||/^(mois|annee|année|date)/i.test(w.group))out.sort(function(a,b){return a[0]<b[0]?-1:1;});else out.sort(function(a,b){return (b[1]||0)-(a[1]||0);});
  return out.slice(0,w.type==='pie'?8:20);}
function svgBar(d){var W=560,H=230,L=46,B=44,mx=Math.max.apply(null,d.map(function(x){return x[1]||0;}).concat([1])),n=d.length,bw=(W-L-10)/n,s='<svg viewBox="0 0 '+W+' '+H+'">';
  for(var t=0;t<=4;t++){var y=H-B-(H-B-14)*t/4;s+='<line x1="'+L+'" x2="'+W+'" y1="'+y+'" y2="'+y+'" stroke="#e3e9ef"/><text x="'+(L-5)+'" y="'+(y+3)+'" text-anchor="end" font-size="9" fill="#52606d">'+fmt(mx*t/4)+'</text>';}
  d.forEach(function(x,i){var h=(H-B-14)*(x[1]||0)/mx,bx=L+i*bw+bw*.15;s+='<rect x="'+bx+'" y="'+(H-B-h)+'" width="'+bw*.7+'" height="'+h+'" rx="2" fill="'+PAL[0]+'"><title>'+esc(x[0])+' : '+fmt(x[1])+'</title></rect>';
    var lab=String(x[0]);if(lab.length>11)lab=lab.slice(0,10)+'…';s+='<text x="'+(bx+bw*.35)+'" y="'+(H-B+13)+'" text-anchor="end" font-size="9" fill="#52606d" transform="rotate(-28 '+(bx+bw*.35)+' '+(H-B+13)+')">'+esc(lab)+'</text>';});
  return s+'</svg>';}
function svgLine(d){var W=560,H=230,L=46,B=36,mx=Math.max.apply(null,d.map(function(x){return x[1]||0;}).concat([1])),mn=Math.min(0,Math.min.apply(null,d.map(function(x){return x[1]||0;}))),n=d.length,s='<svg viewBox="0 0 '+W+' '+H+'">',pts=[];
  for(var t=0;t<=4;t++){var y=H-B-(H-B-14)*t/4;s+='<line x1="'+L+'" x2="'+W+'" y1="'+y+'" y2="'+y+'" stroke="#e3e9ef"/><text x="'+(L-5)+'" y="'+(y+3)+'" text-anchor="end" font-size="9" fill="#52606d">'+fmt(mn+(mx-mn)*t/4)+'</text>';}
  d.forEach(function(x,i){var px=L+(n>1?i*(W-L-14)/(n-1):(W-L)/2),py=H-B-(H-B-14)*((x[1]||0)-mn)/((mx-mn)||1);pts.push([px,py,x]);});
  s+='<polyline fill="none" stroke="'+PAL[0]+'" stroke-width="2.5" points="'+pts.map(function(p){return p[0]+','+p[1];}).join(' ')+'"/>';
  pts.forEach(function(p,i){s+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="3.5" fill="'+PAL[1]+'"><title>'+esc(p[2][0])+' : '+fmt(p[2][1])+'</title></circle>';if(n<=14||i%Math.ceil(n/12)===0)s+='<text x="'+p[0]+'" y="'+(H-B+14)+'" text-anchor="middle" font-size="9" fill="#52606d">'+esc(String(p[2][0]).slice(0,10))+'</text>';});
  return s+'</svg>';}
function svgPie(d){var tot=d.reduce(function(a,x){return a+(x[1]||0);},0)||1,cx=95,cy=95,r=85,a0=-Math.PI/2,s='<svg viewBox="0 0 440 190"><g>';
  d.forEach(function(x,i){var v=x[1]||0,a1=a0+2*Math.PI*v/tot;if(d.length===1){s+='<circle cx="'+cx+'" cy="'+cy+'" r="'+r+'" fill="'+PAL[0]+'"/>';}else{var l=a1-a0>Math.PI?1:0;
    s+='<path d="M'+cx+','+cy+' L'+(cx+r*Math.cos(a0))+','+(cy+r*Math.sin(a0))+' A'+r+','+r+' 0 '+l+' 1 '+(cx+r*Math.cos(a1))+','+(cy+r*Math.sin(a1))+' Z" fill="'+PAL[i%PAL.length]+'" stroke="#fff"><title>'+esc(x[0])+' : '+fmt(v)+'</title></path>';}a0=a1;});
  s+='</g>';d.forEach(function(x,i){s+='<rect x="205" y="'+(14+i*21)+'" width="11" height="11" fill="'+PAL[i%PAL.length]+'"/><text x="222" y="'+(24+i*21)+'" font-size="11" fill="#0b2a4a">'+esc(String(x[0]).slice(0,22))+' ('+Math.round(100*(x[1]||0)/tot)+' %)</text>';});
  return s+'</svg>';}
function widgetHTML(w){
  if(w.type==='kpi')return '<div class="big">'+fmt(agg(filtered(),w.agg,w.field))+'</div>';
  if(w.type==='table'){var rs=filtered().slice(0,50),cs=cols.slice(0,8);return '<div class="ent-scroll" style="max-height:300px"><table class="ent-table"><tr>'+cs.map(function(c){return '<th>'+esc(c.name)+'</th>';}).join('')+'</tr>'+rs.map(function(r){return '<tr>'+cs.map(function(c){return '<td>'+esc(r[c.name]==null?'':r[c.name])+'</td>';}).join('')+'</tr>';}).join('')+'</table></div>';}
  if(!w.group)return '<div class="empty">Choisissez un champ de regroupement.</div>';
  var d=groups(w);if(!d.length)return '<div class="empty">Aucune donnée.</div>';
  return w.type==='bar'?svgBar(d):w.type==='line'?svgLine(d):svgPie(d);}
function render(){
  document.getElementById('d-sub').textContent=rows.length+' lignes dans la source ; '+filtered().length+' après filtres';
  grid.innerHTML=cfg.widgets.map(function(w,i){return '<div class="wd w'+w.w+'"><h3>'+esc(w.title||'')+'</h3>'+widgetHTML(w)+'<div class="wtools"><button data-up="'+i+'">&uarr;</button><button data-dn="'+i+'">&darr;</button><button data-rm="'+i+'">Supprimer</button></div></div>';}).join('')||'<div class="empty ent-card" style="grid-column:1/-1">Tableau de bord vide. Cliquez sur « Modifier » pour ajouter des éléments.</div>';}
function drawFilters(){
  if(!cfg.filters.length){fbox.style.display='none';return;}fbox.style.display='flex';
  fbox.innerHTML=cfg.filters.map(function(f){var vals={};rows.forEach(function(r){if(r[f]!=null&&r[f]!=='')vals[r[f]]=1;});var o=Object.keys(vals).sort();
    return '<div><label>'+esc(f)+'</label><select data-f="'+esc(f)+'"><option value="">Tous</option>'+o.slice(0,200).map(function(v){return '<option'+(state.filters[f]===v?' selected':'')+'>'+esc(v)+'</option>';}).join('')+'</select></div>';}).join('')+'<button class="ent-btn ghost sm" id="f-reset" style="align-self:end">Réinitialiser</button>';
  fbox.querySelectorAll('select').forEach(function(s){s.onchange=function(){state.filters[s.dataset.f]=s.value;render();};});
  document.getElementById('f-reset').onclick=function(){state.filters={};drawFilters();render();};}
function fillEditor(){
  var nums=cols.filter(function(c){return c.type==='number';}),cats=cols.filter(function(c){return c.type!=='number';});
  document.getElementById('a-field').innerHTML='<option value="">(aucun)</option>'+nums.map(function(c){return '<option>'+esc(c.name)+'</option>';}).join('');
  document.getElementById('a-group').innerHTML='<option value="">(aucun)</option>'+cols.map(function(c){return '<option>'+esc(c.name)+'</option>';}).join('');
  var fs=document.getElementById('e-filters');fs.innerHTML=cats.map(function(c){return '<option'+(cfg.filters.indexOf(c.name)>=0?' selected':'')+'>'+esc(c.name)+'</option>';}).join('');
  fs.onchange=function(){cfg.filters=[].filter.call(fs.options,function(o){return o.selected;}).map(function(o){return o.value;});state.filters={};drawFilters();render();};}
document.getElementById('b-edit').onclick=function(){app.classList.toggle('editing');};
document.getElementById('a-add').onclick=function(){
  var t=document.getElementById('a-type').value,a=document.getElementById('a-agg').value,f=document.getElementById('a-field').value,g=document.getElementById('a-group').value,msg=document.getElementById('a-msg');
  if((a!=='count'&&a!=='distinct')&&!f&&t!=='table'){msg.style.color='#b03a2e';msg.textContent='Choisissez un champ numérique pour ce calcul.';return;}
  if(a==='distinct'&&!f){f=g;}
  var title=document.getElementById('a-title').value||(t==='kpi'?'Indicateur':t==='table'?'Données':(g?'Par '+g:'Graphique'));
  cfg.widgets.push({type:t,title:title,agg:a,field:f,group:g,w:+document.getElementById('a-w').value});msg.style.color='#176a3d';msg.textContent='';render();};
grid.addEventListener('click',function(e){var t=e.target,w=cfg.widgets;
  if(t.dataset.rm!==undefined)w.splice(+t.dataset.rm,1);
  else if(t.dataset.up!==undefined&&+t.dataset.up>0){var i=+t.dataset.up;w.splice(i-1,0,w.splice(i,1)[0]);}
  else if(t.dataset.dn!==undefined&&+t.dataset.dn<w.length-1){var j=+t.dataset.dn;w.splice(j+1,0,w.splice(j,1)[0]);}else return;render();});
document.getElementById('a-save').onclick=function(){var msg=document.getElementById('a-msg');
  fetch(SAVE_URL,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:document.getElementById('e-title').value,widgets:cfg.widgets,filters:cfg.filters})})
  .then(function(r){return r.json();}).then(function(j){if(j.ok){msg.style.color='#176a3d';msg.textContent='Enregistré.';document.getElementById('d-title').textContent=document.getElementById('e-title').value;}});};
fetch(DATA_URL,{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(j){cols=j.columns;rows=j.rows;fillEditor();drawFilters();render();window.__dash={render:render,cfg:cfg};});
})();
