import { appendLinkifiedText, glossaryAnchorId } from "../data/glossaryLinkify";
import { taGlossaryEntry, type TaGlossaryEntry } from "../data/taGlossary";
import { t } from "../i18n";

export function glossaryTextBlock(
  className: string,
  text: string,
  navigateToEntry: (entryId: string) => void,
): HTMLElement {
  const block = document.createElement("p");
  block.className = className;
  appendLinkifiedText(block, text, navigateToEntry);
  return block;
}

export function glossaryRelatedBlock(
  entry: TaGlossaryEntry,
  navigateToEntry: (entryId: string) => void,
): HTMLElement | null {
  const related = entry.related?.filter(Boolean) ?? [];
  if (!related.length) return null;

  const block = document.createElement("p");
  block.className = "gp-ta-glossary-related";
  const label = document.createElement("strong");
  label.textContent = t("bots.glossary.see_also");
  block.append(label, " ");
  related.forEach((id: string, idx: number) => {
    if (idx > 0) block.append(", ");
    const link = document.createElement("a");
    link.href = `#${glossaryAnchorId(id)}`;
    link.className = "gp-ta-glossary-link";
    link.dataset.glossaryTarget = id.toUpperCase();
    link.textContent = taGlossaryEntry(id).title;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      navigateToEntry(id);
    });
    block.appendChild(link);
  });
  return block;
}

export function renderGlossaryCard(
  entry: TaGlossaryEntry,
  navigateToEntry: (entryId: string) => void,
  setCategory: (category: string) => void,
): HTMLElement {
  const card = document.createElement("article");
  card.className = "gp-ta-glossary-card";
  card.id = glossaryAnchorId(entry.id);
  card.dataset.testid = `ta-glossary-${entry.id}`;

  const heading = document.createElement("h3");
  const permalink = document.createElement("a");
  permalink.href = `#${glossaryAnchorId(entry.id)}`;
  permalink.className = "gp-ta-glossary-permalink";
  permalink.title = t("bots.glossary.permalink");
  permalink.setAttribute("aria-label", t("bots.glossary.permalink"));
  permalink.textContent = "#";
  permalink.addEventListener("click", (event) => {
    event.preventDefault();
    navigateToEntry(entry.id);
  });
  heading.append(permalink, document.createTextNode(` ${entry.title} `));
  const idSpan = document.createElement("span");
  idSpan.className = "gp-ta-glossary-id";
  idSpan.textContent = entry.id;
  heading.appendChild(idSpan);

  const category = document.createElement("p");
  category.className = "gp-ta-glossary-category";
  const badge = document.createElement("button");
  badge.type = "button";
  badge.className = "gp-ta-glossary-category-badge";
  badge.textContent = entry.category ?? t("bots.glossary.category_unknown");
  badge.addEventListener("click", () => {
    const cat = entry.category ?? t("bots.glossary.category_unknown");
    setCategory(cat);
  });
  category.appendChild(badge);

  const formula = document.createElement("p");
  formula.className = "gp-ta-glossary-formula";
  const formulaLabel = document.createElement("strong");
  formulaLabel.textContent = t("bots.glossary.formula");
  formula.append(formulaLabel, " ", entry.formula);

  card.append(
    heading,
    category,
    glossaryTextBlock("gp-ta-glossary-short", entry.short, navigateToEntry),
    glossaryTextBlock("gp-ta-glossary-long", entry.long, navigateToEntry),
    formula,
  );
  const related = glossaryRelatedBlock(entry, navigateToEntry);
  if (related) card.appendChild(related);
  return card;
}
