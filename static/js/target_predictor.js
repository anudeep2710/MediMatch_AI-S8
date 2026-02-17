// Target Predictor JS
// Handles input, dropdown, POST to backend, and rendering results (targets, similar molecules, explanations)

document.addEventListener('DOMContentLoaded', function() {
    populateTargetDropdown();
    document.getElementById('predict-target-btn').addEventListener('click', predictTarget);
});

async function populateTargetDropdown() {
    const dropdown = document.getElementById('target-dropdown');
    try {
        const response = await fetch('/api/drugs');
        const drugs = await response.json();
        drugs.forEach(drug => {
            const option = document.createElement('option');
            option.value = drug;
            option.textContent = drug;
            dropdown.appendChild(option);
        });
    } catch (e) {
        // Fail silently
    }
}

async function predictTarget() {
    const dropdown = document.getElementById('target-dropdown');
    const input = document.getElementById('target-input').value.trim();
    let smiles = '';
    let drug_name = '';
    if (dropdown.value) {
        drug_name = dropdown.value;
    } else if (input) {
        // Could be SMILES or drug name
        smiles = input;
        drug_name = input;
    } else {
        showTargetPredictorError('Please select a drug or enter a SMILES string or drug name.');
        return;
    }
    showTargetPredictorLoading(true);
    try {
        const response = await fetch('/api/predict_target', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ smiles, drug_name })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Prediction failed');
        }
        renderTargetPredictorResults(data);
    } catch (error) {
        showTargetPredictorError(error.message);
    } finally {
        showTargetPredictorLoading(false);
    }
}

function showTargetPredictorLoading(isLoading) {
    document.getElementById('target-loading-spinner').style.display = isLoading ? 'block' : 'none';
}

function showTargetPredictorError(msg) {
    const err = document.getElementById('target-error');
    err.textContent = msg;
    err.style.display = 'block';
    document.getElementById('target-results').style.display = 'none';
}

async function renderTargetPredictorResults(data) {
    document.getElementById('target-error').style.display = 'none';
    // Always show the main heading
    const targetsDiv = document.getElementById('predicted-targets');
    let html = '<h5>🎯 Predicted Targets</h5>';
    if (data.predicted_targets && data.predicted_targets.length) {
        html += '<div class="row">';
        data.predicted_targets.forEach(t => {
            html += `
            <div class="col-md-4 mb-3">
                <div class="card shadow flashcard-target h-100">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-2">
                            <span class="badge bg-success me-2" style="font-size:1.2em;">🎯</span>
                            <h6 class="mb-0">${t.target || 'Unknown Target'}</h6>
                        </div>
                        <div><strong>Type:</strong> ${t.target_type || '-'}</div>
                        <div><strong>Organism:</strong> ${t.organism || '-'}</div>
                        <div><strong>Mechanism:</strong> ${t.mechanism_of_action || '-'}</div>
                        <div><strong>Confidence:</strong> ${t.confidence ? (t.confidence*100).toFixed(1)+'%' : '-'}</div>
                    </div>
                </div>
            </div>
            `;
        });
        html += '</div>';
    } else {
        html += '<div class="alert alert-warning">No predicted targets found.</div>';
    }
    targetsDiv.innerHTML = html;

    // Always show similar molecules heading
    const simVisDiv = document.getElementById('similar-molecules-visuals');
    let simHeader = `<h6>🧬 Similar Molecules</h6>`;
    simVisDiv.innerHTML = simHeader;
    if (data.similar_drugs && data.similar_drugs.length) {
        simVisDiv.innerHTML += `<div class="row" id="sim-mol-row"></div>`;
        const rowDiv = document.getElementById('sim-mol-row');
        for (let i = 0; i < data.similar_drugs.length; i++) {
            const d = data.similar_drugs[i];
            const molDivId = `sim-mol-${i}`;
            const col = document.createElement('div');
            col.className = 'col-md-4 mb-3';
            // Card layout: image, then name, then info
            col.innerHTML = `<div class="card h-100"><div class="card-body d-flex flex-column align-items-center justify-content-between"><div id="${molDivId}" style="height:180px; width:100%; margin-bottom:10px;"></div><div class="mt-2 mb-2 text-center"><strong>${d.drug_name || ''}</strong></div><div class="w-100"><small>Target: ${d.target || 'N/A'}<br>Mechanism: ${d.mechanism_of_action || 'N/A'}<br>Shared: ${d.shared_property || ''}<br><em>${d.justification || ''}</em></small></div></div></div>`;
            rowDiv.appendChild(col);
            // Use same logic as Visualizer: fetch MOL block and use renderMolecule
            if (d.SMILES) {
                try {
                    // Fetch MOL block from backend
                    fetch('/api/molblock', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ smiles: d.SMILES })
                    })
                    .then(res => res.json())
                    .then(molData => {
                        if (molData.molblock && window.renderMolecule && window.$3Dmol) {
                            // Create a new viewer for each card
                            const viewer = window.$3Dmol.createViewer(molDivId, {backgroundColor: 'white'});
                            window.renderMolecule(viewer, molData.molblock, d.drug_name || '');
                        } else {
                            document.getElementById(molDivId).innerText = d.SMILES || '';
                        }
                    })
                    .catch(() => {
                        document.getElementById(molDivId).innerText = d.SMILES || '';
                    });
                } catch (e) {
                    document.getElementById(molDivId).innerText = d.SMILES || '';
                }
            } else {
                document.getElementById(molDivId).innerText = d.SMILES || '';
            }
            // Make card clickable to re-run prediction
            col.onclick = () => {
                document.getElementById('target-input').value = d.SMILES || '';
                predictTarget();
            };
        }
    } else {
        simVisDiv.innerHTML += '<div class="alert alert-warning">No similar molecules found.</div>';
    }

    // Similar drugs table
    const simDiv = document.getElementById('similar-drugs');
    let simTableHeader = `<h6 class="mt-3">💊 Similar Drugs <span class="badge bg-secondary" style="cursor:pointer" onclick="toggleSimilarDrugs()">Show/Hide</span></h6>`;
    if (data.similar_drugs && data.similar_drugs.length) {
        let simHtml = simTableHeader + `<div id="similar-drugs-table" style="display:none">`;
        simHtml += `<table class="table table-sm table-striped"><thead><tr><th>Name</th><th>ID</th><th>SMILES</th><th>Target</th><th>Mechanism</th><th>Similarity</th><th>Shared</th><th>Justification</th></tr></thead><tbody>`;
        data.similar_drugs.forEach(d => {
            simHtml += `<tr><td>${d.drug_name || ''}</td><td>${d.drug_id || ''}</td><td style="font-size:0.9em">${d.SMILES || ''}</td><td>${d.target || ''}</td><td>${d.mechanism_of_action || ''}</td><td>${d.similarity ? (d.similarity*100).toFixed(1)+'%' : ''}</td><td>${d.shared_property || ''}</td><td>${d.justification || ''}</td></tr>`;
        });
        simHtml += '</tbody></table></div>';
        simDiv.innerHTML = simHtml;
    } else {
        simDiv.innerHTML = simTableHeader + '<div class="alert alert-warning">No similar drugs found.</div>';
    }

    // Explanation
    const explDiv = document.getElementById('target-explanation');
    let explHeader = `<h6>🤔 Why these molecules/targets?</h6>`;
    let explIntro = `<div class="mb-2"><small><strong>Similarity percentages are calculated as the Tanimoto similarity between ECFP4 (Morgan) fingerprints of the query and each molecule. Tanimoto = (number of bits in common) / (number of bits set in either molecule). Molecules are considered similar if they share a target, mechanism, or have high structural similarity. Below, you see the actual SMILES and the reason for each match.</strong></small></div>`;
    if (data.similar_drugs && data.similar_drugs.length) {
        let explHtml = explHeader + explIntro + '<div class="row">';
        data.similar_drugs.forEach((d, i) => {
            // Compose a detailed explanation
            let reason = '';
            if (d.shared_property === 'same mechanism of action') {
                reason = `Matched mechanism: <b>${d.mechanism_of_action || ''}</b>.`;
            } else if (d.shared_property === 'shared target') {
                reason = `Matched target: <b>${d.target || ''}</b>.`;
            } else {
                reason = 'High structural similarity (no shared target or mechanism).';
            }
            explHtml += `
            <div class="col-md-6 mb-3">
                <div class="card shadow flashcard-reason h-100">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-2">
                            <span class="badge bg-info me-2" style="font-size:1.1em;">💡</span>
                            <strong>${d.drug_name || ''}</strong> <span class="ms-2 text-muted" style="font-size:0.9em"><code>${d.SMILES || ''}</code></span>
                        </div>
                        <div><b>Similarity:</b> ${(d.similarity*100).toFixed(1)}%</div>
                        <div><b>Reason:</b> ${reason}</div>
                        <div><b>Justification:</b> ${d.justification ? d.justification : ''}</div>
                    </div>
                </div>
            </div>
            `;
        });
        explHtml += '</div>';
        explDiv.innerHTML = explHtml;
    } else {
        explDiv.innerHTML = explHeader + explIntro + '<div class="alert alert-warning">No explanation available.</div>';
    }

    document.getElementById('target-results').style.display = 'block';
}

function toggleSimilarDrugs() {
    const table = document.getElementById('similar-drugs-table');
    if (table) {
        table.style.display = table.style.display === 'none' ? 'block' : 'none';
    }
}

// Attach event
window.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('predict-target-btn');
    if (btn) btn.onclick = predictTarget;
});
