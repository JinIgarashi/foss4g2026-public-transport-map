import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter(),
			paths: {
				base: (process.env.BASE_PATH || '') as '' | `/${string}`
			},
			alias: {
				'@/*': './src/lib/*'
			}
		})
	],
	ssr: {
		noExternal: ['maplibre-gl', 'pmtiles', '@lucide/svelte', 'bits-ui']
	}
});
