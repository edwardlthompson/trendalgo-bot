/** Full-page searchable TA strategy glossary. */

import { appendLinkifiedText, glossaryAnchorId, parseGlossaryHash } from "../data/glossaryLinkify";
import {
  allTaGlossaryEntries,
  glossaryCategoriesWithCounts,
  taGlossaryEntry,
  type TaGlossaryEntry,
} from "../data/taGlossary";
import { t } from "../i18n";

const HIGHLIGHT_MS = 2200;

export function createTaGlossaryPage(
  onBack: () => void,
  focusEntryId?: string | null,
): { root: HTMLElement; cleanup: () => void } {
  const root = document.createElement("section");
  root.className = "gp-panel gp-ta-glossary-page";
  root.dataset.testid = "ta-glossary-page";

  const header = document.createElement("header");
  header.className = "gp-ta-glossary-page-header";

  const back = document.createElement("button");
  back.type = "button";
  back.className = "gp-btn-secondary";
  back.dataset.testid = "ta-glossary-back";
  back.textContent = t("bots.glossary.back");
  back.addEventListener("click", onBack);

  const title = document.createElement("h2");
  title.className = "gp-panel-title";
  title.textContent = t("bots.glossary.page_title");

  const intro = document.createElement("p");
  intro.className = "gp-ta-glossary-page-intro";
  intro.textContent = t("bots.glossary.page_intro");

  header.append(back, title, intro);

  const search = document.createElement("input");
  search.type = "search";
  search.className = "gp-ta-glossary-search";
  search.placeholder = t("bots.glossary.search");
  search.dataset.testid = "ta-glossary-page-search";

  const categoryNav = document.createElement("nav");
  categoryNav.className = "gp-ta-glossary-category-nav";
  categoryNav.dataset.testid = "ta-glossary-category-nav";
  categoryNav.setAttribute("aria-label", t("bots.glossary.categories_label"));

  const meta = document.createElement("p");
  meta.className = "gp-ta-glossary-page-meta";
  meta.dataset.testid = "ta-glossary-count";

  const list = document.createElement("div");
  list.className = "gp-ta-glossary-list gp-ta-glossary-page-list";

  let pendingTarget: string | null =
    focusEntryId?.toUpperCase() ?? parseGlossaryHash(window.location.hash);
  let selectedCategory: string | null = null;
  let singleEntryFilter: string | null = pendingTarget;
  let highlightTimer: ReturnType<typeof setTimeout> | undefined;

  const clearFilterBtn = document.createElement("button");
  clearFilterBtn.type = "button";
  clearFilterBtn.className = "gp-btn-secondary gp-ta-glossary-clear-filter";
  clearFilterBtn.dataset.testid = "ta-glossary-show-all";
  clearFilterBtn.textContent = t("bots.glossary.show_all");
  clearFilterBtn.hidden = true;
  clearFilterBtn.addEventListener("click", () => {
    singleEntryFilter = null;
    pendingTarget = null;
    search.value = "";
    selectedCategory = null;
    history.replaceState(null, "", window.location.pathname + window.location.search);
    renderCategoryNav();
    render();
  });

  function clearHighlight(): void {
    list.querySelectorAll(".gp-ta-glossary-card-highlight").forEach((el) => {
      el.classList.remove("gp-ta-glossary-card-highlight");
    });
    if (highlightTimer) clearTimeout(highlightTimer);
    highlightTimer = undefined;
  }

  function highlightCard(card: HTMLElement): void {
    clearHighlight();
    card.classList.add("gp-ta-glossary-card-highlight");
    highlightTimer = setTimeout(() => card.classList.remove("gp-ta-glossary-card-highlight"), HIGHLIGHT_MS);
  }

  function setCategory(category: string | null): void {
    singleEntryFilter = null;
    pendingTarget = null;
    selectedCategory = category;
    renderCategoryNav();
    render();
    list.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderCategoryNav(): void {
    categoryNav.innerHTML = "";
    const total = allTaGlossaryEntries().length;

    function addChip(label: string, category: string | null, count: number, testId: string): void {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "gp-ta-glossary-category-chip";
      btn.dataset.testid = testId;
      btn.dataset.category = category ?? "";
      btn.setAttribute("aria-pressed", String(selectedCategory === category));
      if (selectedCategory === category) btn.classList.add("gp-ta-glossary-category-chip-active");
      btn.textContent = t("bots.glossary.category_chip").replace("{label}", label).replace("{count}", String(count));
      btn.addEventListener("click", () => setCategory(category));
      categoryNav.appendChild(btn);
    }

    addChip(t("bots.glossary.all_categories"), null, total, "ta-glossary-category-all");
    for (const row of glossaryCategoriesWithCounts()) {
      const slug = row.category.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      addChip(row.category, row.category, row.count, `ta-glossary-category-${slug}`);
    }
  }

  function navigateToEntry(entryId: string, opts?: { updateHash?: boolean; scroll?: boolean }): void {
    const id = entryId.toUpperCase();
    const updateHash = opts?.updateHash ?? true;
    const scroll = opts?.scroll ?? true;

    singleEntryFilter = id;
    search.value = id;
    selectedCategory = null;
    pendingTarget = id;
    clearFilterBtn.hidden = false;
    renderCategoryNav();
    render();

    if (updateHash) {
      const anchor = `#${glossaryAnchorId(id)}`;
      if (window.location.hash !== anchor) {
        history.replaceState(null, "", anchor);
      }
    }

    if (!scroll) return;
    requestAnimationFrame(() => {
      const card = list.querySelector<HTMLElement>(`#${glossaryAnchorId(id)}`);
      if (!card) return;
      card.scrollIntoView({ behavior: "smooth", block: "start" });
      highlightCard(card);
      pendingTarget = null;
    });
  }

  function textBlock(className: string, text: string): HTMLElement {
    const block = document.createElement("p");
    block.className = className;
    appendLinkifiedText(block, text, navigateToEntry);
    return block;
  }

  function relatedBlock(entry: TaGlossaryEntry): HTMLElement | null {
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

  function renderCard(entry: TaGlossaryEntry): HTMLElement {
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
      textBlock("gp-ta-glossary-short", entry.short),
      textBlock("gp-ta-glossary-long", entry.long),
      formula,
    );
    const related = relatedBlock(entry);
    if (related) card.appendChild(related);
    return card;
  }

  function matchesSearch(entry: TaGlossaryEntry, q: string): boolean {
    if (!q) return true;
    const relatedText = (entry.related ?? []).map((id: string) => taGlossaryEntry(id).title).join(" ");
    const haystack = [entry.id, entry.title, entry.short, entry.long, entry.formula, entry.category ?? "", relatedText]
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  }

  function matchesCategory(entry: TaGlossaryEntry): boolean {
    if (!selectedCategory) return true;
    const cat = entry.category ?? t("bots.glossary.category_unknown");
    return cat === selectedCategory;
  }

  function render(): void {
    const q = search.value.trim().toLowerCase();
    const target = pendingTarget?.toUpperCase() ?? singleEntryFilter;
    clearFilterBtn.hidden = !singleEntryFilter;

    let entries: TaGlossaryEntry[];
    if (singleEntryFilter) {
      entries = allTaGlossaryEntries().filter(
        (e: TaGlossaryEntry) => e.id.toUpperCase() === singleEntryFilter,
      );
    } else {
      entries = allTaGlossaryEntries().filter(
        (e: TaGlossaryEntry) => matchesCategory(e) && matchesSearch(e, q),
      );
    }

    if (singleEntryFilter && entries.length) {
      meta.textContent = t("bots.glossary.single_entry").replace("{id}", entries[0]!.id);
    } else if (selectedCategory) {
      meta.textContent = t("bots.glossary.count_in_category")
        .replace("{category}", selectedCategory)
        .replace("{count}", String(entries.length));
    } else {
      meta.textContent = t("bots.glossary.count").replace("{count}", String(entries.length));
    }
    list.innerHTML = "";
    if (!entries.length) {
      list.innerHTML = `<p class="gp-ta-glossary-empty">${t("bots.glossary.empty")}</p>`;
      return;
    }
    for (const entry of entries) {
      list.appendChild(renderCard(entry));
    }
    if (target) {
      requestAnimationFrame(() => {
        const card = list.querySelector<HTMLElement>(`#${glossaryAnchorId(target)}`);
        if (!card) return;
        card.scrollIntoView({ behavior: "smooth", block: "start" });
        highlightCard(card);
        pendingTarget = null;
      });
    }
  }

  function onHashChange(): void {
    const target = parseGlossaryHash(window.location.hash);
    if (!target) return;
    navigateToEntry(target, { updateHash: false });
  }

  search.addEventListener("input", () => {
    singleEntryFilter = null;
    pendingTarget = null;
    render();
  });
  window.addEventListener("hashchange", onHashChange);
  renderCategoryNav();
  const searchRow = document.createElement("div");
  searchRow.className = "gp-ta-glossary-search-row";
  searchRow.append(search, clearFilterBtn);
  root.append(header, searchRow, categoryNav, meta, list);
  if (singleEntryFilter) {
    search.value = singleEntryFilter;
    clearFilterBtn.hidden = false;
  }
  render();
  if (pendingTarget) {
    navigateToEntry(pendingTarget, { updateHash: false });
  }

  return {
    root,
    cleanup: () => {
      window.removeEventListener("hashchange", onHashChange);
      clearHighlight();
    },
  };
}
