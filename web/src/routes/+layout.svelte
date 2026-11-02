<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import favicon from '#lib/assets/favicon.svg';
	import { api, errorMessage } from '#lib/api.ts';
	import { auth, goToDashboard, refreshAuth } from '#lib/auth.svelte.ts';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	let signOutError = $state<string | null>(null);
	const onLoginPage = $derived(page.url.pathname === resolve('/login'));
	const signedIn = $derived(auth.status?.signed_in ?? false);

	onMount(refreshAuth);

	$effect(() => {
		if (auth.loading || !auth.status) return;
		if (!signedIn && !onLoginPage) goto(resolve('/login'), { replace: true });
		if (signedIn && onLoginPage) goToDashboard();
	});

	async function signOut() {
		signOutError = null;
		try {
			await api.logout();
			await refreshAuth();
		} catch (error) {
			signOutError = errorMessage(error);
		}
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Gmail AI Inbox Agent</title>
</svelte:head>

{#if signedIn}
	<header>
		<div class="container row">
			<strong>Gmail AI Inbox Agent</strong>
			<nav class="row">
				<a href={resolve('/')} class:active={page.url.pathname === resolve('/')}>Dashboard</a>
				<a
					href={resolve('/preferences')}
					class:active={page.url.pathname === resolve('/preferences')}>Preferences</a
				>
			</nav>
			<span class="spacer"></span>
			<span class="muted">{auth.status?.email}</span>
			<button onclick={signOut}>Sign out</button>
		</div>
	</header>
{/if}

<main class="container">
	{#if auth.error}
		<div class="alert error">
			{auth.error}
			<button class="link" onclick={refreshAuth}>Retry</button>
		</div>
	{/if}
	{#if signOutError}
		<div class="alert error">{signOutError}</div>
	{/if}

	{#if auth.loading}
		<div class="loading-screen">
			<span class="spinner" aria-hidden="true"></span>
			<span class="muted">Loading…</span>
		</div>
	{:else if signedIn || onLoginPage}
		{@render children()}
	{/if}
</main>

<style>
	header {
		background: var(--surface);
		border-bottom: 1px solid var(--border);
	}

	header .container {
		padding-top: 0.75rem;
		padding-bottom: 0.75rem;
	}

	nav a {
		color: var(--muted);
		text-decoration: none;
		padding: 0.25rem 0.5rem;
		border-radius: 6px;
	}

	nav a.active {
		color: var(--text);
		background: var(--bg);
	}

	.loading-screen {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		padding: 2rem 0;
	}

	.spinner {
		width: 1.1rem;
		height: 1.1rem;
		border: 2px solid var(--border);
		border-top-color: var(--primary);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
