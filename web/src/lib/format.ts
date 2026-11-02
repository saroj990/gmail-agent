import type { Category } from './types';

export function percent(value: number): string {
	return `${Math.round(value * 100)}%`;
}

export function dateTime(iso: string | null): string {
	if (!iso) return '';
	const date = new Date(iso);
	return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

export const categoryLabel: Record<Category, string> = {
	IMPORTANT: 'Important',
	TO_PROCESS: 'To process',
	UNKNOWN: 'Unknown'
};
