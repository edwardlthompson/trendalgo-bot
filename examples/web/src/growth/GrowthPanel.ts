import { t } from "../i18n";

export function createGrowthPanel(
  referralCode: string,
  leaderboard: Array<{ pseudonym: string; score_usd: number }> | null,
  onOptIn: () => void,
  onBoost: () => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "growth-panel";
  section.innerHTML = `
    <h3>${t("growth.title")}</h3>
    <p data-testid="referral-code">${t("growth.referral")}: <code>${referralCode || t("empty.growth_code")}</code></p>
  `;
  const optIn = document.createElement("button");
  optIn.type = "button";
  optIn.className = "gp-btn-secondary";
  optIn.dataset.testid = "leaderboard-opt-in";
  optIn.textContent = t("growth.opt_in");
  optIn.addEventListener("click", onOptIn);
  const boost = document.createElement("button");
  boost.type = "button";
  boost.className = "gp-btn-secondary";
  boost.dataset.testid = "boost-mode";
  boost.textContent = t("growth.boost");
  boost.addEventListener("click", onBoost);
  section.append(optIn, boost);
  const list = document.createElement("ul");
  list.dataset.testid = "leaderboard-list";
  if (!leaderboard?.length) {
    const empty = document.createElement("p");
    empty.className = "gp-empty";
    empty.dataset.testid = "growth-leaderboard-empty";
    empty.textContent = t("empty.growth_leaderboard");
    section.appendChild(empty);
  } else {
    for (const row of leaderboard) {
      const li = document.createElement("li");
      li.textContent = `${row.pseudonym}: $${row.score_usd.toFixed(2)}`;
      list.appendChild(li);
    }
    section.appendChild(list);
  }
  return section;
}
