import { useState, useRef, useEffect } from 'react'

/**
 * Query input component with Apple-style design
 */
export default function QueryInput({ onSubmit, disabled }) {
    const [query, setQuery] = useState('')
    const inputRef = useRef(null)

    useEffect(() => {
        // Focus input on mount
        if (inputRef.current && !disabled) {
            inputRef.current.focus()
        }
    }, [disabled])

    const handleSubmit = (e) => {
        e.preventDefault()
        if (query.trim() && !disabled) {
            onSubmit(query.trim())
        }
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            handleSubmit(e)
        }
    }

    return (
        <form className="query-input-container" onSubmit={handleSubmit}>
            <div className="query-input-wrapper">
                <input
                    ref={inputRef}
                    type="text"
                    className="query-input"
                    placeholder="输入您想了解的热点话题，例如：今天AI领域有什么进展？"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                />
                <button
                    type="submit"
                    className="submit-button"
                    disabled={disabled || !query.trim()}
                >
                    开始分析
                </button>
            </div>
        </form>
    )
}
