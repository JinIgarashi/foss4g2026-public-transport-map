<script lang="ts">
	import { CustomControl } from 'svelte-maplibre-gl';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import { currentMessages } from '$lib/i18n';
	import { STATUS_COLOR, STATUS_KEYS } from './status';

	let t = $derived(currentMessages());
	let expanded = $state(true);
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

				<!-- Shape carries the mode, colour carries the status, so the two
				     legends have to be read together. -->
				<div class="mt-1 flex flex-col gap-1.5 border-t border-border pt-2 text-xs">
					<div class="flex items-center gap-2">
						<svg width="24" height="6" aria-hidden="true" class="shrink-0">
							<line x1="0" y1="3" x2="24" y2="3" stroke="currentColor" stroke-width="3" />
						</svg>
						<span>{t.legend.railwayLine}</span>
					</div>
					<div class="flex items-center gap-2">
						<svg width="24" height="6" aria-hidden="true" class="shrink-0">
							<line
								x1="0"
								y1="3"
								x2="24"
								y2="3"
								stroke="currentColor"
								stroke-width="1.5"
								stroke-dasharray="4 3"
							/>
						</svg>
						<span>{t.legend.busLine}</span>
					</div>
				</div>
			</div>
		{/if}
	</div>
</CustomControl>
