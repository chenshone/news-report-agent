import { useRef, useCallback } from 'react'

/**
 * Report viewer component with PDF download support
 */
export default function ReportViewer({ reportHtml, onNewQuery }) {
    const iframeRef = useRef(null)

    const handleDownloadPdf = useCallback(async () => {
        // Dynamically import html2pdf
        const html2pdf = (await import('html2pdf.js')).default

        // Get the iframe document
        if (iframeRef.current && iframeRef.current.contentDocument) {
            const element = iframeRef.current.contentDocument.body

            const opt = {
                margin: [10, 10, 10, 10],
                filename: `热点资讯分析报告_${new Date().toISOString().split('T')[0]}.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: {
                    scale: 2,
                    useCORS: true,
                    letterRendering: true,
                },
                jsPDF: {
                    unit: 'mm',
                    format: 'a4',
                    orientation: 'portrait'
                }
            }

            html2pdf().set(opt).from(element).save()
        }
    }, [])

    const handleOpenInNewTab = useCallback(() => {
        const newWindow = window.open('', '_blank')
        if (newWindow) {
            newWindow.document.write(reportHtml)
            newWindow.document.close()
        }
    }, [reportHtml])

    if (!reportHtml) {
        return null
    }

    return (
        <div className="report-viewer">
            <div className="report-header">
                <h2>📋 分析报告</h2>
                <div className="report-actions">
                    <button className="action-button" onClick={handleOpenInNewTab}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3" />
                        </svg>
                        新窗口打开
                    </button>
                    <button className="action-button" onClick={handleDownloadPdf}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
                        </svg>
                        下载 PDF
                    </button>
                </div>
            </div>

            <div className="report-content">
                <iframe
                    ref={iframeRef}
                    srcDoc={reportHtml}
                    title="分析报告"
                    sandbox="allow-same-origin"
                />
            </div>

            <div className="new-query-section">
                <button className="new-query-button" onClick={onNewQuery}>
                    开始新的分析
                </button>
            </div>
        </div>
    )
}
