<script lang="ts">
	import { api, errorMessage } from '#lib/api.ts';
	import { auth, refreshAuth } from '#lib/auth.svelte.ts';

	let startError = $state<string | null>(null);
	let starting = $state(false);

	const inProgress = $derived(auth.status?.login_in_progress ?? false);

	// Poll while the Google consent page is open in another browser tab.
	$effect(() => {
		if (!inProgress) return;
		const timer = setInterval(refreshAuth, 2000);
		return () => clearInterval(timer);
	});

	async function signIn() {
		starting = true;
		startError = null;
		try {
			await api.login();
			await refreshAuth();
		} catch (error) {
			startError = errorMessage(error);
		} finally {
			starting = false;
		}
	}
</script>

<div class="login card">
	<h1>Sign in</h1>
	<p class="muted">
		Connect your Gmail account so the agent can read and classify your inbox. It never
		permanently deletes mail, and nothing changes in Gmail unless you start a real run or
		approve items from a dry run.
	</p>

	{#if auth.status?.error}
		<div class="alert error">{auth.status.error}</div>
	{/if}
	{#if auth.status?.login_error}
		<div class="alert error">{auth.status.login_error}</div>
	{/if}
	{#if startError}
		<div class="alert error">{startError}</div>
	{/if}

	{#if inProgress}
		<div class="alert warning">
			A Google sign-in page opened in your browser. Approve access there, then come back to
			this tab. Waiting…
		</div>
	{:else}
		<button class="primary" onclick={signIn} disabled={starting}>
			{starting ? 'Opening Google…' : 'Sign in with Google'}
		</button>
	{/if}

	<p class="hint">
		Uses the OAuth client in <code>credentials.json</code> and saves the login to
		<code>token.json</code> on this machine.
	</p>
</div>

<style>
	.login {
		max-width: 520px;
		margin: 4rem auto;
	}
</style>
