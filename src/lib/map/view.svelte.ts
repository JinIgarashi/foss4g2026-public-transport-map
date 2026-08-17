import { SvelteSet } from 'svelte/reactivity';
import type { FilterSpecification } from 'maplibre-gl';
import { STATUS, STATUS_KEYS, type StatusKey } from './status';

export type LayerKey = 'railway' | 'bus' | 'station' | 'busstop';

/** Protomaps basemap flavours offered by the style switcher. */
export type BasemapKey = 'white' | 'light' | 'dark';

/**
 * What the map is currently showing. A single rune-backed object rather than a
 * prop chain, because the controls, the legend and the layers all read and
 * write it from different corners of the tree.
 */
class MapView {
	#layers = $state<Record<LayerKey, boolean>>({
		railway: true,
		bus: true,
		station: true,
		busstop: true
	});
	#statuses = new SvelteSet<StatusKey>(STATUS_KEYS);
	#operators = new SvelteSet<string>();
	#basemap = $state<BasemapKey>('white');

	get layers() {
		return this.#layers;
	}

	isVisible(layer: LayerKey) {
		return this.#layers[layer];
	}

	toggleLayer(layer: LayerKey, value?: boolean) {
		this.#layers[layer] = value ?? !this.#layers[layer];
	}

	get statuses() {
		return this.#statuses;
	}

	hasStatus(status: StatusKey) {
		return this.#statuses.has(status);
	}

	toggleStatus(status: StatusKey, value?: boolean) {
		if (value ?? !this.#statuses.has(status)) this.#statuses.add(status);
		else this.#statuses.delete(status);
	}

	/** Basemap flavour the style switcher last picked. */
	get basemap() {
		return this.#basemap;
	}

	set basemap(value: BasemapKey) {
		this.#basemap = value;
	}

	/** Whether the basemap is dark, so overlay whites and blacks can swap. */
	get isDarkBasemap() {
		return this.#basemap === 'dark';
	}

	/** Operator ids to show. Empty means "show every operator". */
	get operators() {
		return this.#operators;
	}

	hasOperator(id: string) {
		return this.#operators.has(id);
	}

	toggleOperator(id: string, value?: boolean) {
		if (value ?? !this.#operators.has(id)) this.#operators.add(id);
		else this.#operators.delete(id);
	}

	clearOperators() {
		this.#operators.clear();
	}

	/**
	 * The `filter` every transit layer shares: acceptance status AND, when any
	 * operator is selected, operator membership.
	 *
	 * Filtering rather than fading, because something the visitor has excluded
	 * should not still swallow clicks meant for the line underneath it, and a
	 * dimmed nationwide bus network is still a nationwide bus network to read
	 * around.
	 *
	 * The `op` attribute packs every operator of a jointly run route as `|a|b|`;
	 * `["in", needle, haystack]` does substring matching on strings, and the pipes
	 * turn that into exact membership — without them `jr-east` would also match
	 * routes belonging only to `jr-east-bus`.
	 */
	get filter(): FilterSpecification {
		const codes = STATUS_KEYS.filter((key) => this.#statuses.has(key)).map((key) => STATUS[key]);
		const status: FilterSpecification = ['in', ['get', 'st'], ['literal', codes]];
		if (this.#operators.size === 0) return status;
		const clauses = [...this.#operators].map((id) => ['in', `|${id}|`, ['get', 'op']]);
		// `all` and `any` are variadic; the style spec models them as fixed-arity
		// tuples, so a generated clause list can never satisfy them structurally.
		return ['all', status, ['any', ...clauses]] as unknown as FilterSpecification;
	}
}

export const mapView = new MapView();
