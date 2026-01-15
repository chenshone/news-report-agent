import { useState, useCallback } from 'react'
import QueryInput from './components/QueryInput'
import QueryConfirmation from './components/QueryConfirmation'
import StreamingProgress from './components/StreamingProgress'
import ReportViewer from './components/ReportViewer'
import './styles/apple-style.css'

// API base URL - change this for production
const API_BASE = 'http://localhost:8000'

/**
 * Main App component for News Report Agent Web UI
 * 
 * Flow:
 * 1. User inputs query
 * 2. Call /api/analyze/prepare to get search plan
 * 3. Show QueryConfirmation for user to review/adjust
 * 4. Call /api/analyze/execute with user confirmation
 * 5. Stream progress and show final report
 */
function App() {
  // UI states: idle -> preparing -> confirming -> running -> completed/error
  const [status, setStatus] = useState('idle')
  const [events, setEvents] = useState([])
  const [reportHtml, setReportHtml] = useState(null)
  const [error, setError] = useState(null)
  const [searchPlan, setSearchPlan] = useState(null)
  const [currentQuery, setCurrentQuery] = useState('')

  // Phase 1: Prepare analysis (understand query, generate search plan)
  const prepareAnalysis = useCallback(async (query) => {
    setStatus('preparing')
    setError(null)
    setCurrentQuery(query)

    try {
      const response = await fetch(`${API_BASE}/api/analyze/prepare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `HTTP error! status: ${response.status}`)
      }

      const plan = await response.json()
      setSearchPlan(plan)
      setStatus('confirming')

    } catch (err) {
      console.error('Prepare error:', err)
      setError(err.message)
      setStatus('error')
    }
  }, [])

  // Phase 2: Execute analysis with user confirmation
  const executeAnalysis = useCallback(async (confirmation) => {
    setStatus('running')
    setEvents([])
    setReportHtml(null)

    try {
      // Start execution
      const response = await fetch(`${API_BASE}/api/analyze/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: confirmation.task_id,
          confirmation: confirmation,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      const taskId = data.task_id

      // Connect to SSE stream
      const eventSource = new EventSource(`${API_BASE}/api/stream/${taskId}`)

      eventSource.onmessage = (event) => {
        try {
          const eventData = JSON.parse(event.data)

          // Add event to list
          setEvents(prev => [...prev, eventData])

          // Check for completion
          if (eventData.type === 'report') {
            setReportHtml(eventData.data?.report_html)
            setStatus('completed')
            eventSource.close()
          } else if (eventData.type === 'error' && eventData.error) {
            if (!eventData.detail?.includes('正在')) {
              setError(eventData.error)
              setStatus('error')
              eventSource.close()
            }
          }
        } catch (e) {
          console.error('Failed to parse SSE event:', e)
        }
      }

      eventSource.onerror = (err) => {
        console.error('SSE error:', err)
        if (status === 'running') {
          setStatus('idle')
        }
        eventSource.close()
      }

    } catch (err) {
      console.error('Execute error:', err)
      setError(err.message)
      setStatus('error')
    }
  }, [status])

  // Cancel confirmation and go back to input
  const cancelConfirmation = useCallback(() => {
    setStatus('idle')
    setSearchPlan(null)
    setError(null)
  }, [])

  // Start a new query
  const handleNewQuery = useCallback(() => {
    setStatus('idle')
    setEvents([])
    setReportHtml(null)
    setError(null)
    setSearchPlan(null)
    setCurrentQuery('')
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>📰 热点资讯分析</h1>
        <p>AI 驱动的智能新闻分析与报告生成</p>
      </header>

      <main>
        {/* Query input - show when idle */}
        {status === 'idle' && (
          <QueryInput
            onSubmit={prepareAnalysis}
            disabled={false}
          />
        )}

        {/* Preparing state */}
        {status === 'preparing' && (
          <div className="streaming-progress" style={{ marginTop: 'var(--spacing-xl)' }}>
            <div className="progress-header">
              <h2>🔍 正在分析您的查询...</h2>
            </div>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              正在理解您的意图并生成搜索计划，请稍候...
            </p>
            <div className="loading-spinner" style={{ marginTop: '20px' }}>
              <div className="spinner"></div>
            </div>
          </div>
        )}

        {/* Query confirmation - show when awaiting user confirmation */}
        {status === 'confirming' && searchPlan && (
          <QueryConfirmation
            searchPlan={searchPlan}
            onConfirm={executeAnalysis}
            onCancel={cancelConfirmation}
            isLoading={false}
          />
        )}

        {/* Error message */}
        {error && status === 'error' && (
          <div className="streaming-progress" style={{ marginTop: 'var(--spacing-xl)' }}>
            <div className="progress-header">
              <h2>❌ 分析失败</h2>
            </div>
            <p style={{ color: 'var(--color-error)' }}>{error}</p>
            <div className="new-query-section">
              <button className="new-query-button" onClick={handleNewQuery}>
                重新开始
              </button>
            </div>
          </div>
        )}

        {/* Streaming progress */}
        {(status === 'running' || (status === 'completed' && events.length > 0)) && (
          <StreamingProgress
            events={events}
            isRunning={status === 'running'}
          />
        )}

        {/* Report viewer */}
        {status === 'completed' && reportHtml && (
          <ReportViewer
            reportHtml={reportHtml}
            onNewQuery={handleNewQuery}
          />
        )}
      </main>
    </div>
  )
}

export default App
