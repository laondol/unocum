// auto-split from schedule2.html (modularization, behavior preserved)
let calYear, calMonth, schedules = [], friends = [], selDate = null;
function scheduleType(s){ if (s.title && (s.title.includes('이동') || s.title.includes('집으'))) return 'move'; return 'mail'; }
function typeChip(s){ return scheduleType(s)==='move' ? '<span class="chip chip-move">🚌 이동</span> ' : '<span class="chip chip-mail">✉ 메일</span> '; }
let repeatOn = false, addCalMode = 'start', addCalYear, addCalMonth;

fetch('/api/chat/friends').then(r=>r.json()).then(d => {
    friends = d.friends || [];
    renderFriendCheckboxes();
});

function renderFriendCheckboxes() {
    var box = document.getElementById('friendCheckboxes');
    if (!friends.length) { box.innerHTML = '<div class="text-muted">벗이 없습니다</div>'; return; }
    box.innerHTML = friends.map(function(f){
        var name = f.username || f.name || f;
        return '<label class="d-block"><input type="checkbox" class="friend-cb" value="'+f.id+'"> '+name+'</label>';
    }).join('');
}
