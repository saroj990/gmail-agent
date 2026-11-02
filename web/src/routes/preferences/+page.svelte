<script lang="ts">
	import { onMount } from 'svelte';
	import { api, errorMessage } from '#lib/api.ts';
	import { percent } from '#lib/format.ts';
	import type { Settings, SettingsResponse } from '#lib/types.ts';

	let config = $state<SettingsResponse | null>(null);
	let form = $state<Settings | null>(null);
	let models = $state<string[]>([]);
	let modelsError = $state<string | null>(null);
	let loadingModels = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let saved = $state(false);

	const dirty = $derived(
		!!form && !!config && JSON.stringify(form) !== JSON.stringify(config.settings)
	);

	onMount(async () => {
		try {
			apply(await api.getSettings());
			await loadModels();
		} catch (e) {
			error = errorMessage(e);
		}
	});

	function apply(response: SettingsResponse) {
		config = response;
		form = { ...response.settings };
	}

	async function loadModels() {
		if (!form) return;
		loadingModels = true;
		modelsError = null;
		try {
			models = (await api.ollamaModels(form.ollama_base_url)).models;
		} catch (e) {
			models = [];
			modelsError = errorMessage(e);
		} finally {
			loadingModels = false;
		}
	}

	async function save(event: SubmitEvent) {
		event.preventDefault();
		if (!form) return;
		saving = true;
		error = null;
		saved = false;
		try {
			apply(await api.saveSettings(form));
			saved = true;
		} catch (e) {
			error = errorMessage(e);
		} finally {
			saving = false;
		}
	}

	async function reset() {
		if (!confirm('Reset all preferences to the defaults from .env?')) return;
		error = null;
		saved = false;
		try {
			apply(await api.resetSettings());
			saved = true;
		} catch (e) {
			error = errorMessage(e);
		}
	}
</script>

<h1>Preferences</h1>
<p class="muted">
	Applied to runs started from this UI. Defaults come from your <code>.env</code>; saved values
	are stored in <code>data/settings.json</code>.
</p>

{#if error}
	<div class="alert error">{error}</div>
{/if}
{#if saved && !dirty}
	<div class="alert success">Preferences saved.</div>
{/if}

{#if form && config}
	<form onsubmit={save}>
		<section class="card">
			<h2>Classifier</h2>
			<fieldset class="field">
				<legend>Provider</legend>
				<label class="row">
					<input type="radio" bind:group={form.llm_provider} value="ollama" />
					Ollama (local, email text stays on this machine)
				</label>
				<label class="row">
					<input type="radio" bind:group={form.llm_provider} value="gemini" />
					Gemini (faster, email text is sent to Google)
				</label>
			</fieldset>

			{#if form.llm_provider === 'ollama'}
				<label class="field">
					<span>Ollama URL</span>
					<input bind:value={form.ollama_base_url} onchange={loadModels} required />
				</label>
				<label class="field">
					<span>Ollama model</span>
					<div class="row">
						<input bind:value={form.ollama_model} list="ollama-models" required style:flex="1" />
						<button type="button" onclick={loadModels} disabled={loadingModels}>
							{loadingModels ? 'Loading…' : 'Refresh list'}
						</button>
					</div>
					<datalist id="ollama-models">
						{#each models as name (name)}
							<option value={name}></option>
						{/each}
					</datalist>
					{#if modelsError}
						<div class="hint">{modelsError}</div>
					{:else if models.length > 0}
						<div class="hint">Installed: {models.join(', ')}</div>
					{/if}
					{#if models.length > 0 && !models.includes(form.ollama_model)}
						<div class="alert warning" style:margin-top="0.5rem">
							<code>{form.ollama_model}</code> is not installed. Run
							<code>ollama pull {form.ollama_model}</code> or pick an installed model.
						</div>
					{/if}
				</label>
			{:else}
				<label class="field">
					<span>Gemini model</span>
					<input bind:value={form.gemini_model} required />
				</label>
				{#if config.gemini_api_key_configured}
					<p class="hint">Gemini API key is configured in <code>.env</code>.</p>
				{:else}
					<div class="alert warning">
						No Gemini API key found. Add <code>GEMINI_API_KEY</code> to your local
						<code>.env</code> and restart the server. The key is intentionally not editable here.
					</div>
				{/if}
			{/if}
		</section>

		<section class="card">
			<h2>Actions</h2>
			<label class="field">
				<span>Gmail label</span>
				<input bind:value={form.gmail_label} maxlength="225" required />
				<div class="hint">Applied to low-value emails before they are archived.</div>
			</label>
			<label class="field">
				<span>Confidence threshold: {percent(form.confidence_threshold)}</span>
				<input
					type="range"
					min="0"
					max="1"
					step="0.01"
					bind:value={form.confidence_threshold}
					style:width="100%"
				/>
				<div class="hint">
					Only "To process" emails at or above this confidence can be labeled and archived.
				</div>
			</label>
			<label class="field">
				<span>Emails per run</span>
				<input type="number" min="1" max="100" bind:value={form.max_emails_per_run} required />
				<div class="hint">Newest emails fetched per run (already-processed ones are skipped).</div>
			</label>
		</section>

		<p class="hint">
			The <code>MODE</code> in <code>.env</code> (currently <code>{config.cli_mode}</code>) only
			affects the command line. In the UI you choose a dry run or a real run each time.
		</p>

		<div class="row">
			<button class="primary" type="submit" disabled={saving || !dirty}>
				{saving ? 'Saving…' : 'Save preferences'}
			</button>
			<button type="button" onclick={() => config && apply(config)} disabled={!dirty}>Discard</button>
			<span class="spacer"></span>
			<button type="button" onclick={reset}>Reset to .env defaults</button>
		</div>
	</form>
{:else if !error}
	<p class="muted">Loading…</p>
{/if}

<style>
	fieldset {
		border: none;
		padding: 0;
		margin: 0 0 1rem;
	}

	legend {
		font-weight: 600;
		margin-bottom: 0.3rem;
	}
</style>
