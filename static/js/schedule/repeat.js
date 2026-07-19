// auto-split from schedule2.html (modularization, behavior preserved)
var repeatExceptions = [];
function setRepeatOptionsVisible(v) {
    document.getElementById('repeatOptions').style.display = v ? 'flex' : 'none';
    repeatOn = v;
    if (!v) { repeatExceptions = []; renderExceptions(); }
    var b = document.getElementById('btnRepeat');
    b.classList.toggle('btn-primary', v);
    b.classList.toggle('btn-outline-secondary', !v);
    updateOccCount();
}
function toggleRepeat() {
    repeatOn = !repeatOn;
    setRepeatOptionsVisible(repeatOn);
}
function closeRepeatOptions() {
    document.getElementById('repeatOptions').style.display = 'none';
    var b = document.getElementById('btnRepeat');
    b.classList.add('btn-primary');
    b.classList.remove('btn-outline-secondary');
    updateOccCount();
}
function computeOccurrences() {
    if (!repeatOn) return null;
    var startDate = document.getElementById('addDate').value;
    var endDate = document.getElementById('addEndDate').value;
    if (!startDate || !endDate) return null;
    if (endDate < startDate) return -1; // 무한반복(시작일 이후)
    var rt = '';
    var rbs = document.getElementsByName('repeatType');
    for (var i=0;i<rbs.length;i++){ if(rbs[i].checked){ rt = rbs[i].value; break; } }
    if (!rt) return null;
    var interval = parseInt(document.getElementById('addRepeatInterval').value) || 1;
    var wmask = getWeekdayMask();
    var wom = parseInt(document.getElementById('addRepeatWeekOfMonth').value) || 0;
    var moy = parseInt(document.getElementById('addRepeatMonthOfYear').value) || 0;
    var sd = startDate.split('-'); var ed = endDate.split('-');
    var s = new Date(parseInt(sd[0]), parseInt(sd[1])-1, parseInt(sd[2]));
    var e = new Date(parseInt(ed[0]), parseInt(ed[1])-1, parseInt(ed[2]));
    function nthWeekday(y,m,wd,n){ var d=1; while(new Date(y,m,d).getDay()!==wd) d++; d+=(n-1)*7; var last=new Date(y,m+1,0).getDate(); return d>last?-1:d; }
    var cur = new Date(s.getTime()); cur.setDate(cur.getDate()+1);
    var count=1, guard=0;
    while (cur <= e && count < 120 && guard < 600000) {
        guard++;
        var emit=false; var nxt=new Date(cur.getTime()); nxt.setDate(nxt.getDate()+1);
        if (wmask) {
            var wd = cur.getDay();
            if (wmask & (1<<wd)) {
                var ok = true;
                if (moy && cur.getMonth()+1 !== moy) ok=false;
                else if (wom && cur.getDate() !== nthWeekday(cur.getFullYear(), cur.getMonth(), wd, wom)) ok=false;
                if (ok) emit=true;
            }
        } else if (rt==='daily') {
            if (Math.floor((cur - s)/86400000) % interval === 0) emit=true;
        } else if (rt==='weekly') {
            if (cur.getDay()===s.getDay() && Math.floor((cur-s)/604800000)%interval===0) emit=true;
        } else if (rt==='monthly') {
            if (cur.getDate()===s.getDate()) {
                var months=(cur.getFullYear()-s.getFullYear())*12+(cur.getMonth()-s.getMonth());
                if (months%interval===0) emit=true;
                nxt = new Date(cur.getFullYear(), cur.getMonth()+interval, 1);
            }
        } else if (rt==='yearly') {
            if (cur.getMonth()===s.getMonth() && cur.getDate()===s.getDate()) {
                if ((cur.getFullYear()-s.getFullYear())%interval===0) emit=true;
                nxt = new Date(cur.getFullYear()+interval, cur.getMonth(), 1);
            }
        }
        if (emit) count++;
        cur = nxt;
    }
    return count;
}
function updateOccCount() {
    var el = document.getElementById('occCount');
    if (!el) return;
    var warn = document.getElementById('occWarn');
    if (!repeatOn) { el.textContent='–'; if(warn) warn.style.display='none'; return; }
    var c = computeOccurrences();
    if (c === null) { el.textContent='–'; if(warn) warn.style.display='none'; return; }
    if (c === -1) { el.textContent='무한'; if(warn) warn.style.display='none'; return; }
    if (c >= 120) { el.textContent = c + ' (120 제한)'; if(warn) warn.style.display=''; }
    else { el.textContent = c; if(warn) warn.style.display='none'; }
}
function addExceptionDate() {
    var d = document.getElementById('addExceptDate').value;
    if (!d) return;
    if (repeatExceptions.indexOf(d) < 0) repeatExceptions.push(d);
    renderExceptions();
    updateOccCount();
}
function removeException(idx) { repeatExceptions.splice(idx,1); renderExceptions(); updateOccCount(); }
function renderExceptions() {
    var box = document.getElementById('exceptList');
    if (!box) return;
    if (!repeatExceptions.length) { box.innerHTML='<span class="text-muted small">없음</span>'; return; }
    box.innerHTML = repeatExceptions.map(function(d,i){
        return '<span class="chip chip-mail" style="cursor:pointer;" onclick="removeException('+i+')">'+d+' ✕</span>';
    }).join(' ');
}
function getWeekdayMask() {
    var mask = 0;
    document.querySelectorAll('.wd-cb').forEach(function(cb){ if (cb.checked) mask |= (1 << parseInt(cb.value)); });
    return mask;
}
function updateRepeatMode() {
    var wd = getWeekdayMask();
    var rbs = document.getElementsByName('repeatType');
    for (var i=0;i<rbs.length;i++) {
        var v = rbs[i].value;
        // 요일 반복은 매주/매월 만 허용 (매일/매년 비활성)
        rbs[i].disabled = !!wd && (v === 'daily' || v === 'yearly');
    }
    if (wd) {
        var sel = false;
        for (var i=0;i<rbs.length;i++) { if (rbs[i].checked && !rbs[i].disabled) { sel = true; break; } }
        if (!sel) {
            for (var i=0;i<rbs.length;i++) { if (rbs[i].value === 'weekly') { rbs[i].checked = true; break; } }
        }
    }
    updateOccCount();
}
