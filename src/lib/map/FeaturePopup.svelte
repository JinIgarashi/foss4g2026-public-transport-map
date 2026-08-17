<script module lang="ts">
	/** Everything the popup needs, lifted out of the clicked vector-tile feature. */
	export interface FeatureInfo {
		kind: 'railway' | 'bus' | 'station';
		lngLat: [number, number];
		properties: {
			st: number;
			op?: string;
			/** Station name on the station layer, operator name on the others. */
			nm?: string;
			/** Operator name — station layer only, where `nm` is taken. */
			cp?: string;
			ln?: string;
			ar?: string;
			kd?: string;
			it?: string;
		};
	}
</script>

<script lang="ts">
	import { Popup } from 'svelte-maplibre-gl';
	import { currentMessages, type Locale } from '$lib/i18n';
	import { areaName, operatorById, operatorName, unpackOperatorIds } from './operators';
	import { STATUS_BY_CODE, STATUS_COLOR } from './status';

	let { info, locale, onclose }: { info: FeatureInfo; locale: Locale; onclose: () => void } =
		$props();

	let t = $derived(currentMessages());
	let feature = $derived(info.properties);
	let status = $derived(STATUS_BY_CODE[feature.st] ?? 'unknown');

	let operators = $derived(
		unpackOperatorIds(feature.op)
			.map(operatorById)
			.filter((operator) => operator !== undefined)
	);

	// The raw MLIT string is what is painted on the actual vehicle, so it leads;
	// a curated English name is offered alongside when we have one.
	let sourceName = $derived(info.kind === 'station' ? (feature.cp ?? '') : (feature.nm ?? ''));
	let englishName = $derived(
		locale === 'en'
			? operators
					.map((operator) => operatorName(operator, locale))
					.filter((name) => name !== sourceName)
					.join(' / ')
			: ''
	);

	let area = $derived(areaName(feature.ar || undefined, locale));

	// Only one note is shown: on a jointly run route, the first operator that has
	// one is the restriction the traveller runs into first.
	let note = $derived(operators.map((operator) => operator.note?.[locale]).find(Boolean));

	let kindLabel = $derived(
		info.kind === 'station'
			? t.popup.station
			: info.kind === 'bus'
				? t.popup.bus
				: (t.railKind[feature.kd as keyof typeof t.railKind] ?? t.popup.railway)
	);

	// JR vs private vs third-sector is half the reason a card works or does not,
	// so it earns a line of its own rather than being folded into the type.
	let institutionLabel = $derived(
		t.institution[feature.it as keyof typeof t.institution] ?? undefined
	);
</script>

<Popup lnglat={info.lngLat} open closeButton={false} maxWidth="320px" {onclose}>
	<div class="flex w-full max-w-[19rem] flex-col gap-2 text-foreground">
		<div class="flex items-start gap-2">
			<span
				class="mt-1 h-3 w-3 shrink-0 rounded-full"
				style={`background-color: ${STATUS_COLOR[status]}`}
				aria-hidden="true"
			></span>
			<div class="min-w-0">
				{#if info.kind === 'station'}
					<p class="text-sm leading-tight font-semibold">{feature.nm}</p>
					<p class="text-xs text-muted-foreground">{sourceName}</p>
				{:else}
					<p class="text-sm leading-tight font-semibold">{sourceName}</p>
				{/if}
				{#if englishName}
					<p class="text-xs text-muted-foreground">{englishName}</p>
				{/if}
			</div>
		</div>

		<p class="text-sm font-medium" style={`color: ${STATUS_COLOR[status]}`}>
			{t.status[status].label}
		</p>
		<p class="text-xs leading-snug text-muted-foreground">{t.status[status].description}</p>

		<dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
			{#if feature.ln}
				<dt class="text-muted-foreground">{t.popup.line}</dt>
				<dd class="min-w-0 break-words">{feature.ln}</dd>
			{/if}
			<dt class="text-muted-foreground">{t.popup.mode}</dt>
			<dd>{kindLabel}</dd>
			{#if institutionLabel}
				<dt class="text-muted-foreground">{t.popup.operatorType}</dt>
				<dd>{institutionLabel}</dd>
			{/if}
			{#if area}
				<dt class="text-muted-foreground">{t.popup.cardArea}</dt>
				<dd>{area}</dd>
			{/if}
		</dl>

		{#if note}
			<p class="border-t border-border pt-2 text-xs leading-snug text-muted-foreground">
				{note}
			</p>
		{/if}
	</div>
</Popup>
