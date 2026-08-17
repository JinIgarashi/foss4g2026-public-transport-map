/** Colour scheme the visitor asked for; `system` follows the OS setting. */
export type ThemePreference = 'light' | 'dark' | 'system';

/** Key under which the visitor's choice is remembered. Mirrored by the
 * no-flash script in `app.html`, so keep the two in sync. */
export const THEME_STORAGE_KEY = 'theme';

export const THEME_PREFERENCES: ThemePreference[] = ['light', 'dark', 'system'];

const DARK_QUERY = '(prefers-color-scheme: dark)';

function isPreference(value: unknown): value is ThemePreference {
	return value === 'light' || value === 'dark' || value === 'system';
}

let preference = $state<ThemePreference>('system');
let systemDark = $state(false);

function resolve(): 'light' | 'dark' {
	if (preference === 'system') return systemDark ? 'dark' : 'light';
	return preference;
}

/** Push the resolved scheme onto `<html>`, the same way the no-flash script does. */
function apply() {
	const resolved = resolve();
	document.documentElement.classList.toggle('dark', resolved === 'dark');
	document.documentElement.style.colorScheme = resolved;
}

export const theme = {
	get preference(): ThemePreference {
		return preference;
	},
	set preference(value: ThemePreference) {
		preference = value;
		try {
			localStorage.setItem(THEME_STORAGE_KEY, value);
		} catch {
			// Private mode / blocked storage: the choice just does not persist.
		}
		apply();
	},
	/** The scheme actually in effect — `system` already resolved. */
	get resolved(): 'light' | 'dark' {
		return resolve();
	}
};

/**
 * Adopt the stored choice and keep `system` following the OS. Call once from the
 * root layout; returns the teardown for `$effect`.
 */
export function initTheme(): () => void {
	let stored: string | null = null;
	try {
		stored = localStorage.getItem(THEME_STORAGE_KEY);
	} catch {
		// Ignore: fall back to `system`.
	}
	preference = isPreference(stored) ? stored : 'system';

	const media = window.matchMedia(DARK_QUERY);
	systemDark = media.matches;
	const onChange = (event: MediaQueryListEvent) => {
		systemDark = event.matches;
		apply();
	};
	media.addEventListener('change', onChange);

	// The no-flash script already applied this, but re-run it in case storage was
	// written by another tab between page load and hydration.
	apply();

	return () => media.removeEventListener('change', onChange);
}
