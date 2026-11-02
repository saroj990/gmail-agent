import { api, errorMessage } from './api';
import type { AuthStatus } from './types';

export const auth = $state<{
	status: AuthStatus | null;
	loading: boolean;
	error: string | null;
}>({ status: null, loading: true, error: null });

export async function refreshAuth(): Promise<void> {
	try {
		auth.status = await api.authStatus();
		auth.error = null;
	} catch (error) {
		auth.error = errorMessage(error);
	} finally {
		auth.loading = false;
	}
}
