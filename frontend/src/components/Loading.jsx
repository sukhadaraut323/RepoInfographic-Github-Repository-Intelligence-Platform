import { motion } from 'framer-motion'

// The current analyze API returns one final payload and does not stream
// per-stage events. Keep progress indeterminate rather than claiming stages
// have completed before the server confirms the full analysis response.
const AREAS = [
  'Repository details',
  'File structure',
  'Git history',
  'Engineering metrics',
  'Analytics',
  'Advanced Visualizations',
  'AI engineering insights',
]

export default function Loading({ url }) {
  return (
    <main className="grid min-h-screen place-items-center px-6" role="status" aria-live="polite">
      <div className="w-full max-w-md">
        <h1 className="font-display text-3xl font-bold">Analyzing repository</h1>
        <p className="mt-2 break-all text-sm text-muted">{url}</p>
        <ul className="mt-8 space-y-4">
          {AREAS.map((label, i) => (
            <li key={label}>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-text">{label}</span>
                <span className="text-[10px] text-muted">Awaiting server result</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-line">
                <motion.div
                  className="h-full w-1/3 rounded-full bg-gradient-to-r from-primary to-accent"
                  animate={{ x: ['-100%', '300%'] }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut', delay: i * 0.18 }}
                />
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-5 text-xs text-muted">Advanced Visualizations is part of the server analysis pipeline. This API does not currently expose per-stage progress events, so stages remain indeterminate until the final response arrives.</p>
        <p className="mt-3 text-sm text-muted">The AI engineering summary runs locally and can take a minute or more on top of the analysis. Please keep this page open.</p>
      </div>
    </main>
  )
}
