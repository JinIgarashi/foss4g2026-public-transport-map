<script lang="ts">
	import {
		AttributionControl,
		CircleLayer,
		CustomControl,
		GeolocateControl,
		Hash,
		LineLayer,
		MapLibre,
		NavigationControl,
		Protocol,
		ScaleControl,
		SymbolLayer,
		VectorTileSource
	} from 'svelte-maplibre-gl';
	import type {
		DataDrivenPropertyValueSpecification,
		Map as MapLibreMap,
		MapLayerMouseEvent,
		VisibilitySpecification
	} from 'maplibre-gl';
	// Bundled rather than left to `autoloadGlobalCss`, which fetches it from
	// unpkg at runtime: without this stylesheet every map control loses its
	// layout, and a static site should not depend on a CDN staying reachable.
	import 'maplibre-gl/dist/maplibre-gl.css';
	import { PUBLIC_PROTOMAP_KEY } from '$env/static/public';
	import { currentLocale, currentLocaleDefinition, currentMessages } from '$lib/i18n';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { pmtilesProtocol, tilesUrl } from './pmtiles';
	import { mapView } from './view.svelte';
	import { operatorBounds } from './operators';
	import { BUS_STOP_COLOR, statusColorExpression } from './status';
	import AboutDialog from '$lib/AboutDialog.svelte';
	import BasemapSwitcher from './BasemapSwitcher.svelte';
	import FeaturePopup, { type FeatureInfo } from './FeaturePopup.svelte';
	import LayerControl from './LayerControl.svelte';
	import Legend from './Legend.svelte';

	/** Hiroshima city centre — the conference is here, so the map opens here. */
	const HIROSHIMA: [number, number] = [132.4553, 34.3853];

	let t = $derived(currentMessages());
	let locale = $derived(currentLocale());
	let localeDefinition = $derived(currentLocaleDefinition());

	// Protomaps serves one style per language and per flavour, so place names on
	// the basemap follow the site language rather than staying Japanese under
	// `/en`, and the flavour follows the style switcher. Keeping the URL derived
	// here — rather than letting the switcher plugin call `setStyle` itself — is
	// what stops a language change from resetting the visitor's basemap choice.
	let styleUrl = $derived(
		`https://api.protomaps.com/styles/v5/${mapView.basemap}/${localeDefinition.protomaps}.json?key=${PUBLIC_PROTOMAP_KEY}`
	);

	let map = $state<MapLibreMap>();
	let loaded = $state(false);
	let popup = $state<FeatureInfo | null>(null);

	const statusColor = statusColorExpression();

	/**
	 * One dot size for stations and bus stops both. They are the same kind of
	 * thing to a traveller, so sizing them differently would say something the
	 * map does not mean — and the legend draws them at one size too.
	 */
	const STOP_RADIUS: DataDrivenPropertyValueSpecification<number> = [
		'interpolate',
		['linear'],
		['zoom'],
		9,
		2,
		12,
		3.5,
		15,
		5
	];

	/** Ink that has to stay legible against the basemap, not against the theme. */
	let paper = $derived(mapView.isDarkBasemap ? '#0b1120' : '#ffffff');
	let ink = $derived(mapView.isDarkBasemap ? '#e8eaed' : '#1f2328');

	let busVisibility = $derived<VisibilitySpecification>(
		mapView.isVisible('bus') ? 'visible' : 'none'
	);
	let railwayVisibility = $derived<VisibilitySpecification>(
		mapView.isVisible('railway') ? 'visible' : 'none'
	);
	let stationVisibility = $derived<VisibilitySpecification>(
		mapView.isVisible('station') ? 'visible' : 'none'
	);
	let busStopVisibility = $derived<VisibilitySpecification>(
		mapView.isVisible('busstop') ? 'visible' : 'none'
	);

	/**
	 * Which name a label shows. `ne` is the English name the tile pipeline
	 * resolved — from OpenStreetMap, Wikidata or, failing both, transliteration —
	 * and `coalesce` falls back to the Japanese one for the few features that
	 * have none, which beats an unlabelled dot.
	 */
	let labelField = $derived<DataDrivenPropertyValueSpecification<string>>(
		locale === 'en' ? ['coalesce', ['get', 'ne'], ['get', 'nm']] : ['get', 'nm']
	);

	/** Layers a click can open a popup for, innermost first. */
	const CLICKABLE = ['station-dot', 'busstop-dot', 'railway-line', 'bus-line'];

	/**
	 * The line under the cursor, identified by attributes rather than by feature
	 * id. Neither dataset carries a route id, and `build_tiles.py` runs tippecanoe
	 * without `--use-attribute-for-id`, so there is no feature id to hang
	 * `feature-state` off — but a bus route is dissolved per operator name and
	 * then split into chunks, and a railway line is split into sections, so
	 * matching those attributes back is exactly what lights the whole line up.
	 */
	type Hovered = { nm: string; op: string; ln: string };

	let hoveredBus = $state<Hovered | null>(null);
	let hoveredRailway = $state<Hovered | null>(null);

	function read(event: MapLayerMouseEvent): Hovered | null {
		const properties = event.features?.[0]?.properties;
		if (!properties) return null;
		return {
			nm: (properties.nm as string) ?? '',
			op: (properties.op as string) ?? '',
			ln: (properties.ln as string) ?? ''
		};
	}

	/**
	 * Zoom ramp for `line-width` where every feature of the hovered line is drawn
	 * at the second width of each stop.
	 *
	 * The `case` sits inside the ramp rather than around it: `zoom` may only feed
	 * a top-level `interpolate`, so wrapping the whole ramp in a `case` is not a
	 * legal expression.
	 */
	function hoverWidth(
		hovered: Hovered | null,
		keys: ('nm' | 'op' | 'ln')[],
		stops: [zoom: number, base: number, wide: number][]
	): DataDrivenPropertyValueSpecification<number> {
		const ramp = ['interpolate', ['linear'], ['zoom']];
		if (!hovered) {
			return [...ramp, ...stops.flatMap(([zoom, base]) => [zoom, base])] as unknown as never;
		}
		const match = ['all', ...keys.map((key) => ['==', ['get', key], hovered[key]])];
		return [
			...ramp,
			...stops.flatMap(([zoom, base, wide]) => [zoom, ['case', match, wide, base]])
		] as unknown as never;
	}

	// Bus routes are dissolved per operator name, so `nm` + `op` is the route.
	let busWidth = $derived(
		hoverWidth(
			hoveredBus,
			['nm', 'op'],
			[
				[6, 1, 2.5],
				[10, 2.2, 5],
				[14, 4.5, 10]
			]
		)
	);
	// Railways are split per section, so company + line name is the line.
	let railwayWidth = $derived(
		hoverWidth(
			hoveredRailway,
			['nm', 'ln'],
			[
				[5, 1, 2.5],
				[10, 2.5, 6],
				[14, 5, 11]
			]
		)
	);
	// The white casing widens with it, or the halo would vanish under the line.
	let railwayCasingWidth = $derived(
		hoverWidth(
			hoveredRailway,
			['nm', 'ln'],
			[
				[5, 2, 4],
				[10, 4.5, 9],
				[14, 8, 16]
			]
		)
	);

	/**
	 * Filtering to a set of operators is useless if they are off-screen, so move
	 * to them. Bounds come precomputed from `scripts/build_tiles.py`, because
	 * `querySourceFeatures` only ever sees the tiles already loaded — a Hokkaido
	 * operator picked while looking at Hiroshima would fit to nothing.
	 */
	let operatorKey = $derived([...mapView.operators].sort().join('|'));

	$effect(() => {
		const target = map;
		if (!target || !operatorKey) return;
		const bounds = operatorBounds(operatorKey.split('|'));
		if (bounds) target.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 800 });
	});

	function pick(event: MapLayerMouseEvent, kind: FeatureInfo['kind']) {
		const feature = event.features?.[0];
		if (!feature) return;
		popup = {
			kind,
			lngLat: [event.lngLat.lng, event.lngLat.lat],
			properties: feature.properties as FeatureInfo['properties']
		};
	}

	/**
	 * A click on empty basemap closes the popup. This re-queries rather than
	 * tracking whether a layer handler ran, because MapLibre fires listeners in
	 * registration order — the map-wide one is registered before any layer, so it
	 * always runs first and can never observe a flag the layer handler sets.
	 */
	function closeIfBackground(event: MapLayerMouseEvent) {
		const layers = CLICKABLE.filter((id) => event.target.getLayer(id));
		if (event.target.queryRenderedFeatures(event.point, { layers }).length === 0) popup = null;
	}
</script>

<MapLibre
	bind:map
	class="h-full w-full"
	autoloadGlobalCss={false}
	style={styleUrl}
	center={HIROSHIMA}
	zoom={11}
	maxZoom={17}
	attributionControl={false}
	cursor={hoveredBus || hoveredRailway || popup ? 'pointer' : undefined}
	onload={() => (loaded = true)}
	onclick={closeIfBackground}
>
	<Protocol scheme="pmtiles" loadFn={pmtilesProtocol} />
	<Hash />

	<AttributionControl
		position="bottom-right"
		compact
		customAttribution={`<a href="https://nlftp.mlit.go.jp/ksj/" target="_blank" rel="noopener noreferrer">${t.map.attribution}</a> (CC BY 4.0)`}
	/>
	<!-- MapLibre *prepends* into the bottom corners, so the reading order down the
	     screen is the reverse of the order here: bottom-right ends up geolocate,
	     zoom, about, attribution, and bottom-left legend, basemap picker, scale.

	     The About dialog lives on the map rather than in the header because what
	     it explains, the line colours, is a question the map itself raises. -->
	<CustomControl position="bottom-right" group={false}>
		<AboutDialog />
	</CustomControl>
	<NavigationControl position="bottom-right" showCompass={false} />
	<GeolocateControl position="bottom-right" />

	<ScaleControl position="bottom-left" maxWidth={120} unit="metric" />
	<BasemapSwitcher />
	<Legend />

	<!-- Buses first so railways draw over them: a rail line is the thing a
	     visitor is most likely to be looking for, and bus routes are dense
	     enough to bury it otherwise. -->
	<VectorTileSource id="bus" url={tilesUrl('bus')} attribution="">
		<LineLayer
			id="bus-line"
			sourceLayer="bus"
			filter={mapView.filter}
			layout={{
				visibility: busVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': statusColor,
				'line-opacity': 0.85,
				// The dash pattern is measured in line widths, so widening the
				// line lengthens the dashes with it; the ratio tightens to keep
				// the route reading as dashed rather than as a chain of blobs.
				'line-dasharray': [1, 2],
				'line-width': busWidth
			}}
			onmousemove={(event) => (hoveredBus = read(event))}
			onmouseleave={() => (hoveredBus = null)}
			onclick={(event) => pick(event, 'bus')}
		/>
	</VectorTileSource>

	<!-- Bus stops sit above their routes and below the railways, the same order
	     the lines themselves are in. They only appear from z13: nationwide there
	     are a quarter of a million of them, and at city zooms they are what a
	     visitor is actually looking for rather than clutter. -->
	<VectorTileSource id="busstop" url={tilesUrl('busstop')} attribution="">
		<CircleLayer
			id="busstop-dot"
			sourceLayer="busstop"
			minzoom={13}
			filter={mapView.filter}
			layout={{ visibility: busStopVisibility }}
			paint={{
				// Hollow, blue-ringed and exactly the size of a station dot: the
				// two read as the same kind of thing — a place you board — and
				// the blue keeps them apart from the acceptance colours. See
				// `BUS_STOP_COLOR`.
				'circle-color': paper,
				'circle-stroke-color': BUS_STOP_COLOR,
				'circle-stroke-width': 1.8,
				'circle-opacity': 1,
				'circle-stroke-opacity': 1,
				'circle-radius': STOP_RADIUS
			}}
			onclick={(event) => pick(event, 'busstop')}
		/>
		<!-- Two zooms later than the dots, and `text-optional` on both, so a
		     crowded terminal drops bus stop names before station names. -->
		<SymbolLayer
			id="busstop-label"
			sourceLayer="busstop"
			minzoom={15}
			filter={mapView.filter}
			layout={{
				visibility: busStopVisibility,
				'text-field': labelField,
				'text-font': ['Noto Sans Regular'],
				'text-size': 10,
				'text-anchor': 'left',
				'text-offset': [0.6, 0],
				'text-optional': true
			}}
			paint={{
				'text-color': ink,
				'text-halo-color': paper,
				'text-halo-width': 1.2,
				'text-opacity': 0.9
			}}
		/>
	</VectorTileSource>

	<VectorTileSource id="railway" url={tilesUrl('railway')} attribution="">
		<!-- A casing under the coloured line keeps green-on-green readable where a
		     railway crosses a park or a golf course on the basemap. -->
		<LineLayer
			id="railway-casing"
			sourceLayer="railway"
			filter={mapView.filter}
			layout={{
				visibility: railwayVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': paper,
				'line-opacity': 0.9,
				'line-width': railwayCasingWidth
			}}
		/>
		<LineLayer
			id="railway-line"
			sourceLayer="railway"
			filter={mapView.filter}
			layout={{
				visibility: railwayVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': statusColor,
				'line-opacity': 1,
				'line-width': railwayWidth
			}}
			onmousemove={(event) => (hoveredRailway = read(event))}
			onmouseleave={() => (hoveredRailway = null)}
			onclick={(event) => pick(event, 'railway')}
		/>
	</VectorTileSource>

	<VectorTileSource id="station" url={tilesUrl('station')} attribution="">
		<CircleLayer
			id="station-dot"
			sourceLayer="station"
			minzoom={9}
			filter={mapView.filter}
			layout={{ visibility: stationVisibility }}
			paint={{
				'circle-color': paper,
				'circle-stroke-color': statusColor,
				'circle-stroke-width': 1.8,
				'circle-opacity': 1,
				'circle-stroke-opacity': 1,
				'circle-radius': STOP_RADIUS
			}}
			onclick={(event) => pick(event, 'station')}
		/>
		<!-- Labels only from z12: below that the dots already say where stations
		     are, and the names collide into an unreadable mat. -->
		<SymbolLayer
			id="station-label"
			sourceLayer="station"
			minzoom={12}
			filter={mapView.filter}
			layout={{
				visibility: stationVisibility,
				'text-field': labelField,
				'text-font': ['Noto Sans Medium'],
				'text-size': 11,
				'text-anchor': 'left',
				'text-offset': [0.7, 0],
				'text-optional': true
			}}
			paint={{
				'text-color': ink,
				'text-halo-color': paper,
				'text-halo-width': 1.4,
				'text-opacity': 1
			}}
		/>
	</VectorTileSource>

	{#if popup}
		<FeaturePopup info={popup} {locale} onclose={() => (popup = null)} />
	{/if}

	<LayerControl />
</MapLibre>

{#if !loaded}
	<div
		class="pointer-events-none absolute inset-0 flex items-center justify-center gap-3 bg-background/70"
	>
		<Spinner />
		<span class="text-sm text-muted-foreground">{t.map.loading}</span>
	</div>
{/if}
