/**
 * Source of truth for every user-facing string.
 *
 * `Messages` is derived from this object, so `ja.ts` is checked against it:
 * a missing key and an excess key are both type errors. Add strings here first.
 */
const en = {
	meta: {
		title: 'Where does my Suica work? — Japan Public Transport IC Card Map',
		description:
			'An interactive map of Japanese railways and bus routes, coloured by whether the nationwide transit IC cards (Suica, ICOCA, PASMO and the rest of the ten) are accepted. Built for FOSS4G Hiroshima 2026.'
	},

	header: {
		siteName: 'Japan Transit IC Card Map',
		logoAlt: 'FOSS4G Hiroshima 2026',
		theme: 'Theme',
		language: 'Language',
		github: 'Source code on GitHub',
		about: 'About this map'
	},

	theme: {
		light: 'Light',
		dark: 'Dark',
		system: 'System'
	},

	status: {
		full: {
			label: 'Accepted',
			description: 'The ten nationwide IC cards, including Suica, work across this operator.'
		},
		partial: {
			label: 'Partly accepted',
			description:
				'Accepted only inside certain IC areas or on certain sections. Check before you ride.'
		},
		none: {
			label: 'Not accepted',
			description: 'IC cards are not accepted as a ticket here. Buy a paper ticket or pay cash.'
		},
		unknown: {
			label: 'Unconfirmed',
			description:
				'We could not confirm this operator against the published lists. Treat it as unknown, not as "not accepted".'
		}
	},

	layers: {
		title: 'Layers',
		shinkansen: 'Shinkansen',
		railway: 'Railways',
		tram: 'Trams and monorails',
		bus: 'Bus routes',
		station: 'Railway stations',
		busstop: 'Bus stops',
		filterTitle: 'Show status',
		collapse: 'Hide panel',
		expand: 'Show layers and filters'
	},

	popup: {
		line: 'Line',
		mode: 'Type',
		operator: 'Operator',
		operatorType: 'Operator type',
		cardArea: 'IC card area',
		routes: 'Routes',
		moreRoutes: (count: number) => `and ${count} more`,
		station: 'Station',
		railway: 'Railway',
		bus: 'Bus route',
		busStop: 'Bus stop'
	},

	operatorFilter: {
		title: 'Filter operators',
		placeholder: 'Search operators…',
		empty: 'No operator found.',
		clear: 'Clear filter',
		allOperators: 'All operators',
		showing: (name: string) => `Showing only ${name}`,
		open: 'Choose operators',
		dialogTitle: 'Choose operators to show',
		dialogDescription:
			'Search by Japanese or English name, narrow by type or IC card status, and pick as many operators as you like. Everything else is hidden and the map zooms to what is left.',
		filterMode: 'Type',
		filterStatus: 'IC card',
		mode: {
			rail: 'Railway',
			bus: 'Bus'
		},
		results: (count: number) => `${count.toLocaleString('en')} match${count === 1 ? '' : 'es'}`,
		selectedCount: (count: number) => `${count} selected`,
		showingCount: (count: number) => `Showing ${count} operators`,
		clearAll: 'Clear all',
		showMore: (count: number) => `Show ${count.toLocaleString('en')} more`,
		close: 'Close'
	},

	railKind: {
		'11': 'JR conventional railway',
		'12': 'Railway',
		'13': 'Funicular',
		'14': 'Suspended monorail',
		'15': 'Straddle-beam monorail',
		'16': 'Guideway transit',
		'17': 'Trolleybus',
		'21': 'Tramway',
		'22': 'Suspended monorail',
		'23': 'Straddle-beam monorail',
		'24': 'Guideway transit',
		'25': 'Maglev'
	},

	institution: {
		'1': 'JR Shinkansen',
		'2': 'JR conventional line',
		'3': 'Public railway',
		'4': 'Private railway',
		'5': 'Third-sector railway'
	},

	about: {
		title: 'About this map',
		intro:
			'Japan has ten transit IC cards — Suica, PASMO, ICOCA, TOICA, manaca, PiTaPa, Kitaca, SUGOCA, nimoca and Hayakaken — and since 2013 they are mutually usable. If a railway or bus accepts any of them, your Suica works there too. This map shows where that is, and where it is not.',
		howToRead: 'How to read it',
		howToReadBody:
			'Acceptance is the colour of the outline around each route; the route itself is coloured by what it is, blue for the shinkansen and dark for everything else. Green means your Suica works. Amber means the operator only accepts IC cards inside certain areas or on certain sections — long JR lines run in and out of coverage, so read the note in the popup. Red means no IC ticketing at all. Grey means we could not confirm the operator; that is not the same as "not accepted".',
		dataSources: 'Data sources',
		icSource: 'IC card acceptance',
		icSourceBody:
			'Compiled by hand from the list of participating operators in the Japanese Wikipedia article on the nationwide mutual-use service, cross-checked against the operator lists published by JR East and JR West.',
		basemap: 'Basemap',
		names: 'English names',
		namesBody:
			'MLIT publishes no English names at all, so station, bus stop, line and operator names in English come from the `name:en` tags of OpenStreetMap and from Wikidata where they exist. Everything else is transliterated automatically, which gets the reading of a place name wrong now and then — the Japanese name is always shown alongside.',
		disclaimer: 'Please read',
		disclaimerBody:
			'This is a hobby project, not an official service. IC card coverage changes, the bus dataset is from 2022, and the acceptance table is our own compilation. Use it to plan, but confirm with the operator before you rely on it at a ticket gate.',
		asOf: (date: string) => `IC card coverage as of ${date}.`,
		license: 'Licence',
		licenseBody:
			'The railway and bus geometries are National Land Numerical Information published by MLIT under CC BY 4.0.',
		close: 'Close'
	},

	map: {
		loading: 'Loading map…',
		attribution:
			'MLIT National Land Numerical Information (Railway N02 / Bus routes N07 / Bus stops P11)'
	}
};

export default en;

export type Messages = typeof en;
