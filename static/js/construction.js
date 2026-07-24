// ========================================
// location-based 안내 (풍경/가게/교통/알림)
// ========================================

var transitData = null, suggestData = null, alarmTimer = null, alarmTimers = [];

function loadTrafficLive() {
    var parent = document.getElementById('alertList');
    var el = document.getElementById('trafficLive');
    if (!el) { el = document.createElement('div'); el.id = 'trafficLive'; document.getElementById('scenerySection').insertAdjacentElement('beforebegin', el); }
    el.innerHTML = '<div class="text-center py-2"><span class="spinner-border spinner-border-sm"></span> 교통정보 확인 중...</div>';
    fetch('/construction/traffic/gg').then(function(r){return r.json()}).then(function(d){
        if (!d.available || !d.incidents || d.incidents.length===0) {
            el.innerHTML = '<div class="text-muted text-center py-2">현재 양평군 교통 이슈가 없습니다.</div>'; return;
        }
        var html = '<div class="small mb-1 text-muted">🕐 UTIC 실시간 (' + d.yangpyeong + '건)</div>';
        d.incidents.forEach(function(i){
            html += '<div class="card mb-2 border-start border-3 border-danger"><div class="card-body p-2 small">';
            html += '<span class="badge bg-danger me-1">'+i.type+'</span><strong>'+i.title+'</strong>';
            if (i.road) html += '<br><small>🛣️ '+i.road+'</small>';
            if (i.start) html += '<br><small>🕐 '+i.start+'</small>';
            html += '</div></div>';
        });
        html += '<small class="text-muted">출처: 도시교통정보센터(UTIC)</small>';
        el.innerHTML = html;
    }).catch(function(){ el.innerHTML = '<div class="text-danger">불러오기 실패</div>'; });
}

function switchToHeritage() {
    document.querySelector('#infoTabs .nav-link[data-type=heritage]').click();
}

// ---- showInline: 풍경탭 내 인라인 콘텐츠 ----

function showInline(type) {
    var el = document.getElementById('inlineContent');
    var sc = document.getElementById('sceneryContent');
    if (type === 'scenery') {
        el.style.display = 'none';
        sc.style.display = '';
        return;
    }
    el.style.display = '';
    sc.style.display = 'none';
    if (type === 'traffic') {
        el.innerHTML = '<div class="text-center py-2"><span class="spinner-border spinner-border-sm"></span> 교통정보 확인 중...</div>';
        fetch('/construction/traffic/gg').then(function(r){return r.json()}).then(function(d){
            if (!d.available || !d.incidents || d.incidents.length===0) {
                el.innerHTML = '<div class="text-muted text-center py-2 small">현재 양평군 교통 이슈가 없습니다.</div>'; return;
            }
            var html = '<div class="small mb-1 text-muted">🕐 UTIC 실시간 (' + d.yangpyeong + '건)</div>';
            d.incidents.forEach(function(i){
                html += '<div class="card mb-2 border-start border-3 border-danger"><div class="card-body p-2 small">';
                html += '<span class="badge bg-danger me-1">'+i.type+'</span><strong>'+i.title+'</strong>';
                if (i.road) html += '<br><small>🛣️ '+i.road+'</small>';
                if (i.start) html += '<br><small>🕐 '+i.start+'</small>';
                html += '</div></div>';
            });
            el.innerHTML = html;
        });
    } else if (type === 'localstore') {
        el.innerHTML = '<div class="text-center py-2"><span class="spinner-border spinner-border-sm"></span> 가게 불러오는 중...</div>';
        fetch('/construction/local-stores').then(function(r){return r.json()}).then(function(d){
            if (!d.stores||d.stores.length===0) { el.innerHTML = '<div class="text-muted text-center py-2 small">등록된 가게가 없습니다.</div>'; return; }
            var html = '<div class="row g-2">';
            d.stores.forEach(function(g){
                var lat = g.lat ? parseFloat(g.lat).toFixed(4) : '0';
                var lng = g.lng ? parseFloat(g.lng).toFixed(4) : '0';
                var detailUrl = '/construction/store/' + encodeURIComponent(g.name) + '?town=' + encodeURIComponent(d.town) + '&village=' + encodeURIComponent(d.village) + '&lat=' + lat + '&lng=' + lng;
                var imgs = [];
                g.posts.forEach(function(p){ if (p.image) imgs.push(p.image); });
                if (!imgs.length && g.image) imgs.push(g.image);
                html += '<div class="col-6"><div class="store-card position-relative">';
                if (imgs.length) {
                    html += '<a href="'+detailUrl+'" class="text-decoration-none"><div class="store-img-scroll">';
                    imgs.forEach(function(img){ html += '<img src="'+img+'" class="store-img-item">'; });
                    html += '</div></a>';
                } else {
                    html += '<a href="'+detailUrl+'" class="text-decoration-none"><div class="store-img-placeholder">🏪</div></a>';
                }
                html += '<div class="p-2 text-center"><a href="'+detailUrl+'" class="text-decoration-none"><strong class="small text-dark">'+g.name+'</strong></a><br><small class="text-muted">글 '+g.posts.length+'개</small>';
                if (g.store_link) html += '<br><a href="'+g.store_link+'" class="btn btn-xs btn-outline-success py-0 px-1 mt-1" style="font-size:0.65rem;">'+(g.link_label||'🔗 링크')+'</a>';
                html += '</div></div></div>';
            });
            html += '</div>';
            el.innerHTML = html;
        });
    } else if (type === 'facility') {
        el.innerHTML = '<div class="text-center py-2"><span class="spinner-border spinner-border-sm"></span> 편의시설 불러오는 중...</div>';
        fetch('/api/facilities?type=toilet').then(function(r){return r.json()}).then(function(d){
            var facs = d.facilities || [];
            if (!facs.length) { el.innerHTML = '<div class="text-muted text-center py-3 small">근처 공중화장실 정보가 없습니다.<br>관리자 메뉴에서 편의시설을 동기화해 주세요.</div>'; return; }
            var html = '<div class="small mb-1 text-muted">생활안전지도(행정안전부) 공중화장실 · 양평군</div><div class="row g-2">';
            facs.forEach(function(f){
                var dir = (f.latitude!=null && f.longitude!=null) ? 'https://www.google.com/maps/dir/?api=1&destination='+f.latitude+','+f.longitude : '#';
                var kakao = (f.latitude!=null && f.longitude!=null) ? 'https://map.kakao.com/link/to/'+encodeURIComponent(f.name)+','+f.latitude+','+f.longitude : '#';
                html += '<div class="col-12"><div class="card border-0 shadow-sm" style="border-radius:16px;border-left:4px solid #198754;">';
                html += '<div class="card-body p-2"><div class="d-flex justify-content-between"><h6 class="fw-bold mb-1 small">'+f.name+'</h6>'+(f.distance_km!=null?'<span class="badge bg-light text-dark">'+f.distance_km+'km</span>':'')+'</div>';
                if (f.address) html += '<div class="small text-muted">'+f.address+'</div>';
                var tags = [];
                if (f.open_hr) tags.push('개방 '+f.open_hr);
                if (f.emergency_bell) tags.push('<span class="text-danger">비상벨</span>');
                if (f.cctv) tags.push('<span class="text-primary">CCTV</span>');
                if (tags.length) html += '<div class="small mt-1">'+tags.join(' · ')+'</div>';
                if (f.latitude!=null) html += '<div class="mt-1"><a class="btn btn-sm btn-outline-secondary" href="'+dir+'" target="_blank">길찾기(구글)</a> <a class="btn btn-sm btn-outline-success" href="'+kakao+'" target="_blank">카카오맵</a></div>';
                html += '</div></div>';
            });
            html += '</div>';
            el.innerHTML = html;
        }).catch(function(){ el.innerHTML = '<div class="text-danger">불러오기 실패</div>'; });
    } else if (type === 'alert') {
        var alHtml = document.getElementById('alertList');
        if (alHtml && alHtml.innerHTML.trim()) {
            el.innerHTML = alHtml.innerHTML;
        } else {
            el.innerHTML = '<div class="text-muted text-center py-2 small">현재 마을 알림이 없습니다.</div>';
        }
    }
}

// ---- switchTab ----

function switchTab(type) {
    ['heritageSection','scenerySection','homeSection','localStoresSection','facilitySection'].forEach(function(id){ document.getElementById(id).style.display='none'; });
    document.querySelectorAll('.notice-item').forEach(function(item){ item.style.display='none'; });
    if (document.getElementById('emptyNotices')) document.getElementById('emptyNotices').style.display='none';
    if (document.getElementById('alertList')) document.getElementById('alertList').style.display='none';
    var tl = document.getElementById('trafficLive'); if (tl) tl.style.display='none';
    if (type === 'localstore') { document.getElementById('localStoresSection').style.display=''; loadLocalStores(); }
    else if (type === 'facility') { var fsec=document.getElementById('facilitySection'); if(fsec) fsec.style.display=''; loadFacility(); }
    else if (type === 'traffic') {
        document.querySelectorAll('.notice-item').forEach(function(item){
            var dt = item.dataset.type;
            if (dt==='traffic_incident'||dt==='traffic_congestion'||dt==='road_construction') item.style.display='';
        });
        loadTrafficLive();
    }
    else if (type === 'alert') {
        if (document.getElementById('alertList')) document.getElementById('alertList').style.display='';
        if (document.getElementById('emptyNotices')) document.getElementById('emptyNotices').style.display='';
    }
    else if (type === 'building') {
        document.querySelectorAll('.notice-item').forEach(function(item){
            var dt = item.dataset.type;
            if (dt==='building_permit') item.style.display='';
        });
    }
}

// ---- 탭 클릭 이벤트 ----

document.querySelectorAll('#infoTabs .nav-link').forEach(function(tab){
    tab.addEventListener('click', function(e){
        e.preventDefault();
        document.querySelectorAll('#infoTabs .nav-link').forEach(function(t){ t.classList.remove('active'); });
        this.classList.add('active');
        var type = this.dataset.type;
        hideAllSections();
        var emptyEl = document.getElementById('emptyNotices');
        var alertList = document.getElementById('alertList');
        var ic = document.getElementById('inlineContent');
        var tl = document.getElementById('trafficLive'); if (tl) tl.style.display='none';

        switch(type) {
            case 'heritage': document.getElementById('heritageSection').style.display=''; loadHeritage(); if(ic)ic.style.display='none'; break;
            case 'scenery': document.getElementById('scenerySection').style.display=''; loadScenery(); break;
            case 'home': document.getElementById('homeSection').style.display=''; loadHome(); if(ic)ic.style.display='none'; break;
            case 'traffic':
                document.querySelectorAll('.notice-item').forEach(function(item){
                    var dt = item.dataset.type;
                    if (dt==='traffic_incident'||dt==='traffic_congestion'||dt==='road_construction') item.style.display='';
                });
                if (emptyEl && !document.querySelector('.notice-item:not([style*="display:none"])')) emptyEl.style.display='';
                break;
            case 'alert':
                if (alertList) alertList.style.display='';
                if (emptyEl) emptyEl.style.display='';
                break;
            case 'building':
                loadBuilding();
                break;
        }
    });
});

function hideAllSections() {
    ['heritageSection','scenerySection','homeSection','localStoresSection'].forEach(function(id){ document.getElementById(id).style.display='none'; });
    document.querySelectorAll('.notice-item').forEach(function(item){ item.style.display='none'; });
    var emptyEl = document.getElementById('emptyNotices'); if (emptyEl) emptyEl.style.display='none';
    var alertEl = document.getElementById('emptyAlert'); if (alertEl) alertEl.style.display='none';
    var alertList = document.getElementById('alertList'); if (alertList) alertList.style.display='none';
}

// ---- 헤리티지 ----

function loadHeritage() {
    var el = document.getElementById('heritageList');
    el.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm"></span> 위치 확인 중...</div>';
    if (!navigator.geolocation) { el.innerHTML = '<div class="alert alert-warning">이 브라우저는 위치 정보를 지원하지 않습니다.</div>'; return; }
    navigator.geolocation.getCurrentPosition(function(pos){
        var lat = pos.coords.latitude, lng = pos.coords.longitude;
        el.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm"></span> 가까운 국가유산 검색 중...</div>';
        fetch('/construction/heritage?lat=' + lat + '&lng=' + lng)
            .then(function(r){return r.json()}).then(function(data){
                if (!data || data.length === 0) { el.innerHTML = '<div class="text-center py-5 text-muted"><div class="fs-1 mb-3">🏛️</div><p>반경 5km 이내 국가유산이 없습니다.</p></div>'; return; }
                var html = '<div class="row g-3">';
                data.forEach(function(h){
                    var tUrl = 'https://map.naver.com/index.nhn?slat='+lat+'&slng='+lng+'&stitle='+encodeURIComponent('현재위치')+'&elat='+h.lat+'&elng='+h.lng+'&etitle='+encodeURIComponent(h.name)+'&pathType=1';
                    var bUrl = 'https://map.naver.com/index.nhn?slat='+lat+'&slng='+lng+'&elat='+h.lat+'&elng='+h.lng+'&etitle='+encodeURIComponent(h.name)+'&pathType=2';
                    var wUrl = 'https://map.naver.com/index.nhn?slat='+lat+'&slng='+lng+'&elat='+h.lat+'&elng='+h.lng+'&etitle='+encodeURIComponent(h.name)+'&pathType=3';
                    var nearHome = h.near_home, stamped = h.stamped;
                    html += '<div class="col-12"><div class="card border-0 shadow-sm heritage-card" style="border-left:4px solid '+(nearHome?'#0d6efd':'#198754')+'">';
                    html += '<div class="card-body p-3">';
                    html += '<div class="d-flex align-items-center gap-2 mb-2">';
                    html += '<span class="badge '+(nearHome?'bg-primary':'bg-success')+' small">'+h.type+'</span>';
                    html += '<span class="fw-bold flex-grow-1 small">'+(stamped?'⭐ ':'')+h.name+'</span>';
                    html += '<small class="text-muted flex-shrink-0">'+h.dist+'km</small></div>';
                    if (nearHome) {
                        html += '<div class="small text-primary mb-1">🏠 집에서 '+(h.dist_from_home||h.dist)+'km · 내 지역 문화유산</div>';
                        html += '<div class="d-flex gap-1 flex-wrap mb-2">';
                        html += '<button class="btn btn-sm btn-outline-secondary" onclick="openExternal(\'https://ko.wikipedia.org/w/index.php?search='+encodeURIComponent(h.name)+'\',\'📖 위키백과: '+h.name+'\')">📖 위키백과</button>';
                        html += '<button class="btn btn-sm btn-outline-success" onclick="openExternal(\'https://search.naver.com/search.naver?query='+encodeURIComponent(h.name+' 문화재')+'\',\'🔍 네이버: '+h.name+'\')">🔍 자세히보기</button>';
                        html += '</div>';
                    } else {
                        html += '<div class="small text-muted mb-1">🧳 관광객 추천 · 현재위치 '+h.dist+'km</div>';
                    }
                    html += '<div class="d-flex gap-1 flex-wrap align-items-center">';
                    html += '<button class="btn btn-sm btn-outline-primary" onclick="openExternal(\''+tUrl+'\',\'🚌 대중교통: '+h.name+'\')">🚌 대중교통</button>';
                    html += '<button class="btn btn-sm btn-outline-success" onclick="openExternal(\''+bUrl+'\',\'🚲 자전거: '+h.name+'\')">🚲 자전거</button>';
                    html += '<button class="btn btn-sm btn-outline-secondary" onclick="openExternal(\''+wUrl+'\',\'🚶 도보: '+h.name+'\')">🚶 도보</button>';
                    if (stamped) { html += '<span class="btn btn-sm btn-warning disabled">✅ 방문완료</span>'; }
                    else { html += '<button class="btn btn-sm btn-outline-danger stamp-btn" data-name="'+h.name.replace(/"/g,'&quot;')+'" data-lat="'+h.lat+'" data-lng="'+h.lng+'">🔖 스탬프</button>'; }
                    html += '</div></div></div></div>';
                });
                html += '</div><small class="text-muted d-block mt-2">출처: 국가유산청 공간정보</small>';
                el.innerHTML = html;
            }).catch(function(){ el.innerHTML = '<div class="alert alert-danger">불러오기 실패</div>'; });
    }, function(){ el.innerHTML = '<div class="alert alert-warning">위치 권한이 필요합니다. 브라우저 설정에서 위치 접근을 허용해 주세요.</div>'; }, { enableHighAccuracy: true, timeout: 10000 });
}

// ---- 풍경사진 ----

function loadScenery() {
    var sc = document.getElementById('sceneryContent');
    var ic = document.getElementById('inlineContent');
    if (ic) ic.style.display = 'none';
    sc.style.display = '';
    sc.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm"></span> 풍경사진 불러오는 중...</div>';
    fetch('/construction/local-scenery').then(function(r){return r.json()}).then(function(data){
        if (data.error) { sc.innerHTML = '<div class="alert alert-warning">'+data.error+'</div>'; return; }
        var tabEl = document.getElementById('sceneryTab');
        if (tabEl && data.village) tabEl.textContent = '🌄 ' + data.village;
        else if (tabEl && data.town) tabEl.textContent = '🌄 ' + data.town;
        if (!data.sceneries||data.sceneries.length===0) { sc.innerHTML = '<div class="text-muted text-center py-2 small">'+data.town+' '+data.village+'에 '+data.season+' 풍경사진이 없습니다.</div>'; return; }
        var html = '<div class="mb-2"><span class="badge bg-success">'+data.town+' '+data.village+'</span> <span class="badge bg-info ms-1">'+data.season+'</span> <small class="text-muted ms-1">사진 '+data.sceneries.length+'장</small></div><div class="row g-3">';
        data.sceneries.forEach(function(s){
            html += '<div class="col-6 col-md-4"><a href="/share/detail/'+s.id+'" target="_blank" class="text-decoration-none"><div class="card border-0 shadow-sm h-100 scenery-card">';
            if (s.image_path) html += '<img src="'+s.image_path+'" class="card-img-top scenery-thumb" alt="'+s.title+'">';
            else html += '<div class="bg-light d-flex align-items-center justify-content-center scenery-placeholder">🌄</div>';
            html += '<div class="card-body p-2 text-center"><p class="small fw-bold text-dark mb-0 text-truncate">'+s.title+'</p></div></div></a></div>';
        });
        html += '</div><div class="text-center mt-3"><a href="/share-report" class="btn btn-sm btn-outline-primary">내 사진도 등록하기</a></div>';
        sc.innerHTML = html;
    }).catch(function(){ sc.innerHTML = '<div class="alert alert-danger">불러오기 실패</div>'; });
}

// ---- 가게 (레거시, switchTab 전용) ----

function loadLocalStores() {
    var el = document.getElementById('localStoresContent');
    el.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm"></span> 가게 불러오는 중...</div>';
    fetch('/api/user/location').then(function(r){return r.json()}).then(function(loc){
        if (loc.error||!loc.village) { el.innerHTML = '<div class="alert alert-warning">등록된 주소(리)가 없습니다. 마이페이지에서 설정해 주세요.</div>'; return; }
        fetch('/construction/local-stores').then(function(r){return r.json()}).then(function(data){
            if (data.error) { el.innerHTML = '<div class="alert alert-warning">'+data.error+'</div>'; return; }
            if (!data.stores||data.stores.length===0) { el.innerHTML = '<div class="text-center py-5 text-muted"><div class="fs-1 mb-3">🏪</div><p>같은 리('+data.town+' '+data.village+')에 등록된 가게가 없습니다.</p><p class="small"><a href="/share-report">공유마당에 가게 등록하기</a></p></div>'; return; }
            var html = '<div class="mb-3"><span class="badge bg-primary">'+data.town+' '+data.village+'</span> <small class="text-muted">가게 '+data.stores.length+'곳</small></div><div class="row g-3">';
            data.stores.forEach(function(s){
                html += '<div class="col-6 col-md-4"><a href="/share/detail/'+s.id+'" target="_blank" class="text-decoration-none"><div class="card border-0 shadow-sm h-100 scenery-card">';
                if (s.image_path) html += '<img src="'+s.image_path+'" class="card-img-top scenery-thumb" alt="'+s.title+'" onerror="this.src=\'https://placehold.co/300x200/e9ecef/6c757d?text=No+Image\'">';
                else html += '<div class="bg-light d-flex align-items-center justify-content-center scenery-placeholder">🏪</div>';
                html += '<div class="card-body p-2 text-center"><p class="small fw-bold text-dark mb-0 text-truncate">'+s.title+'</p></div></div></a></div>';
            });
            html += '</div><div class="text-center mt-3"><a href="/share-report" class="btn btn-sm btn-outline-primary">내 가게도 등록하기</a></div>';
            el.innerHTML = html;
        }).catch(function(){ el.innerHTML = '<div class="alert alert-danger">불러오기 실패</div>'; });
    }).catch(function(){ el.innerHTML = '<div class="alert alert-danger">사용자 정보를 불러올 수 없습니다.</div>'; });
}

function loadFacility() {
    var el = document.getElementById('facilityContent');
    if (!el) return;
    el.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm"></span> 편의시설 불러오는 중...</div>';
    fetch('/api/facilities?type=toilet').then(function(r){return r.json()}).then(function(d){
        var facs = d.facilities || [];
        if (!facs.length) { el.innerHTML = '<div class="text-muted text-center py-3 small">근처 공중화장실 정보가 없습니다.<br>관리자 메뉴에서 편의시설을 동기화해 주세요.</div>'; return; }
        var html = '<div class="small mb-1 text-muted">생활안전지도(행정안전부) 공중화장실 · 양평군</div><div class="row g-2">';
        facs.forEach(function(f){
            var dir = (f.latitude!=null && f.longitude!=null) ? 'https://www.google.com/maps/dir/?api=1&destination='+f.latitude+','+f.longitude : '#';
            var kakao = (f.latitude!=null && f.longitude!=null) ? 'https://map.kakao.com/link/to/'+encodeURIComponent(f.name)+','+f.latitude+','+f.longitude : '#';
            html += '<div class="col-12"><div class="card border-0 shadow-sm" style="border-radius:16px;border-left:4px solid #198754;">';
            html += '<div class="card-body p-2"><div class="d-flex justify-content-between"><h6 class="fw-bold mb-1 small">'+f.name+'</h6>'+(f.distance_km!=null?'<span class="badge bg-light text-dark">'+f.distance_km+'km</span>':'')+'</div>';
            if (f.address) html += '<div class="small text-muted">'+f.address+'</div>';
            var tags = [];
            if (f.open_hr) tags.push('개방 '+f.open_hr);
            if (f.emergency_bell) tags.push('<span class="text-danger">비상벨</span>');
            if (f.cctv) tags.push('<span class="text-primary">CCTV</span>');
            if (tags.length) html += '<div class="small mt-1">'+tags.join(' · ')+'</div>';
            if (f.latitude!=null) html += '<div class="mt-1"><a class="btn btn-sm btn-outline-secondary" href="'+dir+'" target="_blank">길찾기(구글)</a> <a class="btn btn-sm btn-outline-success" href="'+kakao+'" target="_blank">카카오맵</a></div>';
            html += '</div></div>';
        });
        html += '</div>';
        el.innerHTML = html;
    }).catch(function(){ el.innerHTML = '<div class="text-danger">불러오기 실패</div>'; });
}
// ---- 집으로 ----

function loadHome() {
    var el = document.getElementById('homeContent');
    el.innerHTML = '<div class="text-center py-5 text-muted"><span class="spinner-border spinner-border-sm"></span> 위치 확인 중...</div>';
    if (!navigator.geolocation) { el.innerHTML = '<div class="alert alert-warning">이 브라우저는 위치 정보를 지원하지 않습니다.</div>'; return; }
    fetch('/api/user/location').then(function(r){return r.json()}).then(function(loc){
        if (loc.error) { el.innerHTML = '<div class="alert alert-warning">로그인이 필요합니다.</div>'; return; }
        if (!loc.village && !loc.address) { el.innerHTML = '<div class="alert alert-warning">등록된 주소(리)가 없습니다. 마이페이지에서 설정해 주세요.</div>'; return; }
        navigator.geolocation.getCurrentPosition(function(pos){
            var lat = pos.coords.latitude, lng = pos.coords.longitude;
            document.getElementById('corrGpsLat').value = lat;
            document.getElementById('corrGpsLng').value = lng;
            el.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm"></span> 대중교통 경로 검색 중...</div>';
            Promise.all([
                fetch('/construction/transit?from_lat='+lat+'&from_lng='+lng).then(function(r){return r.json()}),
                fetch('/construction/transit/suggest?from_lat='+lat+'&from_lng='+lng).then(function(r){return r.json()})
            ]).then(function(results){
                var data = results[0], suggest = results[1];
                if (data.error) { el.innerHTML = '<div class="alert alert-warning">'+data.error+'</div>'; return; }
                transitData = data; suggestData = suggest&&!suggest.error?suggest:null;
                if (loc.address) data.departure.address = loc.address;
                renderHome(data, loc);
            }).catch(function(){
                var gpsInfo = '위도: ' + lat.toFixed(6) + ', 경도: ' + lng.toFixed(6);
                fetch('/construction/transit/suggest?from_lat='+lat+'&from_lng='+lng).then(function(r){return r.json()}).then(function(s){
                    if (s && s.already_home) {
                        var homeAddr = s.home_address || (loc.town+' '+loc.village);
                        el.innerHTML = '<div class="card border-0 shadow-sm mb-3 text-center" style="border-radius:16px;border:2px solid #198754;">'
                            +'<div class="card-body p-4"><div class="fs-1 mb-2">🏠</div>'
                            +'<h4 class="fw-bold text-success mb-2">집 또는 회사 입니다</h4>'
                            +'<p class="text-muted small mb-1">📍 '+homeAddr+'</p>'
                            +'<p class="text-muted small">📡 '+gpsInfo+'</p></div></div>';
                    } else {
                        el.innerHTML = '<div class="alert alert-warning text-center">'
                            +'<div class="mb-2">😅 경로 검색에 실패했습니다</div>'
                            +'<div class="small text-muted">📡 '+gpsInfo+'</div></div>';
                    }
                }).catch(function(){
                    el.innerHTML = '<div class="alert alert-warning text-center">'
                        +'<div class="mb-2">😅 경로 검색에 실패했습니다</div>'
                        +'<div class="small text-muted">📡 '+gpsInfo+'</div></div>';
                });
            });
        }, function(err){
            var msg = '위치 정보를 가져올 수 없습니다.';
            if (err.code===1) msg='위치 권한이 거부되었습니다.';
            else if (err.code===2) msg='GPS 신호가 약합니다.';
            else if (err.code===3) msg='시간이 초과되었습니다.';
            el.innerHTML = '<div class="alert alert-warning">'+msg+'</div>';
        }, { enableHighAccuracy:false, timeout:15000, maximumAge:60000 });
    }).catch(function(){ el.innerHTML = '<div class="alert alert-danger">사용자 정보를 불러올 수 없습니다.</div>'; });
}

function renderHome(data, loc) {
    var el = document.getElementById('homeContent');
    var dep = data.departure.address, dest = data.destination.address, km = data.distance_km;
    var html = '';
    if (suggestData && suggestData.already_home) {
        var homeAddr = suggestData.home_address || (loc.town+' '+loc.village);
        var lat = document.getElementById('corrGpsLat').value;
        var lng = document.getElementById('corrGpsLng').value;
        html += '<div class="card border-0 shadow-sm mb-3 text-center" style="border-radius:16px;border:2px solid #198754;">';
        html += '<div class="card-body p-4"><div class="fs-1 mb-2">🏠</div>';
        html += '<h4 class="fw-bold text-success mb-2">집 또는 회사 입니다</h4>';
        html += '<p class="text-muted small mb-1">📍 '+homeAddr+'</p>';
        if (lat && lng) html += '<p class="text-muted small">📡 위도: '+parseFloat(lat).toFixed(6)+', 경도: '+parseFloat(lng).toFixed(6)+'</p>';
        html += '</div></div>';
        el.innerHTML = html;
        return;
    } else if (suggestData && suggestData.optimal_departure) {
        var sd = suggestData, now = new Date(), nowMin = now.getHours()*60+now.getMinutes();
        var optParts = sd.optimal_departure.split(':').map(Number), optMin = optParts[0]*60+optParts[1];
        var lastParts = sd.last_transit_from_station.split(':').map(Number), lastMin = lastParts[0]*60+lastParts[1];
        html += '<div class="card border-0 shadow-sm mb-3 home-transit-card"><div class="card-body p-3">';
        html += '<h6 class="fw-bold text-danger mb-2">🚇 귀가를 위해 지켜야 하는 출발시간</h6><div class="small">';
        html += '<div class="d-flex align-items-center gap-2 mb-1"><span class="badge bg-danger" style="font-size:0.65rem;">환승역</span><strong>'+sd.transfer_station+'</strong> <span class="text-muted">('+sd.line+')</span></div>';
        html += '<div class="mb-1">🕐 <strong>막차 출발:</strong> '+sd.last_transit_from_station+' ('+sd.direction+')</div>';
        if (sd.home_distance_km) html += '<div class="mb-1">🏠 역→집 거리: 약 '+sd.home_distance_km+'km</div>';
        html += '<div class="mb-1">🚶 <strong>내 위치→역:</strong> 약 '+sd.time_to_station_min+'분 소요예상</div><hr class="my-2">';
        html += '<div class="text-center py-2 bg-danger bg-opacity-10 rounded mb-2"><div class="fw-bold text-danger font-size-1-3">⏰ '+sd.optimal_departure+'</div><small class="text-muted">이 시간까지 출발하면 막차를 탈 수 있습니다</small></div>';
        if (nowMin>lastMin) html += '<div class="alert alert-warning py-1 small">⚠️ 막차 시간이 지났습니다.</div>';
        else if (nowMin>optMin) html += '<div class="alert alert-warning py-1 small">⚠️ 최적 출발 시간이 지났습니다. 서두르세요!</div>';
        else { var rem=optMin-nowMin; var remH=Math.floor(rem/60), remM=rem%60; html += '<div class="small text-muted mt-1">⏳ 출발까지 '+(remH>0?remH+'시간 ':'')+remM+'분 남음</div>'; }
        html += '<hr><div class="mt-2"><div class="form-check form-check-inline"><input type="checkbox" id="pre10min" class="form-check-input" checked><label class="form-check-label small" for="pre10min">10분 전 알림</label></div><div class="form-check form-check-inline"><input type="checkbox" id="pre5min" class="form-check-input" checked><label class="form-check-label small" for="pre5min">5분 전 알림</label></div></div>';
        html += '<button class="btn btn-sm btn-danger w-100 mt-2" onclick="setAlarm()">🔔 알람 설정</button><div id="alarmStatus" class="small text-center mt-1"></div>';
        html += '</div></div></div>';
    }
    html += '<div class="card border-0 shadow-sm mb-3 home-loc-card"><div class="card-body p-3">';
    html += '<div class="d-flex align-items-center gap-2 mb-2"><span class="badge bg-primary">📍 현재위치</span><small>'+dep+'</small></div>';
    html += '<div class="d-flex align-items-center gap-2 mb-3"><span class="badge bg-danger">🏠 기본주소</span><small>'+dest+'</small></div>';
    html += '<div class="small text-muted mb-2">📍 직선거리 약 '+km+'km</div>';
    var glat = document.getElementById('corrGpsLat').value;
    var glng = document.getElementById('corrGpsLng').value;
    if (glat && glng) html += '<div class="small text-muted">📡 위도: '+parseFloat(glat).toFixed(6)+', 경도: '+parseFloat(glng).toFixed(6)+'</div>';
    if (data.last_transit&&data.last_transit.length>0){var lt=data.last_transit[0];var h=Math.floor(lt.total_min/60),m=lt.total_min%60;html+='<div class="p-2 bg-success bg-opacity-10 rounded mb-2"><strong>⏱ 소요시간</strong> 약 '+(h>0?h+'시간 ':'')+m+'분</div>';}
    else if(data.rough_estimate_min){var h2=Math.floor(data.rough_estimate_min/60),m2=data.rough_estimate_min%60;html+='<div class="alert alert-info py-2 mb-2"><strong>⏱ 예상 소요시간</strong> 약 '+(h2>0?h2+'시간 ':'')+m2+'분 (직선거리 기반 추정)</div>';}
    html += '<hr><div class="mb-2"><label class="form-label small fw-bold">⏱ 희망 도착시간</label><div class="input-group input-group-sm"><input type="time" id="arrivalTime" class="form-control" value="21:00"><button class="btn btn-outline-secondary" onclick="calcDeparture()">계산</button></div></div><div id="departureResult" class="small mb-2"></div>';
    html += '</div></div>'; el.innerHTML = html;
}

// ---- 알람 ----

function calcDeparture() {
    var arrivalVal = document.getElementById('arrivalTime').value;
    if (!arrivalVal) return;
    var parts = arrivalVal.split(':').map(Number);
    var totalMin = transitData.last_transit ? transitData.last_transit[0].total_min : (transitData.rough_estimate_min||30);
    var depTotal = parts[0]*60+parts[1]-totalMin;
    if (depTotal<0) { document.getElementById('departureResult').innerHTML = '<span class="text-danger">⏰ 희망 시간에 도착하려면 이미 출발해야 합니다!</span>'; return; }
    var dh=Math.floor(depTotal/60), dm=depTotal%60;
    document.getElementById('departureResult').innerHTML = '<span class="text-success">⏰ <strong>'+String(dh).padStart(2,'0')+':'+String(dm).padStart(2,'0')+'</strong>까지 출발해야 합니다. (소요시간 '+totalMin+'분)</span>';
}

function setAlarm() {
    var departureMin = null;
    if (suggestData && suggestData.optimal_departure) {
        var parts = suggestData.optimal_departure.split(':').map(Number);
        departureMin = parts[0]*60+parts[1];
    } else {
        var arrivalVal = document.getElementById('arrivalTime').value;
        if (!arrivalVal) { document.getElementById('alarmStatus').innerHTML='<span class="text-danger">희망 도착시간을 먼저 입력해 주세요.</span>'; return; }
        var parts = arrivalVal.split(':').map(Number);
        var totalMin = transitData.last_transit ? transitData.last_transit[0].total_min : (transitData.rough_estimate_min||30);
        departureMin = parts[0]*60+parts[1]-totalMin;
        if (departureMin<0) { document.getElementById('alarmStatus').innerHTML='<span class="text-danger">늦었습니다.</span>'; return; }
    }
    var now = new Date(), nowTotal = now.getHours()*60+now.getMinutes(), diffMin = departureMin-nowTotal;
    if (diffMin<=0) { document.getElementById('alarmStatus').innerHTML='<span class="text-danger">출발 시간이 이미 지났습니다.</span>'; return; }
    if (Notification.permission==='denied') { document.getElementById('alarmStatus').innerHTML='<span class="text-danger">알림이 차단되었습니다.</span>'; return; }
    if (Notification.permission==='default') { Notification.requestPermission().then(function(perm){ if (perm==='granted') scheduleAlarms(diffMin); else document.getElementById('alarmStatus').innerHTML='<span class="text-danger">알림 권한이 필요합니다.</span>'; }); }
    else scheduleAlarms(diffMin);
}

function scheduleAlarms(diffMin) {
    alarmTimers.forEach(function(t){ clearTimeout(t); });
    alarmTimers = [];
    if (alarmTimer) { clearTimeout(alarmTimer); alarmTimer = null; }
    var dest = transitData.destination ? transitData.destination.address : '';
    var pre10 = document.getElementById('pre10min') ? document.getElementById('pre10min').checked : false;
    var pre5 = document.getElementById('pre5min') ? document.getElementById('pre5min').checked : false;
    if (pre10 && diffMin > 10) {
        var t10 = setTimeout(function(){
            new Notification('🔔 10분 후 출발 시간', {body: dest+' 방면 막차 10분 전입니다. 준비하세요!', icon:'/static/favicon.ico'});
            document.getElementById('alarmStatus').innerHTML = '<span class="text-warning fw-bold">🔔 10분 전! 준비하세요!</span>';
        }, (diffMin-10)*60*1000);
        alarmTimers.push(t10);
    }
    if (pre5 && diffMin > 5) {
        var t5 = setTimeout(function(){
            new Notification('🔔 5분 후 출발 시간', {body: dest+' 방면 막차 5분 전입니다. 이동을 시작하세요!', icon:'/static/favicon.ico'});
            document.getElementById('alarmStatus').innerHTML = '<span class="text-warning fw-bold">🔔 5분 전! 이동하세요!</span>';
        }, (diffMin-5)*60*1000);
        alarmTimers.push(t5);
    }
    alarmTimer = setTimeout(function(){
        new Notification('🚌 출발 시간입니다!', {body: '지금 출발해야 '+dest+'에 막차를 탈 수 있습니다.', icon:'/static/favicon.ico'});
        document.getElementById('alarmStatus').innerHTML = '<span class="text-danger fw-bold">🔔 출발 시간! 지금 출발하세요!</span>';
    }, diffMin*60*1000);
    var dh=Math.floor(diffMin/60), dm=diffMin%60;
    var msg = '🔔 '+(dh>0?dh+'시간 ':'')+dm+'분 후 알림 예정';
    if (pre10 && diffMin > 10) msg += ' · 10분 전 알림';
    if (pre5 && diffMin > 5) msg += ' · 5분 전 알림';
    document.getElementById('alarmStatus').innerHTML = '<span class="text-success">'+msg+'</span>';
}

// ---- 스탬프 ----

document.addEventListener('click', function(e){
    var btn = e.target.closest('.stamp-btn');
    if (!btn) return; e.preventDefault();
    stampHeritage(btn, btn.dataset.name, parseFloat(btn.dataset.lat), parseFloat(btn.dataset.lng));
});

function stampHeritage(btn, name, lat, lng) {
    if (!navigator.geolocation) { alert('📍 GPS를 켜주세요.'); return; }
    btn.disabled = true; btn.textContent = '확인 중...';
    navigator.geolocation.getCurrentPosition(function(pos){
        fetch('/construction/heritage/stamp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:name,lat:lat,lng:lng,gps_lat:pos.coords.latitude,gps_lng:pos.coords.longitude})})
        .then(function(r){return r.json()}).then(function(data){
            if (data.success) btn.outerHTML='<span class="btn btn-sm btn-warning disabled">✅ 방문완료</span>';
            else { alert(data.error||'스탬프 실패'); btn.disabled=false; btn.textContent='🔖 스탬프'; }
        }).catch(function(){ alert('장소를 옮겨서 다시 시도해 주세요.'); btn.disabled=false; btn.textContent='🔖 스탬프'; });
    }, function(err){ var msg='GPS 확인 불가'; if(err.code===1) msg='위치 권한이 필요합니다.'; alert(msg); btn.disabled=false; btn.textContent='🔖 스탬프'; });
}

// ---- 위치 보정 ----

function manualLocCorrect() {
    var input = document.querySelector('#manualLoc, #manualLoc2');
    if (!input) { alert('입력창을 찾을 수 없습니다.'); return; }
    var loc = input.value.trim();
    if (!loc) { alert('위치를 입력하세요.\n예: 양서면 양수리'); return; }
    if (!navigator.geolocation) { submitManualLoc(loc, 0, 0); return; }
    navigator.geolocation.getCurrentPosition(function(p){ submitManualLoc(loc, p.coords.latitude, p.coords.longitude); }, function(){ submitManualLoc(loc, 0, 0); }, {enableHighAccuracy:true, timeout:5000});
}
window.manualLocCorrect = manualLocCorrect;

function submitManualLoc(loc, gps_lat, gps_lng) {
    fetch('/user/location/correct', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({manual_loc: loc, gps_lat: gps_lat, gps_lng: gps_lng})})
    .then(function(r){return r.json()}).then(function(d){
        alert(d.msg||'결과');
        if(d.status==='success') location.reload();
    });
}

// ---- 초기화 ----

(function init(){
    // notices 있으면 empty 메시지 숨김
    var notices = document.querySelectorAll('.notice-item');
    var emptyE = document.getElementById('emptyNotices');
    if (emptyE && notices.length > 0) emptyE.style.display = 'none';
    var al = document.getElementById('alertList');
    if (al) al.style.display = 'none';

    var params = new URLSearchParams(window.location.search);
    var tab = params.get('tab');
    if (tab) {
        var tabEl = document.querySelector('#infoTabs .nav-link[data-type="' + tab + '"]');
        if (tabEl) tabEl.click();
        else loadHeritage();
    } else {
        loadHeritage();
    }

    fetch('/api/construction/unread').then(function(r){return r.json()}).then(function(d){
        if (d.alerts > 0) { var b = document.getElementById('sceneryBadge'); b.textContent = d.alerts; b.classList.remove('d-none'); }
    }).catch(function(){});
})();

// ---- 건축공사 (위치기반 우선) ----

function loadBuilding() {
    var listEl = document.getElementById('noticeList');
    var emptyEl = document.getElementById('emptyNotices');
    if (emptyEl) emptyEl.style.display = 'none';
    if (listEl) listEl.style.display = '';

    function render(items, town, village) {
        if (listEl) {
            listEl.innerHTML = '';
            if (!items || items.length === 0) {
                if (emptyEl) {
                    emptyEl.style.display = '';
                    var where = (town && village) ? (town + ' ' + village)
                              : (town || village || '현재 위치');
                    emptyEl.innerHTML = '<div class="fs-1 mb-3">🏗️</div>'
                        + '<p><strong>' + where + '</strong> 근처에는 건축 관련 내용이 없습니다.</p>'
                        + '<p class="small text-muted">현재 진행 중이거나 허가된 건축공사 정보가 없습니다. 특별한 내용이 없습니다.</p>'
                        + '<p class="small"><a href="/construction/refresh">정보 갱신하기</a></p>';
                }
                return;
            }
            items.forEach(function(n){
                if (n.notice_type !== 'building_permit') return;
                var dist = (n.distance_km != null) ? ('📍 ' + n.distance_km + 'km · ') : '';
                var html = '<div class="col-12 notice-item" data-type="' + n.notice_type + '">'
                    + '<div class="card border-0 shadow-sm" style="border-radius:16px;">'
                    + '<div class="card-body p-3">'
                    + '<div class="d-flex justify-content-between"><h6 class="fw-bold mb-2">' + (n.title || '건축공사') + '</h6>'
                    + '<span class="badge bg-info">🏗️ 건축공사</span></div>'
                    + (n.description ? '<p class="small text-muted mb-2">' + n.description + '</p>' : '')
                    + '<div class="d-flex gap-3 flex-wrap small text-muted">'
                    + (n.location ? '<span>📍 ' + n.location + '</span>' : '')
                    + (dist ? '<span>' + dist + '</span>' : '')
                    + (n.start_date ? '<span>📅 ' + n.start_date + '</span>' : '')
                    + '</div>'
                    + (n.latitude && n.longitude ? '<a href="https://maps.google.com/?q=' + n.latitude + ',' + n.longitude + '" target="_blank" class="btn btn-sm btn-outline-secondary mt-2">🗺️ 지도보기</a>' : '')
                    + '</div></div></div>';
                listEl.insertAdjacentHTML('beforeend', html);
            });
        }
    }

    if (!navigator.geolocation) {
        // GPS 미지원: 저장된 위치 기준
        fetch('/api/construction/notices').then(function(r){return r.json();}).then(function(d){
            render(d.notices, d.town, d.village);
        }).catch(function(){ render([], '', ''); });
        return;
    }
    navigator.geolocation.getCurrentPosition(function(pos){
        var lat = pos.coords.latitude, lng = pos.coords.longitude;
        fetch('/api/construction/notices?lat=' + lat + '&lng=' + lng).then(function(r){return r.json();}).then(function(d){
            render(d.notices, d.town, d.village);
        }).catch(function(){ render([], '', ''); });
    }, function(){
        // 위치 권한 거부: 저장된 위치 기준
        fetch('/api/construction/notices').then(function(r){return r.json();}).then(function(d){
            render(d.notices, d.town, d.village);
        }).catch(function(){ render([], '', ''); });
    }, { enableHighAccuracy: true, timeout: 10000 });
}
