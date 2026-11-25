(function(){
var box=document.getElementById('chat');if(!box)return;
var url=box.dataset.url,ch=box.dataset.channel,org=box.dataset.org||'',log=document.getElementById('log'),txt=document.getElementById('txt'),last=0,busy=false,first=true;
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function q(extra){return url+'?channel='+ch+(org?'&org='+org:'')+extra;}
function add(m){var d=document.createElement('div');var mine=org?m.staff:m.mine;d.className='bub'+(mine?' mine':'')+(m.staff&&!mine?' staff':'');
  d.innerHTML=(mine?'':'<div class="who">'+esc(m.author)+'</div>')+esc(m.body)+'<small>'+esc(m.at)+'</small>';log.appendChild(d);last=Math.max(last,m.id);}
function poll(){if(busy||document.hidden)return;busy=true;
  fetch(q('&after='+last),{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(j){
    if(first){log.innerHTML='';first=false;if(!j.messages.length)log.innerHTML='<div class="empty">Aucun message. Écrivez le premier !</div>';}
    if(j.messages.length){var e=log.querySelector('.empty');if(e)e.remove();var atEnd=log.scrollHeight-log.scrollTop-log.clientHeight<80;j.messages.forEach(add);if(atEnd||last===j.messages[j.messages.length-1].id)log.scrollTop=log.scrollHeight;}
  }).catch(function(){}).then(function(){busy=false;});}
function send(){var b=txt.value.trim();if(!b)return;txt.value='';
  fetch(url+(org?'?org='+org:''),{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({channel:ch,body:b,org:org})}).then(function(r){return r.json();}).then(function(j){if(j.ok){var e=log.querySelector('.empty');if(e)e.remove();add(j.message);log.scrollTop=log.scrollHeight;}});}
document.getElementById('send').onclick=send;
txt.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}});
poll();setInterval(poll,4000);
})();
