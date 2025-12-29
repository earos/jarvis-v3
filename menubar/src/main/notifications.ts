import { Notification } from 'electron';

export function showNotification(title: string, body: string, severity: string = 'info') {
  // Check if notifications are supported
  if (!Notification.isSupported()) {
    console.warn('[Notifications] Not supported on this platform');
    return;
  }
  
  const notification = new Notification({
    title,
    body,
    icon: getIconForSeverity(severity),
    sound: severity === 'warning' ? 'Basso' : undefined,
    urgency: severity === 'warning' ? 'critical' : 'normal'
  });
  
  notification.on('click', () => {
    console.log('[Notification] Clicked:', title);
    // TODO: Handle notification click (e.g., show relevant window)
  });
  
  notification.show();
}

function getIconForSeverity(severity: string): string | undefined {
  // You can return different icon paths based on severity
  // For now, return undefined to use default
  return undefined;
}

export function requestNotificationPermission() {
  // macOS will automatically prompt for permission
  // on first notification
  console.log('[Notifications] Permission will be requested on first use');
}
