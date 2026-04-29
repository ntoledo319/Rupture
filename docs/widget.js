/**
 * Rupture Embeddable Widget
 * Usage: <script src="https://ntoledo319.github.io/Rupture/widget/embed.js" data-repo="owner/repo"></script>
 */

(function() {
    'use strict';
    
    const SCRIPT = document.currentScript;
    const REPO = SCRIPT?.dataset?.repo;
    const API_BASE = 'https://rupture-worker.ntoledo319.workers.dev';
    
    if (!REPO) {
        console.error('Rupture widget: data-repo attribute required');
        return;
    }
    
    // Widget styles
    const styles = `
        .rupture-widget {
            font-family: system-ui, -apple-system, sans-serif;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 1.5rem;
            max-width: 400px;
            background: white;
        }
        .rupture-widget h3 {
            margin: 0 0 1rem 0;
            font-size: 1.125rem;
            color: #1f2937;
        }
        .rupture-widget .status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0.5rem 0;
        }
        .rupture-widget .status-icon {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        .rupture-widget .status-clean { background: #16a34a; }
        .rupture-widget .status-warn { background: #ca8a04; }
        .rupture-widget .status-critical { background: #dc2626; }
        .rupture-widget .findings {
            margin-top: 1rem;
        }
        .rupture-widget .finding {
            padding: 0.5rem;
            margin: 0.25rem 0;
            border-radius: 6px;
            font-size: 0.875rem;
        }
        .rupture-widget .finding-critical { background: #fef2f2; color: #991b1b; }
        .rupture-widget .finding-warn { background: #fefce8; color: #854d0e; }
        .rupture-widget .cta {
            display: block;
            margin-top: 1rem;
            padding: 0.75rem;
            background: #2563eb;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            text-align: center;
            font-size: 0.875rem;
        }
        .rupture-widget .powered {
            margin-top: 1rem;
            font-size: 0.75rem;
            color: #9ca3af;
            text-align: center;
        }
        .rupture-widget .powered a {
            color: #6b7280;
            text-decoration: none;
        }
    `;
    
    // Create widget container
    const container = document.createElement('div');
    container.className = 'rupture-widget';
    container.innerHTML = `
        <h3>🔍 ${REPO}</h3>
        <div class="status">
            <div class="status-icon status-clean"></div>
            <span>Scanning...</span>
        </div>
        <div class="powered">
            <a href="https://ntoledo319.github.io/Rupture" target="_blank">Powered by Rupture</a>
        </div>
    `;
    
    // Insert styles
    const styleEl = document.createElement('style');
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);
    
    // Insert widget after script
    SCRIPT.parentNode.insertBefore(container, SCRIPT.nextSibling);
    
    // Fetch scan results
    async function fetchResults() {
        try {
            const response = await fetch(`${API_BASE}/api/widget/scan?repo=${encodeURIComponent(REPO)}`);
            
            if (!response.ok) {
                throw new Error('Scan failed');
            }
            
            const data = await response.json();
            renderWidget(data);
        } catch (error) {
            renderError(error);
        }
    }
    
    function renderWidget(data) {
        const statusClass = data.critical > 0 ? 'status-critical' : 
                           data.warnings > 0 ? 'status-warn' : 'status-clean';
        const statusText = data.critical > 0 ? `${data.critical} critical issues` :
                          data.warnings > 0 ? `${data.warnings} warnings` : 'No issues found';
        
        let findingsHtml = '';
        if (data.findings && data.findings.length > 0) {
            findingsHtml = '<div class="findings">';
            for (const finding of data.findings.slice(0, 3)) {
                const severityClass = finding.severity === 'critical' ? 'finding-critical' : 'finding-warn';
                findingsHtml += `<div class="finding ${severityClass}">${finding.message}</div>`;
            }
            if (data.findings.length > 3) {
                findingsHtml += `<div class="finding">+${data.findings.length - 3} more</div>`;
            }
            findingsHtml += '</div>';
        }
        
        container.innerHTML = `
            <h3>🔍 ${REPO}</h3>
            <div class="status">
                <div class="status-icon ${statusClass}"></div>
                <span>${statusText}</span>
            </div>
            ${findingsHtml}
            <a href="https://ntoledo319.github.io/Rupture/audit?repo=${encodeURIComponent(REPO)}" 
               class="cta" target="_blank">Get Full Audit</a>
            <div class="powered">
                <a href="https://ntoledo319.github.io/Rupture" target="_blank">Powered by Rupture</a>
            </div>
        `;
    }
    
    function renderError(error) {
        container.innerHTML = `
            <h3>🔍 ${REPO}</h3>
            <div class="status">
                <div class="status-icon status-warn"></div>
                <span>Unable to scan public repo</span>
            </div>
            <a href="https://ntoledo319.github.io/Rupture/audit" 
               class="cta" target="_blank">Run Manual Scan</a>
            <div class="powered">
                <a href="https://ntoledo319.github.io/Rupture" target="_blank">Powered by Rupture</a>
            </div>
        `;
    }
    
    // Fetch results
    fetchResults();
})();
