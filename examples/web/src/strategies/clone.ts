/** Clone strategy params from library run (T33). */
export function cloneParamsFromRun(
  params: Record<string, number>,
  tweak: Partial<Record<string, number>> = {},
): Record<string, number> {
  const out = { ...params };
  for (const [key, value] of Object.entries(tweak)) {
    if (value !== undefined) out[key] = value;
  }
  return out;
}
