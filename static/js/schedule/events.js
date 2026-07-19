// auto-split from schedule2.html (modularization, behavior preserved)
function editEvent(id) {
    var sid = String(id);
    var bid = sid.indexOf('_') >= 0 ? sid.split('_')[0] : sid;
    var s = schedules.find(function(x){ return String(x.id) === bid; });
    if (!s) return;
    switchTab('add');
    document.querySelector('#tabAdd h6').textContent = '일정 수정';
    document.getElementById('editId').value = bid;
    document.getElementById('addTitle').value = s.title || '';
    if (s.event_date) {
        var parts = s.event_date.split(' ');
        document.getElementById('addDate').value = parts[0];
        document.getElementById('addStart').value = parts.length>1 ? parts[1].substring(0,5) : '';
        if (s.end_date) {
            var ep = s.end_date.split(' ');
            document.getElementById('addEndDate').value = ep[0];
            document.getElementById('addEnd').value = ep[1].substring(0,5);
        } else {
            document.getElementById('addEndDate').value = parts[0];
        }
    }
    document.getElementById('addLoc').value = s.location || '';
    var memoVal = '';
    if (s.memo && s.memo.trim()) memoVal = s.memo;
    else if (s.description && s.description.trim()) memoVal = s.description;
    else if (s.content) { try { var cc = JSON.parse(s.content); if (cc && cc.compact) memoVal = cc.compact; } catch(e){} }
    document.getElementById('memoEditor').innerHTML = memoVal.replace(/\[숙소:[^\]]+\]/g,'').trim();
    var am = s.memo ? s.memo.match(/\[숙소:([^\]]+)\]/) : null;
    if (am) {
        document.getElementById('addAccommodation').value = am[1];
    } else {
        document.getElementById('addAccommodation').value = '';
    }
    if (am || (document.getElementById('addDate').value !== document.getElementById('addEndDate').value)) {
        document.getElementById('accommodationSection').style.display = '';
    } else {
        document.getElementById('accommodationSection').style.display = 'none';
    }
    document.getElementById('addAllDay').checked = s.is_allday || false;
    repeatOn = s.is_recurring || false;
    setRepeatOptionsVisible(repeatOn);
    if (s.is_recurring && s.repeat_type) {
        var rbs = document.getElementsByName('repeatType');
        for (var i=0;i<rbs.length;i++) { rbs[i].checked = rbs[i].value === s.repeat_type; }
    }
    document.getElementById('addRepeatInterval').value = s.repeat_interval || 1;
    var wmask = s.repeat_weekdays || 0;
    document.querySelectorAll('.wd-cb').forEach(function(cb){ cb.checked = !!(wmask & (1 << parseInt(cb.value))); });
    document.getElementById('addRepeatWeekOfMonth').value = s.repeat_week_of_month || 0;
    document.getElementById('addRepeatMonthOfYear').value = s.repeat_month_of_year || 0;
    document.getElementById('addReminder').value = s.reminder_minutes || 0;
    try { repeatExceptions = (s.exceptions ? JSON.parse(s.exceptions) : []) || []; } catch(e) { repeatExceptions = []; }
    if (document.getElementById('exceptList')) renderExceptions();
    updateRepeatMode();
    if (s.repeat_infinite) {
        var _ed = new Date(document.getElementById('addDate').value + 'T00:00');
        _ed.setDate(_ed.getDate() - 1);
        document.getElementById('addEndDate').value = _ed.toISOString().slice(0,10);
    }
    renderAddCal();
    toggleAllDay();
    document.getElementById('saveBtn').textContent = '수정';
}

function toggleAccommodation() {
    var sd = document.getElementById('addDate').value;
    var ed = document.getElementById('addEndDate').value;
    var val = document.getElementById('addAccommodation').value.trim();
    if (sd && ed && sd !== ed) {
        document.getElementById('accommodationSection').style.display = '';
    } else if (!val) {
        document.getElementById('accommodationSection').style.display = 'none';
    }
}

function toggleAllDay() {
    var checked = document.getElementById('addAllDay').checked;
    document.getElementById('addStart').disabled = checked;
    document.getElementById('addEnd').disabled = checked;
    if (checked) {
        document.getElementById('addStart').value = '';
        document.getElementById('addEnd').value = '';
    }
}
function showDetail(id){
    var s=null, baseId=String(id).split('_')[0];
    for(var i=0;i<schedules.length;i++){ if(String(schedules[i].id)===String(id)){ s=schedules[i]; break; } }
    if(!s) return;
    document.getElementById('detailTitle').textContent = s.title || '(제목없음)';
    var meta=[];
    if(s.event_date) meta.push('🕐 '+s.event_date.replace('T',' ').substring(0,16));
    if(s.location) meta.push('📍 '+s.location);
    if(s.memo && s.memo.indexOf('[숙소:')>=0){ var m=s.memo.match(/\[숙소:([^\]]+)\]/); if(m) meta.push('🏠 '+m[1]); }
    document.getElementById('detailMeta').innerHTML = meta.join('<br>');
    var mv = s.memo ? s.memo.replace(/\[숙소:[^\]]+\]/g,'') : '';
    document.getElementById('detailMemo').innerHTML = mv || '<span class="text-muted">메모 없음</span>';
    document.getElementById('detailEditBtn').onclick = function(){ closeDetail(); editEvent(baseId); };
    document.getElementById('detailModal').style.display='flex';
}
function closeDetail(){ document.getElementById('detailModal').style.display='none'; }
var saving = false;
function saveEvent() {
    if (saving) return;
    var id = document.getElementById('editId').value;
    var title = document.getElementById('addTitle').value.trim();
    var date = document.getElementById('addDate').value;
    var endDate = document.getElementById('addEndDate').value;
    var start = document.getElementById('addStart').value;
    var end = document.getElementById('addEnd').value;
    var loc = document.getElementById('addLoc').value.trim();
    var memo = document.getElementById('memoEditor').innerHTML.trim();
    var accommodation = document.getElementById('addAccommodation').value.trim();
    var isAllDay = document.getElementById('addAllDay').checked;
    var isRecurring = repeatOn;
    var repeatType = '';
    var repeatInterval = parseInt(document.getElementById('addRepeatInterval').value) || 1;
    var repeatInfinite = !!(isRecurring && (!endDate || endDate < date));
    var repeatWeekdays = getWeekdayMask();
    var repeatWeekOfMonth = parseInt(document.getElementById('addRepeatWeekOfMonth').value) || 0;
    var repeatMonthOfYear = parseInt(document.getElementById('addRepeatMonthOfYear').value) || 0;
    if (isRecurring) {
        var rbs = document.getElementsByName('repeatType');
        for (var i=0;i<rbs.length;i++) { if(rbs[i].checked) { repeatType = rbs[i].value; break; } }
    }
    if (isRecurring && repeatWeekdays && repeatType !== 'weekly' && repeatType !== 'monthly') {
        return alert('요일 반복은 매주 또는 매월 중 하나를 선택하세요.');
    }
    if (!title || !date) return alert('제목과 날짜를 입력하세요.');
    var evt = isAllDay ? date+'T00:00' : (start ? date+'T'+start : date+'T09:00');
    if (accommodation) memo = (memo ? memo : '')+'<br>[숙소:'+accommodation+']';
    var cbs = document.querySelectorAll('.friend-cb:checked');
    var invited = [];
    cbs.forEach(function(cb){ invited.push(parseInt(cb.value)); });
    var data = {title, event_date: evt, location: loc, memo, invited: JSON.stringify(invited), is_allday: isAllDay, is_recurring: isRecurring, repeat_type: repeatType, repeat_interval: repeatInterval, repeat_infinite: repeatInfinite, repeat_weekdays: repeatWeekdays, repeat_week_of_month: repeatWeekOfMonth, repeat_month_of_year: repeatMonthOfYear, repeat_exceptions: JSON.stringify(repeatExceptions), reminder_minutes: parseInt(document.getElementById('addReminder').value) || 0};
    if (end && !isAllDay) data.end_date = (endDate && endDate !== date ? endDate : date)+'T'+end;
    if (isAllDay) data.end_date = endDate ? endDate+'T23:59' : date+'T23:59';
    if (repeatInfinite) data.end_date = '';
    if (id) data.id = parseInt(id);
    var url = id ? '/api/bot/schedule/update' : '/api/bot/schedule';
    saving = true;
    var btn = document.getElementById('saveBtn');
    if (btn) { btn.disabled = true; btn.textContent = '저장 중...'; }
    fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)})
    .then(function(r){return r.json()}).then(function(d){
        if (d.success) {
            document.getElementById('editId').value = '';
            ['addTitle','addLoc','memoEditor','addStart','addEnd','addEndDate','addAccommodation'].forEach(function(x){
                var el = document.getElementById(x);
                if (el) el.value = '';
            });
            document.getElementById('addAllDay').checked = false;
            repeatOn = false;
            document.getElementById('addRepeatInterval').value = 1;
            setRepeatOptionsVisible(false);
            repeatExceptions = [];
            if (document.getElementById('exceptList')) renderExceptions();
            document.getElementById('addStart').disabled = false;
            document.getElementById('addEnd').disabled = false;
            alert(id?'수정 완료':'등록 완료');
            loadEvents().then(() => switchTab('view'));
        } else {
            alert(d.error || '저장 실패');
        }
    })
    .catch(function(e){ alert('저장 중 오류: '+e); })
    .finally(function(){
        saving = false;
        var b = document.getElementById('saveBtn');
        if (b) { b.disabled = false; b.textContent = document.getElementById('editId').value ? '수정' : '저장'; }
    });
}

function deleteEvent(id, mode, date) {
    var body = { id: id };
    if (mode) body.mode = mode;
    if (date) body.date = date;
    fetch('/api/bot/schedule/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
    .then(function(r){ return r.json(); }).then(function(d){
        if (d.success) loadEvents();
    });
}

var delPending = null;
function confirmDelete(id) {
    var ev = null;
    for (var i=0;i<schedules.length;i++){ if (String(schedules[i].id)===String(id)) { ev = schedules[i]; break; } }
    if (!ev) return;
    if (ev.is_recurring) {
        var baseId = id, date = (ev.event_date||'').slice(0,10);
        var sid = String(id);
        if (sid.indexOf('_') >= 0) {
            var parts = sid.split('_');
            baseId = parts[0];
            date = parts[1].replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3');
        }
        delPending = { baseId: baseId, date: date };
        document.getElementById('delModal').style.display = 'flex';
    } else {
        if (confirm('삭제할까요?')) deleteEvent(id, 'all', null);
    }
}
function closeDel() { document.getElementById('delModal').style.display = 'none'; delPending = null; }
function doDelete(mode) {
    if (!delPending) return;
    var p = delPending;
    closeDel();
    deleteEvent(p.baseId, mode, p.date);
}
