<script lang="ts">
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { resolve } from '$app/paths';
	import { api, errorMessage } from '#lib/api.ts';
	import { categoryLabel, dateTime, percent } from '#lib/format.ts';
	import type { HistoryItem, Run, RunMode, SettingsResponse } from '#lib/types.ts';

	let config = $state<SettingsResponse | null>(null);
	let run = $state<Run | null>(null);
	let history = $state<HistoryItem[]>([]);
	let historyTotal = $state(0);
	let processedToday = $state(0);
	let error = $state<string | null>(null);
	let busy = $state(false);
	const selected = new SvelteSet<string>();

	const running = $derived(run?.status === 'running');
	const settings = $derived(config?.settings);
	const model = $derived(
		settings ? (settings.llm_provider === 'ollama' ? settings.ollama_model : settings.gemini_model) : ''
	);
	const selectable = $derived(
		run?.mode === 'dry_run' && run.status === 'completed'
			? run.items.filter((item) => item.eligible && !item.applied)
			: []
	);
	const counts = $derived.by(() => {
		const items = run?.items ?? [];
		return {
			important: items.filter((i) => i.category === 'IMPORTANT').length,
			toProcess: items.filter((i) => i.category === 'TO_PROCESS').length,
			unknown: items.filter((i) => i.category === 'UNKNOWN').length,
			eligible: items.filter((i) => i.eligible).length,
			applied: items.filter((i) => i.applied || i.execution_note.startsWith('labeled')).length
		};
	});
	const progress = $derived(
		run?.total ? Math.round((run.processed / run.total) * 100) : running ? 5 : 100
	);

	onMount(() => {
		load();
	});

	// Poll the background run until it finishes.
	$effect(() => {
		if (!running || !run) return;
		const id = run.id;
		const timer = setInterval(async () => {
			try {
				run = await api.getRun(id);
				if (run.status !== 'running') loadHistory();
			} catch (e) {
				error = errorMessage(e);
			}
		}, 1000);
		return () => clearInterval(timer);
	});

	async function load() {
		try {
			[config, run] = await Promise.all([api.getSettings(), api.latestRun()]);
			await loadHistory();
		} catch (e) {
			error = errorMessage(e);
		}
	}

	async function loadHistory() {
		try {
			const response = await api.history(25);
			history = response.items;
			historyTotal = response.total;
			processedToday = response.processed_today;
		} catch (e) {
			error = errorMessage(e);
		}
	}

	async function start(mode: RunMode) {
		if (!settings) return;
		if (
			mode === 'automatic' &&
			!confirm(
				`This will change your Gmail: emails classified as "To process" with confidence ` +
					`of at least ${percent(settings.confidence_threshold)} get the "${settings.gmail_label}" ` +
					`label and are archived (removed from Inbox). Continue?`
			)
		) {
			return;
		}
		busy = true;
		error = null;
		selected.clear();
		try {
			run = await api.startRun(mode);
		} catch (e) {
			error = errorMessage(e);
		} finally {
			busy = false;
		}
	}

	function toggleAll(checked: boolean) {
		selected.clear();
		if (checked) selectable.forEach((item) => selected.add(item.message_id));
	}

	async function applySelected() {
		if (!run || selected.size === 0) return;
		if (
			!confirm(
				`Label "${run.settings.gmail_label}" and archive ${selected.size} selected email(s)?`
			)
		) {
			return;
		}
		busy = true;
		error = null;
		try {
			run = await api.applyRun(run.id, [...selected]);
			selected.clear();
			await loadHistory();
		} catch (e) {
			error = errorMessage(e);
		} finally {
			busy = false;
		}
	}
</script>

<h1>Dashboard</h1>

{#if error}
	<div class="alert error">{error}</div>
{/if}

<section class="card">
	<div class="row">
		<div>
			<h2>Run the agent</h2>
			{#if settings}
				<p class="muted">
					Up to <strong>{settings.max_emails_per_run}</strong> new emails ·
					{settings.llm_provider === 'ollama' ? 'Ollama' : 'Gemini'} <code>{model}</code> ·
					threshold <strong>{percent(settings.confidence_threshold)}</strong> · label
					<strong>{settings.gmail_label}</strong>
					· <a href={resolve('/preferences')}>change</a>
				</p>
			{/if}
		</div>
	</div>
	<div class="row">
		<button class="primary" onclick={() => start('dry_run')} disabled={busy || running || !settings}>
			Dry run
		</button>
		<button class="danger" onclick={() => start('automatic')} disabled={busy || running || !settings}>
			Run for real
		</button>
		<span class="hint">
			A dry run only classifies and changes nothing; you can then approve individual emails. A
			real run labels and archives everything that passes the guards.
		</span>
	</div>
</section>

{#if run}
	<section class="card">
		<div class="row">
			<h2>{run.mode === 'dry_run' ? 'Dry run' : 'Real run'}</h2>
			<span class="muted">started {dateTime(run.started_at)}</span>
			<span class="spacer"></span>
			{#if running}
				<span class="muted">
					{run.total === null ? 'Fetching emails…' : `Classifying ${run.processed} / ${run.total}…`}
				</span>
			{:else if run.status === 'completed'}
				<span class="muted">finished {dateTime(run.finished_at)}</span>
			{/if}
		</div>

		{#if running}
			<div class="progress"><div style:width="{progress}%"></div></div>
		{/if}

		{#if run.error}
			<div class="alert error" style:margin-top="1rem">{run.error}</div>
		{/if}

		{#if run.status !== 'running' && run.items.length === 0 && !run.error}
			<p class="muted">
				No new emails to process.
				{#if run.skipped_cached}{run.skipped_cached} already-processed email(s) were skipped.{/if}
			</p>
		{/if}

		{#if run.items.length > 0}
			<div class="stats">
				<div class="stat"><strong>{counts.important}</strong>Important</div>
				<div class="stat"><strong>{counts.toProcess}</strong>To process</div>
				<div class="stat"><strong>{counts.unknown}</strong>Unknown</div>
				<div class="stat"><strong>{counts.eligible}</strong>Pass guards</div>
				<div class="stat"><strong>{counts.applied}</strong>Labeled + archived</div>
			</div>
			{#if run.skipped_cached}
				<p class="hint">Skipped {run.skipped_cached} email(s) already processed in an earlier real run.</p>
			{/if}

			{#if selectable.length > 0}
				<div class="row" style:margin-bottom="0.75rem">
					<label class="row">
						<input
							type="checkbox"
							checked={selected.size === selectable.length}
							onchange={(e) => toggleAll(e.currentTarget.checked)}
						/>
						Select all {selectable.length} eligible
					</label>
					<span class="spacer"></span>
					<button class="primary" onclick={applySelected} disabled={busy || selected.size === 0}>
						Label + archive selected ({selected.size})
					</button>
				</div>
			{/if}

			<div class="table-wrap">
				<table>
					<thead>
						<tr>
							{#if selectable.length > 0}<th></th>{/if}
							<th>From / Subject</th>
							<th>Category</th>
							<th>Confidence</th>
							<th>Reason</th>
							<th>Result</th>
						</tr>
					</thead>
					<tbody>
						{#each run.items as item (item.message_id)}
							<tr>
								{#if selectable.length > 0}
									<td>
										{#if item.eligible && !item.applied}
											<input
												type="checkbox"
												checked={selected.has(item.message_id)}
												onchange={(e) =>
													e.currentTarget.checked
														? selected.add(item.message_id)
														: selected.delete(item.message_id)}
											/>
										{/if}
									</td>
								{/if}
								<td>
									<div>{item.subject || '(no subject)'}</div>
									<div class="hint">{item.sender}</div>
								</td>
								<td><span class="badge {item.category}">{categoryLabel[item.category]}</span></td>
								<td>{percent(item.confidence)}</td>
								<td class="muted">{item.reason}</td>
								<td class="muted">{item.execution_note}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
{/if}

<section class="card">
	<div class="row">
		<h2>History</h2>
		<span class="muted">
			{historyTotal} remembered · {processedToday} processed today (UTC)
		</span>
		<span class="spacer"></span>
		<button onclick={loadHistory}>Refresh</button>
	</div>
	{#if history.length === 0}
		<p class="muted">Nothing yet. Real runs and approved dry-run items show up here.</p>
	{:else}
		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						<th>When</th>
						<th>From / Subject</th>
						<th>Category</th>
						<th>Confidence</th>
						<th>Result</th>
					</tr>
				</thead>
				<tbody>
					{#each history as item (item.message_id)}
						<tr>
							<td class="muted">{dateTime(item.created_at)}</td>
							<td>
								<div>{item.subject || '(no subject)'}</div>
								<div class="hint">{item.sender}</div>
							</td>
							<td><span class="badge {item.category}">{categoryLabel[item.category]}</span></td>
							<td>{percent(item.confidence)}</td>
							<td class="muted">{item.execution_note}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>
