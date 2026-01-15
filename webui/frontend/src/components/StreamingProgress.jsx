import { useEffect, useRef } from 'react'

/**
 * Streaming progress component showing real-time agent events
 */
export default function StreamingProgress({ events, isRunning }) {
    const listRef = useRef(null)

    // Auto-scroll to bottom when new events arrive
    useEffect(() => {
        if (listRef.current) {
            listRef.current.scrollTop = listRef.current.scrollHeight
        }
    }, [events])

    if (events.length === 0 && !isRunning) {
        return null
    }

    return (
        <div className="streaming-progress">
            <div className="progress-header">
                <h2>📊 分析进度</h2>
                {isRunning && <div className="progress-spinner" />}
            </div>

            <div className="event-list" ref={listRef}>
                {events.map((event, index) => (
                    <div
                        key={`${event.timestamp}-${index}`}
                        className={`event-item ${event.error ? 'event-error' : ''}`}
                    >
                        <span className="event-time">{event.time_formatted}</span>
                        <div className="event-content">
                            <div className="event-name">{event.name}</div>
                            {event.detail && (
                                <div className="event-detail">{event.detail}</div>
                            )}
                            {event.error && (
                                <div className="event-detail event-error">❌ {event.error}</div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
