// Global variables
let currentMolecule = null;
let drugList = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function () {
    loadDrugList();
    initializeViewers();
});

// Load the list of available drugs
async function loadDrugList() {
    try {
        const response = await fetch('/api/drugs');
        drugList = await response.json();

        // Populate dropdowns
        const drugSelect = document.getElementById('drug-select');
        const drug1Select = document.getElementById('drug1-select');
        const drug2Select = document.getElementById('drug2-select');
        const compareDrug1Select = document.getElementById('compare-drug1-select');
        const compareDrug2Select = document.getElementById('compare-drug2-select');

        drugList.forEach(drug => {
            const option = new Option(drug, drug);
            if (drugSelect) drugSelect.add(option.cloneNode(true));
            if (drug1Select) drug1Select.add(option.cloneNode(true));
            if (drug2Select) drug2Select.add(option.cloneNode(true));
            if (compareDrug1Select) compareDrug1Select.add(option.cloneNode(true));
            if (compareDrug2Select) compareDrug2Select.add(option.cloneNode(true));
        });
    } catch (error) {
        console.error('Error loading drug list:', error);
        showError('Failed to load drug list');
    }
}

// Initialize 3D molecule viewers
function initializeViewers() {
    // Initialize main viewer
    const viewer = $3Dmol.createViewer('molecule-viewer', {
        backgroundColor: 'white'
    });

    // Initialize comparison viewers
    const viewer1 = $3Dmol.createViewer('molecule-viewer1', {
        backgroundColor: 'white'
    });

    const viewer2 = $3Dmol.createViewer('molecule-viewer2', {
        backgroundColor: 'white'
    });

    // Store viewers globally
    window.mainViewer = viewer;
    window.viewer1 = viewer1;
    window.viewer2 = viewer2;
}

// Load molecule for visualization
async function loadMolecule() {
    const drugSelect = document.getElementById('drug-select');
    const drugSearch = document.getElementById('drug-search');

    let drugName = drugSelect ? drugSelect.value : '';

    // If no drug selected from dropdown, try search input
    if (!drugName && drugSearch) {
        drugName = drugSearch.value.trim();
    }

    if (!drugName) {
        showError('Please select a drug or enter a drug name/SMILES');
        return;
    }

    showLoading(true);

    try {
        // Always use search endpoint for better compatibility
        const response = await fetch(`/api/search_drug?query=${encodeURIComponent(drugName)}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const drugData = await response.json();

        if (drugData.error) {
            showError(drugData.error);
            showLoading(false);
            return;
        }

        if (!drugData.drug_name) {
            showError('Drug not found. Please check the name or SMILES.');
            showLoading(false);
            return;
        }

        if (!drugData.SMILES) {
            showError('No molecular structure available for this drug.');
            showLoading(false);
            return;
        }

        // Get MOL block from backend
        const molRes = await fetch('/api/molblock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ smiles: drugData.SMILES })
        });

        if (!molRes.ok) {
            throw new Error(`HTTP error! status: ${molRes.status}`);
        }

        const molData = await molRes.json();

        if (molData.error) {
            showError(molData.error);
            showLoading(false);
            return;
        }

        if (!molData.molblock) {
            showError('Could not generate molecule structure.');
            showLoading(false);
            return;
        }

        // Render molecule
        renderMolecule(window.mainViewer, molData.molblock, drugData.drug_name);

        // Set name below image
        const nameElement = document.getElementById('main-molecule-name');
        if (nameElement) {
            nameElement.textContent = drugData.drug_name || '';
        }

        // Show save button and reset state
        const saveBtn = document.getElementById('save-drug-btn');
        if (saveBtn) {
            saveBtn.classList.remove('d-none');
            saveBtn.innerHTML = '<i class="bi bi-heart"></i>';
            saveBtn.classList.remove('btn-danger');
            saveBtn.classList.add('btn-outline-danger');
            saveBtn.disabled = false;
        }

        // Display properties
        displayProperties(drugData, 'properties-content');
        const propsCard = document.getElementById('properties-card');
        if (propsCard) {
            propsCard.style.display = 'block';
        }

        currentMolecule = drugData;

    } catch (error) {
        console.error('Error loading molecule:', error);
        showError('Failed to load molecule data: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Compare two drugs with improved side-by-side display
async function compareDrugs() {
    // Get drug names from either dropdown or text input
    let drug1Name = document.getElementById('drug1-select').value;
    let drug2Name = document.getElementById('drug2-select').value;

    // If no dropdown selection, try text input
    const drug1Input = document.getElementById('drug1-input');
    const drug2Input = document.getElementById('drug2-input');

    if (!drug1Name && drug1Input) {
        drug1Name = drug1Input.value.trim();
    }
    if (!drug2Name && drug2Input) {
        drug2Name = drug2Input.value.trim();
    }

    if (!drug1Name || !drug2Name) {
        showError('Please select or enter both drugs for comparison');
        return;
    }
    if (drug1Name.toLowerCase() === drug2Name.toLowerCase()) {
        showError('Please select two different drugs for comparison');
        return;
    }
    showLoading(true);
    try {
        // Fetch both drugs' info and summary in one call
        const response = await fetch(`/api/compare_drugs?drug1=${encodeURIComponent(drug1Name)}&drug2=${encodeURIComponent(drug2Name)}`);
        const data = await response.json();
        if (data.error || !data.drug1 || !data.drug2) {
            showError(data.error || 'Failed to fetch drug comparison data.');
            showLoading(false);
            return;
        }
        // Fetch molblocks for both drugs using their SMILES from compare_drugs
        const [mol1, mol2] = await Promise.all([
            fetch('/api/molblock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ smiles: data.drug1.SMILES })
            }).then(res => res.json()),
            fetch('/api/molblock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ smiles: data.drug2.SMILES })
            }).then(res => res.json())
        ]);
        if (mol1.error || mol2.error || !mol1.molblock || !mol2.molblock) {
            showError(mol1.error || mol2.error || 'Could not generate 3D structure for one or both drugs.');
            showLoading(false);
            return;
        }
        // Render molecules
        renderMolecule(window.viewer1, mol1.molblock, data.drug1.drug_name);
        document.getElementById('drug1-name-below').textContent = data.drug1.drug_name || '';
        renderMolecule(window.viewer2, mol2.molblock, data.drug2.drug_name);
        document.getElementById('drug2-name-below').textContent = data.drug2.drug_name || '';

        // Display Interaction Alerts
        const alertBox = document.getElementById('interaction-alert');
        const alertList = document.getElementById('interaction-list');
        if (data.interactions && data.interactions.length > 0) {
            alertList.innerHTML = data.interactions.map(i => `<li>${i}</li>`).join('');
            alertBox.style.display = 'block';
        } else {
            alertBox.style.display = 'none';
        }

        // Render Analytics Chart
        renderComparisonChart(data.drug1, data.drug2);

        // Display toxicity alerts
        displayToxicityAlert(data.drug1, 'drug1-toxicity');
        displayToxicityAlert(data.drug2, 'drug2-toxicity');

        // Display side-by-side properties comparison
        displaySideBySideComparison(data.drug1, data.drug2);

        // Show names
        document.getElementById('drug1-name').textContent = data.drug1.drug_name;
        document.getElementById('drug2-name').textContent = data.drug2.drug_name;

        // Show summary
        displayComparisonSummary(data.comparison_summary || 'No comparison summary available.', data.comparison_summary_points);
        document.getElementById('comparison-results').style.display = 'block';
    } catch (error) {
        console.error('Error comparing drugs:', error);
        showError('Failed to compare drugs');
    } finally {
        showLoading(false);
    }
}

// Render molecule in 3D viewer (now takes MOL block)
// Render molecule in 3D viewer (now takes MOL block)
function renderMolecule(viewer, molblock, drugName) {
    if (!viewer) return;

    try {
        // Aggressive cleanup to ensure no artifacts remain
        viewer.clear();
        if (viewer.removeAllModels) viewer.removeAllModels();
        if (viewer.removeAllShapes) viewer.removeAllShapes();
        if (viewer.removeAllSurfaces) viewer.removeAllSurfaces();

        // Add new model
        viewer.addModel(molblock, "sdf");
        viewer.setStyle({}, { stick: { colorscheme: 'default' } });

        // Add surface (try/catch in case of WebGL issues)
        try {
            viewer.addSurface($3Dmol.SurfaceType.VDW, { opacity: 0.1, color: 'lightgray' });
        } catch (surfaceErr) {
            console.warn("Could not add surface:", surfaceErr);
        }

        // Center and zoom properly
        viewer.zoomTo();
        viewer.zoom(0.8); // Zoom out slightly to ensure molecule fits
        viewer.center();
        viewer.render();

        // Ensure the viewer fits the frame with a slight delay for layout catch-up
        setTimeout(() => {
            if (viewer.resize) viewer.resize();
            viewer.render();
        }, 50);
    } catch (e) {
        console.error('Error rendering molecule:', e);
    }
}

// Display molecular properties, highlight differences if comparatorDrug provided
function displayProperties(drugData, containerId, comparatorDrug = null) {
    const container = document.getElementById(containerId);
    // Compose properties, including solubility
    const properties = [
        { label: 'Drug ID', value: drugData.drug_id, icon: 'bi-hash', key: 'drug_id' },
        { label: 'LogP', value: formatNumber(drugData.logP), icon: 'bi-droplet', key: 'logP' },
        { label: 'LogD', value: formatNumber(drugData.logD), icon: 'bi-droplet-fill', key: 'logD' },
        { label: 'PSA', value: formatNumber(drugData.psa), icon: 'bi-bounding-box', key: 'psa' },
        { label: 'Solubility', value: drugData.solubility, icon: 'bi-water', key: 'solubility' },
        { label: 'Toxicity', value: drugData.toxicity_alert, icon: 'bi-exclamation-triangle', key: 'toxicity_alert' },
        { label: 'IC50', value: formatNumber(drugData.IC50), icon: 'bi-activity', key: 'IC50' },
        { label: 'pIC50', value: formatNumber(drugData.pIC50), icon: 'bi-activity', key: 'pIC50' },
        { label: 'Target', value: drugData.target, icon: 'bi-bullseye', key: 'target' },
        { label: 'Organism', value: drugData.organism, icon: 'bi-bug', key: 'organism' },
        { label: 'Target Type', value: drugData.target_type, icon: 'bi-diagram-3', key: 'target_type' },
        { label: 'Mechanism', value: drugData.mechanism_of_action, icon: 'bi-gear', key: 'mechanism_of_action' },
        { label: 'Drug-likeness', value: drugData.drug_likeness, icon: 'bi-check-circle', key: 'drug_likeness' },
        { label: 'Max Phase', value: drugData.max_phase, icon: 'bi-flag', key: 'max_phase' },
        { label: 'EFO Term', value: drugData.efo_term, icon: 'bi-journal', key: 'efo_term' },
        { label: 'MeSH Heading', value: drugData.mesh_heading, icon: 'bi-journal-text', key: 'mesh_heading' },
    ];
    let html = '<div class="d-grid gap-3" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));">';
    properties.forEach(prop => {
        if (prop.value !== undefined && prop.value !== null && prop.value !== '' && prop.value !== 'N/A') {
            let className = 'property-card';
            if (comparatorDrug) {
                if (String(prop.value) !== String(comparatorDrug[prop.key])) {
                    className += ' bg-danger-subtle text-danger fw-bold';
                } else {
                    className += ' bg-success-subtle text-success';
                }
            }
            html += `
                <div class="${className}">
                    <div class="property-label">
                        <i class="${prop.icon} me-2"></i>
                        ${prop.label}
                    </div>
                    <div class="property-value">${prop.value}</div>
                </div>
            `;
        }
    });
    html += '</div>';
    container.innerHTML = html;
}

// Display toxicity alert with red styling
function displayToxicityAlert(drugData, containerId) {
    const container = document.getElementById(containerId);
    const toxicity = drugData.toxicity_alert;

    if (toxicity && toxicity !== 'N/A' && toxicity !== '') {
        container.innerHTML = `
            <div class="toxicity-alert">
                <i class="bi bi-exclamation-triangle-fill"></i>
                <strong>TOXICITY ALERT:</strong> ${toxicity}
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="no-toxicity">
                <i class="bi bi-check-circle-fill"></i>
                No toxicity alerts detected
            </div>
        `;
    }
}

// Display side-by-side properties comparison
function displaySideBySideComparison(drug1, drug2) {
    const container = document.getElementById('side-by-side-properties');

    const properties = [
        { key: 'drug_id', label: 'Drug ID', icon: 'bi-hash' },
        { key: 'logP', label: 'LogP', icon: 'bi-droplet' },
        { key: 'logD', label: 'LogD', icon: 'bi-droplet-fill' },
        { key: 'psa', label: 'PSA', icon: 'bi-bounding-box' },
        { key: 'solubility', label: 'Solubility', icon: 'bi-water' },
        { key: 'drug_likeness', label: 'Drug-likeness', icon: 'bi-check-circle' },
        { key: 'max_phase', label: 'Max Phase', icon: 'bi-flag' },
        { key: 'IC50', label: 'IC50', icon: 'bi-activity' },
        { key: 'pIC50', label: 'pIC50', icon: 'bi-activity' },
        { key: 'target', label: 'Target', icon: 'bi-bullseye' },
        { key: 'organism', label: 'Organism', icon: 'bi-bug' },
        { key: 'target_type', label: 'Target Type', icon: 'bi-diagram-3' },
        { key: 'mechanism_of_action', label: 'Mechanism', icon: 'bi-gear' },
        { key: 'efo_term', label: 'EFO Term', icon: 'bi-journal' },
        { key: 'mesh_heading', label: 'MeSH Heading', icon: 'bi-journal-text' }
    ];

    let html = '<div class="side-by-side-comparison">';

    // Add header row
    html += `
        <div class="comparison-row" style="background: linear-gradient(135deg, var(--secondary-color), var(--primary-color)); color: white; font-weight: 700;">
            <div class="comparison-label" style="background: transparent; color: white; border: none;">
                <i class="bi bi-capsule me-2"></i>${drug1.drug_name}
            </div>
            <div class="comparison-label" style="background: transparent; color: white; border: none;">
                <i class="bi bi-capsule me-2"></i>${drug2.drug_name}
            </div>
        </div>
    `;

    properties.forEach(prop => {
        const value1 = drug1[prop.key];
        const value2 = drug2[prop.key];

        if (value1 !== undefined && value1 !== null && value1 !== '' && value1 !== 'N/A' ||
            value2 !== undefined && value2 !== null && value2 !== '' && value2 !== 'N/A') {

            const formattedValue1 = formatNumber(value1);
            const formattedValue2 = formatNumber(value2);

            let value1Class = 'comparison-value';
            let value2Class = 'comparison-value';

            // Highlight differences
            if (formattedValue1 !== formattedValue2 && formattedValue1 !== 'N/A' && formattedValue2 !== 'N/A') {
                value1Class += ' bg-warning-subtle';
                value2Class += ' bg-warning-subtle';
            } else if (formattedValue1 === formattedValue2 && formattedValue1 !== 'N/A') {
                value1Class += ' bg-success-subtle';
                value2Class += ' bg-success-subtle';
            }

            html += `
                <div class="comparison-row">
                    <div class="comparison-label">
                        <i class="${prop.icon} me-2"></i>${prop.label}
                    </div>
                    <div class="${value1Class}">${formattedValue1}</div>
                    <div class="${value2Class}">${formattedValue2}</div>
                </div>
            `;
        }
    });

    html += '</div>';
    if (container) {
        container.innerHTML = html;
    } else {
        console.warn('Element #side-by-side-properties not found on page');
    }
}

// Display comparison summary
function displayComparisonSummary(summary, summaryPoints) {
    const container = document.getElementById('comparison-summary');
    if (Array.isArray(summaryPoints) && summaryPoints.length > 0) {
        container.innerHTML = `
            <h5><i class="bi bi-clipboard-data me-2"></i>Comparison Summary</h5>
            <ul style="margin-bottom:0; padding-left:1.5em;">
                ${summaryPoints.map(point => `<li style='margin-bottom: 0.5em;'>${point}</li>`).join('')}
            </ul>
        `;
    } else {
        container.innerHTML = `
            <h5><i class="bi bi-clipboard-data me-2"></i>Comparison Summary</h5>
            <p class="mb-0">${summary}</p>
        `;
    }
}

// Format numbers for display
function formatNumber(value) {
    if (value === null || value === undefined || value === 'nan' || value === 'None') {
        return 'N/A';
    }

    const num = parseFloat(value);
    if (isNaN(num)) {
        return value;
    }

    return num.toFixed(3);
}

// Show/hide loading spinner
function showLoading(show) {
    const spinner = document.getElementById('loading-spinner');
    spinner.style.display = show ? 'block' : 'none';
}

// Show error message
function showError(message) {
    // Remove existing error messages
    const existingErrors = document.querySelectorAll('.error-message, .alert-danger');
    existingErrors.forEach(error => error.remove());
    // Create Bootstrap 5 alert
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger error-message';
    errorDiv.role = 'alert';
    errorDiv.innerHTML = `
        <i class="bi bi-exclamation-triangle me-2"></i>
        ${message}
    `;
    // Insert error message after the main container
    const mainContainer = document.querySelector('.main-container');
    mainContainer.parentNode.insertBefore(errorDiv, mainContainer.nextSibling);
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

// Add event listeners for search functionality
document.addEventListener('DOMContentLoaded', function () {
    const drugSearch = document.getElementById('drug-search');

    // Auto-search on Enter key
    if (drugSearch) {
        drugSearch.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                loadMolecule();
            }
        });
    }

    // Auto-search on dropdown change
    const drugSelect = document.getElementById('drug-select');
    if (drugSelect) {
        drugSelect.addEventListener('change', function () {
            if (this.value) {
                loadMolecule();
            }
        });
    }

    // Drug comparison - clear text input when dropdown is selected
    const drug1Select = document.getElementById('drug1-select');
    const drug1Input = document.getElementById('drug1-input');
    const drug2Select = document.getElementById('drug2-select');
    const drug2Input = document.getElementById('drug2-input');

    if (drug1Select && drug1Input) {
        drug1Select.addEventListener('change', function () {
            if (this.value) drug1Input.value = '';
        });
        drug1Input.addEventListener('input', function () {
            if (this.value.trim()) drug1Select.value = '';
        });
        drug1Input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') compareDrugs();
        });
    }

    if (drug2Select && drug2Input) {
        drug2Select.addEventListener('change', function () {
            if (this.value) drug2Input.value = '';
        });
        drug2Input.addEventListener('input', function () {
            if (this.value.trim()) drug2Select.value = '';
        });
        drug2Input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') compareDrugs();
        });
    }
});

/* =========================================
   Library / Bookmarks Functions
   ========================================= */

window.saveInternalDrug = async function () {
    if (!currentMolecule) {
        alert("No molecule loaded to save.");
        return;
    }

    const saveBtn = document.getElementById('save-drug-btn');
    if (saveBtn) {
        saveBtn.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
        saveBtn.disabled = true;
    }

    // Prepare data
    const payload = {
        drug_name: currentMolecule.drug_name || document.getElementById('main-molecule-name').textContent,
        drug_id: currentMolecule.drug_id,
        smiles: currentMolecule.SMILES,
        category: 'General'
    };

    try {
        const response = await fetch('/api/library/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            // Update button to filled heart
            if (saveBtn) {
                saveBtn.innerHTML = '<i class="bi bi-heart-fill"></i>';
                saveBtn.classList.remove('btn-outline-danger');
                saveBtn.classList.add('btn-danger');
                saveBtn.title = "Saved to Library";
            }
        } else {
            alert("Error saving: " + data.message);
            if (saveBtn) {
                saveBtn.innerHTML = '<i class="bi bi-heart"></i>';
                saveBtn.disabled = false;
            }
        }
    } catch (err) {
        console.error("Save error:", err);
        alert("Failed to save drug.");
        if (saveBtn) {
            saveBtn.innerHTML = '<i class="bi bi-heart"></i>';
            saveBtn.disabled = false;
        }
    }
};

window.openLibraryModal = async function () {
    const modal = new bootstrap.Modal(document.getElementById('libraryModal'));
    modal.show();

    const listDiv = document.getElementById('libraryList');
    const loading = document.getElementById('libraryLoading');
    const empty = document.getElementById('libraryEmpty');

    listDiv.innerHTML = '';
    loading.classList.remove('d-none');
    empty.classList.add('d-none');

    try {
        const response = await fetch('/api/library');
        const data = await response.json();

        loading.classList.add('d-none');

        if (data.success && data.drugs.length > 0) {
            renderLibrary(data.drugs);
        } else {
            empty.classList.remove('d-none');
        }
    } catch (err) {
        loading.classList.add('d-none');
        listDiv.innerHTML = '<div class="alert alert-danger">Failed to load library.</div>';
    }
};

function renderLibrary(drugs) {
    const listDiv = document.getElementById('libraryList');

    let html = '';
    drugs.forEach(drug => {
        html += `
        <div class="col-md-6 col-lg-4">
            <div class="card h-100 shadow-sm border-0">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="card-title fw-bold text-primary mb-0 text-truncate" title="${drug.drug_name}">${drug.drug_name}</h6>
                        <button class="btn btn-link text-danger p-0 ms-2" onclick="removeFromLibrary(${drug.id}, this)">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                    <p class="small text-muted mb-2">Saved: ${new Date(drug.saved_at).toLocaleDateString()}</p>
                    
                    <div class="d-grid gap-2">
                        <button class="btn btn-sm btn-outline-primary" onclick="loadFromLibrary('${drug.drug_name}')">
                            <i class="bi bi-eye me-1"></i>View
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;
    });

    listDiv.innerHTML = html;
}

window.removeFromLibrary = async function (id, btn) {
    if (!confirm("Remove this drug from library?")) return;

    const card = btn.closest('.col-md-6, .col-lg-4');
    card.style.opacity = '0.5';

    try {
        const response = await fetch(`/api/library/remove/${id}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.success) {
            card.remove();
            // Check if empty
            if (document.getElementById('libraryList').children.length === 0) {
                document.getElementById('libraryEmpty').classList.remove('d-none');
            }
        } else {
            alert("Error removing: " + (data.error || data.message));
            card.style.opacity = '1';
        }
    } catch (err) {
        alert("Failed to remove drug.");
        card.style.opacity = '1';
    }
};

window.loadFromLibrary = function (drugName) {
    // Close modal
    const modalEl = document.getElementById('libraryModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();

    const searchInput = document.getElementById('drug-search');
    if (searchInput) {
        searchInput.value = drugName;
        // Trigger search logic
        // We can call the same logic as the search button
        // Assuming loadMolecule() reads from the input
        loadMolecule(); // defined in global scope or via window

        // Scroll to viewer
        const viewer = document.getElementById('molecule-viewer');
        if (viewer) viewer.scrollIntoView({ behavior: 'smooth' });
    }
};

/* =========================================
   Analytics / Charts
   ========================================= */

function renderComparisonChart(d1, d2) {
    console.log('[Chart] renderComparisonChart called with:', { d1_name: d1?.drug_name, d2_name: d2?.drug_name });
    const canvas = document.getElementById('comparison-chart');
    console.log('[Chart] Canvas element:', canvas);
    if (!canvas) {
        console.error('[Chart] ERROR: comparison-chart canvas not found!');
        return;
    }
    const ctx = canvas.getContext('2d');

    // Destroy previous chart if exists
    if (window.comparisonChartInstance) {
        window.comparisonChartInstance.destroy();
    }

    // safe parsing
    const safeVal = (v) => parseFloat(v) || 0;

    // Normalize properties for Radar Chart
    // 1. LogP (Target < 5)
    // 2. PSA (Target < 140)
    // 3. MW (Target < 500)
    // 4. QED / Drug-likeness (Approximate)

    // Normalize to 0-100 scale where 100 is the "Limit" or Max
    const normLogP = (val) => Math.min((safeVal(val) / 5) * 100, 150);
    const normPSA = (val) => Math.min((safeVal(val) / 140) * 100, 150);
    const normMW = (val) => Math.min((safeVal(val) / 500) * 100, 150);

    const d1Data = [
        normLogP(d1.logP),
        normPSA(d1.psa),
        normMW(d1.molecular_weight),
        // Dummy 4th axis to make it a shape
        Math.min((safeVal(d1.logP || 2) * safeVal(d1.molecular_weight || 300) / 1500) * 100, 100)
    ];

    const d2Data = [
        normLogP(d2.logP),
        normPSA(d2.psa),
        normMW(d2.molecular_weight),
        Math.min((safeVal(d2.logP || 2) * safeVal(d2.molecular_weight || 300) / 1500) * 100, 100)
    ];

    const labels = [
        'Lipophilicity (LogP)',
        'Polar Surface Area',
        'Molecular Weight',
        'Complexity Score'
    ];

    window.comparisonChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: d1.drug_name || 'Drug 1',
                data: d1Data,
                fill: true,
                backgroundColor: 'rgba(0, 150, 136, 0.2)',
                borderColor: 'rgba(0, 150, 136, 1)',
                pointBackgroundColor: 'rgba(0, 150, 136, 1)',
                borderWidth: 2
            }, {
                label: d2.drug_name || 'Drug 2',
                data: d2Data,
                fill: true,
                backgroundColor: 'rgba(233, 30, 99, 0.2)',
                borderColor: 'rgba(233, 30, 99, 1)',
                pointBackgroundColor: 'rgba(233, 30, 99, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: '#eee' },
                    grid: { color: '#eee' },
                    suggestedMin: 0,
                    suggestedMax: 120,
                    ticks: { display: false } // Hide numbers
                }
            },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            // Show raw value in tooltip? Hard map back.
                            return context.dataset.label + ': ' + Math.round(context.raw) + '% of Limit';
                        }
                    }
                }
            }
        }
    });
    console.log('[Chart] Radar chart successfully rendered!');
}

// Function to compare drugs from the Comparator tab
function compareDrugsFromTab() {
    // Get drug names from selects or search inputs
    const drug1Select = document.getElementById('compare-drug1-select').value;
    const drug1Search = document.getElementById('compare-drug1-search').value.trim();
    const drug2Select = document.getElementById('compare-drug2-select').value;
    const drug2Search = document.getElementById('compare-drug2-search').value.trim();

    const drug1 = drug1Select || drug1Search;
    const drug2 = drug2Select || drug2Search;

    if (!drug1 || !drug2) {
        alert('Please select or enter both drugs to compare');
        return;
    }

    // Call the existing compareDrugs function
    compareDrugs(drug1, drug2);
}