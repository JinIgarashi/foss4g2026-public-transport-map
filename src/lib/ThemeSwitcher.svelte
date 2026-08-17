<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Monitor from '@lucide/svelte/icons/monitor';
	import Moon from '@lucide/svelte/icons/moon';
	import Sun from '@lucide/svelte/icons/sun';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { currentMessages } from '$lib/i18n';
	import { theme, THEME_PREFERENCES, type ThemePreference } from '$lib/theme.svelte';

	let { class: className = '' }: { class?: string } = $props();

	let t = $derived(currentMessages());

	const icons: Record<ThemePreference, typeof Sun> = {
		light: Sun,
		dark: Moon,
		system: Monitor
	};

	let TriggerIcon = $derived(theme.resolved === 'dark' ? Moon : Sun);
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger
		class={`${buttonVariants({ variant: 'ghost', size: 'sm' })} cursor-pointer gap-1 ${className}`}
		aria-label={t.header.theme}
	>
		<TriggerIcon size={18} />
		<ChevronDown size={14} class="opacity-60" />
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="end" class="w-40">
		{#each THEME_PREFERENCES as item (item)}
			{@const Icon = icons[item]}
			<DropdownMenu.Item
				class="cursor-pointer gap-2"
				onSelect={() => (theme.preference = item)}
				aria-current={item === theme.preference ? 'true' : undefined}
			>
				<Icon size={16} />
				<span class="flex-1">{t.theme[item]}</span>
				{#if item === theme.preference}
					<Check size={14} />
				{/if}
			</DropdownMenu.Item>
		{/each}
	</DropdownMenu.Content>
</DropdownMenu.Root>
