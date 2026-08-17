<script lang="ts">
	import Info from '@lucide/svelte/icons/info';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { currentLocale, currentMessages } from '$lib/i18n';
	import { REPO_URL } from '$lib/seo';
	import metadataJson from '$lib/data/datasets.json';
	import { STATUS_COLOR, STATUS_KEYS } from '$lib/map/status';
	import type { Locale } from '$lib/i18n';

	interface DatasetMeta {
		id: string;
		label: Record<Locale, string>;
		edition: Record<Locale, string>;
		url: string;
	}

	let t = $derived(currentMessages());
	let locale = $derived(currentLocale());

	// Editions come from the tile build, not from the translations, so the dialog
	// cannot claim a data vintage the tiles do not actually have.
	const { datasets, icSourceDate, icReferences } = metadataJson as unknown as {
		datasets: DatasetMeta[];
		icSourceDate: string;
		icReferences: string[];
	};

	let sourceDate = $derived(
		new Date(icSourceDate).toLocaleDateString(locale === 'ja' ? 'ja-JP' : 'en-GB', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		})
	);
</script>

<Dialog.Root>
	<!-- `map-ctrl-btn`: this sits among MapLibre's own controls, so it has to keep
	     their light colours rather than follow the app theme. -->
	<Dialog.Trigger
		class={`${buttonVariants({ variant: 'outline', size: 'icon' })} map-ctrl-btn h-8 w-8 cursor-pointer`}
		aria-label={t.header.about}
	>
		<Info size={16} />
	</Dialog.Trigger>
	<Dialog.Content class="max-h-[85dvh] overflow-y-auto sm:max-w-lg" closeLabel={t.about.close}>
		<Dialog.Header>
			<Dialog.Title>{t.about.title}</Dialog.Title>
			<Dialog.Description>{t.about.intro}</Dialog.Description>
		</Dialog.Header>

		<section class="flex flex-col gap-2">
			<h3 class="text-sm font-semibold">{t.about.howToRead}</h3>
			<ul class="flex flex-col gap-1.5">
				{#each STATUS_KEYS as status (status)}
					<li class="flex items-start gap-2 text-sm">
						<span
							class="mt-1.5 h-1 w-6 shrink-0 rounded-full"
							style={`background-color: ${STATUS_COLOR[status]}`}
							aria-hidden="true"
						></span>
						<span>
							<span class="font-medium">{t.status[status].label}</span>
							<span class="text-muted-foreground"> — {t.status[status].description}</span>
						</span>
					</li>
				{/each}
			</ul>
		</section>

		<section class="flex flex-col gap-2">
			<h3 class="text-sm font-semibold">{t.about.dataSources}</h3>
			<dl class="flex flex-col gap-2 text-sm">
				{#each datasets as dataset (dataset.id)}
					<div>
						<dt class="font-medium">
							<a
								href={dataset.url}
								target="_blank"
								rel="noopener noreferrer"
								class="inline-flex items-center gap-1 underline underline-offset-2"
							>
								{dataset.label[locale]}
								<ExternalLink size={12} class="opacity-60" />
							</a>
						</dt>
						<dd class="text-muted-foreground">{dataset.edition[locale]}</dd>
					</div>
				{/each}
				<div>
					<dt class="font-medium">{t.about.icSource}</dt>
					<dd class="text-muted-foreground">{t.about.icSourceBody}</dd>
					<dd class="text-muted-foreground">{t.about.asOf(sourceDate)}</dd>
					<dd class="mt-1 flex flex-col gap-0.5">
						{#each icReferences as reference (reference)}
							<a
								href={reference}
								target="_blank"
								rel="noopener noreferrer"
								class="truncate text-xs underline underline-offset-2"
							>
								{decodeURI(reference)}
							</a>
						{/each}
					</dd>
				</div>
				<div>
					<dt class="font-medium">{t.about.names}</dt>
					<dd class="text-muted-foreground">{t.about.namesBody}</dd>
					<dd class="mt-1">
						<a
							href="https://www.openstreetmap.org/copyright"
							target="_blank"
							rel="noopener noreferrer"
							class="text-xs underline underline-offset-2">OpenStreetMap (ODbL)</a
						>
						&middot;
						<a
							href="https://www.wikidata.org/"
							target="_blank"
							rel="noopener noreferrer"
							class="text-xs underline underline-offset-2">Wikidata (CC0)</a
						>
					</dd>
				</div>
				<div>
					<dt class="font-medium">{t.about.basemap}</dt>
					<dd class="text-muted-foreground">
						<a
							href="https://protomaps.com/"
							target="_blank"
							rel="noopener noreferrer"
							class="underline underline-offset-2">Protomaps</a
						>
						&middot;
						<a
							href="https://www.openstreetmap.org/copyright"
							target="_blank"
							rel="noopener noreferrer"
							class="underline underline-offset-2">OpenStreetMap</a
						>
					</dd>
				</div>
			</dl>
		</section>

		<section class="flex flex-col gap-1 rounded-md bg-muted p-3">
			<h3 class="text-sm font-semibold">{t.about.disclaimer}</h3>
			<p class="text-sm text-muted-foreground">{t.about.disclaimerBody}</p>
		</section>

		<section class="flex flex-col gap-1">
			<h3 class="text-sm font-semibold">{t.about.license}</h3>
			<p class="text-sm text-muted-foreground">{t.about.licenseBody}</p>
			<a
				href={REPO_URL}
				target="_blank"
				rel="noopener noreferrer"
				class="inline-flex items-center gap-1 text-sm underline underline-offset-2"
			>
				{REPO_URL.replace('https://', '')}
				<ExternalLink size={12} class="opacity-60" />
			</a>
		</section>
	</Dialog.Content>
</Dialog.Root>
