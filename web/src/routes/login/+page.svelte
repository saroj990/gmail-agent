<script lang="ts">
	import { onMount } from 'svelte';
	import { api, errorMessage } from '#lib/api.ts';
	import { auth, goToDashboard, refreshAuth } from '#lib/auth.svelte.ts';
	import {
		isOAuthCallbackMessage,
		isTrustedOAuthOrigin,
		openOAuthPopup,
		openOAuthSameTab
	} from '#lib/oauth-popup.ts';

	type Step = 'idle' | 'opening' | 'waiting' | 'success' | 'error';

	let step = $state<Step>('idle');
	let message = $state<string | null>(null);
	let popupRef = $state<Window | null>(null);
	let pollTimer: ReturnType<typeof setInterval> | undefined;

	onMount(() => {
		const onMessage = (event: MessageEvent) => {
			if (!isTrustedOAuthOrigin(event.origin) || !isOAuthCallbackMessage(event.data)) return;
			void completeSignIn();
		};
		window.addEventListener('message', onMessage);
		return () => {
			window.removeEventListener('message', onMessage);
			stopPolling();
			popupRef?.close();
		};
	});

	// Backup if postMessage is missed: react as soon as /api/auth/status reports signed_in.
	$effect(() => {
		if (step === 'waiting' && auth.status?.signed_in) {
			void completeSignIn();
		}
	});

	function stopPolling() {
		if (pollTimer !== undefined) {
			clearInterval(pollTimer);
			pollTimer = undefined;
		}
	}

	async function completeSignIn() {
		await refreshAuth();
		if (!auth.status?.signed_in) {
			return;
		}
		step = 'success';
		message = null;
		stopPolling();
		popupRef?.close();
		popupRef = null;
		goToDashboard();
	}

	function startPolling() {
		stopPolling();
		pollTimer = setInterval(async () => {
			await refreshAuth();
			if (auth.status?.signed_in) {
				await completeSignIn();
				return;
			}
			if (!auth.status?.login_in_progress && auth.status?.login_error) {
				stopPolling();
				step = 'error';
				message = auth.status.login_error;
			}
		}, 400);
	}

	async function signIn() {
		step = 'opening';
		message = null;
		try {
			const body = await api.login();
			const url = body.authorization_url;
			if (!url) {
				throw new Error(
					'The API did not return a sign-in URL. Stop and restart the Python server (python main.py serve), then try again.'
				);
			}
			step = 'waiting';
			const popup = openOAuthPopup(url);
			popupRef = popup;
			if (!popup) {
				message =
					'Pop-up blocked. Opening Google sign-in in this tab instead — you will return here when done.';
				openOAuthSameTab(url);
				startPolling();
				return;
			}
			startPolling();
		} catch (error) {
			step = 'error';
			message = errorMessage(error);
			stopPolling();
		}
	}
</script>

<div class="login-shell">
	<div class="login card">
		<p class="eyebrow">Local inbox agent</p>
		<h1>Connect Gmail</h1>
		<p class="lead">
			Sign in once so the agent can read and classify your inbox on this machine. Nothing is
			changed in Gmail until you run for real or approve items from a dry run.
		</p>

		<ol class="steps">
			<li>Click <strong>Continue with Google</strong></li>
			<li>Approve access in the pop-up window</li>
			<li>You land on the dashboard automatically</li>
		</ol>

		{#if auth.status?.error}
			<div class="alert error">{auth.status.error}</div>
		{/if}
		{#if message}
			<div class="alert {step === 'error' ? 'error' : 'warning'}">{message}</div>
		{/if}

		{#if step === 'waiting'}
			<div class="waiting row">
				<span class="spinner" aria-hidden="true"></span>
				<div>
					<strong>Waiting for Google…</strong>
					<p class="hint">Finish sign-in in the pop-up. This page will redirect when you are done.</p>
				</div>
			</div>
			<button type="button" class="link" onclick={signIn}>Open Google again</button>
		{:else if step === 'success'}
			<div class="alert success">Signed in. Opening dashboard…</div>
		{:else}
			<button type="button" class="google-btn" onclick={signIn} disabled={step === 'opening'}>
				<span class="g" aria-hidden="true">G</span>
				{step === 'opening' ? 'Starting…' : 'Continue with Google'}
			</button>
		{/if}

		<p class="hint foot">
			Uses <code>credentials.json</code> on this computer. Your session is saved in
			<code>token.json</code>.
		</p>
	</div>
</div>

<style>
	.login-shell {
		min-height: calc(100vh - 3rem);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem 0 2rem;
	}

	.login {
		width: 100%;
		max-width: 440px;
		margin: 0;
	}

	.eyebrow {
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-size: 0.72rem;
		font-weight: 700;
		color: var(--muted);
		margin: 0 0 0.35rem;
	}

	.lead {
		color: var(--muted);
		margin: 0 0 1.25rem;
	}

	.steps {
		margin: 0 0 1.25rem 1.1rem;
		padding: 0;
		color: var(--muted);
		font-size: 0.92rem;
	}

	.steps li {
		margin-bottom: 0.35rem;
	}

	.google-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.65rem;
		width: 100%;
		padding: 0.65rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface);
		font-weight: 600;
		cursor: pointer;
	}

	.google-btn:disabled {
		opacity: 0.6;
		cursor: wait;
	}

	.google-btn .g {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.35rem;
		height: 1.35rem;
		border-radius: 4px;
		background: #fff;
		border: 1px solid #dadce0;
		color: #4285f4;
		font-weight: 700;
		font-family: Georgia, serif;
	}

	.waiting {
		align-items: flex-start;
		margin-bottom: 0.75rem;
	}

	.spinner {
		width: 1.25rem;
		height: 1.25rem;
		border: 2px solid var(--border);
		border-top-color: var(--primary);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		flex-shrink: 0;
		margin-top: 0.15rem;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.foot {
		margin-top: 1.25rem;
		margin-bottom: 0;
	}
</style>
