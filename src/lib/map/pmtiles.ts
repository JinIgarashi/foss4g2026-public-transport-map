import type { AddProtocolAction } from 'maplibre-gl';
import { Protocol } from 'pmtiles';
import { browser } from '$app/environment';
import { base } from '$app/paths';

/**
 * Handler for the `pmtiles://` scheme, mounted through
 * `svelte-maplibre-gl`'s `<Protocol>` so it is torn down with the map.
 */
export const pmtilesProtocol: AddProtocolAction = new Protocol().tile;

/**
 * URL of a tileset in `static/tiles/`.
 *
 * PMTiles fetches the archive with HTTP range requests, so this has to be an
 * absolute URL: a site-relative path would resolve against the current page,
 * which breaks under the repository subpath the site is published on.
 */
export function tilesUrl(name: string): string {
	const path = `${base}/tiles/${name}.pmtiles`;
	return `pmtiles://${browser ? new URL(path, location.href).href : path}`;
}
