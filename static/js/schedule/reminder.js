// auto-split from schedule2.html (modularization, behavior preserved)
let shownReminderIds = new Set();
let shownMsgReminderIds = new Set();
let mutedUntil = {};
let _beepCtx = null;
let _blinkTimers = {};   // id -> interval handle

function beep(){
  try{
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if(!Ctx) return;
    if(!_beepCtx) _beepCtx = new Ctx();
    if(_beepCtx.state === 'suspended') _beepCtx.resume();
    var ctx = _beepCtx;
    var o = ctx.createOscillator();
    var g = ctx.createGain();
    o.connect(g); g.connect(ctx.destination);
    o.type='sine'; o.frequency.value=880;
    g.gain.setValueAtTime(0.0001, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.3, ctx.currentTime+0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime+0.5);
    o.start(); o.stop(ctx.currentTime+0.5);
  }catch(e){}
}
function blinkBell(on){
  var b = document.getElementById('bellBtn');
  if(!b) return;
  if(on) b.classList.add('bell-blink'); else b.classList.remove('bell-blink');
}
function startBlink(el){
  if(!el) return;
  var on = false;
  return setInterval(function(){
    on = !on;
    el.style.background = on ? '#dc3545' : '#7a1018';
  }, 600);
}
function fireNotification(r){
  var now = Date.now();
  if(mutedUntil[r.id] && now < mutedUntil[r.id]) return;
  beep();
  try{ if(navigator.vibrate) navigator.vibrate([200,100,200]); }catch(e){}
  if('Notification' in window && Notification.permission==='granted'){
    try{ new Notification(r.title, {body:(r.event_date||'')+' 알림'}); }catch(e){}
  }
  showToast(r);
}
function showToast(r){
  var old = document.getElementById('noti-toast-'+r.id);
  if(old){
    if(_blinkTimers[r.id]) clearInterval(_blinkTimers[r.id]);
    old.parentNode.removeChild(old);
  }
  var t=document.createElement('div');
  t.id='noti-toast-'+r.id;
  t.className='toast align-items-center text-white border-0 show';
  t.style.cssText='position:fixed;top:60px;right:10px;z-index:90;min-width:260px;background:#dc3545;';
  t.innerHTML='<div class="toast-body"><strong>🔔 '+r.title+'</strong><div class="small text-white-50">'+(r.event_date||'')+'</div>'+
    '<div class="mt-2 d-flex gap-2">'+
    '<button class="btn btn-sm btn-light py-0" onclick="dismissReminder('+r.id+')">확인 / 소리 끄기</button>'+
    '<button class="btn btn-sm btn-outline-light py-0" onclick="snoozeReminder('+r.id+')">2분 뒤 다시</button>'+
    '</div></div>';
  document.body.appendChild(t);
  _blinkTimers[r.id] = startBlink(t);
  blinkBell(true);
}
function fireMsgNotification(r){
  beep();
  try{ if(navigator.vibrate) navigator.vibrate([200,100,200]); }catch(e){}
  if('Notification' in window && Notification.permission==='granted'){
    try{ new Notification('편지: '+r.sender, {body:r.subject}); }catch(e){}
  }
  showMsgToast(r);
}
function showMsgToast(r){
  var old = document.getElementById('msg-noti-toast-'+r.id);
  if(old){
    if(_blinkTimers['msg'+r.id]) clearInterval(_blinkTimers['msg'+r.id]);
    old.parentNode.removeChild(old);
  }
  var t=document.createElement('div');
  t.id='msg-noti-toast-'+r.id;
  t.className='toast align-items-center text-white border-0 show';
  t.style.cssText='position:fixed;top:60px;right:10px;z-index:90;min-width:260px;background:#0d6efd;';
  t.innerHTML='<div class="toast-body"><strong>편지 ✉️ '+r.sender+'</strong><div class="small text-white-50">'+r.subject+'</div>'+
    '<div class="mt-2 d-flex gap-2">'+
    '<button class="btn btn-sm btn-light py-0" onclick="dismissMsgReminder('+r.id+')">확인</button>'+
    '<button class="btn btn-sm btn-outline-light py-0" onclick="snoozeMsgReminder('+r.id+')">2분 뒤 다시</button>'+
    '</div></div>';
  document.body.appendChild(t);
  _blinkTimers['msg'+r.id] = startBlink(t);
  blinkBell(true);
}
function dismissMsgReminder(id){
  var t=document.getElementById('msg-noti-toast-'+id);
  if(t){ if(_blinkTimers['msg'+id]) clearInterval(_blinkTimers['msg'+id]); t.parentNode.removeChild(t); }
  mutedUntil['msg'+id] = 0;
  blinkBell(false);
  markMsgReminderSeen([id]);
}
function snoozeMsgReminder(id){
  var t=document.getElementById('msg-noti-toast-'+id);
  if(t){ if(_blinkTimers['msg'+id]) clearInterval(_blinkTimers['msg'+id]); t.parentNode.removeChild(t); }
  mutedUntil['msg'+id] = Date.now() + 2*60*1000;
  blinkBell(false);
}
function markMsgReminderSeen(ids){
  if(!ids || !ids.length) return;
  fetch('/api/bot/messages/reminder/seen', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ids:ids})})
    .then(function(){ checkMessageReminders(); })
    .catch(function(){});
}
function checkMessageReminders(){
  fetch('/api/bot/messages/unread')
    .then(function(r){return r.json();})
    .then(function(d){
      var list=d.messages||[];
      if(list.length) blinkBell(true);
      list.forEach(function(r){
        if(!shownMsgReminderIds.has(r.id)){ shownMsgReminderIds.add(r.id); fireMsgNotification(r); }
        else { fireMsgNotification(r); }
      });
    })
    .catch(function(){});
}
function dismissReminder(id){
  var t=document.getElementById('noti-toast-'+id);
  if(t){ if(_blinkTimers[id]) clearInterval(_blinkTimers[id]); t.parentNode.removeChild(t); }
  mutedUntil[id] = 0;
  blinkBell(false);
  markReminderSeen([id]);
}
function snoozeReminder(id){
  var t=document.getElementById('noti-toast-'+id);
  if(t){ if(_blinkTimers[id]) clearInterval(_blinkTimers[id]); t.parentNode.removeChild(t); }
  mutedUntil[id] = Date.now() + 2*60*1000; // 2분간 묵음 후 재알림
  blinkBell(false);
}
function markReminderSeen(ids){
  if(!ids || !ids.length) return;
  fetch('/api/bot/schedule/reminder/seen', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ids:ids})})
    .then(function(){ checkReminders(); })
    .catch(function(){});
}
function checkReminders(){
  fetch('/api/bot/schedule/reminders')
    .then(function(r){return r.json();})
    .then(function(d){
      var list=d.reminders||[];
      if(list.length) blinkBell(true); else blinkBell(false);
      list.forEach(function(r){
        if(!shownReminderIds.has(r.id)){ shownReminderIds.add(r.id); fireNotification(r); }
        else { fireNotification(r); }
      });
      renderBellPanel(list);
    })
    .catch(function(){});
}
function renderBellPanel(list){
  list = list || [];
  var badge=document.getElementById('bellBadge');
  if(list.length>0){ badge.style.display=''; badge.textContent=list.length; }
  else { badge.style.display='none'; }
  var p=document.getElementById('bellPanel');
  if(!p) return;
  if(!list.length){ p.innerHTML='<div class="small text-muted">알림 없음</div>'; return; }
  var h='<div class="small fw-bold mb-2">알림 ('+list.length+')</div>';
  list.forEach(function(r){
    h+='<div class="border-bottom py-1 small"><div><strong>🔔 '+r.title+'</strong></div><div class="text-muted">'+r.event_date+'</div><button class="btn btn-sm btn-outline-secondary py-0 mt-1" onclick="dismissReminder('+r.id+')">확인</button> <button class="btn btn-sm btn-outline-secondary py-0 mt-1" onclick="snoozeReminder('+r.id+')">2분 뒤</button></div>';
  });
  p.innerHTML=h;
}
function toggleBell(){
  if('Notification' in window && Notification.permission==='default'){ Notification.requestPermission(); }
  var p=document.getElementById('bellPanel');
  if(p.style.display==='none' || !p.style.display){ p.style.display='block'; checkReminders(); }
  else { p.style.display='none'; }
}
function startReminderPoll(){
  if('Notification' in window && Notification.permission === 'default'){
    Notification.requestPermission().catch(function(){});
  }
  checkReminders();
  checkMessageReminders();
  setInterval(checkReminders, 20000);
  setInterval(checkMessageReminders, 20000);
}
function _unlockAudio(){ try{ if(!_beepCtx) _beepCtx = new (window.AudioContext||window.webkitAudioContext)(); if(_beepCtx.state==='suspended') _beepCtx.resume(); }catch(e){} window.removeEventListener('click',_unlockAudio); window.removeEventListener('touchstart',_unlockAudio); }
window.addEventListener('click', _unlockAudio);
window.addEventListener('touchstart', _unlockAudio);
startReminderPoll();
// WebPush registration (appended)
function _pushKeyB64(buf){
  if(!buf) return '';
  return btoa(String.fromCharCode.apply(null, new Uint8Array(buf)));
}

function registerWebPush(){
  if(!('serviceWorker' in navigator) || !('PushManager' in window)){
    console.log('[push] not supported'); return;
  }
  var pubKey = 'BMfhOnZmATulfkJYvgkhLxMgNCLaq_9F6PURGlbmCdDNEJ1s9YcnliGfppTI4iKlym4zNbkqtFdPoFBuHlMnMRs';
  navigator.serviceWorker.register('/sw.js', {scope:'/'}).then(function(reg){
    return reg.pushManager.getSubscription().then(function(sub){
      if(sub){ return sub; }
      return Notification.requestPermission().then(function(perm){
        if(perm !== 'granted') return null;
        return reg.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:urlBase64ToUint8Array(pubKey)});
      });
    });
  }).then(function(sub){
    if(!sub){ console.log('[push] no subscription'); return; }
    var payload = JSON.stringify({
      endpoint: sub.endpoint,
      p256dh: _pushKeyB64(sub.getKey('p256dh')),
      auth: _pushKeyB64(sub.getKey('auth'))
    });
    fetch('/api/bot/schedule/push/subscribe', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: payload
    }).then(function(){ console.log('[push] subscribed'); }).catch(function(e){ console.error('[push] subscribe failed', e); });
  }).catch(function(e){ console.error('[push] sw register failed', e); });
}

function urlBase64ToUint8Array(base64String){
  var padding = '='.repeat((4 - base64String.length % 4) % 4);
  var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  var rawData = atob(base64);
  var outputArray = new Uint8Array(rawData.length);
  for(var i=0;i<rawData.length;++i){ outputArray[i]=rawData.charCodeAt(i); }
  return outputArray;
}

window.addEventListener('load', function(){ setTimeout(registerWebPush, 1500); });
