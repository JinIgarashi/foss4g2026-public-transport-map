import type { ExpressionSpecification } from 'maplibre-gl';

/**
 * IC-card acceptance, as written into the tiles by `scripts/coverage.py`.
 * The numbers are part of the tile format — renumbering them silently breaks
 * every published tileset, so they are fixed here and there together.
 */
export const STATUS = {
	none: 0,
	full: 1,
	partial: 2,
	unknown: 3
} as const;

export type StatusKey = keyof typeof STATUS;
export type StatusCode = (typeof STATUS)[StatusKey];

/** Legend order: best news first, "we don't know" last. */
export const STATUS_KEYS: StatusKey[] = ['full', 'partial', 'none', 'unknown'];

export const STATUS_BY_CODE: Record<number, StatusKey> = Object.fromEntries(
	Object.entries(STATUS).map(([key, code]) => [code, key as StatusKey])
) as Record<number, StatusKey>;

/**
 * Acceptance colours. Chosen to stay apart for the most common colour-vision
 * deficiencies — green vs amber vs red alone would not — by pairing hue with a
 * clear lightness ramp, and to hold up on every Protomaps flavour the style
 * switcher offers, White through Dark.
 *
 * These paint the *casing* under each route rather than the route itself: the
 * line on top carries the mode in a fixed colour (see `LINE_COLOR`), and the
 * acceptance colour reads as an outline around it.
 */
export const STATUS_COLOR: Record<StatusKey, string> = {
	full: '#0f9d58',
	partial: '#f09300',
	none: '#d93025',
	unknown: '#9aa0a6'
};

/**
 * The ring around a bus stop. Bus stops are the one thing on the map that is not
 * coloured by acceptance: at z13 and closer there are hundreds of them in view,
 * and four colours of dot on top of four colours of line was unreadable. One
 * blue ring on a hollow dot says "bus stop" and leaves the colour vocabulary to
 * the routes underneath, which carry the same operator's acceptance anyway. The
 * status filter still applies, so a stop hidden by the filter disappears.
 */
export const BUS_STOP_COLOR = '#1a73e8';

/**
 * The colour of the route itself, which says what kind of transit it is and
 * nothing about IC cards: dark for railways, trams and buses, blue for the
 * shinkansen. Station rings take `LINE_COLOR` too, so a station reads as
 * belonging to the line it sits on.
 *
 * Each has a light counterpart for the Dark basemap flavour, where a near-black
 * line would vanish into the ground. `MapView.svelte` picks between them the
 * same way it picks `paper` and `ink`.
 */
export const LINE_COLOR = '#3c4043';
export const LINE_COLOR_DARK = '#e8eaed';
export const SHINKANSEN_COLOR = '#1967d2';
export const SHINKANSEN_COLOR_DARK = '#8ab4f8';

/** `["match", ["get","st"], 0, colour, …]` for a paint property. */
export function statusColorExpression(): ExpressionSpecification {
	const stops = STATUS_KEYS.flatMap((key) => [STATUS[key], STATUS_COLOR[key]]);
	// `match` is variadic; the style spec models it as a fixed-arity tuple, so a
	// generated stop list can never satisfy it structurally.
	return [
		'match',
		['get', 'st'],
		...stops,
		STATUS_COLOR.unknown
	] as unknown as ExpressionSpecification;
}
