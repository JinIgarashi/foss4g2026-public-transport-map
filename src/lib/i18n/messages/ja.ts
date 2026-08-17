import type { Messages } from './en';

/**
 * The `Messages` annotation is what makes this file safe to edit: TypeScript
 * reports a missing key and a leftover key alike, so this file cannot silently
 * drift from `en.ts`.
 */
const ja: Messages = {
	meta: {
		title: 'Suicaはどこで使える？ — 日本の交通系ICカード対応マップ',
		description:
			'全国の鉄道路線とバスルートを、交通系ICカード全国相互利用サービス（Suica・ICOCA・PASMOなど10カード）が使えるかどうかで色分けした地図です。FOSS4G Hiroshima 2026 参加者向け。'
	},

	header: {
		siteName: '交通系ICカード対応マップ',
		logoAlt: 'FOSS4G Hiroshima 2026',
		theme: 'テーマ',
		language: '言語',
		github: 'GitHubでソースコードを見る',
		about: 'この地図について'
	},

	theme: {
		light: 'ライト',
		dark: 'ダーク',
		system: 'システム'
	},

	status: {
		full: {
			label: '利用できる',
			description: 'Suicaを含む全国相互利用の10カードが、この事業者の全線で使えます。'
		},
		partial: {
			label: '一部で利用できる',
			description: '特定のICエリア内や一部区間でのみ使えます。乗車前に対象区間を確認してください。'
		},
		none: {
			label: '利用できない',
			description: 'ICカードは乗車券として使えません。きっぷを購入するか現金で支払ってください。'
		},
		unknown: {
			label: '確認できていない',
			description:
				'公開されている対象事業者一覧と照合できませんでした。「利用不可」ではなく「不明」です。'
		}
	},

	layers: {
		title: 'レイヤー',
		railway: '鉄道',
		bus: 'バスルート',
		station: '駅',
		filterTitle: '表示する状態',
		collapse: 'パネルを隠す',
		expand: 'レイヤーと絞り込みを表示'
	},

	legend: {
		title: 'ICカードの対応状況',
		railwayLine: '鉄道',
		busLine: 'バスルート',
		collapse: '凡例を隠す',
		expand: '凡例を表示'
	},

	popup: {
		line: '路線',
		mode: '種別',
		operatorType: '事業者種別',
		cardArea: 'ICカードエリア',
		station: '駅',
		railway: '鉄道',
		bus: 'バスルート'
	},

	operatorFilter: {
		title: '事業者で絞り込み',
		placeholder: '事業者を検索…',
		empty: '該当する事業者がありません。',
		clear: '絞り込みを解除',
		allOperators: 'すべての事業者',
		showing: (name: string) => `${name} のみ表示中`,
		open: '事業者を選ぶ',
		dialogTitle: '表示する事業者を選ぶ',
		dialogDescription:
			'日本語名・英語名・ローマ字で検索できます。種別やICカード対応状況で絞り込み、複数の事業者を選べます。選んだ事業者以外は非表示になり、地図はその範囲にズームします。',
		filterMode: '種別',
		filterStatus: 'ICカード',
		mode: {
			rail: '鉄道',
			bus: 'バス'
		},
		results: (count: number) => `${count.toLocaleString('ja')} 件`,
		selectedCount: (count: number) => `${count} 件選択中`,
		showingCount: (count: number) => `${count} 事業者のみ表示中`,
		clearAll: 'すべて解除',
		showMore: (count: number) => `さらに ${count.toLocaleString('ja')} 件表示`,
		close: '閉じる'
	},

	railKind: {
		'11': '普通鉄道（JR）',
		'12': '普通鉄道',
		'13': '鋼索鉄道（ケーブルカー）',
		'14': '懸垂式モノレール',
		'15': '跨座式モノレール',
		'16': '案内軌条式鉄道',
		'17': '無軌条鉄道（トロリーバス）',
		'21': '軌道（路面電車）',
		'22': '懸垂式モノレール',
		'23': '跨座式モノレール',
		'24': '案内軌条式',
		'25': '浮上式鉄道'
	},

	institution: {
		'1': 'JR新幹線',
		'2': 'JR在来線',
		'3': '公営鉄道',
		'4': '民営鉄道',
		'5': '第三セクター'
	},

	about: {
		title: 'この地図について',
		intro:
			'日本にはSuica・PASMO・ICOCA・TOICA・manaca・PiTaPa・Kitaca・SUGOCA・nimoca・はやかけんの10種類の交通系ICカードがあり、2013年から相互に利用できます。つまりどれか1枚に対応している鉄道・バスなら、手持ちのSuicaでも乗れます。この地図は、それがどこなのかを示すものです。',
		howToRead: '地図の読み方',
		howToReadBody:
			'緑はSuicaがそのまま使える路線です。黄色は特定のICエリア内や一部区間でのみ使える事業者で、JRの長距離路線はエリアを出たり入ったりするため、ポップアップの備考を確認してください。赤はIC乗車券に非対応です。グレーは対応状況を確認できなかった事業者で、「利用不可」という意味ではありません。',
		dataSources: 'データの出典',
		icSource: 'ICカード対応状況',
		icSourceBody:
			'日本語版Wikipedia「交通系ICカード全国相互利用サービス」の対象事業者一覧をもとに手作業で整理し、JR東日本・JR西日本が公開している対象事業者一覧と突き合わせています。',
		basemap: '背景地図',
		disclaimer: 'ご利用にあたって',
		disclaimerBody:
			'これは公式サービスではなく個人の制作物です。IC対応状況は変わりますし、バスデータは2022年度版、対応表も独自の集計です。旅程の検討にはお使いいただけますが、実際に改札を通る前に事業者の公式情報をご確認ください。',
		asOf: (date: string) => `ICカード対応状況は${date}時点の情報です。`,
		license: 'ライセンス',
		licenseBody: '鉄道・バスの形状データは国土交通省の国土数値情報（CC BY 4.0）を使用しています。',
		close: '閉じる'
	},

	map: {
		loading: '地図を読み込んでいます…',
		attribution: '国土数値情報（鉄道データ N02 / バスルートデータ N07）国土交通省'
	}
};

export default ja;
