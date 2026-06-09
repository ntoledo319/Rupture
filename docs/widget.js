/**
 * EOLkits embeddable widget.
 * Usage: <script src="https://eolkits.com/widget.js" data-repo="owner/repo"></script>
 */
(function() {
  'use strict';
  const script = document.currentScript;
  const repo = script && script.dataset ? script.dataset.repo : '';
  if (!repo) {
    console.error('EOLkits widget: data-repo attribute required');
    return;
  }
  const styles = `
    .eolkits-widget{font-family:system-ui,-apple-system,sans-serif;border:1px solid #e5e7eb;border-radius:12px;padding:1rem;max-width:420px;background:#fff;color:#111827}
    .eolkits-widget h3{margin:0 0 .5rem;font-size:1rem}
    .eolkits-widget p{margin:.4rem 0;color:#4b5563;font-size:.9rem}
    .eolkits-widget a{display:inline-block;margin-top:.75rem;background:#2563eb;color:#fff;padding:.55rem .8rem;border-radius:6px;text-decoration:none;font-size:.875rem}
    .eolkits-widget .powered{margin-top:.75rem;color:#9ca3af;font-size:.75rem}
  `;
  const style = document.createElement('style');
  style.textContent = styles;
  document.head.appendChild(style);
  const container = document.createElement('div');
  container.className = 'eolkits-widget';
  container.innerHTML = `
    <h3>${repo}</h3>
    <p>Check this repository for AWS runtime and platform deprecation risks.</p>
    <a href="https://eolkits.com/audit/?repo=${encodeURIComponent(repo)}&utm_source=widget&utm_medium=embed&source=widget" target="_blank" rel="noopener">Run EOLkits audit</a>
    <div class="powered">Powered by EOLkits</div>
  `;
  script.parentNode.insertBefore(container, script.nextSibling);
  try {
    navigator.sendBeacon('https://eolkits.com/api/events', new Blob([JSON.stringify({ event: 'widget_view', source: 'widget', sku: 'audit', meta: { repo: repo } })], { type: 'application/json' }));
  } catch (e) {}
})();
