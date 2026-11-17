// Headless real-DOM check (Vitest + jsdom + Testing Library) that the AI
// Insights UI actually renders from real backend-shaped data, and that the
// full Analyze -> Dashboard -> AI Insights tab click-through works end to
// end against a mocked network call. No sandbox browser was available to
// take a literal screenshot; this executes the real component tree instead
// of only checking that the project builds.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import AIInsights from '../components/AIInsights'
import sample from './fixtures/sample_dashboard_data.json'

const AI_COMPLETED = {
  status: 'completed', model: 'qwen2.5:7b', generated_at: '2026-09-29T12:00:00Z',
  insights: {
    repository_summary: { available: true, summary: 'FastAPI is actively maintained.',
      observations: [{ statement: 'Sustained commit activity.', evidence: ['total_commits=4200'] }],
      recommendations: [], stages: [], missing_information: [] },
    architecture_explanation: { available: true, summary: '', observations: [], recommendations: [], stages: [], missing_information: ['source code contents'] },
    contribution_guide: { available: true, summary: '', observations: [], recommendations: ['[Medium] The repository has 53 contributors but no CONTRIBUTING.md, so start by drafting one.'], stages: [], missing_information: [] },
    project_evolution_roadmap: { available: true, summary: '', observations: [], recommendations: [],
      stages: [{ level: 'Beginner Developer', description: 'Minimal implementation.', items: ['Basic routing'] }], missing_information: [] },
    learning_roadmap: { available: true, summary: '', observations: [], recommendations: [], stages: [], missing_information: [] },
    commit_suggestions: { available: true, summary: '', observations: [], recommendations: ['[Low] Fix a typo in documentation.'], stages: [], missing_information: [] },
    improvement_suggestions: { available: true, summary: '', observations: [{ statement: 'Documentation coverage appears limited.', evidence: ['documentation_score=45'] }], recommendations: [], stages: [], missing_information: [] },
    readme_review: { available: false, summary: '', observations: [], recommendations: [], stages: [], missing_information: ['README text was not provided.'] },
  },
  error: null,
}

afterEach(() => vi.restoreAllMocks())

describe('AIInsights component, real render', () => {
  it('renders repository summary, evidence chips, recommendations and roadmap stages from real data shape', () => {
    render(<AIInsights aiInsights={AI_COMPLETED} />)
    expect(screen.getByText('AI-generated')).toBeTruthy()
    expect(screen.getByText('qwen2.5:7b')).toBeTruthy()
    expect(screen.getByText('FastAPI is actively maintained.')).toBeTruthy()
    expect(screen.getByText('Sustained commit activity.')).toBeTruthy()
    expect(screen.getByText('total_commits=4200')).toBeTruthy() // evidence chip
    expect(screen.getByText('Fix a typo in documentation.')).toBeTruthy() // recommendation text, tag stripped
    expect(screen.getByText('low')).toBeTruthy() // parsed priority badge
    expect(screen.getByText('Beginner Developer')).toBeTruthy() // roadmap stage
    expect(screen.getByText(/README text was not provided/)).toBeTruthy() // missing_information
  })

  it('shows a graceful unavailable state using the backend-provided, sanitized detail message', () => {
    render(<AIInsights aiInsights={{ status: 'unavailable', model: null, generated_at: null, insights: null,
      error: { code: 'AI_SERVICE_UNAVAILABLE', detail: 'Could not connect to Ollama. Make sure it is running.' } }} />)
    expect(screen.getByText('AI insights are unavailable')).toBeTruthy()
    expect(screen.getByText('Could not connect to Ollama. Make sure it is running.')).toBeTruthy()
  })

  it('shows a graceful disabled/empty state when ai_insights is null', () => {
    render(<AIInsights aiInsights={null} />)
    expect(screen.getByText('AI insights are turned off')).toBeTruthy()
  })
})

describe('Full click-through: Analyze -> Dashboard -> AI Insights tab (real components, mocked network)', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ success: true, message: 'ok', data: { ...sample, ai_insights: AI_COMPLETED } }),
    })
  })

  it('a single Analyze click surfaces both Modules 1-6 data and AI insights in the same dashboard', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText(/GitHub Repository URL/i), 'https://github.com/fastapi/fastapi')
    await user.click(screen.getByRole('button', { name: /Analyze Repository/i }))

    await waitFor(() => expect(screen.getByText(/fastapi\/fastapi/)).toBeTruthy())

    expect(global.fetch).toHaveBeenCalledTimes(1) // exactly ONE request for the whole pipeline
    const [url, opts] = global.fetch.mock.calls[0]
    expect(url).toContain('/api/v1/dashboard/analyze')
    expect(JSON.parse(opts.body)).toEqual({ repository_url: 'https://github.com/fastapi/fastapi' })

    await user.click(screen.getByRole('tab', { name: /AI Insights/i }))
    expect(await screen.findByText('AI-generated')).toBeTruthy()
    expect(screen.getByText('FastAPI is actively maintained.')).toBeTruthy()
  })
})

describe('Recommendation priority badges', () => {
  it('parses a [High]/[Medium]/[Low] prefix into a visible badge and strips it from the text', () => {
    render(<AIInsights aiInsights={AI_COMPLETED} />)
    expect(screen.getByText('medium')).toBeTruthy()
    expect(screen.getByText(/so start by drafting one\.$/)).toBeTruthy()
  })

  it('renders a recommendation with no priority tag as plain text, unchanged', () => {
    const ai = JSON.parse(JSON.stringify(AI_COMPLETED))
    ai.insights.commit_suggestions.recommendations = ['Fix a typo in documentation.']
    render(<AIInsights aiInsights={ai} />)
    expect(screen.getByText('Fix a typo in documentation.')).toBeTruthy()
  })
})
