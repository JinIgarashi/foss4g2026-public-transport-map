<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import Bus from '@lucide/svelte/icons/bus';
	import Check from '@lucide/svelte/icons/check';
	import Search from '@lucide/svelte/icons/search';
	import TrainFront from '@lucide/svelte/icons/train-front';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { currentLocale, currentMessages } from '$lib/i18n';
	import { OPERATOR_SEARCH, areaName, operatorName, type OperatorEntry } from './operators';
	import { STATUS_COLOR, STATUS_KEYS, type StatusKey } from './status';
	import { mapView } from './view.svelte';

	let { open = $bindable(false) }: { open?: boolean } = $props();

	let t = $derived(currentMessages());
	let locale = $derived(currentLocale());

	/** How many rows to add each time the visitor asks for more. */
	const PAGE = 200;

	const modes = ['rail', 'bus'] as const;
	type Mode = (typeof modes)[number];

	let query = $state('');
	let modeFilter = new SvelteSet<Mode>();
	let statusFilter = new SvelteSet<StatusKey>();
	let limit = $state(PAGE);

	// Empty filter sets mean "no narrowing", so the dialog opens on everything.
	let tokens = $derived(query.toLowerCase().split(/\s+/).filter(Boolean));

	// Which ids float to the top of the list. A snapshot rather than the live
	// selection, so that ticking a row does not make it jump away under the
	// pointer — the order only settles again on the next search.
	let pinned = $state(new Set<string>());

	let filtered = $derived.by(() => {
		const matches = OPERATOR_SEARCH.filter(({ operator, haystack }) => {
			if (!tokens.every((token) => haystack.includes(token))) return false;
			if (modeFilter.size > 0 && !operator.modes.some((mode) => modeFilter.has(mode))) return false;
			if (statusFilter.size > 0 && !statusFilter.has(operator.status)) return false;
			return true;
		}).map(({ operator }) => operator);

		if (pinned.size === 0) return matches;
		// Already-selected first: with the list capped at a few hundred rows, an
		// operator picked earlier could otherwise be impossible to find again to
		// switch back off.
		return [
			...matches.filter((operator) => pinned.has(operator.id)),
			...matches.filter((operator) => !pinned.has(operator.id))
		];
	});

	let visible = $derived(filtered.slice(0, limit));

	/** Changes whenever the result set is rebuilt from scratch. */
	let listKey = $derived([query, modeFilter.size, statusFilter.size, open].join('|'));

	// A new search starts a new list: keeping a grown limit would dump hundreds of
	// unrelated rows the moment the query is cleared. The pinned ids are re-read
	// here too, untracked — tracking them would reshuffle the list on every tick.
	let lastKey = '';
	$effect(() => {
		if (listKey === lastKey) return;
		lastKey = listKey;
		limit = PAGE;
		pinned = new Set(untrack(() => mapView.operators));
	});

	function toggleMode(mode: Mode) {
		if (modeFilter.has(mode)) modeFilter.delete(mode);
		else modeFilter.add(mode);
	}

	function toggleStatus(status: StatusKey) {
		if (statusFilter.has(status)) statusFilter.delete(status);
		else statusFilter.add(status);
	}

	/** The name in the other language, when it says something the first does not. */
	function secondaryName(operator: OperatorEntry): string {
		const primary = operatorName(operator, locale);
		const other = locale === 'en' ? operator.ja : (operator.en ?? '');
		return other === primary ? '' : other;
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content
		class="flex max-h-[85dvh] flex-col gap-3 sm:max-w-lg"
		closeLabel={t.operatorFilter.close}
	>
		<Dialog.Header>
			<Dialog.Title>{t.operatorFilter.dialogTitle}</Dialog.Title>
			<Dialog.Description>{t.operatorFilter.dialogDescription}</Dialog.Description>
		</Dialog.Header>

		<div class="relative">
			<Search
				size={16}
				class="absolute top-1/2 left-2.5 -translate-y-1/2 text-muted-foreground"
				aria-hidden="true"
			/>
			<Input
				bind:value={query}
				placeholder={t.operatorFilter.placeholder}
				aria-label={t.operatorFilter.placeholder}
				autocomplete="off"
				class="pl-8"
			/>
		</div>

		<div class="flex flex-col gap-1.5">
			<div class="flex flex-wrap items-center gap-1.5">
				<span class="text-xs font-medium text-muted-foreground">{t.operatorFilter.filterMode}</span>
				{#each modes as mode (mode)}
					<Button
						variant={modeFilter.has(mode) ? 'default' : 'outline'}
						size="sm"
						class="h-7 gap-1 px-2 text-xs font-normal"
						aria-pressed={modeFilter.has(mode)}
						onclick={() => toggleMode(mode)}
					>
						{#if mode === 'rail'}
							<TrainFront size={13} />
						{:else}
							<Bus size={13} />
						{/if}
						{t.operatorFilter.mode[mode]}
					</Button>
				{/each}
			</div>
			<div class="flex flex-wrap items-center gap-1.5">
				<span class="text-xs font-medium text-muted-foreground"
					>{t.operatorFilter.filterStatus}</span
				>
				{#each STATUS_KEYS as status (status)}
					<Button
						variant={statusFilter.has(status) ? 'default' : 'outline'}
						size="sm"
						class="h-7 gap-1.5 px-2 text-xs font-normal"
						aria-pressed={statusFilter.has(status)}
						onclick={() => toggleStatus(status)}
					>
						<span
							class="h-2 w-2 shrink-0 rounded-full"
							style={`background-color: ${STATUS_COLOR[status]}`}
							aria-hidden="true"
						></span>
						{t.status[status].label}
					</Button>
				{/each}
			</div>
		</div>

		<div class="flex items-center justify-between gap-2 text-xs text-muted-foreground">
			<span aria-live="polite">
				{t.operatorFilter.results(filtered.length)}
				{#if mapView.operators.size > 0}
					&middot; {t.operatorFilter.selectedCount(mapView.operators.size)}
				{/if}
			</span>
			{#if mapView.operators.size > 0}
				<Button
					variant="ghost"
					size="sm"
					class="h-7 px-2 text-xs"
					onclick={() => mapView.clearOperators()}
				>
					{t.operatorFilter.clearAll}
				</Button>
			{/if}
		</div>

		<div class="-mx-1 min-h-0 flex-1 overflow-y-auto px-1">
			{#if filtered.length === 0}
				<p class="py-6 text-center text-sm text-muted-foreground">{t.operatorFilter.empty}</p>
			{:else}
				<ul class="flex flex-col gap-0.5">
					{#each visible as operator (operator.id)}
						{@const selected = mapView.hasOperator(operator.id)}
						{@const secondary = secondaryName(operator)}
						{@const area = areaName(operator.area, locale)}
						<li>
							<button
								type="button"
								aria-pressed={selected}
								class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-accent hover:text-accent-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none aria-pressed:bg-accent"
								onclick={() => mapView.toggleOperator(operator.id)}
							>
								<span
									class="flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] border border-input {selected
										? 'border-primary bg-primary text-primary-foreground'
										: ''}"
									aria-hidden="true"
								>
									{#if selected}<Check size={12} />{/if}
								</span>
								<span
									class="h-2.5 w-2.5 shrink-0 rounded-full"
									style={`background-color: ${STATUS_COLOR[operator.status]}`}
									aria-hidden="true"
								></span>
								<span class="min-w-0 flex-1">
									<span class="block truncate text-sm">{operatorName(operator, locale)}</span>
									{#if secondary || area}
										<span class="block truncate text-xs text-muted-foreground">
											{[secondary, area].filter(Boolean).join(' · ')}
										</span>
									{/if}
								</span>
								<span class="flex shrink-0 gap-1 text-muted-foreground" aria-hidden="true">
									{#if operator.modes.includes('rail')}<TrainFront size={14} />{/if}
									{#if operator.modes.includes('bus')}<Bus size={14} />{/if}
								</span>
							</button>
						</li>
					{/each}
				</ul>

				{#if filtered.length > visible.length}
					<Button variant="outline" size="sm" class="mt-2 w-full" onclick={() => (limit += PAGE)}>
						{t.operatorFilter.showMore(filtered.length - visible.length)}
					</Button>
				{/if}
			{/if}
		</div>

		<Dialog.Footer>
			<Dialog.Close>
				{#snippet child({ props })}
					<Button {...props} variant="outline" size="sm">{t.operatorFilter.close}</Button>
				{/snippet}
			</Dialog.Close>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
