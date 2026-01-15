import { useState } from 'react'
import PropTypes from 'prop-types'

/**
 * Query Confirmation Component
 * 
 * Displays the system's understanding of the user's query and search plan,
 * allowing users to confirm or adjust before execution.
 */
function QueryConfirmation({
    searchPlan,
    onConfirm,
    onCancel,
    isLoading = false
}) {
    const [selectedInterests, setSelectedInterests] = useState(
        searchPlan?.intent?.possible_interests || []
    )
    const [excludedTopics, setExcludedTopics] = useState([])
    const [newExcludedTopic, setNewExcludedTopic] = useState('')
    const [depthPreference, setDepthPreference] = useState(
        searchPlan?.intent?.suggested_depth || 'deep'
    )
    const [additionalContext, setAdditionalContext] = useState('')

    const toggleInterest = (interest) => {
        setSelectedInterests(prev =>
            prev.includes(interest)
                ? prev.filter(i => i !== interest)
                : [...prev, interest]
        )
    }

    const addExcludedTopic = () => {
        if (newExcludedTopic.trim() && !excludedTopics.includes(newExcludedTopic.trim())) {
            setExcludedTopics(prev => [...prev, newExcludedTopic.trim()])
            setNewExcludedTopic('')
        }
    }

    const removeExcludedTopic = (topic) => {
        setExcludedTopics(prev => prev.filter(t => t !== topic))
    }

    const handleConfirm = () => {
        onConfirm({
            task_id: searchPlan.task_id,
            approved: true,
            selected_interests: selectedInterests,
            excluded_topics: excludedTopics,
            depth_preference: depthPreference,
            additional_context: additionalContext,
        })
    }

    if (!searchPlan) return null

    const { intent, included_directions, estimated_time_minutes } = searchPlan

    return (
        <div className="query-confirmation">
            <div className="confirmation-header">
                <h2>🔍 确认分析方向</h2>
                <p className="subtitle">系统已解析您的查询，请确认或调整以下设置</p>
            </div>

            {/* Intent Understanding Section */}
            <section className="confirmation-section">
                <h3>💡 查询理解</h3>
                <div className="understanding-card">
                    <div className="understanding-row">
                        <span className="label">原始查询:</span>
                        <span className="value">{intent.original_query}</span>
                    </div>
                    <div className="understanding-row">
                        <span className="label">系统理解:</span>
                        <span className="value highlight">{intent.understood_query}</span>
                    </div>
                    <div className="understanding-row">
                        <span className="label">时间范围:</span>
                        <span className="value">{intent.time_range_description}</span>
                    </div>
                    <div className="understanding-row">
                        <span className="label">领域:</span>
                        <span className="value">
                            {intent.domain_keywords.map((kw, i) => (
                                <span key={i} className="keyword-tag">{kw}</span>
                            ))}
                        </span>
                    </div>
                </div>
            </section>

            {/* Clarification Questions */}
            {intent.clarification_questions && intent.clarification_questions.length > 0 && (
                <section className="confirmation-section">
                    <h3>❓ 需要您确认</h3>
                    <ul className="clarification-list">
                        {intent.clarification_questions.map((q, i) => (
                            <li key={i}>{q}</li>
                        ))}
                    </ul>
                </section>
            )}

            {/* Interest Selection */}
            <section className="confirmation-section">
                <h3>🎯 关注方向 (可多选)</h3>
                <div className="interest-grid">
                    {intent.possible_interests.map((interest, i) => (
                        <button
                            key={i}
                            className={`interest-button ${selectedInterests.includes(interest) ? 'selected' : ''}`}
                            onClick={() => toggleInterest(interest)}
                        >
                            {selectedInterests.includes(interest) ? '✓ ' : ''}{interest}
                        </button>
                    ))}
                </div>
            </section>

            {/* Search Plan Preview */}
            <section className="confirmation-section">
                <h3>📋 搜索计划</h3>
                <div className="search-plan-list">
                    {included_directions.map((direction, i) => (
                        <div key={i} className={`search-direction ${direction.priority}`}>
                            <div className="direction-header">
                                <span className="source-icon">
                                    {direction.source === 'search_arxiv' && '📚'}
                                    {direction.source === 'search_github_trending' && '🔥'}
                                    {direction.source === 'search_github_repos' && '💻'}
                                    {direction.source === 'search_hackernews' && '🗣️'}
                                    {direction.source === 'fetch_rss_feeds' && '📰'}
                                    {direction.source === 'internet_search' && '🌐'}
                                </span>
                                <span className="source-name">{direction.source}</span>
                                <span className={`priority-badge ${direction.priority}`}>
                                    {direction.priority}
                                </span>
                            </div>
                            <div className="direction-query">{direction.query_template}</div>
                            <div className="direction-purpose">{direction.purpose}</div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Excluded Topics */}
            <section className="confirmation-section">
                <h3>🚫 排除已知内容 (可选)</h3>
                <p className="section-hint">添加您已了解的内容，系统将避免重复介绍</p>
                <div className="excluded-topics-input">
                    <input
                        type="text"
                        value={newExcludedTopic}
                        onChange={(e) => setNewExcludedTopic(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && addExcludedTopic()}
                        placeholder="例如: 我已知道 CrewAI"
                    />
                    <button onClick={addExcludedTopic} className="add-button">添加</button>
                </div>
                {excludedTopics.length > 0 && (
                    <div className="excluded-tags">
                        {excludedTopics.map((topic, i) => (
                            <span key={i} className="excluded-tag">
                                {topic}
                                <button onClick={() => removeExcludedTopic(topic)}>×</button>
                            </span>
                        ))}
                    </div>
                )}
            </section>

            {/* Depth Selection */}
            <section className="confirmation-section">
                <h3>⏱️ 分析深度</h3>
                <div className="depth-options">
                    <button
                        className={`depth-option ${depthPreference === 'quick' ? 'selected' : ''}`}
                        onClick={() => setDepthPreference('quick')}
                    >
                        <span className="depth-icon">⚡</span>
                        <span className="depth-label">快速概览</span>
                        <span className="depth-time">约 5 分钟</span>
                    </button>
                    <button
                        className={`depth-option ${depthPreference === 'deep' ? 'selected' : ''}`}
                        onClick={() => setDepthPreference('deep')}
                    >
                        <span className="depth-icon">🔬</span>
                        <span className="depth-label">深度分析</span>
                        <span className="depth-time">约 {estimated_time_minutes} 分钟</span>
                    </button>
                </div>
            </section>

            {/* Additional Context */}
            <section className="confirmation-section">
                <h3>📝 补充说明 (可选)</h3>
                <textarea
                    value={additionalContext}
                    onChange={(e) => setAdditionalContext(e.target.value)}
                    placeholder="例如: 特别想了解与 LangChain 的对比..."
                    rows={3}
                />
            </section>

            {/* Action Buttons */}
            <div className="confirmation-actions">
                <button
                    className="cancel-button"
                    onClick={onCancel}
                    disabled={isLoading}
                >
                    取消
                </button>
                <button
                    className="confirm-button"
                    onClick={handleConfirm}
                    disabled={isLoading}
                >
                    {isLoading ? '正在启动...' : '✓ 确认执行'}
                </button>
            </div>
        </div>
    )
}

QueryConfirmation.propTypes = {
    searchPlan: PropTypes.shape({
        task_id: PropTypes.string.isRequired,
        intent: PropTypes.shape({
            original_query: PropTypes.string.isRequired,
            understood_query: PropTypes.string.isRequired,
            time_range_description: PropTypes.string.isRequired,
            time_range_days: PropTypes.number.isRequired,
            domain_keywords: PropTypes.arrayOf(PropTypes.string).isRequired,
            possible_interests: PropTypes.arrayOf(PropTypes.string).isRequired,
            suggested_depth: PropTypes.string.isRequired,
            clarification_questions: PropTypes.arrayOf(PropTypes.string),
        }).isRequired,
        included_directions: PropTypes.arrayOf(PropTypes.shape({
            source: PropTypes.string.isRequired,
            query_template: PropTypes.string.isRequired,
            purpose: PropTypes.string.isRequired,
            priority: PropTypes.string.isRequired,
        })).isRequired,
        estimated_time_minutes: PropTypes.number.isRequired,
    }),
    onConfirm: PropTypes.func.isRequired,
    onCancel: PropTypes.func.isRequired,
    isLoading: PropTypes.bool,
}

export default QueryConfirmation
