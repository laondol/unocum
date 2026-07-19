// auto-split from schedule2.html (modularization, behavior preserved)
function memoExec(cmd){ var ed=document.getElementById('memoEditor'); ed.focus(); try{ document.execCommand(cmd, false, null); }catch(e){} }
var savedRange = null;
function saveRange(){ var ed=document.getElementById('memoEditor'); var sel=window.getSelection(); if(sel && sel.rangeCount>0){ var r=sel.getRangeAt(0); try{ if(ed.contains(r.commonAncestorContainer)) savedRange=r.cloneRange(); }catch(e){} } }
if(document.getElementById('memoEditor')){ document.getElementById('memoEditor').addEventListener('keyup', saveRange); document.getElementById('memoEditor').addEventListener('mouseup', saveRange); }
function memoForeColor(c){ var ed=document.getElementById('memoEditor'); ed.focus(); if(savedRange){ var sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(savedRange); } try{ document.execCommand('styleWithCSS', false, true); document.execCommand('foreColor', false, c); }catch(e){} }
function memoBackColor(c){ var ed=document.getElementById('memoEditor'); ed.focus(); if(savedRange){ var sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(savedRange); } try{ document.execCommand('styleWithCSS', false, true); document.execCommand('hiliteColor', false, c); }catch(e){} }
function memoLink(){
    var url = prompt('링크 주소를 입력하세요 (예: https://...)');
    if(!url) return;
    var ed=document.getElementById('memoEditor'); ed.focus();
    var sel = window.getSelection();
    if(sel && sel.toString()){ try{ document.execCommand('createLink', false, url); }catch(e){ insertMemoHtml('<a href="'+url+'" target="_blank">'+sel.toString()+'</a>'); } }
    else { insertMemoHtml('<a href="'+url+'" target="_blank">'+url+'</a>'); }
}
function insertMemoHtml(html){
    var ed = document.getElementById('memoEditor'); ed.focus();
    if(savedRange){ var sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(savedRange); }
    var ok=false; try{ ok = document.execCommand('insertHTML', false, html); }catch(e){}
    if(!ok){ ed.innerHTML += html; }
}
var numColor = '#1971ef';
function buildNumColors(){
    var cs = [['#1971ef','#fff'],['#2e7d32','#fff'],['#e53935','#fff'],['#fdd835','#222'],['#fb8c00','#fff'],['#8e24aa','#fff'],['#607d8b','#fff'],['#222222','#fff']];
    var box = document.getElementById('numColors'); if(!box) return; box.innerHTML='';
    cs.forEach(function(c){
        var b=document.createElement('button'); b.type='button';
        b.style.cssText='width:24px;height:24px;border-radius:50%;border:2px solid '+(numColor===c[0]?'#0d6efd':'#fff')+';background:'+c[0]+';cursor:pointer;';
        b.onclick=function(){ numColor=c[0]; buildNumColors(); };
        box.appendChild(b);
    });
}
function numBadgeClick(){
    if(savedRange && !savedRange.collapsed){ insertNumBadge(); }
    else { toggleNumPanel(); }
}
function toggleNumPanel(){
    var p=document.getElementById('numPanel');
    if(!p) return;
    p.style.display = (p.style.display==='none' || !p.style.display) ? 'block' : 'none';
    if(p.style.display==='block'){ if(!document.getElementById('numColors').children.length) buildNumColors(); document.getElementById('numInput').focus(); }
}
function insertNumBadge(){
    var inp=document.getElementById('numInput'); var txt=(inp.value||'').trim();
    if(!txt){ alert('번호를 입력하세요'); return; }
    var tc = (numColor==='#fdd835') ? '#222222' : '#ffffff';
    var html = '<span contenteditable="false" class="memo-num" style="display:inline-flex;align-items:center;justify-content:center;min-width:1.6em;height:1.6em;padding:0 .4em;margin:0 1px;border-radius:50%;background:'+numColor+';color:'+tc+';font-size:0.85em;font-weight:700;line-height:1;vertical-align:middle;">'+txt.replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</span>';
    insertMemoHtml(html);
    document.getElementById('numPanel').style.display='none';
    inp.value='';
}
function uploadMemoFiles(input){
    var files = input.files;
    if(!files || !files.length) return;
    var fd = new FormData();
    for(var i=0;i<files.length;i++) fd.append('file', files[i]);
    fetch('/api/bot/schedule/attachment', {method:'POST', body:fd})
    .then(function(r){return r.json();})
    .then(function(d){
        if(d.urls){
            d.urls.forEach(function(u){
                var isImg = /\.(png|jpe?g|gif|webp)$/i.test(u);
                if(isImg) insertMemoHtml('<img src="'+u+'" style="max-width:220px; max-height:220px; display:block; margin:4px 0; border:1px solid #ddd; border-radius:6px;">');
                else insertMemoHtml('<a href="'+u+'" target="_blank" style="display:inline-block; margin:4px 0; padding:4px 8px; border:1px solid #ced4da; border-radius:6px;">📎 '+u.split('/').pop()+'</a>');
            });
        } else if(d.error){ alert(d.error); }
        input.value='';
    }).catch(function(e){ alert('업로드 실패'); input.value=''; });
}
var _drawing=false, _drawCtx=null;
function openDraw(){
    var m=document.getElementById('drawModal'); m.style.display='flex';
    var c=document.getElementById('drawCanvas');
    if(!_drawCtx){ _drawCtx=c.getContext('2d'); }
    c.onpointerdown=drawStart; c.onpointermove=drawMove; window.onpointerup=drawEnd;
}
function closeDraw(){ document.getElementById('drawModal').style.display='none'; }
function drawStart(e){ _drawing=true; drawDot(e); }
function drawMove(e){ if(_drawing) drawDot(e); }
function drawEnd(){ _drawing=false; }
function drawDot(e){
    if(!_drawCtx) return;
    var c=document.getElementById('drawCanvas');
    var rect=c.getBoundingClientRect();
    var x=(e.clientX-rect.left)*(c.width/rect.width);
    var y=(e.clientY-rect.top)*(c.height/rect.height);
    _drawCtx.fillStyle=document.getElementById('drawColor').value;
    var sz=parseInt(document.getElementById('drawSize').value)||3;
    _drawCtx.beginPath(); _drawCtx.arc(x,y,sz/2,0,Math.PI*2); _drawCtx.fill();
}
function drawClear(){ if(_drawCtx){ _drawCtx.clearRect(0,0,320,220); } }
function drawSave(){
    var c=document.getElementById('drawCanvas');
    c.toBlob(function(blob){
        if(!blob){ closeDraw(); return; }
        var fd=new FormData(); fd.append('file', blob, 'draw_'+Date.now()+'.png');
        fetch('/api/bot/schedule/attachment', {method:'POST', body:fd})
        .then(function(r){return r.json();})
        .then(function(d){ if(d.urls && d.urls[0]) insertMemoHtml('<img src="'+d.urls[0]+'" style="max-width:220px; max-height:220px; display:block; margin:4px 0; border:1px solid #ddd; border-radius:6px;">'); closeDraw(); })
        .catch(function(){ closeDraw(); });
    }, 'image/png');
}
