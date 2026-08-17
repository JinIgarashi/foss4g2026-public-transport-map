import type { Locale } from '../locales';
import en, { type Messages } from './en';
import ja from './ja';

/**
 * Eager barrel: with two locales the whole table is a few kilobytes, and
 * loading it synchronously keeps `currentMessages()` a plain function call
 * instead of a promise every component has to await.
 */
export const messages: Record<Locale, Messages> = { en, ja };

export type { Messages };
