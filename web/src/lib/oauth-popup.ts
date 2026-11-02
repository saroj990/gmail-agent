/** Google OAuth in a centered popup; falls back to same-tab navigation. */

const POPUP = 'width=520,height=680,left=100,top=80,menubar=no,toolbar=no,status=no';

export function isOAuthCallbackMessage(data: unknown): data is { type: string; status: string } {
	return (
		typeof data === 'object' &&
		data !== null &&
		(data as { type?: string }).type === 'gmail-agent-auth' &&
		(data as { status?: string }).status === 'success'
	);
}

export function isTrustedOAuthOrigin(origin: string): boolean {
	try {
		const url = new URL(origin);
		return url.hostname === '127.0.0.1' || url.hostname === 'localhost';
	} catch {
		return false;
	}
}

export function openOAuthPopup(url: string): Window | null {
	return window.open(url, 'gmail-agent-oauth', POPUP);
}

export function openOAuthSameTab(url: string): void {
	window.location.assign(url);
}
