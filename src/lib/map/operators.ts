import { LngLatBounds } from 'maplibre-gl';
import indexData from '$lib/data/operators.json';
import type { Locale } from '$lib/i18n';
import type { StatusKey } from './status';

export interface OperatorEntry {
	id: string;
	ja: string;
	en?: string;
	/** `en` is a transliteration from `build_tiles.py`, not a curated name. */
	enAuto?: boolean;
	status: StatusKey;
	modes: ('rail' | 'bus')[];
	area?: string;
	note?: { en: string | null; ja: string | null };
	/** `[west, south, east, north]` over every feature, from `build_tiles.py`. */
	bbox?: [number, number, number, number];
}

export interface AreaEntry {
	name: { en: string; ja: string };
	issuer: string;
}

const index = indexData as unknown as {
	areas: Record<string, AreaEntry>;
	operators: OperatorEntry[];
};

/** Every operator that appears in the tiles, sorted by display name. */
export const OPERATORS: OperatorEntry[] = index.operators;

export const AREAS: Record<string, AreaEntry> = index.areas;

const BY_ID = new Map(OPERATORS.map((operator) => [operator.id, operator]));

export function operatorById(id: string): OperatorEntry | undefined {
	return BY_ID.get(id);
}

/**
 * Display name for the active locale. Operators a visitor is likely to meet have
 * a curated English name; the 1,400 community bus services behind them carry a
 * transliterated one flagged `enAuto`, which is still far more use to a reader
 * of English than the Japanese would be. The Japanese name is shown alongside it
 * in the popup, so a wrong reading is visibly a reading and not a claim.
 */
export function operatorName(operator: OperatorEntry, locale: Locale): string {
	return locale === 'en' ? (operator.en ?? operator.ja) : operator.ja;
}

export interface OperatorSearchEntry {
	operator: OperatorEntry;
	haystack: string;
}

/**
 * Pre-built search text, one pass at module load rather than per keystroke over
 * 1,500 operators. Both names go in so `広島電鉄` and `Hiroshima` find the same
 * company whichever language the visitor is reading in, and the id slug adds the
 * romanisation (`hiroden`) that neither display name carries.
 */
export const OPERATOR_SEARCH: OperatorSearchEntry[] = OPERATORS.map((operator) => ({
	operator,
	haystack: `${operator.ja} ${operator.en ?? ''} ${operator.id.replace(/-/g, ' ')}`.toLowerCase()
}));

export function areaName(areaId: string | undefined, locale: Locale): string | undefined {
	if (!areaId) return undefined;
	return AREAS[areaId]?.name[locale];
}

export function operatorNote(
	operator: OperatorEntry | undefined,
	locale: Locale
): string | undefined {
	return operator?.note?.[locale] ?? undefined;
}

/**
 * Operator ids are packed into the `op` tile attribute as `|a|b|`, because a
 * route can be run jointly by several companies and MapLibre has no array
 * membership test. Unpack for the popup.
 */
export function unpackOperatorIds(packed: string | undefined): string[] {
	if (!packed) return [];
	return packed.split('|').filter(Boolean);
}

/**
 * Combined extent of the given operators, for fitting the map to a filter.
 *
 * The bounds are baked into `operators.json` by the build rather than measured
 * from the map, because `querySourceFeatures` only ever reports the tiles that
 * happen to be loaded — picking a Hokkaido operator while looking at Hiroshima
 * would otherwise fit to nothing at all. `undefined` when no operator in the set
 * has bounds, which is what an `operators.json` built before this field looks
 * like; the caller then leaves the view alone.
 */
export function operatorBounds(ids: Iterable<string>): LngLatBounds | undefined {
	let bounds: LngLatBounds | undefined;
	for (const id of ids) {
		const bbox = operatorById(id)?.bbox;
		if (!bbox) continue;
		const [west, south, east, north] = bbox;
		if (bounds) bounds.extend([west, south]).extend([east, north]);
		else bounds = new LngLatBounds([west, south], [east, north]);
	}
	return bounds;
}
