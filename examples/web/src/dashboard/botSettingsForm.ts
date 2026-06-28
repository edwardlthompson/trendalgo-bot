import type { BotDetailData, BotEquityLimits, TaLibraryCategory } from "../api/client";
import { createSearchablePicker, type PickerItem } from "../components/SearchablePicker";
import { buildFallbackTaLibrary } from "../data/taLibraryFallback";
import { taGlossaryEntry } from "../data/taGlossary";
import { timeframeLabel, normalizeTimeframe } from "../components/tradingViewIntervals";
import { coinIconUrl, loadCoinIcons, type CoinIconMeta } from "../icons/iconRegistry";
import { saveBotSettings, type PersistedBotSettings } from "../settings/settingsStore";
import { isSubMinute } from "../bots/botGuardrails";
import { formatGuardrailIssue } from "../bots/botLimitsBanner";
import { checkGuardrailAction } from "../bots/botGuardrails";
import { t } from "../i18n";
import type { BotUpdatePayload } from "./BotDetailPage";
import { createBotEquityField, normalizeEquityMode, updateEquityLimits } from "./botEquityField";

export type BotSettingsContext = {
  botId: number;
  exchanges: Array<{ id: string; name: string }>;
  taLibrary: TaLibraryCategory[];
  exchangePairs: string[];
  equityLimits: BotEquityLimits;
  botEnabled?: boolean;
  guardrailBots?: import("../bots/botGuardrails").BotLike[];
  botLimits?: import("../bots/botGuardrails").BotLimits;
  onExchangeChange: (exchangeId: string, applyPairs: (pairs: string[]) => void) => void;
  onPairChange?: (pair: string) => void;
  onOpenGlossary?: () => void;
};

const DEFAULT_EXCHANGES: Array<{ id: string; name: string }> = [
  { id: "kraken", name: "Kraken" },
  { id: "coinbase", name: "Coinbase" },
  { id: "binanceus", name: "Binance.US" },
  { id: "gemini", name: "Gemini" },
];

const PAPER_LIMITS: BotEquityLimits = {
  base: { symbol: "BTC", max: 10 },
  quote: { symbol: "USD", max: 50_000 },
  portfolio_usd: 100_000,
  paper: true,
};

function taItems(categories: TaLibraryCategory[], currentId: string): PickerItem[] {
  const lib = categories.length ? categories : buildFallbackTaLibrary();
  const out: PickerItem[] = [];
  for (const cat of lib) {
    for (const item of cat.items) {
      const gloss = taGlossaryEntry(item.id);
      out.push({
        id: item.id,
        label: gloss.title,
        category: cat.name,
        tooltipTitle: gloss.title,
        tooltipText: gloss.category ? `${gloss.category} — ${gloss.short}` : gloss.short,
      });
    }
  }
  if (currentId && !out.some((i) => i.id === currentId)) {
    const gloss = taGlossaryEntry(currentId);
    out.unshift({
      id: currentId,
      label: gloss.title,
      category: t("picker.current"),
      tooltipTitle: gloss.title,
      tooltipText: gloss.short,
    });
  }
  return out;
}

function pairItems(pairs: string[], iconMap: Map<string, CoinIconMeta>): PickerItem[] {
  return pairs.map((p) => {
    const base = p.split("/")[0]?.toUpperCase() ?? p;
    return {
      id: p,
      label: p,
      iconUrl: coinIconUrl(iconMap, base),
    };
  });
}

export function createBotSettingsForm(
  detail: BotDetailData,
  ctx: BotSettingsContext,
  onSave: (payload: BotUpdatePayload) => void,
): { form: HTMLFormElement; cleanup: () => void; setEquityLimits: (next: BotEquityLimits) => void } {
  const bot = detail.bot;
  const form = document.createElement("form");
  form.className = "gp-bot-detail-settings";
  form.dataset.testid = "bot-detail-settings";
  const cleanups: Array<() => void> = [];
  let limits = detail.equity_limits ?? ctx.equityLimits ?? PAPER_LIMITS;
  let coinRegistry = new Map<string, CoinIconMeta>();

  const title = document.createElement("h3");
  title.className = "gp-panel-subtitle";
  title.textContent = t("bots.detail.settings");
  form.appendChild(title);

  const labelInput = document.createElement("label");
  labelInput.innerHTML = `${t("bots.field.label")}<input name="label" value="${bot.label}" required />`;
  form.appendChild(labelInput);

  const equityField = createBotEquityField(
    normalizeEquityMode(String(bot.equity_mode)),
    Number(bot.equity_input ?? bot.equity_usd),
    limits,
  );
  form.appendChild(equityField.root);

  const exchanges = ctx.exchanges.length ? ctx.exchanges : DEFAULT_EXCHANGES;
  let selectedExchange = String(bot.exchange ?? "kraken");

  let exchangePicker!: ReturnType<typeof createSearchablePicker>;
  let strategyPicker!: ReturnType<typeof createSearchablePicker>;
  let pairPicker!: ReturnType<typeof createSearchablePicker>;
  let tfPicker!: ReturnType<typeof createSearchablePicker>;

  function collectPayload(): BotUpdatePayload {
    const fd = new FormData(form);
    const equityMode = equityField.getMode();
    const equityInput = equityField.getValue();
    return {
      label: String(fd.get("label") ?? bot.label),
      strategy_id: strategyPicker.getValue(),
      pair: pairPicker.getValue(),
      exchange: exchangePicker.getValue(),
      equity_usd: equityInput,
      equity_mode: equityMode,
      equity_input: equityInput,
      timeframe: tfPicker.getValue(),
      ta_params: { ...detail.strategy_params },
    };
  }

  function persistDraft(): void {
    const payload = collectPayload();
    const stored: PersistedBotSettings = {
      label: payload.label,
      strategy_id: payload.strategy_id,
      pair: payload.pair,
      exchange: payload.exchange,
      timeframe: payload.timeframe,
      equity_mode: payload.equity_mode,
      equity_input: payload.equity_input,
      ta_params: payload.ta_params,
    };
    saveBotSettings(ctx.botId, stored);
  }

  void loadCoinIcons().then((registry) => {
    coinRegistry = registry;
    pairPicker.setItems(pairItems(ctx.exchangePairs, coinRegistry));
  });

  exchangePicker = createSearchablePicker({
    testId: "bot-exchange-picker",
    label: t("bots.field.exchange"),
    value: selectedExchange,
    items: exchanges.map((e) => ({ id: e.id, label: e.name })),
    favoriteKey: "exchanges",
    onChange: (id) => {
      selectedExchange = id;
      persistDraft();
      ctx.onExchangeChange(id, (pairs) => {
        pairPicker.setItems(pairItems(pairs, coinRegistry));
        if (!pairs.includes(pairPicker.getValue()) && pairs.length) {
          pairPicker.setValue(pairs[0]!);
        }
        persistDraft();
      });
    },
  });
  cleanups.push(exchangePicker.cleanup);
  form.insertBefore(exchangePicker.root, equityField.root);

  strategyPicker = createSearchablePicker({
    testId: "bot-strategy-picker",
    label: t("dashboard.strategy"),
    value: bot.strategy_id,
    items: taItems(ctx.taLibrary, bot.strategy_id),
    favoriteKey: "ta-strategies",
    categorized: true,
    labelAction: ctx.onOpenGlossary
      ? { text: t("bots.glossary.open"), onClick: ctx.onOpenGlossary }
      : undefined,
    onChange: () => persistDraft(),
  });
  cleanups.push(strategyPicker.cleanup);
  form.insertBefore(strategyPicker.root, equityField.root);

  pairPicker = createSearchablePicker({
    testId: "bot-pair-picker",
    label: t("dashboard.pair"),
    value: bot.pair,
    items: pairItems(ctx.exchangePairs, coinRegistry),
    favoriteKey: `pairs-${selectedExchange}`,
    onChange: () => {
      persistDraft();
      ctx.onPairChange?.(pairPicker.getValue());
    },
  });
  cleanups.push(pairPicker.cleanup);
  form.insertBefore(pairPicker.root, equityField.root);

  const tfWarn = document.createElement("p");
  tfWarn.className = "gp-bot-tf-warn";
  tfWarn.dataset.testid = "bot-tf-warn";
  tfWarn.hidden = !isSubMinute(normalizeTimeframe(String(bot.timeframe ?? "60")));
  tfWarn.textContent = t("bots.templates.sub_minute_warn");

  tfPicker = createSearchablePicker({
    testId: "bot-timeframe-picker",
    label: t("bots.field.timeframe"),
    value: normalizeTimeframe(String(bot.timeframe ?? "60")),
    items: detail.available_timeframes.map((id) => ({
      id,
      label: detail.timeframe_labels?.[id] ?? timeframeLabel(id),
    })),
    favoriteKey: "timeframes",
    preserveOrder: true,
    onChange: () => {
      tfWarn.hidden = !isSubMinute(tfPicker.getValue());
      persistDraft();
    },
  });
  cleanups.push(tfPicker.cleanup);
  form.insertBefore(tfPicker.root, equityField.root);
  form.insertBefore(tfWarn, equityField.root);

  labelInput.querySelector("input")?.addEventListener("change", () => persistDraft());
  equityField.root.querySelector("[name=equity_mode]")?.addEventListener("change", () => persistDraft());
  equityField.root.querySelector("[name=equity_input]")?.addEventListener("change", () => persistDraft());

  const saveBtn = document.createElement("button");
  saveBtn.type = "submit";
  saveBtn.className = "gp-btn-primary";
  saveBtn.textContent = t("bots.action.save");
  form.appendChild(saveBtn);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    persistDraft();
    const payload = collectPayload();
    if (ctx.botEnabled && ctx.botLimits && ctx.guardrailBots) {
      const blocked = checkGuardrailAction(ctx.botLimits, ctx.guardrailBots, {
        enabling: true,
        timeframe: payload.timeframe,
        botId: ctx.botId,
      });
      if (blocked) {
        tfWarn.hidden = false;
        tfWarn.textContent = formatGuardrailIssue(blocked);
        return;
      }
    }
    onSave(payload);
  });

  return {
    form,
    cleanup: () => cleanups.forEach((fn) => fn()),
    setEquityLimits: (next: BotEquityLimits) => {
      limits = next;
      updateEquityLimits(equityField, next);
    },
  };
}
