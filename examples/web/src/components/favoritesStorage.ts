const PREFIX = "trendalgo.favorites.";

export function loadFavorites(key: string): string[] {
  try {
    const raw = localStorage.getItem(`${PREFIX}${key}`);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === "string") : [];
  } catch {
    return [];
  }
}

export function saveFavorites(key: string, ids: string[]): void {
  localStorage.setItem(`${PREFIX}${key}`, JSON.stringify(ids));
}

export function toggleFavorite(key: string, id: string): string[] {
  const current = loadFavorites(key);
  const next = current.includes(id) ? current.filter((v) => v !== id) : [...current, id];
  saveFavorites(key, next);
  return next;
}
