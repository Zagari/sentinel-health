/**
 * Surgical Video AI - Frontend Application
 * FIAP Tech Challenge - Fase 4
 */

const API_BASE = '/api';

// Elements
const uploadForm = document.getElementById('upload-form');
const urlForm = document.getElementById('url-form');
const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');
const uploadBtn = document.getElementById('upload-btn');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const progressBar = document.getElementById('progress');
const progressText = document.getElementById('progress-text');
const progressStatus = document.getElementById('progress-status');
const samplesList = document.getElementById('samples-list');
const sampleCategory = document.getElementById('sample-category');

// Current job
let currentJobId = null;
let currentGroundTruth = null;

// =====================
// Tab Navigation
// =====================
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab + '-tab').classList.add('active');

        // Load samples when tab is selected
        if (tab.dataset.tab === 'samples') {
            loadSamples();
        }
    });
});

// =====================
// File Upload
// =====================
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        updateDropZone();
    }
});

fileInput.addEventListener('change', updateDropZone);

function updateDropZone() {
    if (fileInput.files.length) {
        const file = fileInput.files[0];
        dropZone.innerHTML = `
            <div class="drop-zone-icon">🎬</div>
            <p><strong>${file.name}</strong></p>
            <p class="small">${(file.size / (1024 * 1024)).toFixed(2)} MB</p>
        `;
        uploadBtn.disabled = false;
    }
}

uploadForm.addEventListener('submit', async e => {
    e.preventDefault();
    currentGroundTruth = null;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        progressStatus.textContent = 'Enviando arquivo...';
        showProgress();

        const response = await fetch(`${API_BASE}/video/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao enviar vídeo');
        }

        const data = await response.json();
        pollStatus(data.job_id);
    } catch (error) {
        alert('Erro: ' + error.message);
        hideProgress();
    }
});

// =====================
// URL Processing
// =====================
urlForm.addEventListener('submit', async e => {
    e.preventDefault();
    currentGroundTruth = null;

    const url = document.getElementById('video-url').value;

    try {
        progressStatus.textContent = 'Baixando vídeo da URL...';
        showProgress();

        const response = await fetch(`${API_BASE}/video/url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao processar URL');
        }

        const data = await response.json();
        pollStatus(data.job_id);
    } catch (error) {
        alert('Erro: ' + error.message);
        hideProgress();
    }
});

// =====================
// Sample Clips
// =====================
async function loadSamples(category = '') {
    samplesList.innerHTML = '<p class="loading">Carregando clips de exemplo...</p>';

    try {
        const url = category
            ? `${API_BASE}/samples/list?category=${category}`
            : `${API_BASE}/samples/list`;

        const response = await fetch(url);
        const samples = await response.json();

        if (samples.length === 0) {
            samplesList.innerHTML = '<p class="loading">Nenhum clip encontrado.</p>';
            return;
        }

        samplesList.innerHTML = samples.map(sample => `
            <div class="sample-card" data-category="${sample.category}" data-filename="${sample.name}">
                <span class="category ${sample.category}">
                    ${sample.category === 'bleeding' ? '🩸 Bleeding' : '✓ Non-bleeding'}
                </span>
                <p class="name">${sample.name.substring(0, 40)}...</p>
                <p class="size">${sample.size_mb} MB</p>
            </div>
        `).join('');

        // Add click handlers
        document.querySelectorAll('.sample-card').forEach(card => {
            card.addEventListener('click', () => {
                processSample(card.dataset.category, card.dataset.filename);
            });
        });

    } catch (error) {
        samplesList.innerHTML = `<p class="loading">Erro ao carregar clips: ${error.message}</p>`;
    }
}

sampleCategory.addEventListener('change', e => {
    loadSamples(e.target.value);
});

async function processSample(category, filename) {
    try {
        progressStatus.textContent = `Processando clip: ${filename}`;
        currentGroundTruth = category;
        showProgress();

        const response = await fetch(`${API_BASE}/samples/process/${category}/${filename}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao processar clip');
        }

        const data = await response.json();
        pollStatus(data.job_id);
    } catch (error) {
        alert('Erro: ' + error.message);
        hideProgress();
    }
}

// =====================
// Status Polling
// =====================
async function pollStatus(jobId) {
    currentJobId = jobId;

    const poll = async () => {
        try {
            const response = await fetch(`${API_BASE}/video/status/${jobId}`);
            const data = await response.json();

            progressBar.style.width = data.progress + '%';
            progressText.textContent = Math.round(data.progress) + '%';

            if (data.status === 'downloading') {
                progressStatus.textContent = 'Baixando vídeo...';
            } else if (data.status === 'processing') {
                progressStatus.textContent = 'Analisando frames com YOLOv8...';
            }

            if (data.status === 'completed') {
                showResults(jobId, data);
            } else if (data.status === 'failed') {
                alert('Erro no processamento: ' + (data.error || 'Erro desconhecido'));
                hideProgress();
            } else {
                setTimeout(poll, 1000);
            }
        } catch (error) {
            alert('Erro ao verificar status: ' + error.message);
            hideProgress();
        }
    };

    poll();
}

// =====================
// Results Display
// =====================
function showResults(jobId, data) {
    hideProgress();
    resultsSection.classList.remove('hidden');

    const summary = data.detections || {};

    // Ground truth banner (for sample clips)
    const banner = document.getElementById('ground-truth-banner');
    if (currentGroundTruth) {
        const hasBloodDetection = summary.detections_by_class?.blood > 0;
        const isCorrect = (currentGroundTruth === 'bleeding' && hasBloodDetection) ||
                         (currentGroundTruth === 'non_bleeding' && !hasBloodDetection);

        banner.classList.remove('hidden', 'success', 'warning');
        banner.classList.add(isCorrect ? 'success' : 'warning');

        document.getElementById('ground-truth-label').textContent =
            `Ground Truth: ${currentGroundTruth === 'bleeding' ? '🩸 Bleeding' : '✓ Non-bleeding'}`;
        document.getElementById('ground-truth-match').textContent =
            isCorrect ? '✅ Modelo acertou!' : '⚠️ Divergência';
    } else {
        banner.classList.add('hidden');
    }

    // Results content
    const content = document.getElementById('results-content');
    content.innerHTML = `
        <div class="results-summary">
            <div class="stat">
                <span class="stat-value">${summary.total_detections || 0}</span>
                <span class="stat-label">Detecções</span>
            </div>
            <div class="stat">
                <span class="stat-value">${summary.duration_seconds || 0}s</span>
                <span class="stat-label">Duração</span>
            </div>
            <div class="stat">
                <span class="stat-value">${summary.total_frames || 0}</span>
                <span class="stat-label">Frames</span>
            </div>
            <div class="stat">
                <span class="stat-value">${summary.blood_detection_rate || 0}%</span>
                <span class="stat-label">Taxa Blood</span>
            </div>
        </div>
        <div class="detections-by-class">
            <h4>Detecções por Classe:</h4>
            <ul>
                ${Object.entries(summary.detections_by_class || {}).map(([cls, count]) =>
                    `<li><strong>${cls}:</strong> ${count} detecções</li>`
                ).join('') || '<li>Nenhuma detecção</li>'}
            </ul>
        </div>
    `;

    // Download links
    document.getElementById('download-video').href = `${API_BASE}/video/result/${jobId}/video`;
    document.getElementById('download-report').href = `${API_BASE}/video/result/${jobId}/report`;
}

// =====================
// Progress Management
// =====================
function showProgress() {
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
}

function hideProgress() {
    progressSection.classList.add('hidden');
}

// New Analysis button
document.getElementById('new-analysis').addEventListener('click', () => {
    resultsSection.classList.add('hidden');
    currentJobId = null;
    currentGroundTruth = null;

    // Reset upload form
    fileInput.value = '';
    dropZone.innerHTML = `
        <div class="drop-zone-icon">📁</div>
        <p>Arraste um vídeo aqui ou clique para selecionar</p>
        <p class="small">Formatos: MP4, AVI, MOV, MKV</p>
    `;
    uploadBtn.disabled = true;

    // Reset URL form
    document.getElementById('video-url').value = '';
});

// =====================
// Info Section
// =====================
async function loadInfo() {
    try {
        // Model info
        const modelRes = await fetch(`${API_BASE}/info/model`);
        const model = await modelRes.json();
        document.getElementById('model-info').innerHTML = `
            <p><strong>Nome:</strong> ${model.name}</p>
            <p><strong>Arquitetura:</strong> ${model.architecture}</p>
            <p><strong>Treino:</strong> ${model.training_dataset}</p>
            <p><strong>Validação:</strong> ${model.validation_dataset}</p>
        `;

        // Dataset info
        const datasetRes = await fetch(`${API_BASE}/info/dataset`);
        const dataset = await datasetRes.json();
        document.getElementById('dataset-info').innerHTML = `
            <p><strong>Treino:</strong> ${dataset.training.name}</p>
            <p>${dataset.training.total_images} imagens</p>
            <p><strong>Validação:</strong> ${dataset.validation.name}</p>
            <p>${dataset.validation.sample_clips.bleeding + dataset.validation.sample_clips.non_bleeding} clips de exemplo</p>
        `;

        // Strategy info
        const strategyRes = await fetch(`${API_BASE}/info/strategy`);
        const strategy = await strategyRes.json();
        document.getElementById('strategy-info').innerHTML = `
            <p><strong>${strategy.title}</strong></p>
            <p>${strategy.description}</p>
            <p class="small" style="margin-top: 10px;">
                <strong>Resultado:</strong> ${strategy.final_metrics.detection_rate} detecção,
                ${strategy.final_metrics.false_positive_rate} falso positivo
            </p>
        `;

        // Classes
        const classesRes = await fetch(`${API_BASE}/info/classes`);
        const classes = await classesRes.json();
        document.getElementById('classes-list').innerHTML = classes.map(c => `
            <span class="class-badge" title="${c.description}">${c.name}</span>
        `).join('');

    } catch (error) {
        console.error('Erro ao carregar informações:', error);
    }
}

// =====================
// Initialize
// =====================
loadInfo();
