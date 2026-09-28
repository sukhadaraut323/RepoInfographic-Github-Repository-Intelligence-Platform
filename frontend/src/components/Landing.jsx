import { useState } from 'react'

const GITHUB_URL = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+?(\.git)?\/?$/

export function validateUrl(value) {
  const v = value.trim()
  if (!v) return 'Enter a GitHub repository URL.'
  if (!GITHUB_URL.test(v)) return 'Use the form https://github.com/owner/repository.'
  return ''
}

export default function Landing({ url, setUrl, onSubmit, error }) {
  const [touched, setTouched] = useState(false)
  const fieldError = touched ? validateUrl(url) : ''
  const shown = fieldError || error

  function submit(e) {
    e.preventDefault()
    setTouched(true)
    if (!validateUrl(url)) onSubmit()
  }

  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="grid-bg absolute inset-0" aria-hidden="true" />
      <div className="relative mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-16 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <p className="font-display text-lg font-bold text-primary">RepoInfographic</p>
          <h1 className="mt-5 max-w-xl font-display text-4xl font-bold leading-[1.08] sm:text-6xl">
            Turn any repository into engineering intelligence.
          </h1>
          <p className="mt-5 max-w-lg text-lg text-muted">
            Paste a public GitHub repository. RepoInfographic reads its structure and history, then shows you how healthy it is and where the work happens.
          </p>

          <form onSubmit={submit} className="mt-10 max-w-xl" noValidate>
            <label htmlFor="repo-url" className="text-sm font-semibold">GitHub Repository URL</label>
            <input
              id="repo-url" type="url" inputMode="url" autoComplete="off" spellCheck="false"
              value={url} onChange={(e) => setUrl(e.target.value)} onBlur={() => setTouched(true)}
              placeholder="https://github.com/owner/repository"
              aria-invalid={Boolean(shown)} aria-describedby={shown ? 'repo-url-error' : undefined}
              className="mt-2 w-full rounded-xl border border-line bg-surface px-4 py-3.5 text-base text-text placeholder:text-muted/70 transition-colors hover:border-primary/60 focus:border-accent focus:outline-none aria-[invalid=true]:border-bad"
            />
            {shown && <p id="repo-url-error" role="alert" className="mt-2 text-sm text-bad">{shown}</p>}
            <button
              type="submit"
              className="mt-4 w-full rounded-xl bg-primary px-6 py-3.5 font-display text-base font-bold text-ink transition hover:bg-accent active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            >
              Analyze Repository
            </button>
            <p className="mt-4 text-sm text-muted">No repository analyzed yet. Your results will appear here.</p>
          </form>
        </div>

        <svg viewBox="0 0 320 320" className="mx-auto hidden w-full max-w-sm lg:block" aria-hidden="true">
          <circle cx="160" cy="160" r="120" fill="none" stroke="#263150" strokeWidth="18" />
          <circle cx="160" cy="160" r="120" fill="none" stroke="#8b91ff" strokeWidth="18" strokeLinecap="round" strokeDasharray="560 754" transform="rotate(-90 160 160)" />
          {[40, 90, 60, 120, 80, 150].map((h, i) => (
            <rect key={i} x={98 + i * 24} y={215 - h * 0.7} width="14" height={h * 0.7} rx="4" fill={i % 2 ? '#3fd5e8' : '#8b91ff'} opacity="0.85" />
          ))}
        </svg>
      </div>
    </main>
  )
}
