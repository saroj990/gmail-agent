export type Provider = 'ollama' | 'gemini';
export type RunMode = 'dry_run' | 'automatic';
export type Category = 'IMPORTANT' | 'TO_PROCESS' | 'UNKNOWN';

export interface Settings {
	llm_provider: Provider;
	ollama_base_url: string;
	ollama_model: string;
	gemini_model: string;
	gmail_label: string;
	confidence_threshold: number;
	max_emails_per_run: number;
}

export interface SettingsResponse {
	settings: Settings;
	gemini_api_key_configured: boolean;
	cli_mode: string;
}

export interface AuthStatus {
	signed_in: boolean;
	email: string | null;
	error: string | null;
	login_in_progress: boolean;
	login_error: string | null;
	authorization_url: string | null;
}

export interface LoginStartResponse {
	login_in_progress: boolean;
	authorization_url: string | null;
}

export interface RunItem {
	message_id: string;
	sender: string;
	subject: string;
	date: string;
	snippet: string;
	category: Category;
	importance: string;
	confidence: number;
	reason: string;
	action: string;
	execution_note: string;
	eligible: boolean;
	applied: boolean;
}

export interface Run {
	id: string;
	mode: RunMode;
	status: 'running' | 'completed' | 'failed';
	total: number | null;
	processed: number;
	skipped_cached: number;
	items: RunItem[];
	error: string | null;
	started_at: string;
	finished_at: string | null;
	settings: Settings;
}

export interface HistoryItem {
	message_id: string;
	sender: string;
	subject: string;
	category: Category;
	importance: string;
	confidence: number;
	reason: string;
	action: string;
	execution_note: string;
	created_at: string;
}

export interface HistoryResponse {
	items: HistoryItem[];
	total: number;
}
