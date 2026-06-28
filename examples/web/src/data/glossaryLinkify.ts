/** Parse [[TA_ID|label]] links inside glossary prose. */

const LINK_RE = /\[\[([A-Z0-9_]+)(?:\|([^\]]+))?\]\]/g;

export function glossaryAnchorId(id: string): string {
  return `ta-glossary-${id.toLowerCase().replace(/[^a-z0-9_]+/g, "-")}`;
}

export function parseGlossaryHash(hash: string): string | null {
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!raw.startsWith("ta-glossary-")) return null;
  const slug = raw.slice("ta-glossary-".length);
  return slug.replace(/-/g, "_").toUpperCase();
}

export function appendLinkifiedText(
  el: HTMLElement,
  text: string,
  onNavigate: (id: string) => void,
): void {
  let last = 0;
  LINK_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = LINK_RE.exec(text)) !== null) {
    if (match.index > last) {
      el.appendChild(document.createTextNode(text.slice(last, match.index)));
    }
    const id = match[1];
    const label = match[2] ?? id;
    const link = document.createElement("a");
    link.href = `#${glossaryAnchorId(id)}`;
    link.className = "gp-ta-glossary-link";
    link.dataset.glossaryTarget = id;
    link.textContent = label;
    link.addEventListener("click", (event: MouseEvent) => {
      event.preventDefault();
      onNavigate(id);
    });
    el.appendChild(link);
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    el.appendChild(document.createTextNode(text.slice(last)));
  }
}
