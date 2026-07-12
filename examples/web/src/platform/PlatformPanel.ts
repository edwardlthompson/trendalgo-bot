import { t } from "../i18n";

export type PlatformData = {
  forager: { pair_count: number; pairs: Array<Record<string, unknown>> };
  funding: { rows: Array<Record<string, unknown>> };
  postgres: Record<string, unknown>;
  onchainPreview?: Record<string, unknown>;
};

export function createPlatformPanel(data: PlatformData | null): HTMLElement {
  const panel = document.createElement("section");
  panel.className = "gp-panel gp-platform-panel";
  panel.dataset.testid = "platform-panel";
  panel.innerHTML = `<h3>${t("platform.title")}</h3>`;

  if (!data) {
    panel.innerHTML += `<p>${t("platform.loading")}</p>`;
    return panel;
  }

  const forager = document.createElement("div");
  forager.innerHTML = `<h4>${t("platform.forager")}</h4>`;
  const foragerList = document.createElement("ul");
  for (const row of data.forager.pairs.slice(0, 5)) {
    const li = document.createElement("li");
    li.textContent = `${row.pair as string} · score ${row.forager_score as number}`;
    foragerList.appendChild(li);
  }
  forager.appendChild(foragerList);

  const funding = document.createElement("div");
  funding.innerHTML = `<h4>${t("platform.funding")}</h4>`;
  const fundingList = document.createElement("ul");
  for (const row of data.funding.rows) {
    const li = document.createElement("li");
    li.textContent = `${row.pair as string}: ${row.funding_rate_pct as number}%`;
    fundingList.appendChild(li);
  }
  funding.appendChild(fundingList);

  const pg = document.createElement("p");
  pg.className = "gp-muted";
  pg.dataset.testid = "platform-postgres";
  if (data.postgres.experimental || data.postgres.status_note === "experimental") {
    pg.textContent = `${t("platform.postgres")}: ${t("platform.postgres_experimental")}`;
  } else {
    pg.textContent = `${t("platform.postgres")}: ${data.postgres.dual_write_enabled ? "dual-write" : "sqlite-mvp"}`;
  }

  panel.append(forager, funding, pg);
  return panel;
}
