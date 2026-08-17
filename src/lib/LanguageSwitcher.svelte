<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Languages from '@lucide/svelte/icons/languages';
	import { resolve } from '$app/paths';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { buttonVariants } from '$lib/components/ui/button/index.js';
	import { currentLocale, currentMessages, localeTag, LOCALES } from '$lib/i18n';

	let t = $derived(currentMessages());
	let locale = $derived(currentLocale());

	// Real links rather than a store write: the URL is the source of truth for the
	// language, so switching has to be a navigation. The map hash rides along so a
	// visitor keeps their position and zoom across the switch. Read at click time
	// because `<Hash>` rewrites it as the map moves.
	function href(code: string): string {
		const hash = typeof location === 'undefined' ? '' : location.hash;
		return `${resolve('/[lang]', { lang: code })}${hash}`;
	}
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger
		class={`${buttonVariants({ variant: 'ghost', size: 'sm' })} cursor-pointer gap-1`}
		aria-label={t.header.language}
	>
		<Languages size={18} />
		<ChevronDown size={14} class="opacity-60" />
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="end" class="w-40">
		{#each LOCALES as alternate (alternate.code)}
			<DropdownMenu.Item class="cursor-pointer gap-2 p-0">
				{#snippet child({ props })}
					<a
						{...props}
						href={href(alternate.code)}
						hreflang={localeTag(alternate)}
						lang={localeTag(alternate)}
						class={`${props.class ?? ''} flex w-full items-center gap-2 px-2 py-1.5`}
						aria-current={alternate.code === locale ? 'true' : undefined}
					>
						<span class="flex-1">{alternate.label}</span>
						{#if alternate.code === locale}
							<Check size={14} />
						{/if}
					</a>
				{/snippet}
			</DropdownMenu.Item>
		{/each}
	</DropdownMenu.Content>
</DropdownMenu.Root>
