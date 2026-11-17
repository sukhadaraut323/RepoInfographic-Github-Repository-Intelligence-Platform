import { motion } from 'framer-motion'

const LABELS = {
  repository_summary: 'Repository Summary',
  architecture_explanation: 'Architecture',
  contribution_guide: 'Contribution Guide',
  project_evolution_roadmap: 'Project Evolution',
  learning_roadmap: 'Learning Roadmap',
  commit_suggestions: 'Suggested Commits',
  improvement_suggestions: 'Improvement Suggestions',
  readme_review: 'README Review',
}
const ORDER = Object.keys(LABELS)
const date = (d) => (d ? new Date(d).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : null)

const Sparkle = ({ className = 'h-4 w-4' }) => (
  <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
    <path d="M12 3l1.8 4.9L18.5 9l-4.7 1.9L12 15.8l-1.8-4.9L5.5 9l4.7-1.9L12 3z" fill="currentColor" />
    <path d="M19 15l.9 2.2L22 18l-2.1.8L19 21l-.9-2.2L16 18l2.1-.8L19 15z" fill="currentColor" />
  </svg>
)

function StatusMessage({ icon, title, children }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-8 text-center">
      <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-raised text-muted">{icon}</div>
      <h3 className="mt-4 font-display text-lg font-bold">{title}</h3>
      <p className="mx-auto mt-1 max-w-sm text-sm text-muted">{children}</p>
    </div>
  )
}

function Chip({ children }) {
  return <li className="rounded-full bg-raised px-3 py-1 text-xs text-accent">{children}</li>
}

const PRIORITY_STYLES = {
  high: 'bg-bad/15 text-bad',
  medium: 'bg-warn/15 text-warn',
  low: 'bg-ok/15 text-ok',
}

// Recommendation strings are instructed to start with "[High]"/"[Medium]"/"[Low]".
// Parsed out and shown as a badge; a recommendation without the tag (e.g. an
// older cached response) just renders as plain text, so this never breaks.
function Recommendation({ text }) {
  const match = /^\[(High|Medium|Low)\]\s*/i.exec(text)
  if (!match) return <li>{text}</li>
  const priority = match[1].toLowerCase()
  return (
    <li className="flex items-start gap-2">
      <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${PRIORITY_STYLES[priority]}`}>
        {priority}
      </span>
      <span>{text.slice(match[0].length)}</span>
    </li>
  )
}

function Roadmap({ stages }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {stages.map((s, i) => (
        <div key={i} className="rounded-xl bg-raised p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Stage {i + 1}</p>
          <p className="mt-1 font-display font-bold">{s.level}</p>
          {s.description && <p className="mt-1 text-sm text-muted">{s.description}</p>}
          {s.items?.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-4 text-sm text-muted">
              {s.items.map((it, j) => <li key={j}>{it}</li>)}
            </ul>
          )}
        </div>
      ))}
    </div>
  )
}

function SectionCard({ id, section, index }) {
  const hasContent = section.available && (
    section.summary || section.observations?.length || section.recommendations?.length || section.stages?.length
  )
  return (
    <motion.details
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index * 0.05, 0.3) }}
      open={index < 2}
      className="group overflow-hidden rounded-2xl border border-line bg-surface"
    >
      <summary className="flex cursor-pointer list-none items-start justify-between gap-4 p-5">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-primary to-accent text-ink">
            <Sparkle />
          </span>
          <div>
            <h3 className="font-display text-lg font-bold">{LABELS[id]}</h3>
            {section.available && section.summary && <p className="mt-1 text-sm text-muted">{section.summary}</p>}
          </div>
        </div>
        <svg viewBox="0 0 20 20" className="mt-1.5 h-4 w-4 shrink-0 text-muted transition-transform group-open:rotate-180" fill="none">
          <path d="M5 7.5l5 5 5-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </summary>

      <div className="space-y-5 border-t border-line px-5 pb-5 pt-4">
        {!hasContent ? (
          <p className="text-sm text-muted">The AI did not have enough evidence to generate this section.</p>
        ) : (
          <>
            {section.stages?.length > 0 && <Roadmap stages={section.stages} />}

            {section.observations?.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">Observations</p>
                <ul className="mt-2 space-y-3">
                  {section.observations.map((o, i) => (
                    <li key={i}>
                      <p className="text-sm">{o.statement}</p>
                      {o.evidence?.length > 0 && (
                        <ul className="mt-1.5 flex flex-wrap gap-1.5">{o.evidence.map((e, j) => <Chip key={j}>{e}</Chip>)}</ul>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {section.recommendations?.length > 0 && (
              <div className="rounded-xl border border-primary/30 bg-primary/5 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-primary">Recommendations</p>
                <ul className="mt-2 space-y-2 text-sm">
                  {section.recommendations.map((r, i) => <Recommendation key={i} text={r} />)}
                </ul>
              </div>
            )}
          </>
        )}

        {section.missing_information?.length > 0 && (
          <p className="text-xs text-muted">Not covered: {section.missing_information.join(' ')}</p>
        )}
      </div>
    </motion.details>
  )
}

export default function AIInsights({ aiInsights }) {
  if (!aiInsights) {
    return (
      <StatusMessage icon={<Sparkle className="h-5 w-5" />} title="AI insights are turned off">
        This analysis was generated without the AI Layer enabled. Repository data above is unaffected.
      </StatusMessage>
    )
  }

  if (aiInsights.status === 'unavailable') {
    return (
      <StatusMessage
        icon={<svg viewBox="0 0 24 24" className="h-5 w-5" fill="none"><path d="M12 9v4m0 4h.01M10.3 3.9L2.5 17a2 2 0 001.7 3h15.6a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" stroke="currentColor" strokeWidth="1.6" /></svg>}
        title="AI insights are unavailable"
      >
        {aiInsights.error?.detail ?? 'The AI engine could not generate insights for this repository.'}
      </StatusMessage>
    )
  }

  const insights = aiInsights.insights
  if (!insights) return <StatusMessage icon={<Sparkle className="h-5 w-5" />} title="No AI insights returned">Try analyzing again.</StatusMessage>

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
        <span className="inline-flex items-center gap-1.5 font-semibold text-accent"><Sparkle className="h-3.5 w-3.5" /> AI-generated</span>
        {aiInsights.model && <span>Model: <span className="text-text">{aiInsights.model}</span></span>}
        {date(aiInsights.generated_at) && <span>Generated {date(aiInsights.generated_at)}</span>}
      </div>
      <div className="space-y-3">
        {ORDER.map((id, i) => <SectionCard key={id} id={id} index={i} section={insights[id]} />)}
      </div>
    </div>
  )
}
