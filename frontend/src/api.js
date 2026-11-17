// Single API integration point: the Repository Orchestrator only.
const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

// Stable error codes from the backend's error envelope -> user-friendly text.
// Raw backend detail is never shown (it may reference internal paths).
const MESSAGES = {
  INVALID_REPOSITORY_URL: 'That does not look like a valid public GitHub repository URL.',
  REPOSITORY_NOT_FOUND: 'Repository not found. Check the URL and that the repository is public.',
  GITHUB_RATE_LIMIT_EXCEEDED: 'GitHub rate limit reached. Please try again in a few minutes.',
  GITHUB_AUTHENTICATION_ERROR: 'The service could not authenticate with GitHub. Contact the administrator.',
  GITHUB_API_ERROR: 'GitHub is not responding as expected. Please try again shortly.',
  REPOSITORY_CLONE_ERROR: 'The repository could not be downloaded for analysis.',
  INVALID_GIT_REFERENCE: 'The repository has no usable default branch.',
}

export async function analyzeRepository(repositoryUrl) {
  let res
  try {
    res = await fetch(`${BASE}/api/v1/dashboard/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repository_url: repositoryUrl }),
    })
  } catch {
    throw new Error('Cannot reach the analysis service. Make sure the backend is running.')
  }
  let body = null
  try { body = await res.json() } catch { /* handled below */ }

  if (res.status === 422) throw new Error(MESSAGES.INVALID_REPOSITORY_URL)
  if (!res.ok || !body || body.success !== true) {
    const fallback = res.status >= 500 ? 'The analysis failed on the server. Please try again later.' : 'The analysis could not be completed.'
    throw new Error(MESSAGES[body?.error?.code] ?? fallback)
  }
  if (!body.data) throw new Error('The service returned an empty response.')
  return body.data
}

export async function downloadRepositoryReport(data) {
  let res
  try {
    res = await fetch(`${BASE}/api/v1/dashboard/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data }),
    })
  } catch {
    throw new Error('Cannot reach the report service. Make sure the backend is running.')
  }
  if (!res.ok) {
    let message = 'The PDF report could not be generated.'
    try {
      const body = await res.json()
      if (body?.detail) message = body.detail
    } catch { /* non-JSON server response */ }
    throw new Error(message)
  }
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.toLowerCase().includes('application/pdf')) {
    throw new Error('The report service returned an invalid file format.')
  }
  const blob = await res.blob()
  if (blob.size < 8 || (await blob.slice(0, 5).text()) !== '%PDF-') {
    throw new Error('The generated report is not a valid PDF file.')
  }
  const disposition = res.headers.get('content-disposition') || ''
  const match = disposition.match(/filename="?([^";]+)"?/i)
  const fallback = `RepoInfographic_${(data?.repository_metadata?.full_name || 'repository').replace(/[^a-z0-9._-]+/gi, '_')}_Analysis_Report.pdf`
  const filename = match?.[1] || fallback
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
