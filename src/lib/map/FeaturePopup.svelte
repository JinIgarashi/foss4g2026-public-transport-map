<script module lang="ts">
	/** Everything the popup needs, lifted out of the clicked vector-tile feature. */
	export interface FeatureInfo {
		kind: 'railway' | 'bus' | 'station' | 'busstop';
		lngLat: [number, number];
		properties: {
			st: number;
			op?: string;
			/** Place name on the station and bus stop layers, operator name on the others. */
			nm?: string;
			/** English `nm`, resolved at build time — station and bus stop layers only. */
			ne?: string;
			/** Operator name — station and bus stop layers only, where `nm` is taken. */
			cp?: string;
			ln?: string;
			/** English `ln`. */
			le?: string;
			/** Route names through a bus stop, `、`-joined and capped. */
			rt?: string;
			/** How many further routes `rt` left out. */
			rn?: number;
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

	/** Layers where `nm` is the place and `cp` the operator. */
	let isPlace = $derived(info.kind === 'station' || info.kind === 'busstop');

	// The raw MLIT string, i.e. what is painted on the actual vehicle or sign.
	let operatorJa = $derived(isPlace ? (feature.cp ?? '') : (feature.nm ?? ''));

	// English operator name(s) — a jointly run route lists all of them. Under
	// `/ja` the raw MLIT string wins: our own index splits some joint operators
	// differently, and the sign is the authority on how the company is written.
	let operatorLabel = $derived(
		locale === 'en'
			? operators.map((operator) => operatorName(operator, locale)).join(' / ') || operatorJa
			: operatorJa
	);

	// English first under `/en`, with the Japanese kept underneath: the English
	// name is what a visitor can read, the Japanese is what the sign says.
	let placeName = $derived(locale === 'en' && feature.ne ? feature.ne : (feature.nm ?? ''));
	let placeSubtitle = $derived(placeName === feature.nm ? '' : (feature.nm ?? ''));
	let lineName = $derived(locale === 'en' && feature.le ? feature.le : (feature.ln ?? ''));
	let lineSubtitle = $derived(lineName === feature.ln ? '' : (feature.ln ?? ''));
	let englishOperator = $derived(operatorLabel === operatorJa ? '' : operatorLabel);

	// On a route, the line is what was clicked, so it leads and the operator
	// follows; a route without a line name falls back to leading with the operator.
	let primaryName = $derived(lineName || operatorLabel);
	let secondaryName = $derived(primaryName === lineName ? operatorLabel : '');

	// The Japanese originals, gathered onto one muted line — only the parts whose
	// localised form above actually differs from them.
	let japaneseName = $derived(
		[lineSubtitle, englishOperator ? operatorJa : ''].filter(Boolean).join(' / ')
	);

	let area = $derived(areaName(feature.ar || undefined, locale));

	// Only one note is shown: on a jointly run route, the first operator that has
	// one is the restriction the traveller runs into first.
	let note = $derived(operators.map((operator) => operator.note?.[locale]).find(Boolean));

	let kindLabel = $derived(
		info.kind === 'station'
			? t.popup.station
			: info.kind === 'busstop'
				? t.popup.busStop
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
				{#if isPlace}
					<p class="text-sm leading-tight font-semibold">{placeName}</p>
					{#if placeSubtitle}
						<p class="text-xs text-muted-foreground">{placeSubtitle}</p>
					{/if}
					{#if lineName}
						<p class="text-xs break-words">
							{lineName}
							{#if lineSubtitle}
								<span class="text-muted-foreground">（{lineSubtitle}）</span>
							{/if}
						</p>
					{/if}
					<p class="text-xs text-muted-foreground">{operatorJa}</p>
					{#if englishOperator}
						<p class="text-xs text-muted-foreground">{englishOperator}</p>
					{/if}
				{:else}
					<p class="text-sm leading-tight font-semibold break-words">{primaryName}</p>
					{#if secondaryName}
						<p class="text-xs break-words">{secondaryName}</p>
					{/if}
					{#if japaneseName}
						<p class="text-xs break-words text-muted-foreground">{japaneseName}</p>
					{/if}
				{/if}
			</div>
		</div>

		<p class="text-sm font-medium" style={`color: ${STATUS_COLOR[status]}`}>
			{t.status[status].label}
		</p>
		<p class="text-xs leading-snug text-muted-foreground">{t.status[status].description}</p>

		<dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
			{#if feature.rt}
				<dt class="text-muted-foreground">{t.popup.routes}</dt>
				<dd class="min-w-0 break-words">
					{feature.rt}{#if feature.rn}<span class="text-muted-foreground">
							{t.popup.moreRoutes(feature.rn)}</span
						>{/if}
				</dd>
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
