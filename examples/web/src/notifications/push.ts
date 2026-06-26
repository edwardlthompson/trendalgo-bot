/** PWA Web Push registration stub (Sprint 4). */

export async function registerPushNotifications(): Promise<boolean> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    return false;
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return false;
  }
  const registration = await navigator.serviceWorker.ready;
  await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: undefined,
  });
  return true;
}
