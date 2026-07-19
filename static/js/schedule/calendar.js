// auto-split from schedule2.html (modularization, behavior preserved)
function switchTab(t) {
    ['tabView','tabAdd','tabList','tabFav'].forEach(id => document.getElementById(id).style.display='none');
    document.getElementById('tab'+t.charAt(0).toUpperCase()+t.slice(1)).style.display = '';
    if (t === 'add') {
        document.getElementById('editId').value = '';
        document.getElementById('saveBtn').textContent = '저장';
        document.querySelector('#tabAdd h6').textContent = '새 일정';
        document.getElementById('accommodationSection').style.display = 'none';
        repeatOn = false; setRepeatOptionsVisible(false);
        document.getElementById('addCalPopup').style.display = 'none';
        // 이전 입력값 초기화 (새 일정 진입 시)
        ['addTitle','addLoc','memoEditor','addStart','addEnd','addDate','addEndDate','addAccommodation','numInput'].forEach(function(x){ var el=document.getElementById(x); if(el) el.value=''; });
        var today = new Date().toISOString().slice(0,10);
        document.getElementById('addDate').value = today;
        document.getElementById('addEndDate').value = today;
        document.getElementById('addAllDay').checked = false;
        document.getElementById('addReminder').value = 0;
        document.getElementById('addRepeatInterval').value = 1;
        document.querySelectorAll('.wd-cb').forEach(function(cb){ cb.checked=false; });
        document.getElementById('addRepeatWeekOfMonth').value = 0;
        document.getElementById('addRepeatMonthOfYear').value = 0;
        if (document.getElementById('numPanel')) document.getElementById('numPanel').style.display='none';
        toggleAllDay();
    }
}

function loadEvents() {
    return fetch('/api/bot/schedule?_='+Date.now()).then(r=>r.json()).then(d => {
        schedules = d.schedules || [];
        renderCal();
        renderEventList();
        document.getElementById('dayEvents').innerHTML = '';
    });
}

function renderCal() {
    const now = new Date();
    if (!calYear) { calYear = now.getFullYear(); calMonth = now.getMonth()+1; }
    document.getElementById('calTitle').textContent = calYear+'년 '+calMonth+'월';
    const firstDay = new Date(calYear, calMonth-1, 1).getDay();
    const lastDate = new Date(calYear, calMonth, 0).getDate();
    let html = '';
    for (let i = 0; i < firstDay; i++) html += '<div></div>';
    for (let d = 1; d <= lastDate; d++) {
        const ds = calYear+'-'+String(calMonth).padStart(2,'0')+'-'+String(d).padStart(2,'0');
        const today = now.getFullYear()===calYear && now.getMonth()+1===calMonth && now.getDate()===d;
        const evts = schedules.filter(s => s.event_date && s.event_date.startsWith(ds));
        let cls = '';
        if (evts.length) {
            const colors = evts.map(s => s.color||'gray');
            if (colors.includes('red')) cls = 'event-red';
            else if (colors.includes('blue')) cls = 'event-blue';
            else if (colors.includes('green')) cls = 'event-green';
            else cls = 'event-gray';
        }
        const hasRecur = evts.some(s => s.is_recurring);
        const numHtml = hasRecur ? '<span class="recur-box">'+d+'</span>' : d;
        html += '<div class="cal-day '+(today?'today ':'')+cls+(hasRecur?' event-recur':'')+(ds===selDate?' selected':'')+'" onclick="showDay(\''+ds+'\')">'+numHtml+'</div>';
    }
    document.getElementById('calGrid').innerHTML = html;
}

function showDay(date) {
    selDate = date;
    renderCal();
    const evts = schedules.filter(s => s.event_date && s.event_date.startsWith(date));
    // 종일 일정 먼저 정렬
    evts.sort((a, b) => {
        const aAll = a.is_allday === true;
        const bAll = b.is_allday === true;
        if (aAll && !bAll) return -1;
        if (!aAll && bAll) return 1;
        return (a.event_date || '').localeCompare(b.event_date || '');
    });
    const el = document.getElementById('dayEvents');
    if (!evts.length) { el.innerHTML = '<div class="text-muted small py-2">일정 없음</div><button class="btn btn-sm btn-success mt-1" onclick="addOnDate(\''+date+'\')">➕ '+date+' 일정추가</button>'; return; }
    // 종일 일정 먼저 정렬
    evts.sort((a, b) => (a.is_allday === b.is_allday ? 0 : a.is_allday ? -1 : 1));
    let h = '<div class="d-flex justify-content-between align-items-center mb-2"><span class="small fw-bold">'+date+'</span><button class="btn btn-sm btn-success" onclick="addOnDate(\''+date+'\')">➕ '+date+' 일정추가</button></div>';
    evts.forEach(s => {
        const badge = {'red':'🔴','blue':'🔵','green':'🟢','gray':'⚪'}[s.color||'gray']||'⚪';
        const time = s.event_date ? s.event_date.split(' ')[1].substring(0,5) : '';
        let loc = s.location ? '<br>📍 '+s.location : '';
        var accomm = '';
        if (s.memo && s.memo.includes('[숙소:')) {
            var m = s.memo.match(/\[숙소:([^\]]+)\]/);
            if (m) accomm = '<br>🏠 숙소: '+m[1];
        }
        var repTxt = '';
        if (s.is_recurring && s.repeat_type) {
            var _rm = {'daily':'일','weekly':'주','monthly':'월','yearly':'년'}[s.repeat_type] || '';
            repTxt = ' 🔁매'+(s.repeat_interval||1)+_rm+(s.repeat_infinite ? '(무한)' : '');
        }
        h += '<div class="border-bottom py-1 mb-1 small'+(scheduleType(s)==='move'?' evt-move':'')+'"><strong>'+badge+' '+typeChip(s)+s.title+repTxt+'</strong><br>🕐 '+time+loc+accomm+'<br>';
        if ((s.title && (s.title.includes('이동') || s.title.includes('집으로'))) && s.content) {
            try {
                var r = JSON.parse(s.content);
                if (r && r.from_lat && r.to_lat) {
                    var dl = encodeURIComponent(s.departure_location || '출발');
                    var al = encodeURIComponent(s.return_location || s.location || '도착');
                    h += '<div class="d-flex gap-1 mt-1 flex-wrap">';
// 이동 일정: event_date=출발시간, end_date=도착시간 (저장시간을 UTC로 간주)
                    var ts = s.end_date || s.event_date;
                    var arrTs = '';
                    if (ts) {
                        try {
                            var parts = ts.split(' ');
                            var dateParts = parts[0].split('-');
                            var timeParts = parts[1].split(':');
                            var year = parseInt(dateParts[0]);
                            var month = parseInt(dateParts[1]) - 1;
                            var day = parseInt(dateParts[2]);
                            var hour = parseInt(timeParts[0]);
                            var minute = parseInt(timeParts[1]);
                            // 저장된 시간을 UTC로 간주 (hour - 9 안 함)
                            var d = new Date(Date.UTC(year, month, day, hour, minute));
                            if (!isNaN(d.getTime())) arrTs = Math.floor(d.getTime()/1000);
                        } catch(e) {}
                    }
                    var fromLat = parseFloat(r.from_lat).toFixed(7);
                    var fromLng = parseFloat(r.from_lng).toFixed(7);
                    var toLat = parseFloat(r.to_lat).toFixed(7);
                    var toLng = parseFloat(r.to_lng).toFixed(7);
                    var isHome = s.title && s.title.includes('집으로');
                    var dataParam;
                    if (isHome) {
                        dataParam = '!3m1!4b1!4m4!4m3!2m1!6e2!3e3';
                    } else {
                        dataParam = '!3m1!4b1!4m6!4m5!2m3!6e1!7e2!8j' + (arrTs || '') + '!3e3';
                    }
                    h += '<a class="btn btn-sm btn-outline-danger py-0" target="_blank" href="https://www.google.co.kr/maps/dir/'+fromLat+','+fromLng+'/'+toLat+','+toLng+'/data='+dataParam+'">🌐Google</a>';
                    h += '<a class="btn btn-sm btn-outline-info py-0" target="_blank" href="https://map.naver.com/p/directions/'+r.from_lng+','+r.from_lat+','+dl+'/'+r.to_lng+','+r.to_lat+','+al+'/-/transit">🗺️네이버</a>';
                    h += '<a class="btn btn-sm btn-outline-success py-0" target="_blank" href="https://map.kakao.com/link/by/traffic/'+dl+','+r.from_lat+','+r.from_lng+'/'+al+','+r.to_lat+','+r.to_lng+'">📱카카오</a>';
                    h += '</div>';
                }
            } catch(e){}
        }
        h += '<br><button class="btn btn-sm btn-outline-info py-0 mt-1 me-1" onclick="showDetail(\'' + s.id + '\')">🔍</button><button class="btn btn-sm btn-outline-secondary py-0 mt-1 me-1" onclick="editEvent(\'' + s.id + '\')">✏️</button><button class="btn btn-sm btn-outline-danger py-0 mt-1" onclick="confirmDelete(\'' + s.id + '\')">✕</button></div>';
    });
    el.innerHTML = h;
}

function renderEventList() {
    const el = document.getElementById('eventList');
    if (!schedules.length) { el.innerHTML = '<div class="text-muted">일정 없음</div>'; return; }
    el.innerHTML = schedules.map(s => {
        const badge = {'red':'🔴','blue':'🔵','green':'🟢','gray':'⚪'}[s.color||'gray']||'⚪';
        const time = s.event_date ? s.event_date.split(' ')[1].substring(0,5) : '';
        return '<div class="border-bottom py-1'+(scheduleType(s)==='move'?' evt-move':'')+'"><strong>'+badge+' '+typeChip(s)+s.title+'</strong><br><small>🕐 '+time+'</small>'+(s.location?'<br><small>📍 '+s.location+'</small>':'')+'<br><button class="btn btn-sm btn-outline-secondary mt-1 me-1" onclick="editEvent(\'' + s.id + '\')">✏️</button><button class="btn btn-sm btn-outline-danger mt-1" onclick="confirmDelete(\'' + s.id + '\')">✕</button></div>';
    }).join('');
}

function addOnDate(date) {
    document.getElementById('accommodationSection').style.display = 'none';
    document.getElementById('addAccommodation').value = '';
    switchTab('add');
    document.getElementById('addDate').value = date;
    document.getElementById('addEndDate').value = date;
}
function renderAddCal() {
    const now = new Date();
    if (!addCalYear) { addCalYear = now.getFullYear(); addCalMonth = now.getMonth()+1; }
    document.getElementById('addCalTitle').textContent = addCalYear+'년 '+addCalMonth+'월';
    const firstDay = new Date(addCalYear, addCalMonth-1, 1).getDay();
    const lastDate = new Date(addCalYear, addCalMonth, 0).getDate();
    const sd = document.getElementById('addDate').value;
    const ed = document.getElementById('addEndDate').value;
    let html = '';
    for (let i = 0; i < firstDay; i++) html += '<div></div>';
    for (let d = 1; d <= lastDate; d++) {
        const ds = addCalYear+'-'+String(addCalMonth).padStart(2,'0')+'-'+String(d).padStart(2,'0');
        const isToday = now.getFullYear()===addCalYear && now.getMonth()+1===addCalMonth && now.getDate()===d;
        let cls = 'cal-day';
        if (ds === sd || ds === ed) cls += ' selstart';
        else if (sd && ed && ds > sd && ds < ed) cls += ' cal-sel';
        if (isToday) cls += ' today';
        html += '<div class="'+cls+'" onclick="addCalClick(\''+ds+'\')">'+d+'</div>';
    }
    document.getElementById('addCalGrid').innerHTML = html;
}
function showAddCal(mode, inputEl) {
    addCalMode = mode;
    var popup = document.getElementById('addCalPopup');
    if (inputEl && inputEl.offsetParent) {
        popup.style.top = (inputEl.offsetTop + inputEl.offsetHeight + 4) + 'px';
        popup.style.left = inputEl.offsetLeft + 'px';
    }
    document.getElementById('addCalHint').textContent = (mode === 'start' ? '시작일' : '종료일') + '을 선택하세요. 시작일보다 앞으로 정하면 무한반복됩니다.';
    renderAddCal();
    popup.style.display = '';
}
function addCalClick(ds) {
    if (addCalMode === 'start') {
        document.getElementById('addDate').value = ds;
    } else {
        document.getElementById('addEndDate').value = ds;
    }
    toggleAccommodation();
    renderAddCal();
}
function addChangeMonth(d) {
    addCalMonth += d;
    if (addCalMonth > 12) { addCalMonth = 1; addCalYear++; }
    if (addCalMonth < 1) { addCalMonth = 12; addCalYear--; }
    renderAddCal();
}
document.addEventListener('click', function(e){
    var t = e.target;
    var p = document.getElementById('addCalPopup');
    if (p && p.style.display !== 'none') {
        if (!p.contains(t) && t !== document.getElementById('addDate') && t !== document.getElementById('addEndDate')) {
            p.style.display = 'none';
        }
    }
    var r = document.getElementById('repeatOptions');
    if (r && r.style.display !== 'none') {
        if (!r.contains(t) && t !== document.getElementById('btnRepeat')) {
            r.style.display = 'none';
        }
    }
});


function changeMonth(d) {
    calMonth = (typeof calMonth !== 'undefined' && calMonth) ? calMonth : (new Date().getMonth() + 1);
    calYear = (typeof calYear !== 'undefined' && calYear) ? calYear : new Date().getFullYear();
    calMonth += d;
    if (calMonth > 12) { calMonth = 1; calYear++; }
    if (calMonth < 1) { calMonth = 12; calYear--; }
    renderCal();
}
