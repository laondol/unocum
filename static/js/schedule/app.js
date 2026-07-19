// auto-split from schedule2.html (modularization, behavior preserved)
fetch('/api/chat/friends').then(r=>r.json()).then(d => {
    friends = d.friends || [];
    renderFriendCheckboxes();
});
loadEvents();
renderCal();

if(document.getElementById('memoEditor')){ document.getElementById('memoEditor').addEventListener('keyup', saveRange); document.getElementById('memoEditor').addEventListener('mouseup', saveRange); }
startReminderPoll();
