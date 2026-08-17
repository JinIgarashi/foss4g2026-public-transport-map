<script lang="ts">
	import { CustomControl } from 'svelte-maplibre-gl';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import { currentMessages } from '$lib/i18n';
	import { BUS_STOP_COLOR, STATUS_COLOR, STATUS_KEYS } from './status';

	let t = $derived(currentMessages());
	let expanded = $state(true);

	/**
	 * Between `SHINKANSEN_COLOR` and `SHINKANSEN_COLOR_DARK`: this panel is
	 * painted in the UI theme rather than the basemap flavour, so it cannot
	 * follow the map's pair, and either one alone is unreadable on the opposite
	 * background.
	 */
	const LEGEND_SHINKANSEN = '#4285f4';
</script>

<!-- `group={false}`: the default `maplibregl-ctrl-group` styling is built for
     rows of 29px icon buttons and squashes a real panel. -->
<CustomControl position="bottom-left" group={false}>
	<div class="rounded-md border border-border bg-background/95 shadow-md backdrop-blur-sm">
		<button
			type="button"
			class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold"
			aria-expanded={expanded}
			aria-label={expanded ? t.legend.collapse : t.legend.expand}
			onclick={() => (expanded = !expanded)}
		>
			<span class="flex-1">{t.legend.title}</span>
			{#if expanded}
				<ChevronDown size={14} class="opacity-60" />
			{:else}
				<ChevronUp size={14} class="opacity-60" />
			{/if}
		</button>

		{#if expanded}
			<div class="flex flex-col gap-1.5 px-3 pb-3">
				{#each STATUS_KEYS as status (status)}
					<div class="flex items-center gap-2 text-xs">
						<span
							class="h-1 w-6 shrink-0 rounded-full"
							style={`background-color: ${STATUS_COLOR[status]}`}
							aria-hidden="true"
						></span>
						<span>{t.status[status].label}</span>
					</div>
				{/each}

				<!-- Shape and colour carry the mode, the casing above carries the
				     status, so the two legends have to be read together. -->
				<div class="mt-1 flex flex-col gap-1.5 border-t border-border pt-2 text-xs">
					<!-- Drawn the way the map draws them, with two substitutions: the
					     dark routes use `currentColor` and the hatch uses the panel
					     background, because this panel follows the UI theme while the
					     map follows the basemap flavour. The shinkansen blue is a mid
					     tone that holds up on a light and a dark panel both. -->
					<div class="flex items-center gap-2">
						<svg width="24" height="8" aria-hidden="true" class="shrink-0">
							<line x1="0" y1="4" x2="24" y2="4" stroke={LEGEND_SHINKANSEN} stroke-width="6" />
							<line
								x1="0"
								y1="4"
								x2="24"
								y2="4"
								stroke="var(--color-background)"
								stroke-width="6"
								stroke-dasharray="3.6 9.6"
							/>
						</svg>
						<span>{t.legend.shinkansenLine}</span>
					</div>
					<div class="flex items-center gap-2">
						<svg width="24" height="8" aria-hidden="true" class="shrink-0">
							<line x1="0" y1="4" x2="24" y2="4" stroke="currentColor" stroke-width="4.5" />
							<line
								x1="0"
								y1="4"
								x2="24"
								y2="4"
								stroke="var(--color-background)"
								stroke-width="4.5"
								stroke-dasharray="2.7 7.2"
							/>
						</svg>
						<span>{t.legend.railwayLine}</span>
					</div>
					<div class="flex items-center gap-2">
						<svg width="24" height="8" aria-hidden="true" class="shrink-0">
							<line x1="0" y1="4" x2="24" y2="4" stroke="currentColor" stroke-width="3" />
						</svg>
						<span>{t.legend.tramLine}</span>
					</div>
					<div class="flex items-center gap-2">
						<svg width="24" height="6" aria-hidden="true" class="shrink-0">
							<line
								x1="0"
								y1="3"
								x2="24"
								y2="3"
								stroke="currentColor"
								stroke-width="2.5"
								stroke-linecap="round"
								stroke-dasharray="0 5"
							/>
						</svg>
						<span>{t.legend.busLine}</span>
					</div>
					<!-- Both dots are drawn the way the map draws them: a hollow
					     circle, so the fill reads as "no colour of its own", and
					     the station a size larger than the bus stop. The station
					     ring takes the acceptance colour on the map and stands in
					     as neutral here; the bus stop ring is blue on the map too.
					     Both swatches share a height so the two rows line up. -->
					<div class="flex items-center gap-2">
						<svg width="24" height="16" aria-hidden="true" class="shrink-0">
							<circle
								cx="12"
								cy="8"
								r="5.5"
								fill="var(--color-background)"
								stroke="currentColor"
								stroke-width="2.2"
							/>
						</svg>
						<span>{t.legend.railwayStation}</span>
					</div>
					<div class="flex items-center gap-2">
						<svg width="24" height="16" aria-hidden="true" class="shrink-0">
							<circle
								cx="12"
								cy="8"
								r="4"
								fill="var(--color-background)"
								stroke={BUS_STOP_COLOR}
								stroke-width="1.8"
							/>
						</svg>
						<span>{t.legend.busStop}</span>
					</div>
				</div>
			</div>
		{/if}
	</div>
</CustomControl>
