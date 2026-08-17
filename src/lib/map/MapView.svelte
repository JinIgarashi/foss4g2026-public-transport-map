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
	import {
		BUS_STOP_COLOR,
		LINE_COLOR,
		LINE_COLOR_DARK,
		SHINKANSEN_COLOR,
		SHINKANSEN_COLOR_DARK,
		statusColorExpression
	} from './status';
	import { railKindFilter } from './railway';
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
	 * Bus stops keep the smaller of the two dot sizes. They are the denser
	 * layer by far, and at z13 upwards there are enough of them on screen that
	 * a larger dot would close the gaps between them.
	 */
	const BUSSTOP_RADIUS: DataDrivenPropertyValueSpecification<number> = [
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

	/**
	 * Stations are drawn a size and a half larger than bus stops: they are what
	 * a visitor navigates by, they come in at z9 where the map is still coarse,
	 * and at the old size they were easy to lose against the line they sit on.
	 * The legend follows the same size relation.
	 */
	const STATION_RADIUS: DataDrivenPropertyValueSpecification<number> = [
		'interpolate',
		['linear'],
		['zoom'],
		9,
		3.5,
		12,
		5.5,
		15,
		7.5
	];

	/** Ink that has to stay legible against the basemap, not against the theme. */
	let paper = $derived(mapView.isDarkBasemap ? '#0b1120' : '#ffffff');
	let ink = $derived(mapView.isDarkBasemap ? '#e8eaed' : '#1f2328');
	/** The route colours, which flip with the basemap for the same reason. */
	let lineColor = $derived(mapView.isDarkBasemap ? LINE_COLOR_DARK : LINE_COLOR);
	let shinkansenColor = $derived(mapView.isDarkBasemap ? SHINKANSEN_COLOR_DARK : SHINKANSEN_COLOR);

	let busVisibility = $derived<VisibilitySpecification>(
		mapView.isVisible('bus') ? 'visible' : 'none'
	);
	let shinkansenVisibility = $derived<VisibilitySpecification>(
		mapView.isVisible('shinkansen') ? 'visible' : 'none'
	);
	let railwayVisibility = $derived<VisibilitySpecification>(
		mapView.isVisible('railway') ? 'visible' : 'none'
	);
	let tramVisibility = $derived<VisibilitySpecification>(
		mapView.isVisible('tram') ? 'visible' : 'none'
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

	/**
	 * Layers a click can open a popup for, innermost first. Each rail group is
	 * represented by its casing, the widest layer of the three and so the easiest
	 * to hit — the hatch drawn on top of it has gaps a click could fall through.
	 */
	const CLICKABLE = [
		'station-dot',
		'busstop-dot',
		'shinkansen-casing',
		'railway-casing',
		'tram-casing',
		'bus-casing'
	];

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

	type WidthStops = [zoom: number, base: number, wide: number][];

	/**
	 * Route widths. The lines themselves never change width — not with hover,
	 * only with zoom — so their `wide` column repeats the base; what widens is
	 * the casing under them.
	 */
	const RAIL_LINE: WidthStops = [
		[5, 2, 2],
		[10, 4.5, 4.5],
		[14, 8, 8]
	];
	const TRAM_LINE: WidthStops = [
		[5, 1, 1],
		[10, 2.5, 2.5],
		[14, 5, 5]
	];
	const BUS_LINE: WidthStops = [
		[6, 1, 1],
		[10, 2.2, 2.2],
		[14, 4.5, 4.5]
	];

	const scale = (stops: WidthStops, factor: number): WidthStops =>
		stops.map(([zoom, base, wide]) => [zoom, base * factor, wide * factor]);

	/**
	 * The acceptance-coloured casing: 1px of colour down each side of the route,
	 * and 3px when the route is hovered. Since the line on top keeps its width,
	 * that growing rim is the whole of the hover highlight — at 2px it was too
	 * small a change to notice against a 1px rim.
	 */
	const casing = (stops: WidthStops): WidthStops =>
		stops.map(([zoom, base]) => [zoom, base + 2, base + 6]);

	// Bus routes are dissolved per operator name, so `nm` + `op` is the route.
	let busKeys: ('nm' | 'op')[] = ['nm', 'op'];
	// Railways are split per section, so company + line name is the line.
	let railKeys: ('nm' | 'ln')[] = ['nm', 'ln'];

	const busWidth = hoverWidth(null, busKeys, BUS_LINE);
	let busCasingWidth = $derived(hoverWidth(hoveredBus, busKeys, casing(BUS_LINE)));

	// A shinkansen is drawn wider than the line it runs beside. The hatch is a
	// multiple of the line width, so widening it does not change the pattern.
	const SHINKANSEN_LINE = scale(RAIL_LINE, 1.35);
	const shinkansenWidth = hoverWidth(null, railKeys, SHINKANSEN_LINE);
	let shinkansenCasingWidth = $derived(
		hoverWidth(hoveredRailway, railKeys, casing(SHINKANSEN_LINE))
	);

	const railwayWidth = hoverWidth(null, railKeys, RAIL_LINE);
	let railwayCasingWidth = $derived(hoverWidth(hoveredRailway, railKeys, casing(RAIL_LINE)));

	const tramWidth = hoverWidth(null, railKeys, TRAM_LINE);
	let tramCasingWidth = $derived(hoverWidth(hoveredRailway, railKeys, casing(TRAM_LINE)));

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

	<!-- MapLibre *prepends* into the bottom corners, so the reading order down the
	     screen is the reverse of the order here: bottom-right ends up geolocate,
	     zoom, attribution, and bottom-left legend, basemap picker, scale.

	     Keyed on the locale because the attribution text is localised, and
	     `AttributionControl` answers a changed `customAttribution` by removing and
	     re-adding its control — which, with prepending, lands it above everything
	     else in the corner. Rebuilding the whole corner together is what puts it
	     back at the bottom where it belongs; re-adding it alone cannot. -->
	{#key locale}
		<AttributionControl
			position="bottom-right"
			compact
			customAttribution={`<a href="https://nlftp.mlit.go.jp/ksj/" target="_blank" rel="noopener noreferrer">${t.map.attribution}</a> (CC BY 4.0)`}
		/>
		<NavigationControl position="bottom-right" showCompass={true} />
		<GeolocateControl position="bottom-right" />
	{/key}

	<!-- The About dialog lives on the map rather than in the header because what
	     it explains, the line colours, is a question the map itself raises. -->
	<CustomControl position="top-right" group={false}>
		<AboutDialog />
	</CustomControl>

	<ScaleControl position="bottom-left" maxWidth={120} unit="metric" />
	<BasemapSwitcher />
	<Legend />

	<!-- Buses first so railways draw over them: a rail line is the thing a
	     visitor is most likely to be looking for, and bus routes are dense
	     enough to bury it otherwise.

	     They only start at z10, the zoom a bus route is a route rather than a
	     smear. Each mode comes in at the scale it means something on — the
	     shinkansen at z4, railways at z6, trams and buses at z10 — because
	     drawing all of them from z0 turned the country view into a mat. -->
	<VectorTileSource id="bus" url={tilesUrl('bus')} attribution="">
		<!-- The casing stays solid where the route is dotted. A dotted casing
		     would have to keep its dots in step with the ones on top, and a dash
		     pattern is measured in line widths — so a wider casing spaces its dots
		     further apart and drifts out of phase along the route. Solid, it reads
		     as a thin acceptance-coloured route with the bus dots laid over it. -->
		<LineLayer
			id="bus-casing"
			sourceLayer="bus"
			minzoom={10}
			filter={mapView.filter}
			layout={{
				visibility: busVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': statusColor,
				'line-opacity': 0.85,
				'line-width': busCasingWidth
			}}
			onmousemove={(event) => (hoveredBus = read(event))}
			onmouseleave={() => (hoveredBus = null)}
			onclick={(event) => pick(event, 'bus')}
		/>
		<!-- Between the two: a solid `paper` core the width of the dots, so what
		     shows between them is the ground rather than the casing colour. Without
		     it the route reads as a coloured line with dots on it instead of as a
		     dotted black line with a coloured rim. -->
		<LineLayer
			id="bus-core"
			sourceLayer="bus"
			minzoom={10}
			filter={mapView.filter}
			layout={{
				visibility: busVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': paper,
				'line-opacity': 1,
				'line-width': busWidth
			}}
		/>
		<!-- A zero-length dash with round caps is a dot the width of the line. -->
		<LineLayer
			id="bus-line"
			sourceLayer="bus"
			minzoom={10}
			filter={mapView.filter}
			layout={{
				visibility: busVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': lineColor,
				'line-opacity': 1,
				'line-dasharray': [0, 2],
				'line-width': busWidth
			}}
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
				// Hollow and blue-ringed: it reads as the same kind of thing as a
				// station — a place you board — a size down, and the blue keeps
				// it apart from the acceptance colours. See `BUS_STOP_COLOR`.
				'circle-color': paper,
				'circle-stroke-color': BUS_STOP_COLOR,
				'circle-stroke-width': 1.8,
				'circle-opacity': 1,
				'circle-stroke-opacity': 1,
				'circle-radius': BUSSTOP_RADIUS
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

	<!-- One source, three groups drawn bottom to top: trams, then local railways,
	     then the shinkansen, so the fastest line stays legible where several run
	     side by side.

	     Every group is the same three-layer sandwich: an acceptance-coloured
	     casing, the route itself in its mode colour, and — for the two hatched
	     kinds — white ticks punched through it. Where a tick falls, the casing
	     shows as a rim around the white rather than as colour across the line,
	     which is why the casing has to be the widest of the three.

	     The hatch layers are `line-cap: 'butt'`: round caps grow each dash by
	     half a width at both ends, which closes up a fine hatch into a solid
	     line. Dash lengths are multiples of the line width, so they follow the
	     zoom ramp on their own. -->
	<VectorTileSource id="railway" url={tilesUrl('railway')} attribution="">
		<!-- A tram is the one rail kind drawn unhatched: the lines are short and
		     tightly curved, and a hatch on them reads as noise. -->
		<LineLayer
			id="tram-casing"
			sourceLayer="railway"
			minzoom={10}
			filter={railKindFilter('tram', mapView.filter)}
			layout={{
				visibility: tramVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': statusColor,
				'line-opacity': 1,
				'line-width': tramCasingWidth
			}}
			onmousemove={(event) => (hoveredRailway = read(event))}
			onmouseleave={() => (hoveredRailway = null)}
			onclick={(event) => pick(event, 'railway')}
		/>
		<LineLayer
			id="tram-line"
			sourceLayer="railway"
			minzoom={10}
			filter={railKindFilter('tram', mapView.filter)}
			layout={{
				visibility: tramVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': lineColor,
				'line-opacity': 1,
				'line-width': tramWidth
			}}
		/>

		<LineLayer
			id="railway-casing"
			sourceLayer="railway"
			minzoom={6}
			filter={railKindFilter('railway', mapView.filter)}
			layout={{
				visibility: railwayVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': statusColor,
				'line-opacity': 1,
				'line-width': railwayCasingWidth
			}}
			onmousemove={(event) => (hoveredRailway = read(event))}
			onmouseleave={() => (hoveredRailway = null)}
			onclick={(event) => pick(event, 'railway')}
		/>
		<LineLayer
			id="railway-line"
			sourceLayer="railway"
			minzoom={6}
			filter={railKindFilter('railway', mapView.filter)}
			layout={{
				visibility: railwayVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': lineColor,
				'line-opacity': 1,
				'line-width': railwayWidth
			}}
		/>
		<LineLayer
			id="railway-hatch"
			sourceLayer="railway"
			minzoom={6}
			filter={railKindFilter('railway', mapView.filter)}
			layout={{
				visibility: railwayVisibility,
				'line-cap': 'butt',
				'line-join': 'round'
			}}
			paint={{
				'line-color': paper,
				'line-opacity': 1,
				// Short ticks on a long run: an even 1:1 alternation breaks the
				// line into a chain of blocks at close zooms.
				'line-dasharray': [0.6, 1.6],
				'line-width': railwayWidth
			}}
		/>

		<!-- The shinkansen: the same hatch, in blue and a third wider again, so it
		     stays the line you find first where several run together. -->
		<LineLayer
			id="shinkansen-casing"
			sourceLayer="railway"
			minzoom={4}
			filter={railKindFilter('shinkansen', mapView.filter)}
			layout={{
				visibility: shinkansenVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': statusColor,
				'line-opacity': 1,
				'line-width': shinkansenCasingWidth
			}}
			onmousemove={(event) => (hoveredRailway = read(event))}
			onmouseleave={() => (hoveredRailway = null)}
			onclick={(event) => pick(event, 'railway')}
		/>
		<LineLayer
			id="shinkansen-line"
			sourceLayer="railway"
			minzoom={4}
			filter={railKindFilter('shinkansen', mapView.filter)}
			layout={{
				visibility: shinkansenVisibility,
				'line-cap': 'round',
				'line-join': 'round'
			}}
			paint={{
				'line-color': shinkansenColor,
				'line-opacity': 1,
				'line-width': shinkansenWidth
			}}
		/>
		<LineLayer
			id="shinkansen-hatch"
			sourceLayer="railway"
			minzoom={4}
			filter={railKindFilter('shinkansen', mapView.filter)}
			layout={{
				visibility: shinkansenVisibility,
				'line-cap': 'butt',
				'line-join': 'round'
			}}
			paint={{
				'line-color': paper,
				'line-opacity': 1,
				'line-dasharray': [0.6, 1.6],
				'line-width': shinkansenWidth
			}}
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
				// The ring takes the line colour, not the acceptance colour: a
				// station belongs to the line it sits on, and the acceptance
				// colour is the casing's job everywhere else on the map.
				'circle-color': paper,
				'circle-stroke-color': lineColor,
				// Thicker than the bus stop ring in proportion to the larger
				// radius: at 1.8 the bigger dot read as a white blob.
				'circle-stroke-width': 2.2,
				'circle-opacity': 1,
				'circle-stroke-opacity': 1,
				'circle-radius': STATION_RADIUS
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
