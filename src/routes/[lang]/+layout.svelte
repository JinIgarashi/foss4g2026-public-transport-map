<script lang="ts">
	import logo from '$lib/assets/logo-with-title.svg';
	import logoDark from '$lib/assets/logo-with-title-dark.svg';
	import siGithub from 'simple-icons/icons/github.svg?raw';
	import LanguageSwitcher from '$lib/LanguageSwitcher.svelte';
	import ThemeSwitcher from '$lib/ThemeSwitcher.svelte';
	import {
		currentLocale,
		currentMessages,
		getLocaleDefinition,
		localeTag,
		LOCALES
	} from '$lib/i18n';
	import { CONFERENCE_URL, OG_IMAGE, OG_SITE_NAME, REPO_URL, SITE_URL } from '$lib/seo';

	let { children } = $props();

	let locale = $derived(currentLocale());
	let definition = $derived(getLocaleDefinition(locale));
	let t = $derived(currentMessages());
	let pageUrl = $derived(`${SITE_URL}/${locale}`);

	// `hooks.server.ts` bakes `lang`/`dir` into the prerendered HTML; keep them in
	// sync when the visitor switches language client-side.
	$effect(() => {
		document.documentElement.lang = localeTag(definition);
		document.documentElement.dir = definition.dir;
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
	<meta property="og:url" content={pageUrl} />
	<meta property="og:locale" content={localeTag(definition)} />
	<meta property="og:site_name" content={OG_SITE_NAME} />

	<!-- Twitter Card -->
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={t.meta.title} />
	<meta name="twitter:description" content={t.meta.description} />
	<meta name="twitter:image" content={OG_IMAGE} />
	<meta name="twitter:image:alt" content={t.header.logoAlt} />

	<link rel="canonical" href={pageUrl} />
	{#each LOCALES as alternate (alternate.code)}
		<link rel="alternate" hreflang={localeTag(alternate)} href={`${SITE_URL}/${alternate.code}`} />
	{/each}
	<link rel="alternate" hreflang="x-default" href={`${SITE_URL}/`} />
</svelte:head>

<div class="flex h-dvh flex-col">
	<!-- `dir="ltr"` even under an RTL locale: the header is brand chrome, and the
	     logo lockup is a fixed left-hand mark. -->
	<header dir="ltr" class="flex items-center gap-3 border-b border-border bg-background px-4 py-2">
		<a href={CONFERENCE_URL} target="_blank" rel="noopener noreferrer">
			<!-- Two lockups, one visible at a time: the default artwork is near-black,
			     so dark mode needs the white one. -->
			<span class="dark:hidden">
				<img src={logo} alt={t.header.logoAlt} class="h-10" />
			</span>
			<span class="hidden dark:block">
				<img src={logoDark} alt={t.header.logoAlt} class="h-10" />
			</span>
		</a>
		<!-- Hidden on phones: the title is long enough to squeeze the logo. -->
		<p class="hidden font-semibold sm:block">{t.header.siteName}</p>
		<div class="ms-auto flex items-center">
			<ThemeSwitcher />
			<LanguageSwitcher />
			<a
				href={REPO_URL}
				target="_blank"
				rel="noopener noreferrer"
				aria-label={t.header.github}
				class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
			>
				<span
					aria-hidden="true"
					class="inline-flex h-6 w-6 [&>svg]:h-full [&>svg]:w-full [&>svg]:fill-current"
				>
					<!-- eslint-disable-next-line svelte/no-at-html-tags -->
					{@html siGithub}
				</span>
			</a>
		</div>
	</header>
	<main class="relative flex-1">
		{@render children()}
	</main>
</div>
