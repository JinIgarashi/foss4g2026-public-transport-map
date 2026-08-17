import type { Handle } from '@sveltejs/kit';
import { DEFAULT_LOCALE, getLocaleDefinition, isLocale, localeTag } from '$lib/i18n/locales';

/**
 * Bakes the active language into `<html lang>` and `<html dir>`. This runs while
 * prerendering, so each generated page ships the correct attributes without any
 * client JS.
 */
export const handle: Handle = ({ event, resolve }) => {
	const lang = isLocale(event.params.lang) ? event.params.lang : DEFAULT_LOCALE;
	const definition = getLocaleDefinition(lang);

	return resolve(event, {
		transformPageChunk: ({ html }) =>
			html.replace('%page.lang%', localeTag(definition)).replace('%page.dir%', definition.dir)
	});
};
