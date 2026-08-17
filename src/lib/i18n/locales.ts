/**
 * Locale definition.
 *
 * The site ships English and Japanese. The URL segment (`/en`, `/ja`) is the
 * single source of truth for the active locale — there is no locale store, and
 * switching language is a navigation.
 */
export interface LocaleDefinition {
	/**
	 * URL segment, e.g. `/ja`. Always lowercase: these become prerendered file
	 * names (`build/ja.html`), and mixed-case paths break on static hosts.
	 */
	code: string;
	/** Name of the language written in that language. */
	label: string;
	/** BCP 47 tag passed to `Intl` / `toLocaleDateString`. */
	dateLocale: string;
	/**
	 * Language code of the Protomaps basemap style. Swapping this swaps the whole
	 * style URL, so place names on the basemap follow the site language.
	 * @see https://docs.protomaps.com/basemaps/localization
	 */
	protomaps: string;
	/** Writing direction. Drives `<html dir>`. Both locales are LTR today. */
	dir: 'ltr' | 'rtl';
}

export const LOCALES = [
	{
		code: 'en',
		label: 'English',
		dateLocale: 'en-US',
		protomaps: 'en',
		dir: 'ltr'
	},
	{
		code: 'ja',
		label: '日本語',
		dateLocale: 'ja-JP',
		protomaps: 'ja',
		dir: 'ltr'
	}
] as const satisfies readonly LocaleDefinition[];

export type Locale = (typeof LOCALES)[number]['code'];

export const DEFAULT_LOCALE: Locale = 'en';

const LOCALE_BY_CODE = new Map<string, (typeof LOCALES)[number]>(
	LOCALES.map((locale) => [locale.code, locale])
);

export function isLocale(value: unknown): value is Locale {
	return typeof value === 'string' && LOCALE_BY_CODE.has(value);
}

export function getLocaleDefinition(locale: Locale): (typeof LOCALES)[number] {
	return LOCALE_BY_CODE.get(locale) ?? LOCALE_BY_CODE.get(DEFAULT_LOCALE)!;
}

/** BCP 47 tag for `hreflang` / `<html lang>`. */
export function localeTag(locale: LocaleDefinition | Locale): string {
	const definition = typeof locale === 'string' ? getLocaleDefinition(locale) : locale;
	return definition.code;
}

/**
 * Best locale for a visitor landing on `/`, preferring their last explicit
 * choice over the browser's `Accept-Language` order.
 */
export function resolvePreferredLocale(
	stored: string | null,
	navigatorLanguages: readonly string[]
): Locale {
	if (isLocale(stored)) return stored;

	for (const language of navigatorLanguages) {
		const lower = language.toLowerCase();
		if (isLocale(lower)) return lower;
		// `ja-JP` → `ja`
		const prefix = lower.split('-')[0];
		if (isLocale(prefix)) return prefix;
	}

	return DEFAULT_LOCALE;
}
