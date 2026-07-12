/** Web Push is not configured — preference exists for future VAPID wiring. */

export async function registerPushNotifications(): Promise<boolean> {
  // Scope: demote stub — do not subscribe without applicationServerKey.
  return false;
}
