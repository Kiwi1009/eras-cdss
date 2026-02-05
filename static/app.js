// ERAS CDSS Frontend Application
// Use current origin so it works when frontend is served from same server (e.g. / or /static/)
const API_BASE_URL = window.location.origin;

// Scenario field configurations
const SCENARIO_FIELDS = {
    PONV: [
        { name: 'female', label: 'Female', type: 'checkbox', required: true },
        { name: 'non_smoker', label: 'Non-smoker', type: 'checkbox', required: true },
        { name: 'hx_ponv', label: 'History of PONV', type: 'checkbox', required: true },
        { name: 'hx_motion_sickness', label: 'History of motion sickness', type: 'checkbox', required: true },
        { name: 'surgery_duration_min', label: 'Surgery duration (min)', type: 'number', required: true, min: 0 }
    ],
    POD: [
        { name: 'nu_desc.disorientation', label: 'Disorientation (0-2)', type: 'number', required: true, min: 0, max: 2 },
        { name: 'nu_desc.inappropriate_behavior', label: 'Inappropriate behavior (0-2)', type: 'number', required: true, min: 0, max: 2 },
        { name: 'nu_desc.inappropriate_communication', label: 'Inappropriate communication (0-2)', type: 'number', required: true, min: 0, max: 2 },
        { name: 'nu_desc.illusions', label: 'Illusions/hallucinations (0-2)', type: 'number', required: true, min: 0, max: 2 },
        { name: 'nu_desc.psychomotor_retardation', label: 'Psychomotor retardation (0-2)', type: 'number', required: true, min: 0, max: 2 },
        { name: 'surgery_duration_min', label: 'Surgery duration (min)', type: 'number', required: true, min: 0 }
    ],
    CHEST_TUBE: [
        { name: 'air_leak_present', label: 'Air leak present', type: 'checkbox', required: true },
        { name: 'drain_output_ml_24h', label: '24h drain output (ml)', type: 'number', required: true, min: 0 },
        { name: 'fluid_quality', label: 'Fluid quality', type: 'select', required: true, options: ['serous', 'serosanguineous', 'bloody', 'other'] },
        { name: 'active_bleeding_suspected', label: 'Active bleeding suspected', type: 'checkbox', required: true },
        { name: 'lung_expanded', label: 'Lung well expanded', type: 'checkbox', required: true },
        { name: 'threshold_ml_24h', label: 'Drain threshold (ml)', type: 'number', required: false, min: 0, value: 450 }
    ]
};

// Store loaded patients for "fill form" action
let loadedPatients = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const scenarioSelect = document.getElementById('scenario-select');
    const form = document.getElementById('evaluation-form');
    
    scenarioSelect.addEventListener('change', updateDynamicFields);
    form.addEventListener('submit', handleSubmit);
    
    checkHealth();
    loadPatients();
});

// Load and display 30 patients
async function loadPatients() {
    const wrap = document.getElementById('patients-table-wrap');
    const loading = document.getElementById('patients-loading');
    const errorEl = document.getElementById('patients-error');
    
    try {
        // Use static JSON to avoid API 404
        const url = `${API_BASE_URL}/static/patients.json`;
        const response = await fetch(url);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || `Failed to load patient data (${response.status})`);
        }
        const patients = Array.isArray(data) ? data : [];
        loadedPatients = patients;
        
        loading.classList.add('hidden');
        errorEl.classList.add('hidden');
        wrap.classList.remove('hidden');
        
        const tbody = document.getElementById('patients-tbody');
        const scenarioLabels = { PONV: 'PONV', POD: 'POD', CHEST_TUBE: 'Chest Tube' };
        
        tbody.innerHTML = patients.map((p, idx) => {
            const scenario = p.scenario || '—';
            const question = (p.question || '').substring(0, 50) + (p.question && p.question.length > 50 ? '…' : '');
            const summary = formatPatientSummary(p.patient_fhir || {}, scenario);
            return `
                <tr class="hover:bg-gray-50 ${idx % 2 ? 'bg-gray-50/50' : ''}">
                    <td class="px-3 py-2 font-medium text-gray-900">${p.patient_id || ('P' + String(idx + 1).padStart(3, '0'))}</td>
                    <td class="px-3 py-2"><span class="scenario-badge scenario-${scenario}">${scenarioLabels[scenario] || scenario}</span></td>
                    <td class="px-3 py-2 text-gray-700 max-w-xs truncate" title="${(p.question || '').replace(/"/g, '&quot;')}">${question}</td>
                    <td class="px-3 py-2 text-gray-600 max-w-xs">${summary}</td>
                    <td class="px-3 py-2 text-center">
                        <button type="button" onclick="fillFormWithPatient(${idx})" class="text-blue-600 hover:text-blue-800 font-medium">Fill Form</button>
                        <span class="mx-1">|</span>
                        <button type="button" onclick="fillAndEvaluate(${idx})" class="text-green-600 hover:text-green-800 font-medium">Fill & Evaluate</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        loading.classList.add('hidden');
        wrap.classList.add('hidden');
        errorEl.classList.remove('hidden');
        errorEl.textContent = err.message || 'Failed to load patient list (ensure backend is running and static/patients.json exists)';
    }
}

function formatPatientSummary(fhir, scenario) {
    const parts = [];
    if (fhir.age != null) parts.push('Age ' + fhir.age);
    if (fhir.gender) parts.push(fhir.gender === 'F' ? 'F' : 'M');
    if (scenario === 'POD' && fhir.nu_desc) {
        const n = fhir.nu_desc;
        const total = (n.disorientation || 0) + (n.inappropriate_behavior || 0) + (n.inappropriate_communication || 0) + (n.illusions || n.illusions_hallucinations || 0) + (n.psychomotor_retardation || 0);
        parts.push('Nu-DESC ' + total);
    }
    if (scenario === 'PONV') {
        if (fhir.female !== undefined) parts.push(fhir.female ? 'F' : 'M');
        if (fhir.non_smoker !== undefined) parts.push(fhir.non_smoker ? 'Non-smoker' : 'Smoker');
    }
    if (scenario === 'CHEST_TUBE' && fhir.drain_output_ml_24h != null) parts.push('Drain ' + fhir.drain_output_ml_24h + 'ml');
    return parts.length ? parts.join(' · ') : '—';
}

function fillFormWithPatient(idx) {
    const p = loadedPatients[idx];
    if (!p) return;
    document.getElementById('scenario-select').value = p.scenario || '';
    document.getElementById('question-input').value = p.question || '';
    updateDynamicFields();
    const fhir = p.patient_fhir || {};
    const scenario = p.scenario;
    // Map legacy keys to form field names (e.g. history_of_ponv -> hx_ponv, gender F/M -> female)
    const mapFhir = { ...fhir };
    if (scenario === 'PONV') {
        if (mapFhir.gender !== undefined) mapFhir.female = mapFhir.gender === 'F';
        if (mapFhir.history_of_ponv !== undefined) mapFhir.hx_ponv = mapFhir.history_of_ponv;
        if (mapFhir.hx_motion_sickness === undefined && mapFhir.motion_sickness !== undefined) mapFhir.hx_motion_sickness = mapFhir.motion_sickness;
    }
    if (scenario === 'CHEST_TUBE') {
        if (mapFhir.air_leak !== undefined && mapFhir.air_leak_present === undefined) mapFhir.air_leak_present = mapFhir.air_leak;
        if (mapFhir.lung_expansion !== undefined && mapFhir.lung_expanded === undefined) mapFhir.lung_expanded = mapFhir.lung_expansion === 'good' || mapFhir.lung_expansion === 'excellent';
    }
    if (!scenario || !SCENARIO_FIELDS[scenario]) return;
    setTimeout(() => {
        SCENARIO_FIELDS[scenario].forEach(field => {
            const el = document.querySelector(`[name="${field.name}"]`);
            if (!el) return;
            if (field.name.includes('.')) {
                const [parent, child] = field.name.split('.');
                const val = mapFhir[parent] && mapFhir[parent][child];
                if (field.type === 'checkbox') el.checked = !!val;
                else if (el.tagName === 'SELECT') el.value = val || '';
                else el.value = val != null ? val : '';
            } else {
                const val = mapFhir[field.name];
                if (field.type === 'checkbox') el.checked = !!val;
                else if (el.tagName === 'SELECT') el.value = val || '';
                else el.value = val != null ? val : (field.value !== undefined ? field.value : '');
            }
        });
    }, 50);
    document.getElementById('evaluation-form').scrollIntoView({ behavior: 'smooth' });
}

async function fillAndEvaluate(idx) {
    fillFormWithPatient(idx);
    const p = loadedPatients[idx];
    if (!p) return;
    showLoading();
    try {
        const response = await fetch(`${API_BASE_URL}/eras/evaluate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scenario: p.scenario || null,
                question: p.question || '',
                top_k: p.top_k || 6,
                patient_fhir: p.patient_fhir || {}
            })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        displayResults(data);
    } catch (err) {
        showError(err.message);
    }
}

window.fillFormWithPatient = fillFormWithPatient;
window.fillAndEvaluate = fillAndEvaluate;

// Check API health
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/healthz`);
        const data = await response.json();
        
        const statusIndicator = document.getElementById('status-indicator');
        if (data.status === 'ok') {
            statusIndicator.innerHTML = `
                <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span class="text-sm text-gray-600">System ready (Build: ${data.rag_current_build_id || 'N/A'})</span>
            `;
        }
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Update dynamic fields based on scenario
function updateDynamicFields() {
    const scenario = document.getElementById('scenario-select').value;
    const container = document.getElementById('dynamic-fields');
    
    container.innerHTML = '';
    
    if (!scenario || !SCENARIO_FIELDS[scenario]) {
        return;
    }
    
    const fields = SCENARIO_FIELDS[scenario];
    
    fields.forEach(field => {
        const fieldDiv = document.createElement('div');
        
        let inputHTML = '';
        
        if (field.type === 'checkbox') {
            inputHTML = `
                <label class="flex items-center space-x-2">
                    <input type="checkbox" name="${field.name}" 
                        class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        ${field.required ? 'required' : ''}>
                    <span class="text-sm text-gray-700">${field.label}</span>
                </label>
            `;
        } else if (field.type === 'select') {
            inputHTML = `
                <select name="${field.name}" 
                    class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    ${field.required ? 'required' : ''}>
                    <option value="">Select...</option>
                    ${field.options.map(opt => `<option value="${opt}">${opt}</option>`).join('')}
                </select>
            `;
        } else {
            inputHTML = `
                <input type="${field.type}" name="${field.name}" 
                    class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    ${field.required ? 'required' : ''}
                    ${field.min !== undefined ? `min="${field.min}"` : ''}
                    ${field.max !== undefined ? `max="${field.max}"` : ''}
                    ${field.value !== undefined ? `value="${field.value}"` : ''}
                    placeholder="${field.label}">
            `;
        }
        
        fieldDiv.innerHTML = `
            <label class="block text-sm font-medium text-gray-700 mb-2">
                ${field.label} ${field.required ? '<span class="text-red-500">*</span>' : ''}
            </label>
            ${inputHTML}
        `;
        
        container.appendChild(fieldDiv);
    });
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const scenario = formData.get('scenario') || null;
    const question = formData.get('question');
    
    // Build patient_fhir object
    const patientFhir = {};
    const scenarioFields = scenario ? SCENARIO_FIELDS[scenario] : [];
    
    scenarioFields.forEach(field => {
        const value = formData.get(field.name);
        if (value !== null) {
            if (field.name.includes('.')) {
                // Nested field (e.g., nu_desc.disorientation)
                const [parent, child] = field.name.split('.');
                if (!patientFhir[parent]) {
                    patientFhir[parent] = {};
                }
                if (field.type === 'checkbox') {
                    patientFhir[parent][child] = value === 'on';
                } else if (field.type === 'number') {
                    patientFhir[parent][child] = parseInt(value) || 0;
                } else {
                    patientFhir[parent][child] = value;
                }
            } else {
                if (field.type === 'checkbox') {
                    patientFhir[field.name] = value === 'on';
                } else if (field.type === 'number') {
                    patientFhir[field.name] = parseInt(value) || 0;
                } else {
                    patientFhir[field.name] = value;
                }
            }
        }
    });
    
    // Show loading state
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/eras/evaluate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                scenario: scenario,
                question: question,
                top_k: 6,
                patient_fhir: patientFhir
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        showError(error.message);
    }
}

// Show loading state
function showLoading() {
    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('error-state').classList.add('hidden');
    document.getElementById('results-container').classList.add('hidden');
    document.getElementById('loading-state').classList.remove('hidden');
}

// Show error state
function showError(message) {
    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('results-container').classList.add('hidden');
    document.getElementById('error-state').classList.remove('hidden');
    document.getElementById('error-message').textContent = message;
}

// Display results
function displayResults(data) {
    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('error-state').classList.add('hidden');
    document.getElementById('results-container').classList.remove('hidden');
    
    // Scenario badge
    const scenario = data.metrics?.scenario || 'UNKNOWN';
    const badge = document.getElementById('scenario-badge');
    const colors = {
        'PONV': 'bg-purple-100 text-purple-800',
        'POD': 'bg-blue-100 text-blue-800',
        'CHEST_TUBE': 'bg-green-100 text-green-800'
    };
    badge.className = `px-3 py-1 rounded-full text-sm font-medium ${colors[scenario] || 'bg-gray-100 text-gray-800'}`;
    badge.textContent = scenario;
    
    // Final recommendation
    document.getElementById('final-recommendation').textContent = data.final_recommendation || 'No recommendation';
    
    // Final actions
    const actionsContainer = document.getElementById('final-actions');
    if (data.final_actions && data.final_actions.length > 0) {
        actionsContainer.innerHTML = data.final_actions.map(action => 
            `<div class="flex items-start space-x-2">
                <i class="fas fa-check text-green-600 mt-1"></i>
                <span class="text-gray-700">${action}</span>
            </div>`
        ).join('');
    } else {
        actionsContainer.innerHTML = '<p class="text-gray-500">No suggested actions</p>';
    }
    
    // Key reasons
    const reasonsList = document.getElementById('key-reasons');
    if (data.key_reasons && data.key_reasons.length > 0) {
        reasonsList.innerHTML = data.key_reasons.map(reason => 
            `<li class="text-gray-700">${reason}</li>`
        ).join('');
    } else {
        reasonsList.innerHTML = '<li class="text-gray-500">None</li>';
    }
    
    // Risks and notes
    const risksList = document.getElementById('risks-notes');
    if (data.risks_and_notes && data.risks_and_notes.length > 0) {
        risksList.innerHTML = data.risks_and_notes.map(risk => 
            `<li class="text-gray-700">${risk}</li>`
        ).join('');
    } else {
        risksList.innerHTML = '<li class="text-gray-500">None</li>';
    }
    
    // Citations
    const citationsList = document.getElementById('citations-list');
    const citationCount = document.getElementById('citation-count');
    if (data.citations && data.citations.length > 0) {
        citationCount.textContent = data.citations.length;
        citationsList.innerHTML = data.citations.map((cit, idx) => `
            <div class="citation-card bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div class="flex items-start justify-between mb-2">
                    <div class="flex-1">
                        <span class="text-sm font-medium text-gray-900">Citation ${idx + 1}</span>
                        <span class="text-xs text-gray-500 ml-2">${cit.source}</span>
                    </div>
                    <button onclick="toggleCitation(${idx})" class="text-blue-600 hover:text-blue-800 text-sm">
                        <i class="fas fa-chevron-down" id="citation-icon-${idx}"></i>
                    </button>
                </div>
                <div id="citation-text-${idx}" class="hidden text-sm text-gray-700 mt-2 p-3 bg-white rounded border border-gray-200">
                    ${cit.text}
                </div>
            </div>
        `).join('');
    } else {
        citationCount.textContent = '0';
        citationsList.innerHTML = '<p class="text-gray-500">No citations</p>';
    }
    
    // Agent decisions
    const agentsList = document.getElementById('agents-list');
    if (data.agents && data.agents.length > 0) {
        agentsList.innerHTML = data.agents.map((agent, idx) => {
            const agentName = agent.name || agent.agent_role || `Agent ${idx + 1}`;
            const decision = agent.decision || {};
            return `
                <div class="border border-gray-200 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="font-semibold text-gray-900">${agentName}</h4>
                        ${agent.error ? '<span class="text-xs text-red-600">Error</span>' : '<span class="text-xs text-green-600">OK</span>'}
                    </div>
                    <div class="text-sm text-gray-700">
                        <p class="mb-2"><strong>Recommendation:</strong> ${decision.recommendation || 'None'}</p>
                        ${decision.actions && decision.actions.length > 0 ? 
                            `<p class="mb-2"><strong>Actions:</strong> ${decision.actions.join(', ')}</p>` : ''}
                        ${agent.error ? `<p class="text-red-600 text-xs mt-2">Error: ${agent.error}</p>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } else {
        agentsList.innerHTML = '<p class="text-gray-500">No agent decision data</p>';
    }
    
    // Metrics
    const metricsDisplay = document.getElementById('metrics-display');
    if (data.metrics) {
        const metrics = [
            { label: 'Latency', value: `${data.metrics.latency_ms || 0} ms`, icon: 'clock' },
            { label: 'Trace ID', value: data.metrics.trace_id || 'N/A', icon: 'fingerprint' },
            { label: 'Backend', value: data.metrics.backend || 'N/A', icon: 'server' },
            { label: 'Citations', value: data.metrics.citations_count || 0, icon: 'book' }
        ];
        metricsDisplay.innerHTML = metrics.map(metric => `
            <div class="bg-gray-50 rounded-lg p-4">
                <div class="flex items-center space-x-2 mb-1">
                    <i class="fas fa-${metric.icon} text-blue-600"></i>
                    <span class="text-sm font-medium text-gray-700">${metric.label}</span>
                </div>
                <p class="text-lg font-semibold text-gray-900">${metric.value}</p>
            </div>
        `).join('');
    }
}

// Toggle citation text
function toggleCitation(idx) {
    const textDiv = document.getElementById(`citation-text-${idx}`);
    const icon = document.getElementById(`citation-icon-${idx}`);
    
    if (textDiv.classList.contains('hidden')) {
        textDiv.classList.remove('hidden');
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        textDiv.classList.add('hidden');
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}

// Make toggleCitation available globally
window.toggleCitation = toggleCitation;
