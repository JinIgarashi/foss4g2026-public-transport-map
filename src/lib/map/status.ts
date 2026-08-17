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
 * Line colours. Chosen to stay apart for the most common colour-vision
 * deficiencies — green vs amber vs red alone would not — by pairing hue with a
 * clear lightness ramp, and to hold up on every Protomaps flavour the style
 * switcher offers, White through Dark. The casings and halos around them do
 * flip with the basemap; see `paper` and `ink` in `MapView.svelte`.
 */
export const STATUS_COLOR: Record<StatusKey, string> = {
	full: '#0f9d58',
	partial: '#f09300',
	none: '#d93025',
	unknown: '#9aa0a6'
};

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
