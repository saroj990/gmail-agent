import type {
	AuthStatus,
	HistoryResponse,
	Run,
	RunMode,
	Settings,
	SettingsResponse
} from './types';

export class ApiError extends Error {
	readonly status: number;

	constructor(message: string, status: number) {
		super(message);
		this.status = status;
	}
}

const SERVER_HINT = 'Is the local server running (python main.py serve)?';

type ValidationIssue = { loc?: unknown[]; msg?: string };

function formatDetail(detail: unknown): string | null {
	if (typeof detail === 'string') return detail;
	if (Array.isArray(detail)) {
		return (detail as ValidationIssue[])
			.map((issue) => {
				const field = (issue.loc ?? []).filter((part) => part !== 'body').join('.');
				return field ? `${field}: ${issue.msg}` : (issue.msg ?? 'invalid value');
			})
			.join('; ');
	}
	return null;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
	const headers: Record<string, string> = { 'X-Gmail-Agent': '1' };
	if (body !== undefined) headers['Content-Type'] = 'application/json';

	let response: Response;
	try {
		response = await fetch(`/api${path}`, {
			method,
			headers,
			body: body === undefined ? undefined : JSON.stringify(body)
		});
	} catch {
		throw new ApiError(`Cannot reach the local API. ${SERVER_HINT}`, 0);
	}

	const text = await response.text();
	let data: unknown = null;
	try {
		data = text ? JSON.parse(text) : null;
	} catch {
		throw new ApiError(`Local API unavailable (HTTP ${response.status}). ${SERVER_HINT}`, response.status);
	}

	if (!response.ok) {
		const detail = formatDetail((data as { detail?: unknown } | null)?.detail);
		throw new ApiError(detail ?? `Request failed (HTTP ${response.status})`, response.status);
	}
	return data as T;
}

export function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}

export const api = {
	authStatus: () => request<AuthStatus>('GET', '/auth/status'),
	login: () => request<{ login_in_progress: boolean }>('POST', '/auth/login'),
	logout: () => request<{ signed_in: boolean }>('POST', '/auth/logout'),

	getSettings: () => request<SettingsResponse>('GET', '/settings'),
	saveSettings: (settings: Settings) => request<SettingsResponse>('PUT', '/settings', settings),
	resetSettings: () => request<SettingsResponse>('POST', '/settings/reset'),
	ollamaModels: (baseUrl: string) =>
		request<{ models: string[] }>('GET', `/ollama/models?base_url=${encodeURIComponent(baseUrl)}`),

	startRun: (mode: RunMode) => request<Run>('POST', '/runs', { mode }),
	latestRun: () => request<Run | null>('GET', '/runs/latest'),
	getRun: (id: string) => request<Run>('GET', `/runs/${id}`),
	applyRun: (id: string, messageIds: string[]) =>
		request<Run>('POST', `/runs/${id}/apply`, { message_ids: messageIds }),

	history: (limit = 25) => request<HistoryResponse>('GET', `/history?limit=${limit}`)
};
