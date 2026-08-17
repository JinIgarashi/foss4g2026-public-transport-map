import { error } from '@sveltejs/kit';
import { isLocale, LOCALES } from '$lib/i18n/locales';

/** Enumerates the locales to prerender: `build/en.html`, `build/ja.html`. */
export function entries() {
	return LOCALES.map((locale) => ({ lang: locale.code }));
}

export function load({ params }) {
	if (!isLocale(params.lang)) {
		error(404, 'Unknown language');
	}

	return {};
}
