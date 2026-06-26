import { t } from "../i18n";

export type InboxItem = {
  id: number;
  category: string;
  title: string;
  body: string;
  created_at: string;
  read: boolean;
};

export function createNotificationInbox(items: InboxItem[], onClose: () => void): HTMLElement {
  const panel = document.createElement("section");
  panel.className = "gp-panel gp-inbox-panel";
  panel.dataset.testid = "notification-inbox";
  panel.innerHTML = `
    <div class="gp-inbox-header">
      <h2>${t("inbox.title")}</h2>
      <button type="button" class="gp-btn-secondary" data-close>${t("inbox.close")}</button>
    </div>
  `;
  panel.querySelector("[data-close]")?.addEventListener("click", onClose);
  if (!items.length) {
    panel.innerHTML += `<p>${t("inbox.empty")}</p>`;
    return panel;
  }
  const list = document.createElement("ul");
  list.className = "gp-inbox-list";
  for (const item of items) {
    const li = document.createElement("li");
    li.className = item.read ? "gp-inbox-read" : "gp-inbox-unread";
    li.innerHTML = `<strong>${item.title}</strong><p>${item.body}</p><time>${item.created_at}</time>`;
    list.appendChild(li);
  }
  panel.appendChild(list);
  return panel;
}
