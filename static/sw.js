// service worker for web push
self.addEventListener('push', function(event) {
  var data = {title: '알림', body: '', url: '/schedule'};
  try { if (event.data) data = Object.assign(data, event.data.json()); } catch (e) {}
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      data: { url: data.url }
    })
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  var target = (event.notification.data && event.notification.data.url) || '/schedule';
  event.waitUntil(
    clients.matchAll({type: 'window', includeUncontrolled: true}).then(function(win){
      for (var i = 0; i < win.length; i++) {
        if ('focus' in win[i]) { win[i].focus(); win[i].navigate(target); return; }
      }
      if (clients.openWindow) return clients.openWindow(target);
    })
  );
});
