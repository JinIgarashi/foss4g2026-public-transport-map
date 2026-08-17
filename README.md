# Japan Public Transport IC Card Map

**Where does my Suica actually work?**

Japan has ten transit IC cards — Suica, PASMO, ICOCA, TOICA, manaca, PiTaPa,
Kitaca, SUGOCA, nimoca and Hayakaken — and since 2013 they are mutually usable:
if a railway or bus accepts any of them, your Suica works there too. Where that
is true is documented across a few hundred operator pages and PDFs, which is not
much help when you are standing at a ticket gate.

This is an interactive map of every railway line and bus route in Japan, coloured
by whether the ten cards are accepted. Built for visitors coming to
[FOSS4G Hiroshima 2026](https://2026.foss4g.org), so it opens on Hiroshima — but
attendees travel, so it covers the whole country.

English and Japanese. Live at
<https://jinigarashi.github.io/foss4g2026-public-transport-map>.

## How to read it

|                        |                                                                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 🟢 **Accepted**        | The ten cards work across this operator.                                                                                     |
| 🟠 **Partly accepted** | Only inside certain IC areas or on certain sections — long JR lines run in and out of coverage. Check the note in the popup. |
| 🔴 **Not accepted**    | No IC ticketing. Buy a paper ticket or pay cash.                                                                             |
| ⚪ **Unconfirmed**     | We could not determine it. Not the same as "not accepted".                                                                   |

This is a hobby project, not an official service. Use it to plan; confirm with
the operator before you rely on it at a gate.

## Development

```bash
pnpm install
pnpm dev
```

Needs `PUBLIC_PROTOMAP_KEY` in `.env` for the [Protomaps](https://protomaps.com/)
basemap — copy `.env.example` and fill it in.

```bash
pnpm check    # svelte-check
pnpm lint     # prettier + eslint
pnpm build    # static build into ./build
pnpm tiles    # regenerate the PMTiles — see scripts/README.md
```

The vector tiles in `static/tiles/` are committed, so a fresh checkout runs
without the Python pipeline. Regenerating them is documented in
[`scripts/README.md`](scripts/README.md), which is also where the IC-card
acceptance table and the review behind it are explained.

## Stack

SvelteKit (static adapter, prerendered) · MapLibre GL JS via
[svelte-maplibre-gl](https://github.com/MIERUNE/svelte-maplibre-gl) · PMTiles ·
shadcn-svelte + Tailwind CSS v4 · Python + tippecanoe for the tiles.

Localisation is hand-rolled: the `[lang]` route segment is the single source of
truth, and `src/lib/i18n/messages/en.ts` is typed as the contract every other
locale must satisfy.

## Data

- Railway (N02) and bus route (N07) geometries: MLIT
  [National Land Numerical Information](https://nlftp.mlit.go.jp/ksj/), CC BY 4.0.
- IC card acceptance: compiled by hand from the participating-operator list in
  the Japanese Wikipedia article on the nationwide mutual-use service,
  cross-checked against the lists published by JR East and JR West.
- Basemap: Protomaps and OpenStreetMap contributors.

## Licence

MIT — see [LICENSE](LICENSE).
