import { loadFavorites, toggleFavorite } from "./favoritesStorage";
import { t } from "../i18n";

export type PickerItem = {
  id: string;
  label: string;
  category?: string;
  iconUrl?: string | null;
  tooltipTitle?: string;
  tooltipText?: string;
};

export type SearchablePickerOptions = {
  testId: string;
  label: string;
  value: string;
  items: PickerItem[];
  favoriteKey: string;
  onChange: (id: string) => void;
  categorized?: boolean;
  preserveOrder?: boolean;
  labelAction?: { text: string; onClick: () => void };
};

function starSvg(filled: boolean): string {
  const fill = filled ? "currentColor" : "none";
  return `<svg class="gp-picker-star" width="14" height="14" viewBox="0 0 24 24" aria-hidden="true"><path fill="${fill}" stroke="currentColor" stroke-width="2" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01z"/></svg>`;
}

export function createSearchablePicker(opts: SearchablePickerOptions): {
  root: HTMLElement;
  getValue: () => string;
  setValue: (id: string) => void;
  setItems: (items: PickerItem[]) => void;
  cleanup: () => void;
} {
  let value = opts.value;
  let items = opts.items;
  let favorites = loadFavorites(opts.favoriteKey);
  let open = false;

  const root = document.createElement("div");
  root.className = "gp-searchable-picker";
  root.dataset.testid = opts.testId;

  const label = document.createElement("span");
  label.className = "gp-picker-label";
  label.textContent = opts.label;
  if (opts.labelAction) {
    const link = document.createElement("button");
    link.type = "button";
    link.className = "gp-picker-label-link";
    link.dataset.testid = `${opts.testId}-label-link`;
    link.textContent = opts.labelAction.text;
    link.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      opts.labelAction?.onClick();
    });
    label.appendChild(document.createTextNode(" "));
    label.appendChild(link);
  }

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "gp-picker-trigger";
  trigger.dataset.testid = `${opts.testId}-trigger`;
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");

  const panel = document.createElement("div");
  panel.className = "gp-picker-panel";
  panel.hidden = true;
  panel.dataset.testid = `${opts.testId}-panel`;
  panel.setAttribute("role", "listbox");

  const search = document.createElement("input");
  search.type = "search";
  search.className = "gp-picker-search";
  search.placeholder = t("picker.search");
  search.dataset.testid = `${opts.testId}-search`;
  search.autocomplete = "off";

  const list = document.createElement("div");
  list.className = "gp-picker-list";

  function itemLabel(id: string): string {
    return items.find((i) => i.id === id)?.label ?? id;
  }

  function syncTrigger(): void {
    trigger.textContent = itemLabel(value);
  }

  function positionPanel(): void {
    const rect = trigger.getBoundingClientRect();
    const width = Math.min(Math.max(rect.width, 220), window.innerWidth - 16);
    const maxH = Math.min(280, window.innerHeight - 16);
    panel.style.maxHeight = `${maxH}px`;
    let top = rect.bottom + 4;
    let left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    if (top + maxH > window.innerHeight - 8) {
      top = Math.max(8, rect.top - maxH - 4);
    }
    panel.style.position = "fixed";
    panel.style.top = `${top}px`;
    panel.style.left = `${left}px`;
    panel.style.width = `${width}px`;
    panel.style.transform = "none";
  }

  function renderList(): void {
    const q = search.value.trim().toLowerCase();
    const filtered = q
      ? items.filter((i) => i.label.toLowerCase().includes(q) || i.id.toLowerCase().includes(q))
      : items;
    const favItems = favorites.map((id) => filtered.find((i) => i.id === id)).filter(Boolean) as PickerItem[];
    list.innerHTML = "";
    if (!filtered.length) {
      const empty = document.createElement("p");
      empty.className = "gp-picker-empty";
      empty.textContent = t("picker.empty");
      list.appendChild(empty);
      return;
    }
    const appendSection = (title: string, sectionItems: PickerItem[]): void => {
      if (!sectionItems.length) return;
      const head = document.createElement("div");
      head.className = "gp-picker-section";
      head.textContent = title;
      list.appendChild(head);
      for (const item of sectionItems) appendRow(item);
    };
    const appendRow = (item: PickerItem): void => {
      const row = document.createElement("div");
      row.className = "gp-picker-row";
      if (item.id === value) row.classList.add("gp-picker-row-active");
      if (item.tooltipTitle || item.tooltipText) {
        row.classList.add("gp-picker-row-has-tip");
        row.dataset.tipTitle = item.tooltipTitle ?? item.label;
        row.dataset.tipText = item.tooltipText ?? "";
      }
      const pick = document.createElement("button");
      pick.type = "button";
      pick.className = "gp-picker-row-btn";
      if (item.iconUrl) {
        const icon = document.createElement("img");
        icon.className = "gp-picker-row-icon";
        icon.src = item.iconUrl;
        icon.alt = "";
        icon.width = 18;
        icon.height = 18;
        pick.append(icon, document.createTextNode(` ${item.label}`));
      } else {
        pick.textContent = item.label;
      }
      if (item.tooltipTitle) pick.title = item.tooltipTitle;
      pick.addEventListener("click", (e) => {
        e.stopPropagation();
        value = item.id;
        opts.onChange(value);
        syncTrigger();
        closePanel();
      });
      const star = document.createElement("button");
      star.type = "button";
      star.className = "gp-picker-fav-btn";
      star.setAttribute("aria-label", t("picker.favorite"));
      star.innerHTML = starSvg(favorites.includes(item.id));
      star.addEventListener("click", (e) => {
        e.stopPropagation();
        favorites = toggleFavorite(opts.favoriteKey, item.id);
        renderList();
      });
      row.append(pick, star);
      if (item.tooltipText) {
        const tip = document.createElement("div");
        tip.className = "gp-picker-row-tooltip";
        tip.innerHTML = `<strong>${item.tooltipTitle ?? item.label}</strong><span>${item.tooltipText}</span>`;
        row.appendChild(tip);
      }
      list.appendChild(row);
    };
    appendSection(t("picker.favorites"), favItems);
    if (opts.categorized) {
      const cats = [...new Set(filtered.map((i) => i.category ?? t("picker.other")))].sort();
      for (const cat of cats) {
        appendSection(
          cat,
          filtered.filter((i) => (i.category ?? t("picker.other")) === cat).sort((a, b) => a.label.localeCompare(b.label)),
        );
      }
    } else {
      const sectionItems = opts.preserveOrder ? filtered : [...filtered].sort((a, b) => a.label.localeCompare(b.label));
      appendSection(t("picker.all"), sectionItems);
    }
  }

  function openPanel(): void {
    open = true;
    panel.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    search.value = "";
    panel.style.zIndex = "300";
    positionPanel();
    renderList();
    search.focus();
  }

  function closePanel(): void {
    open = false;
    panel.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  }

  trigger.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (open) closePanel();
    else openPanel();
  });

  search.addEventListener("input", () => renderList());
  search.addEventListener("click", (e) => e.stopPropagation());
  panel.addEventListener("click", (e) => e.stopPropagation());

  const onDocPointer = (e: Event): void => {
    if (!open) return;
    const target = e.target as Node | null;
    if (target && root.contains(target)) return;
    closePanel();
  };

  const onReposition = (): void => {
    if (open) positionPanel();
  };

  document.addEventListener("pointerdown", onDocPointer);
  window.addEventListener("resize", onReposition);
  window.addEventListener("scroll", onReposition, true);

  panel.append(search, list);
  root.append(label, trigger, panel);
  syncTrigger();

  return {
    root,
    getValue: () => value,
    setValue: (id) => {
      value = id;
      syncTrigger();
    },
    setItems: (next) => {
      items = next;
      syncTrigger();
      if (open) renderList();
    },
    cleanup: () => {
      closePanel();
      document.removeEventListener("pointerdown", onDocPointer);
      window.removeEventListener("resize", onReposition);
      window.removeEventListener("scroll", onReposition, true);
    },
  };
}
