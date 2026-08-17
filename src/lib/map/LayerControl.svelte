<script lang="ts">
	import { CustomControl } from 'svelte-maplibre-gl';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { currentMessages } from '$lib/i18n';
	import OperatorFilter from './OperatorFilter.svelte';
	import { STATUS_COLOR, STATUS_KEYS } from './status';
	import { mapView, type LayerKey } from './view.svelte';

	let t = $derived(currentMessages());

	// Collapsed by default on phones: the panel is taller than a phone map is
	// useful, and the legend already explains the colours.
	let expanded = $state(true);

	const layers: LayerKey[] = ['railway', 'bus', 'station', 'busstop'];
</script>

<!-- `group={false}`: the default `maplibregl-ctrl-group` styling is built for
     rows of 29px icon buttons and squashes a real panel. -->
<CustomControl position="top-left" group={false}>
	{#if expanded}
		<div
			class="w-64 rounded-md border border-border bg-background/95 p-3 shadow-md backdrop-blur-sm"
		>
			<div class="mb-2 flex items-center justify-between">
				<span class="text-sm font-semibold">{t.layers.title}</span>
				<Button
					variant="ghost"
					size="icon"
					class="h-6 w-6"
					aria-label={t.layers.collapse}
					onclick={() => (expanded = false)}
				>
					<X size={14} />
				</Button>
			</div>

			<div class="flex flex-col gap-2">
				{#each layers as layer (layer)}
					<div class="flex items-center justify-between gap-2">
						<Label for={`layer-${layer}`} class="text-sm font-normal">{t.layers[layer]}</Label>
						<Switch
							id={`layer-${layer}`}
							checked={mapView.isVisible(layer)}
							onCheckedChange={(value) => mapView.toggleLayer(layer, value)}
						/>
					</div>
				{/each}
			</div>

			<Separator class="my-3" />

			<span class="text-xs font-medium text-muted-foreground">{t.layers.filterTitle}</span>
			<div class="mt-1.5 flex flex-col gap-1.5">
				{#each STATUS_KEYS as status (status)}
					<div class="flex items-center gap-2">
						<Checkbox
							id={`status-${status}`}
							checked={mapView.hasStatus(status)}
							onCheckedChange={(value) => mapView.toggleStatus(status, value === true)}
						/>
						<span
							class="h-2.5 w-2.5 shrink-0 rounded-full"
							style={`background-color: ${STATUS_COLOR[status]}`}
							aria-hidden="true"
						></span>
						<Label for={`status-${status}`} class="text-sm font-normal">
							{t.status[status].label}
						</Label>
					</div>
				{/each}
			</div>

			<Separator class="my-3" />

			<OperatorFilter />
		</div>
	{:else}
		<Button
			variant="outline"
			size="icon"
			class="map-ctrl-btn h-8 w-8"
			aria-label={t.layers.expand}
			onclick={() => (expanded = true)}
		>
			<SlidersHorizontal size={16} />
		</Button>
	{/if}
</CustomControl>
