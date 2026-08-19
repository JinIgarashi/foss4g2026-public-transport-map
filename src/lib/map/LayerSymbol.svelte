<script lang="ts">
	import { BUS_STOP_COLOR } from './status';
	import type { LayerKey } from './view.svelte';

	let { layer }: { layer: LayerKey } = $props();

	/**
	 * Between `SHINKANSEN_COLOR` and `SHINKANSEN_COLOR_DARK`: this panel is
	 * painted in the UI theme rather than the basemap flavour, so it cannot
	 * follow the map's pair, and either one alone is unreadable on the opposite
	 * background.
	 */
	const LEGEND_SHINKANSEN = '#4285f4';
</script>

<!-- Drawn the way the map draws them, with two substitutions: the dark routes
     use `currentColor` and the hatch uses the panel background, because this
     panel follows the UI theme while the map follows the basemap flavour. The
     shinkansen blue is a mid tone that holds up on a light and a dark panel
     both. The fixed-width box keeps the six rows aligned even though the lines
     and the dots are different heights. -->
<span class="flex w-6 shrink-0 items-center justify-center">
	{#if layer === 'shinkansen'}
		<svg width="24" height="8" aria-hidden="true">
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
	{:else if layer === 'railway'}
		<svg width="24" height="8" aria-hidden="true">
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
	{:else if layer === 'tram'}
		<svg width="24" height="8" aria-hidden="true">
			<line x1="0" y1="4" x2="24" y2="4" stroke="currentColor" stroke-width="3" />
		</svg>
	{:else if layer === 'bus'}
		<svg width="24" height="6" aria-hidden="true">
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
		<!-- Both dots are drawn the way the map draws them: a hollow circle, so
		     the fill reads as "no colour of its own", and the station a size
		     larger than the bus stop. The station ring takes the acceptance
		     colour on the map and stands in as neutral here; the bus stop ring is
		     blue on the map too. -->
	{:else if layer === 'station'}
		<svg width="24" height="16" aria-hidden="true">
			<circle
				cx="12"
				cy="8"
				r="5.5"
				fill="var(--color-background)"
				stroke="currentColor"
				stroke-width="2.2"
			/>
		</svg>
	{:else}
		<svg width="24" height="16" aria-hidden="true">
			<circle
				cx="12"
				cy="8"
				r="4"
				fill="var(--color-background)"
				stroke={BUS_STOP_COLOR}
				stroke-width="1.8"
			/>
		</svg>
	{/if}
</span>
