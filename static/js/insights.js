// insights.js - Handles Insights (Internet RAG) feature

document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners after DOM is loaded
    const insightsTabBtn = document.getElementById('insights-tab-btn');
    const insightsDrugSelect = document.getElementById('insights-drug-select');
    const insightsDrugInput = document.getElementById('insights-drug-input');
    const insightsFetchBtn = document.getElementById('insights-fetch-btn');
    const insightsSummary = document.getElementById('insights-summary');
    const insightsArticles = document.getElementById('insights-articles');
    const insightsSpinner = document.getElementById('insights-loading-spinner');
    const insightsError = document.getElementById('insights-error');

    // Populate dropdown
    if (insightsDrugSelect) {
        fetch('/api/drugs')
            .then(resp => resp.json())
            .then(drugs => {
                drugs.forEach(drug => {
                    const opt = document.createElement('option');
                    opt.value = drug;
                    opt.textContent = drug;
                    insightsDrugSelect.appendChild(opt);
                });
            });
        insightsDrugSelect.addEventListener('change', function() {
            if (insightsDrugSelect.value) {
                insightsDrugInput.value = insightsDrugSelect.value;
            }
        });
    }

    if (insightsFetchBtn) {
        insightsFetchBtn.addEventListener('click', function() {
            const drugName = insightsDrugInput.value.trim();
            if (!drugName) {
                insightsError.textContent = 'Please enter a drug name.';
                insightsError.style.display = 'block';
                return;
            }
            insightsError.style.display = 'none';
            insightsSummary.innerHTML = '';
            insightsArticles.innerHTML = '';
            insightsSpinner.style.display = 'block';

            fetch('/api/insights', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ drug_name: drugName })
            })
            .then(resp => resp.json())
            .then(data => {
                insightsSpinner.style.display = 'none';
                if (data.error) {
                    insightsError.textContent = data.error;
                    insightsError.style.display = 'block';
                    return;
                }
                // Render summary (with markdown-like structure)
                insightsSummary.innerHTML = formatInsightsSummary(data.summary);
                // Render articles
                insightsArticles.innerHTML = renderInsightsArticles(data.articles);
            })
            .catch(err => {
                insightsSpinner.style.display = 'none';
                insightsError.textContent = 'Error fetching insights.';
                insightsError.style.display = 'block';
            });
        });
    }
});

// Helper to format summary in a beautiful card
function formatInsightsSummary(summary) {
    if (!summary) return '<div class="text-danger">No summary available.</div>';
    let html = summary
        .replace(/\n\n/g, '<br><br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
    return `<div class="card shadow mb-3 insights-summary-card">
        <div class="card-body">
            <h5 class="card-title mb-3"><i class="bi bi-lightbulb me-2"></i>Scientific Summary</h5>
            <div class="card-text">${html}</div>
        </div>
    </div>`;
}

// Override rendering for articles as cards
function renderInsightsArticles(articles) {
    if (!articles || articles.length === 0) {
        return '<div class="text-muted">No related articles found.</div>';
    }
    let html = '<div class="row">';
    articles.forEach(art => {
        html += `
        <div class="col-md-6 mb-3">
            <div class="card h-100 shadow insights-article-card">
                <div class="card-body">
                    <h6 class="card-title">
                        <a href="${art.link}" target="_blank" class="text-decoration-none">
                            <i class="bi bi-journal-text me-1"></i>${art.title}
                        </a>
                    </h6>
                    <div class="mb-2"><span class="badge bg-secondary">${art.source}</span></div>
                    <div class="card-text" style="font-size:0.97em;">${art.snippet}</div>
                </div>
            </div>
        </div>
        `;
    });
    html += '</div>';
    return html;
}
