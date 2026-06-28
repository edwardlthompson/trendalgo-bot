import type { OhlcvWarmupJob } from "../api/client";
import { bindPanelDialog } from "../panelDialog";
import { t } from "../i18n";

function formatMsg(key: string, vars?: Record<string, string>): string {
  let text = t(key);
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replaceAll(`{${k}}`, v);
    }
  }
  return text;
}

export type OhlcvWarmupDialogHandle = {
  update: (job: OhlcvWarmupJob) => void;
  close: () => void;
};

export function createOhlcvWarmupDialog(): OhlcvWarmupDialogHandle {
  const dialog = document.createElement("dialog");
  dialog.className = "gp-ohlcv-warmup-dialog";
  dialog.dataset.testid = "ohlcv-warmup-dialog";

  const panel = document.createElement("div");
  panel.className = "gp-ohlcv-warmup-panel";

  const title = document.createElement("h2");
  title.className = "gp-panel-title";
  title.textContent = t("ohlcv.warmup.title");

  const intro = document.createElement("p");
  intro.className = "gp-ohlcv-warmup-intro";
  intro.dataset.testid = "ohlcv-warmup-intro";
  intro.textContent = t("ohlcv.warmup.intro");

  const track = document.createElement("div");
  track.className = "gp-ohlcv-warmup-track";
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "100");
  track.setAttribute("aria-valuenow", "0");
  track.dataset.testid = "ohlcv-warmup-progress-track";

  const fill = document.createElement("div");
  fill.className = "gp-ohlcv-warmup-fill";
  fill.dataset.testid = "ohlcv-warmup-progress-fill";
  track.appendChild(fill);

  const stats = document.createElement("p");
  stats.className = "gp-ohlcv-warmup-stats";
  stats.dataset.testid = "ohlcv-warmup-stats";

  const current = document.createElement("p");
  current.className = "gp-ohlcv-warmup-current";
  current.dataset.testid = "ohlcv-warmup-current";

  const log = document.createElement("div");
  log.className = "gp-ohlcv-warmup-log";
  log.dataset.testid = "ohlcv-warmup-log";

  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "gp-btn-secondary";
  closeBtn.dataset.testid = "ohlcv-warmup-close";
  closeBtn.textContent = t("ohlcv.warmup.close");
  closeBtn.disabled = true;

  panel.append(title, intro, track, stats, current, log, closeBtn);
  dialog.appendChild(panel);
  document.body.appendChild(dialog);

  let unbind = (): void => {};
  const close = (): void => {
    unbind();
    if (dialog.open) dialog.close();
  };

  closeBtn.addEventListener("click", close);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog && !closeBtn.disabled) close();
  });

  if (typeof dialog.showModal === "function") {
    dialog.showModal();
    unbind = bindPanelDialog(panel, close);
  }

  function update(job: OhlcvWarmupJob): void {
    const pct = job.progress_pct ?? 0;
    fill.style.width = `${pct}%`;
    track.setAttribute("aria-valuenow", String(pct));
    track.setAttribute("aria-label", formatMsg("ohlcv.warmup.progress_aria", { pct: String(pct) }));

    stats.textContent = formatMsg("ohlcv.warmup.stats", {
      series: String(job.completed_series ?? 0),
      total: String(job.total_series ?? 0),
      cached: String(job.bars_cached ?? 0),
      downloaded: String(job.bars_downloaded ?? 0),
    });

    if (job.current_series) {
      current.textContent = formatMsg("ohlcv.warmup.current", { label: job.current_series });
      current.hidden = false;
    } else {
      current.hidden = true;
    }

    log.innerHTML = "";
    for (const line of job.messages ?? []) {
      const row = document.createElement("p");
      row.textContent = line;
      log.appendChild(row);
    }
    log.scrollTop = log.scrollHeight;

    const done = job.status === "complete" || job.status === "error" || job.status === "idle";
    closeBtn.disabled = !done;
    if (job.status === "complete") {
      title.textContent = t("ohlcv.warmup.done_title");
      intro.textContent = t("ohlcv.warmup.done_intro");
    }
    if (job.status === "error") {
      title.textContent = t("ohlcv.warmup.error_title");
      intro.textContent = job.error ?? t("ohlcv.warmup.error_intro");
    }
  }

  return { update, close };
}
