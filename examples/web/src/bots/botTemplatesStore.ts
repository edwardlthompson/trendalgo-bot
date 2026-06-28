import type { PersistedBotSettings } from "../settings/settingsStore";

const KEY = "trendalgo.bot-templates.v1";
const MAX_TEMPLATES = 200;

export type BotTemplate = PersistedBotSettings & {
  id: string;
  name: string;
  saved_at: string;
  source_bot_id?: number;
};

type TemplateRoot = {
  templates: BotTemplate[];
};

function readRoot(): TemplateRoot {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { templates: [] };
    const parsed = JSON.parse(raw) as TemplateRoot;
    return { templates: parsed.templates ?? [] };
  } catch {
    return { templates: [] };
  }
}

function writeRoot(root: TemplateRoot): void {
  localStorage.setItem(KEY, JSON.stringify(root));
}

export function listBotTemplates(): BotTemplate[] {
  return readRoot().templates.sort((a, b) => b.saved_at.localeCompare(a.saved_at));
}

export function saveBotTemplate(
  name: string,
  settings: PersistedBotSettings,
  sourceBotId?: number,
): BotTemplate {
  const root = readRoot();
  if (root.templates.length >= MAX_TEMPLATES) {
    throw new Error(`Template limit reached (${MAX_TEMPLATES}). Delete old templates first.`);
  }
  const entry: BotTemplate = {
    ...settings,
    id: crypto.randomUUID(),
    name: name.trim() || settings.label,
    saved_at: new Date().toISOString(),
    source_bot_id: sourceBotId,
  };
  root.templates.unshift(entry);
  writeRoot(root);
  return entry;
}

export function deleteBotTemplate(id: string): void {
  const root = readRoot();
  root.templates = root.templates.filter((t) => t.id !== id);
  writeRoot(root);
}

export function getBotTemplate(id: string): BotTemplate | null {
  return readRoot().templates.find((t) => t.id === id) ?? null;
}

export function templateToNewBotPayload(
  template: BotTemplate,
  label: string,
): {
  label: string;
  strategy_id: string;
  pair: string;
  exchange: string;
  timeframe: string;
  equity_usd: number;
  enabled: boolean;
  ta_params: Record<string, number>;
} {
  return {
    label,
    strategy_id: template.strategy_id,
    pair: template.pair,
    exchange: template.exchange,
    timeframe: template.timeframe,
    equity_usd: template.equity_mode === "quote" ? template.equity_input : 1000,
    enabled: false,
    ta_params: { ...template.ta_params },
  };
}
