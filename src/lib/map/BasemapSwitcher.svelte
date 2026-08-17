<script lang="ts">
	import type { IControl } from 'maplibre-gl';
	import { CustomControl, getMapContext } from 'svelte-maplibre-gl';
	import { asset } from '$app/paths';
	import { mapView, type BasemapKey } from './view.svelte';

	const BASEMAPS: { key: BasemapKey; title: string }[] = [
		{ key: 'white', title: 'White' },
		{ key: 'light', title: 'Light' },
		{ key: 'dark', title: 'Dark' }
	];

	const byTitle = new Map(BASEMAPS.map(({ key, title }) => [title, key]));

	const mapCtx = getMapContext();

	/** Slot the plugin's own markup is mounted into. */
	let host = $state<HTMLDivElement>();

	/**
	 * Selection is read off the plugin's DOM in the capture phase, so this runs
	 * before the plugin's own handlers. That matters for the main button, whose
	 * `alt` names the style it will switch *to* until the plugin rewrites it.
	 */
	function select(event: Event) {
		const image = event.target as HTMLImageElement;
		const key = image?.tagName === 'IMG' ? byTitle.get(image.alt) : undefined;
		if (key) mapView.basemap = key;
	}

	/**
	 * The plugin is used for its UI only.
	 *
	 * Its `changeStyle` returns without touching the map unless `initialise()`
	 * has fetched and cached each style, so skipping that call leaves it doing
	 * exactly what we want — swap the thumbnail, move the `active` marker, update
	 * the tooltip — while `MapView` keeps deriving the style URL from the picked
	 * flavour and the site language together. Letting the plugin call `setStyle`
	 * instead would fight that derivation: switching language would snap the
	 * basemap back to the default.
	 *
	 * It is mounted into a `<CustomControl>` slot rather than added with
	 * `map.addControl`, because the module is imported lazily: a control added
	 * once that import resolves would always land at the bottom of the corner,
	 * under the scale bar, instead of where the markup puts it.
	 */
	$effect(() => {
		const map = mapCtx.map;
		const slot = host;
		if (!map || !slot) return;

		let control: IControl | undefined;
		let element: HTMLElement | undefined;
		let cancelled = false;

		void (async () => {
			const [{ default: MaplibreStyleSwitcherControl }] = await Promise.all([
				import('@undp-data/style-switcher'),
				// Loaded here rather than at the top of the module so the CSS
				// follows the control instead of every page that imports the map.
				import('@undp-data/style-switcher/dist/maplibre-style-switcher.css')
			]);
			if (cancelled) return;

			control = new MaplibreStyleSwitcherControl(
				BASEMAPS.map(({ key, title }) => ({
					title,
					// Never fetched — `initialise()` is deliberately not called — but
					// the plugin's type requires it, and the real URL documents what
					// the thumbnail is showing.
					uri: `https://api.protomaps.com/styles/v5/${key}/en.json`,
					image: asset(`/style-switcher/${key}.webp`)
				})),
				{ defaultStyle: BASEMAPS.find(({ key }) => key === mapView.basemap)?.title }
			) as unknown as IControl;

			element = control.onAdd(map);
			element.addEventListener('click', select, true);
			slot.appendChild(element);
		})();

		return () => {
			cancelled = true;
			element?.removeEventListener('click', select, true);
			control?.onRemove(map);
		};
	});
</script>

<!-- `group={false}`: the plugin brings its own round-thumbnail styling, which the
     default control-group chrome would box in. -->
<CustomControl position="bottom-left" group={false}>
	<div bind:this={host}></div>
</CustomControl>
