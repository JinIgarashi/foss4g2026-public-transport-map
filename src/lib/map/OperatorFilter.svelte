<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button/index.js';
	import { currentLocale, currentMessages } from '$lib/i18n';
	import OperatorSelectDialog from './OperatorSelectDialog.svelte';
	import { operatorById, operatorName } from './operators';
	import { mapView } from './view.svelte';

	let t = $derived(currentMessages());
	let locale = $derived(currentLocale());

	let dialogOpen = $state(false);

	let count = $derived(mapView.operators.size);

	/** The one selected operator's name, or `undefined` when it is not exactly one. */
	let soleName = $derived.by(() => {
		if (count !== 1) return undefined;
		const operator = operatorById([...mapView.operators][0]);
		return operator ? operatorName(operator, locale) : undefined;
	});

	let label = $derived(
		count === 0
			? t.operatorFilter.allOperators
			: (soleName ?? t.operatorFilter.selectedCount(count))
	);
</script>

<div class="flex flex-col gap-1">
	<span class="text-xs font-medium text-muted-foreground">{t.operatorFilter.title}</span>
	<div class="flex items-center gap-1">
		<Button
			variant="outline"
			size="sm"
			class="h-8 min-w-0 flex-1 justify-between gap-2 font-normal"
			aria-label={t.operatorFilter.open}
			onclick={() => (dialogOpen = true)}
		>
			<span class="truncate">{label}</span>
			<Search size={14} class="shrink-0 opacity-50" />
		</Button>

		{#if count > 0}
			<Button
				variant="ghost"
				size="icon"
				class="h-8 w-8 shrink-0"
				aria-label={t.operatorFilter.clear}
				onclick={() => mapView.clearOperators()}
			>
				<X size={14} />
			</Button>
		{/if}
	</div>
	{#if count > 0}
		<span class="text-xs text-muted-foreground">
			{soleName ? t.operatorFilter.showing(soleName) : t.operatorFilter.showingCount(count)}
		</span>
	{/if}
</div>

<OperatorSelectDialog bind:open={dialogOpen} />
