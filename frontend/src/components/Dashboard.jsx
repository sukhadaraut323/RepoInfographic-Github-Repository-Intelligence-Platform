import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import AIInsights from './AIInsights'
import AdvancedVisualizations from './AdvancedVisualizations'
import { downloadRepositoryReport } from '../api'

const SERIES = ['#8b91ff', '#3fd5e8', '#a78bfa', '#5eead4', '#94a3b8', '#c4b5fd']
const TOOLTIP = { contentStyle: { backgroundColor: '#101827', border: '1px solid #64748b', borderRadius: 9, color: '#f8fafc', padding: '10px 12px', boxShadow: '0 8px 24px rgba(0,0,0,.45)' }, labelStyle: { color: '#ffffff', fontWeight: 700 }, itemStyle: { color: '#e2e8f0' }, cursor: { fill: 'rgba(139,145,255,0.08)' } }
const num = (n) => Number(n).toLocaleString()
const date = (d) => (d ? new Date(d).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : null)
const label = (k) => k.replace(/_score$/, '').replace(/_/g, ' ')

function Card({ title, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-line bg-surface p-5 ${className}`}>
      {title && <h3 className="mb-4 font-display text-lg font-bold">{title}</h3>}
      {children}
    </section>
  )
}
const Empty = () => <p className="py-6 text-sm text-muted">No data available for this repository.</p>
const Stat = ({ name, value }) => value == null ? null : (
  <div className="rounded-xl bg-raised px-4 py-3">
    <dd className="font-display text-2xl font-bold">{value}</dd>
    <dt className="text-sm text-muted">{name}</dt>
  </div>
)

function Gauge({ g }) {
  const pct = Math.max(0, Math.min(1, (g.value - g.min) / (g.max - g.min || 1)))
  return (
    <div className="relative mx-auto h-44 w-44 shrink-0" role="img" aria-label={`${g.label}: ${g.value} out of ${g.max}`}>
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle cx="60" cy="60" r="50" fill="none" stroke="#263150" strokeWidth="11" />
        <motion.circle cx="60" cy="60" r="50" fill="none" stroke="#3fd5e8" strokeWidth="11" strokeLinecap="round"
          initial={{ pathLength: 0 }} animate={{ pathLength: pct }} transition={{ duration: 1.2, ease: 'easeOut' }} />
      </svg>
      <div className="absolute inset-0 grid place-content-center text-center">
        <span className="font-display text-4xl font-bold">{Math.round(g.value)}</span>
        <span className="text-xs text-muted">{g.status}</span>
      </div>
    </div>
  )
}

function Header({ data }) {
  const m = data.repository_metadata
  const g = data.analytics.health_gauge
  return (
    <header className="rounded-2xl border border-line bg-surface p-6">
      <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            {m.owner?.avatar_url && <img src={m.owner.avatar_url} alt="" className="h-11 w-11 rounded-full" />}
            <h1 className="break-words font-display text-3xl font-bold">{m.full_name}</h1>
          </div>
          {m.description && <p className="mt-3 max-w-2xl text-muted">{m.description}</p>}
          <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <div><dt className="inline text-muted">Stars </dt><dd className="inline font-semibold">{num(m.stargazers_count)}</dd></div>
            <div><dt className="inline text-muted">Forks </dt><dd className="inline font-semibold">{num(m.forks_count)}</dd></div>
            <div><dt className="inline text-muted">Open issues </dt><dd className="inline font-semibold">{num(m.open_issues_count)}</dd></div>
            {m.primary_language && <div><dt className="inline text-muted">Language </dt><dd className="inline font-semibold">{m.primary_language}</dd></div>}
            {m.license_name && <div><dt className="inline text-muted">License </dt><dd className="inline font-semibold">{m.license_name}</dd></div>}
            <div><dt className="inline text-muted">Visibility </dt><dd className="inline font-semibold">{m.visibility}{m.is_archived ? ', archived' : ''}{m.is_fork ? ', fork' : ''}</dd></div>
            {date(m.updated_at) && <div><dt className="inline text-muted">Updated </dt><dd className="inline font-semibold">{date(m.updated_at)}</dd></div>}
          </dl>
          {m.topics?.length > 0 && <ul className="mt-4 flex flex-wrap gap-2">{m.topics.map((t) => <li key={t} className="rounded-full bg-raised px-3 py-1 text-xs text-accent">{t}</li>)}</ul>}
          <a href={m.html_url} target="_blank" rel="noreferrer" className="mt-4 inline-block text-sm font-semibold text-primary hover:text-accent">View on GitHub</a>
        </div>
        <div className="text-center"><Gauge g={g} /><p className="mt-2 text-sm text-muted">{g.label}</p></div>
      </div>
    </header>
  )
}

function Overview({ data }) {
  const a = data.analytics, s = data.static_analysis_result
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card title="At a glance" className="lg:col-span-3">
        {a.overview_cards.length ? (
          <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {a.overview_cards.map((c) => <Stat key={c.label} name={c.label} value={`${num(c.value)}${c.unit ? ' ' + c.unit : ''}`} />)}
          </dl>
        ) : <Empty />}
      </Card>
      <Card title="Languages" className="lg:col-span-2">
        {a.language_distribution.length ? (
          <div className="grid items-center gap-4 sm:grid-cols-2">
            <div className="h-56">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={a.language_distribution} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} stroke="#131a2b" paddingAngle={2}>
                    {a.language_distribution.map((_, i) => <Cell key={i} fill={SERIES[i % SERIES.length]} />)}
                  </Pie>
                  <Tooltip {...TOOLTIP} formatter={(v, n) => [num(v), n]} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="space-y-2 text-sm">
              {a.language_distribution.map((l, i) => (
                <li key={l.name} className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2"><span className="h-3 w-3 rounded-sm" style={{ background: SERIES[i % SERIES.length] }} />{l.name}</span>
                  <span className="text-muted">{l.percentage.toFixed(1)}%</span>
                </li>
              ))}
            </ul>
          </div>
        ) : <Empty />}
      </Card>
      <Card title="Codebase">
        <dl className="grid grid-cols-2 gap-3">
          <Stat name="Files" value={num(s.total_files)} />
          <Stat name="Directories" value={num(s.total_directories)} />
          <Stat name="Lines" value={num(s.total_lines)} />
          <Stat name="Comment lines" value={num(s.comment_lines)} />
        </dl>
        {s.project_types.length > 0 && <p className="mt-4 text-sm text-muted">Detected: <span className="text-text">{s.project_types.join(', ')}</span></p>}
      </Card>
    </div>
  )
}

function Metrics({ data }) {
  const a = data.analytics, r = data.repository_metrics_result, g = a.health_gauge
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Score breakdown">
        {a.score_breakdown.length ? (
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={a.score_breakdown} layout="vertical" margin={{ left: 12 }}>
                <CartesianGrid stroke="#263150" horizontal={false} />
                <XAxis type="number" domain={[g.min, g.max]} stroke="#98a3c0" />
                <YAxis type="category" dataKey="category" stroke="#98a3c0" width={120} />
                <Tooltip {...TOOLTIP} />
                <Bar dataKey="score" fill="#8b91ff" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <Empty />}
      </Card>
      <Card title="Why each score">
        <div className="space-y-2">
          {Object.entries(r).filter(([, v]) => v && typeof v === 'object' && 'score' in v).map(([k, v]) => (
            <details key={k} className="group rounded-xl bg-raised px-4 py-3">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 capitalize">
                <span>{label(k)}</span><span className="font-display font-bold text-accent">{Math.round(v.score)}</span>
              </summary>
              {[...v.evidence, ...v.reasons].length ? (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">{[...v.evidence, ...v.reasons].map((t, i) => <li key={i}>{t}</li>)}</ul>
              ) : <p className="mt-3 text-sm text-muted">No supporting detail provided.</p>}
            </details>
          ))}
        </div>
      </Card>
    </div>
  )
}

function History({ data }) {
  const h = data.git_history_result, t = data.analytics.commit_timeline
  return (
    <div className="grid gap-4">
      <Card title="Activity">
        <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat name="Commits" value={num(h.total_commits)} />
          <Stat name="Contributors" value={num(h.unique_contributors)} />
          <Stat name="Branches" value={num(h.total_branches)} />
          <Stat name="Commits per week" value={h.average_commits_per_week.toFixed(1)} />
          <Stat name="Recent activity" value={String(h.recent_activity_level).replace(/_/g, ' ')} />
          <Stat name="Repository age" value={`${num(h.repository_age_days)} days`} />
          <Stat name="First commit" value={date(h.first_commit_date)} />
          <Stat name="Latest commit" value={date(h.latest_commit_date)} />
        </dl>
      </Card>
      <Card title="Commits per month">
        {t.length ? (
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={t}>
                <CartesianGrid stroke="#263150" vertical={false} />
                {/* Monthly data can span many years (the backend no longer collapses it to
                    yearly); `interval` thins the VISIBLE labels to roughly a dozen evenly
                    spaced months so they never overlap, while every bar still keeps its own
                    tooltip with its exact month and commit count on hover. */}
                <XAxis
                  dataKey="month" stroke="#98a3c0" minTickGap={24}
                  interval={Math.max(0, Math.ceil(t.length / 12) - 1)}
                />
                <YAxis stroke="#98a3c0" allowDecimals={false} />
                <Tooltip {...TOOLTIP} />
                <Bar dataKey="commits" fill="#3fd5e8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <Empty />}
      </Card>
    </div>
  )
}

function Analytics({ data }) {
  const a = data.analytics
  const maxFiles = Math.max(1, ...a.largest_directories.map((d) => d.file_count))
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="File types">
        {a.file_type_distribution.length ? (
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={a.file_type_distribution} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid stroke="#263150" horizontal={false} />
                <XAxis type="number" stroke="#98a3c0" allowDecimals={false} />
                <YAxis type="category" dataKey="name" stroke="#98a3c0" width={80} />
                <Tooltip {...TOOLTIP} formatter={(v, _n, p) => [`${num(v)} (${p.payload.percentage.toFixed(1)}%)`, 'Files']} />
                <Bar dataKey="value" fill="#a78bfa" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <Empty />}
      </Card>
      <Card title="Largest directories">
        {a.largest_directories.length ? (
          <ul className="space-y-3">
            {a.largest_directories.map((d) => (
              <li key={d.path}>
                <div className="flex justify-between gap-3 text-sm"><span className="truncate" title={d.path}>{d.name}</span><span className="text-muted">{num(d.file_count)} files</span></div>
                <div className="mt-1 h-1.5 rounded-full bg-line"><div className="h-full rounded-full bg-primary" style={{ width: `${(d.file_count / maxFiles) * 100}%` }} /></div>
              </li>
            ))}
          </ul>
        ) : <Empty />}
      </Card>
      <Card title="Repository timeline" className="lg:col-span-2">
        {a.repository_timeline.length ? (
          <ol className="space-y-3 border-l border-line pl-5">
            {a.repository_timeline.map((e, i) => (
              <li key={i} className="relative"><span className="absolute -left-[25px] top-1.5 h-2 w-2 rounded-full bg-accent" /><p className="font-semibold">{e.label}</p><p className="text-sm text-muted">{date(e.date)}</p></li>
            ))}
          </ol>
        ) : <Empty />}
      </Card>
    </div>
  )
}

const AIInsightsTab = ({ data }) => <AIInsights aiInsights={data.ai_insights} />
const AdvancedVisualizationsTab = ({ data }) => <AdvancedVisualizations data={data} />

const TABS = [['overview', 'Overview', Overview], ['metrics', 'Engineering Metrics', Metrics], ['history', 'Git History', History], ['analytics', 'Analytics', Analytics], ['visualizations', 'Advanced Visualizations', AdvancedVisualizationsTab], ['ai', 'AI Insights', AIInsightsTab]]

export default function Dashboard({ data, onReset }) {
  const [tab, setTab] = useState('overview')
  const [reportState, setReportState] = useState({ loading: false, error: '' })
  async function handleReportDownload() {
    if (reportState.loading || !data) return
    setReportState({ loading: true, error: '' })
    try { await downloadRepositoryReport(data); setReportState({ loading: false, error: '' }) }
    catch (error) { setReportState({ loading: false, error: error.message || 'Report generation failed.' }) }
  }
  const Active = TABS.find(([id]) => id === tab)[2]
  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <p className="font-display text-lg font-bold text-primary">RepoInfographic</p>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={handleReportDownload} disabled={reportState.loading || !data} className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-wait disabled:opacity-60">{reportState.loading ? 'Generating PDF report…' : 'Download Repository Report (PDF)'}</button>
        <button onClick={onReset} className="rounded-lg border border-line px-4 py-2 text-sm font-semibold transition hover:border-accent hover:text-accent">Analyze another</button>
        </div>
      </div>
      {reportState.error && <p role="alert" className="mb-4 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-200">{reportState.error}</p>}
      <Header data={data} />
      <div role="tablist" aria-label="Dashboard sections" className="mt-6 flex gap-1 overflow-x-auto border-b border-line">
        {TABS.map(([id, name]) => (
          <button key={id} role="tab" id={`tab-${id}`} aria-selected={tab === id} aria-controls="panel" onClick={() => setTab(id)}
            className={`inline-flex items-center gap-1.5 whitespace-nowrap border-b-2 px-4 py-3 text-sm font-semibold transition ${tab === id ? 'border-accent text-text' : 'border-transparent text-muted hover:text-text'}`}>
            {id === 'ai' && (
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-accent" fill="none" aria-hidden="true">
                <path d="M12 3l1.8 4.9L18.5 9l-4.7 1.9L12 15.8l-1.8-4.9L5.5 9l4.7-1.9L12 3z" fill="currentColor" />
              </svg>
            )}
            {name}
          </button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={tab} id="panel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="mt-5"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
          <Active data={data} />
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
