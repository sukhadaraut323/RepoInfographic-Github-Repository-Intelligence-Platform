import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AdvancedVisualizations from '../components/AdvancedVisualizations'
import Loading from '../components/Loading'

vi.mock('recharts', () => {
  const Wrapper = ({ children }) => <div>{children}</div>
  const Shape = ({ children }) => <g>{children}</g>
  return {
    Bar: Shape, BarChart: Wrapper, CartesianGrid: () => null, Cell: () => null,
    Pie: Shape, PieChart: Wrapper, ResponsiveContainer: Wrapper, Tooltip: () => null,
    XAxis: () => null, YAxis: () => null,
  }
})

const data = { advanced_visualizations: {
  summary: { total_files: 2, total_directories: 1, total_source_files: 2 },
  tree: { name: 'demo', path: '.', type: 'directory', children: [] },
  technologies: [], languages: [], extensions: [],
  dependency_graph: {
    nodes: [
      { id: 'api/a.py', label: 'api/a.py', path: 'api/a.py', package: 'api', type: 'module', incoming_count: 0, outgoing_count: 1 },
      { id: 'service/b.py', label: 'service/b.py', path: 'service/b.py', package: 'service', type: 'module', incoming_count: 1, outgoing_count: 0 },
    ],
    edges: [{ source: 'api/a.py', target: 'service/b.py', type: 'internal', evidence: 'Python import: service.b', source_path: 'api/a.py', line: 1 }],
    metrics: { most_incoming: [], most_outgoing: [], isolated_modules: [] },
  },
  architecture: {
    layers: [{ id: 'API / Interface', name: 'API / Interface', components: ['api'] }],
    nodes: [{ id: 'api', name: 'api', layer: 'API / Interface', description: 'API source', file_count: 1, files: ['api/a.py'] }],
    edges: [], method: 'Static import evidence.',
  },
  workflow: { workflows: [{
    id: 'flow-1', name: 'GET /items', classification: 'Static sequence',
    entry_point: { path: 'api/a.py', line: 1 },
    steps: [
      { id: 'start', label: 'Start', kind: 'start', path: 'api/a.py', line: 1, confidence: 'detected', evidence: 'Entry' },
      { id: 'step', label: 'list_items', kind: 'process', path: 'api/a.py', line: 2, confidence: 'detected', evidence: 'Function declaration' },
      { id: 'end', label: 'Return / end', kind: 'end', path: 'api/a.py', line: 3, confidence: 'inferred', evidence: 'End' },
    ],
  }] },
} }

describe('Advanced Visualizations', () => {
  it('renders architecture, workflow and dependency graph from the backend payload', () => {
    render(<AdvancedVisualizations data={data} />)
    expect(screen.getByText('Dynamic Architecture Diagram')).toBeTruthy()
    expect(screen.getByText('Repository Workflow')).toBeTruthy()
    expect(screen.getByText('Dependency Graph')).toBeTruthy()
    expect(screen.getByText('GET /items')).toBeTruthy()
  })

  it('supports selecting architecture components and workflow steps', async () => {
    const user = userEvent.setup()
    render(<AdvancedVisualizations data={data} />)
    await user.click(screen.getByText('api', { selector: 'text' }))
    expect(screen.getByText('API source')).toBeTruthy()
    await user.click(screen.getByText('list_items'))
    expect(screen.getByText(/Function declaration/)).toBeTruthy()
  })

  it('shows a safe empty state when visualization data is missing', () => {
    render(<AdvancedVisualizations data={{ advanced_visualizations: null }} />)
    expect(screen.getByText(/Visualization data was unavailable/)).toBeTruthy()
  })
})

describe('Analysis progress stages', () => {
  it('includes Advanced Visualizations without falsely marking a stage complete', () => {
    render(<Loading url="https://github.com/example/project" />)
    expect(screen.getByText('Advanced Visualizations')).toBeTruthy()
    expect(screen.getAllByText('Awaiting server result')).toHaveLength(7)
  })
})

describe('Workflow layout resilience', () => {
  it('renders long source-backed branch workflows with adaptive node content and zoom controls', async () => {
    const user = userEvent.setup()
    const workflowData = structuredClone(data)
    workflowData.advanced_visualizations.workflow.workflows[0].steps = [
      { id: 'start', label: 'Start repository processing', kind: 'start', path: 'src/api/main.py', line: 1 },
      { id: 'decision', label: 'Validate repository metadata and access permissions', kind: 'decision', path: 'src/services/validation/repository_access_service.py', line: 42 },
      { id: 'success', label: 'Continue with successful repository validation and prepare analysis context', kind: 'process', path: 'src/services/analysis/context_builder.py', line: 80 },
      { id: 'failure', label: 'Handle authentication or repository validation exception', kind: 'error', path: 'src/services/validation/repository_access_service.py', line: 99 },
      { id: 'end', label: 'Return completed analysis result', kind: 'end', path: 'src/api/main.py', line: 120 },
    ]
    workflowData.advanced_visualizations.workflow.workflows[0].edges = [
      { source: 'start', target: 'decision' },
      { source: 'decision', target: 'success', label: 'True' },
      { source: 'decision', target: 'failure', label: 'False' },
      { source: 'success', target: 'end', label: 'Success' },
    ]
    render(<AdvancedVisualizations data={workflowData} />)
    expect(screen.getByText('Validate repository metadata and access permissions')).toBeTruthy()
    expect(screen.getByText('Handle authentication or repository validation exception')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /Zoom/ }))
    expect(screen.getByRole('img', { name: /Source-derived workflow/ })).toBeTruthy()
  })
})
