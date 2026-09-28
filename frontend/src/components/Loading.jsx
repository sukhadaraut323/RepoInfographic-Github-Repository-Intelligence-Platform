import { motion } from 'framer-motion'

// Indeterminate only: the backend exposes no progress data, so nothing here
// claims a module has finished and there are no percentages.
const AREAS = ['Repository details', 'File structure', 'Git history', 'Engineering metrics', 'Analytics']

export default function Loading({ url }) {
  return (
    <main className="grid min-h-screen place-items-center px-6" role="status" aria-live="polite">
      <div className="w-full max-w-md">
        <h1 className="font-display text-3xl font-bold">Analyzing repository</h1>
        <p className="mt-2 break-all text-sm text-muted">{url}</p>
        <ul className="mt-8 space-y-4">
          {AREAS.map((label, i) => (
            <li key={label}>
              <span className="text-sm text-muted">{label}</span>
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
        <p className="mt-8 text-sm text-muted">Larger repositories can take a minute or more. Please keep this page open.</p>
      </div>
    </main>
  )
}
