import en from "../locales/en.json";

const catalogs: Record<string, Record<string, string>> = {
  en: en as Record<string, string>,
};

let currentLocale = "en";

export function getLocale(): string {
  return currentLocale;
}

export function setLocale(locale: string): void {
  if (!catalogs[locale]) {
    return;
  }
  currentLocale = locale;
  document.documentElement.lang = locale;
}

export function t(key: string, vars?: Record<string, string>): string {
  const catalog = catalogs[currentLocale] ?? catalogs.en;
  let value = catalog[key] ?? catalogs.en[key] ?? key;
  if (vars) {
    for (const [name, replacement] of Object.entries(vars)) {
      value = value.replaceAll(`{${name}}`, replacement);
    }
  }
  return value;
}

export function supportedLocales(): string[] {
  return Object.keys(catalogs);
}
