/** Clone strategy params from library run (T33). */
export function cloneParamsFromRun(
  params: Record<string, number>,
  tweak: Partial<Record<string, number>> = {},
): Record<string, number> {
  return { ...params, ...tweak };
}
