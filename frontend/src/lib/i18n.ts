/** Simple i18n translation system.
 *
 * Loads locale from localStorage or browser settings.
 * Falls back to Chinese (zh) as default.
 */

type Locale = "zh" | "en";
type TranslationMap = Record<string, string>;

const translations: Record<Locale, TranslationMap> = {
  zh: {},
  en: {},
};

let currentLocale: Locale = "zh";

/** Load translations for a locale dynamically */
export async function loadLocale(locale: Locale): Promise<void> {
  try {
    const mod = await import(`@/i18n/${locale}.json`);
    translations[locale] = mod.default || mod;
    currentLocale = locale;
  } catch {
    console.warn(`Failed to load locale: ${locale}`);
  }
}

/** Get the current active locale */
export function getLocale(): Locale {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("locale") as Locale | null;
    if (stored === "zh" || stored === "en") return stored;
  }
  return currentLocale;
}

/** Set the active locale */
export function setLocale(locale: Locale): void {
  currentLocale = locale;
  if (typeof window !== "undefined") {
    localStorage.setItem("locale", locale);
  }
}

/** Translate a key to the current locale */
export function t(key: string, fallback?: string): string {
  const locale = getLocale();
  return translations[locale]?.[key] || fallback || key;
}

/** Initialize locale from browser or localStorage */
export function initLocale(): void {
  if (typeof window === "undefined") return;

  const stored = localStorage.getItem("locale");
  if (stored === "zh" || stored === "en") {
    currentLocale = stored;
    return;
  }

  // Detect from browser
  const browserLang = navigator.language.toLowerCase();
  currentLocale = browserLang.startsWith("zh") ? "zh" : "en";
  localStorage.setItem("locale", currentLocale);
}
