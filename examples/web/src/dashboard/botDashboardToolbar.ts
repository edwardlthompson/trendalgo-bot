import type { BotTemplate } from "../bots/botTemplatesStore";
import type { BotLimits, BotLike } from "../bots/botGuardrails";
import { canAddBot } from "../bots/botGuardrails";
import { createBotLimitsBanner, formatGuardrailIssue } from "../bots/botLimitsBanner";
import { t } from "../i18n";

export type BotDashboardToolbarCallbacks = {
  onCreateBot: () => void;
  onApplyTemplate: (templateId: string) => void;
  onDeleteTemplate: (templateId: string) => void;
};

export function createBotDashboardToolbar(
  templates: BotTemplate[],
  limits: BotLimits,
  bots: BotLike[],
  callbacks: BotDashboardToolbarCallbacks,
): HTMLElement {
  const bar = document.createElement("div");
  bar.className = "gp-bot-dashboard-toolbar";
  bar.dataset.testid = "bot-dashboard-toolbar";

  bar.appendChild(createBotLimitsBanner(limits, bots).root);

  const addBlocked = canAddBot(limits, bots);
  const newBtn = document.createElement("button");
  newBtn.type = "button";
  newBtn.className = "gp-btn-primary";
  newBtn.dataset.testid = "bot-create-new";
  newBtn.textContent = t("bots.create_new");
  if (addBlocked) {
    newBtn.disabled = true;
    newBtn.title = formatGuardrailIssue(addBlocked);
  }
  newBtn.addEventListener("click", () => callbacks.onCreateBot());

  const templateWrap = document.createElement("div");
  templateWrap.className = "gp-bot-template-row";
  const templateLabel = document.createElement("label");
  templateLabel.className = "gp-bot-template-label";
  templateLabel.textContent = t("bots.templates.from_template");
  const select = document.createElement("select");
  select.className = "gp-bot-template-select";
  select.dataset.testid = "bot-template-select";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = t("bots.templates.none");
  select.append(empty);
  for (const tpl of templates) {
    const opt = document.createElement("option");
    opt.value = tpl.id;
    opt.textContent = `${tpl.name} · ${tpl.strategy_id} · ${tpl.pair}`;
    select.appendChild(opt);
  }
  const applyBtn = document.createElement("button");
  applyBtn.type = "button";
  applyBtn.className = "gp-btn-secondary";
  applyBtn.dataset.testid = "bot-template-apply";
  applyBtn.textContent = t("bots.templates.apply");
  applyBtn.disabled = templates.length === 0 || Boolean(addBlocked);
  if (addBlocked) applyBtn.title = formatGuardrailIssue(addBlocked);
  applyBtn.addEventListener("click", () => {
    const id = select.value;
    if (id) callbacks.onApplyTemplate(id);
  });
  templateLabel.append(select);
  templateWrap.append(templateLabel, applyBtn);

  if (templates.length) {
    const manage = document.createElement("details");
    manage.className = "gp-bot-template-manage";
    manage.innerHTML = `<summary>${t("bots.templates.manage")}</summary>`;
    const list = document.createElement("ul");
    list.className = "gp-template-list";
    for (const tpl of templates) {
      const li = document.createElement("li");
      li.textContent = `${tpl.name} — ${tpl.strategy_id} @ ${tpl.timeframe}`;
      const del = document.createElement("button");
      del.type = "button";
      del.className = "gp-btn-secondary";
      del.textContent = t("bots.templates.delete");
      del.addEventListener("click", () => callbacks.onDeleteTemplate(tpl.id));
      li.append(del);
      list.appendChild(li);
    }
    manage.appendChild(list);
    templateWrap.appendChild(manage);
  }

  bar.append(newBtn, templateWrap);
  return bar;
}
