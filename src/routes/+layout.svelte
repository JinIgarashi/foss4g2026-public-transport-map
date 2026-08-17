<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { initTheme } from '$lib/theme.svelte';

	let { children } = $props();

	// `app.html` applies the scheme before first paint; this adopts the stored
	// choice into the store and keeps `system` following the OS.
	$effect(() => initTheme());
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{@render children()}
