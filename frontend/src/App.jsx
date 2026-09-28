import { useRef, useState } from 'react'
import { MotionConfig } from 'framer-motion'
import { analyzeRepository } from './api'
import Landing from './components/Landing'
import Loading from './components/Loading'
import Dashboard from './components/Dashboard'

export default function App() {
  const [url, setUrl] = useState('')
  const [state, setState] = useState({ status: 'idle', data: null, error: null })
  const inFlight = useRef(false) // hard guard against duplicate submissions

  async function run() {
    if (inFlight.current) return
    inFlight.current = true
    setState({ status: 'loading', data: null, error: null })
    try {
      setState({ status: 'success', data: await analyzeRepository(url.trim()), error: null })
    } catch (e) {
      setState({ status: 'error', data: null, error: e.message })
    } finally {
      inFlight.current = false
    }
  }

  return (
    <MotionConfig reducedMotion="user">
      {state.status === 'loading' && <Loading url={url} />}
      {state.status === 'success' && <Dashboard data={state.data} onReset={() => setState({ status: 'idle', data: null, error: null })} />}
      {(state.status === 'idle' || state.status === 'error') && <Landing url={url} setUrl={setUrl} onSubmit={run} error={state.error} />}
    </MotionConfig>
  )
}
