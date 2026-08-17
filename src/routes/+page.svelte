<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import {
		DEFAULT_LOCALE,
		LOCALE_STORAGE_KEY,
		LOCALES,
		localeTag,
		resolvePreferredLocale
	} from '$lib/i18n';
	import { messages } from '$lib/i18n/messages';
	import { OG_IMAGE, OG_SITE_NAME, SITE_URL } from '$lib/seo';

	// Crawlers never run the redirect below, so `/` needs its own card metadata.
	// It describes the site in the default locale and points at `/`, which the
	// `[lang]` pages already declare as `x-default`.
	const t = messages[DEFAULT_LOCALE];
	const rootUrl = `${SITE_URL}/`;

	onMount(() => {
		const locale = resolvePreferredLocale(
			localStorage.getItem(LOCALE_STORAGE_KEY),
			navigator.languages ?? [navigator.language]
		);
		// The map hash is appended so a shared deep link survives the redirect.
		// eslint-disable-next-line svelte/no-navigation-without-resolve
		void goto(`${resolve('/[lang]', { lang: locale })}${location.hash}`, { replaceState: true });
	});
</script>

<svelte:head>
	<title>{t.meta.title}</title>
	<meta name="description" content={t.meta.description} />

	<!-- Open Graph -->
	<meta property="og:type" content="website" />
	<meta property="og:title" content={t.meta.title} />
	<meta property="og:description" content={t.meta.description} />
	<meta property="og:image" content={OG_IMAGE} />
	<meta property="og:image:type" content="image/png" />
	<meta property="og:image:alt" content={t.header.logoAlt} />
	<meta property="og:url" content={rootUrl} />
	<meta property="og:locale" content={DEFAULT_LOCALE} />
	<meta property="og:site_name" content={OG_SITE_NAME} />

	<!-- Twitter Card -->
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={t.meta.title} />
	<meta name="twitter:description" content={t.meta.description} />
	<meta name="twitter:image" content={OG_IMAGE} />
	<meta name="twitter:image:alt" content={t.header.logoAlt} />

	<link rel="canonical" href={rootUrl} />
	{#each LOCALES as alternate (alternate.code)}
		<link rel="alternate" hreflang={localeTag(alternate)} href={`${SITE_URL}/${alternate.code}`} />
	{/each}
	<link rel="alternate" hreflang="x-default" href={rootUrl} />

	<noscript>
		<meta http-equiv="refresh" content={`0; url=${resolve('/[lang]', { lang: DEFAULT_LOCALE })}`} />
	</noscript>
</svelte:head>

<div class="flex h-dvh w-full items-center justify-center bg-background">
	<Spinner />
</div>
