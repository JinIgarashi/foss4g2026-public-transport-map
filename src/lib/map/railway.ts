import type { ExpressionSpecification, FilterSpecification } from 'maplibre-gl';

/**
 * The three kinds of rail line the map draws differently. Shinkansen and local
 * railways are told apart by line style rather than colour, because colour is
 * already spoken for by IC card acceptance; see `status.ts`.
 */
export type RailKindKey = 'shinkansen' | 'railway' | 'tram';

/** Draw order, bottom to top: the shinkansen wins where lines run together. */
export const RAIL_KIND_KEYS: RailKindKey[] = ['tram', 'railway', 'shinkansen'];

/**
 * N02_001 railway class codes, written into the tiles as `kd` by
 * `scripts/n02_railway.py`. 21–25 are the 軌道法 group; of those, tramways,
 * both monorail kinds and guideway transit read as street-level or light
 * transit and are drawn as trams. Maglev (25) is a high-speed railway and
 * stays with the railways.
 *
 * Both `kd` and `it` are strings in the tiles, not numbers, so every
 * comparison here has to be against a string literal.
 */
const TRAM_KINDS = ['21', '22', '23', '24'];

/** N02_002 institution type `it`: 1 is JR Shinkansen. */
const SHINKANSEN: ExpressionSpecification = ['==', ['get', 'it'], '1'];

const TRAM = [
	'all',
	['!', SHINKANSEN],
	['in', ['get', 'kd'], ['literal', TRAM_KINDS]]
] as unknown as ExpressionSpecification;

/** Everything left over — including features with no `kd` at all. */
const RAILWAY = ['all', ['!', SHINKANSEN], ['!', TRAM]] as unknown as ExpressionSpecification;

const FILTERS: Record<RailKindKey, ExpressionSpecification> = {
	shinkansen: SHINKANSEN,
	railway: RAILWAY,
	tram: TRAM
};

/**
 * The kind test for one group, `and`-ed with whatever else is filtering the
 * layer. The three are mutually exclusive and cover every feature, so no line
 * is drawn twice and none is dropped.
 */
export function railKindFilter(kind: RailKindKey, base: FilterSpecification): FilterSpecification {
	return ['all', base, FILTERS[kind]] as unknown as FilterSpecification;
}
