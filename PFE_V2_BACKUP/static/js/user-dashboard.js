// user-dashboard.js - Version complète avec segmentation et classification

document.addEventListener('DOMContentLoaded', () => {
    initializeEventHandlers();
    resetImageDisplays();
    loadProcessingView('segmentation');
});

function t(key, fallback) {
    return (window.I18N && Object.prototype.hasOwnProperty.call(window.I18N, key))
        ? window.I18N[key]
        : fallback;
}

// Fonction pour formater les nombres en toute sécurité
function safeToFixed(value, decimals) {
    if (typeof value === 'undefined' || value === null) {
        return '0.0';
    }
    const num = typeof value === 'string' ? parseFloat(value.replace('%', '')) : value;
    return isNaN(num) ? '0.0' : num.toFixed(decimals);
}

function initializeEventHandlers() {
    // Gestion du téléchargement d'image
    const dropZone = document.getElementById('dropZone');
    const imageInput = document.getElementById('imageInput');

    dropZone.addEventListener('click', () => imageInput.click());
    const gtInput = document.getElementById('gtInput');
    imageInput.addEventListener('change', handleFileSelect);

    // Gestion du click pour la vérité terrain
    const gtDropZone = document.getElementById('gtDropZone');
    if (gtDropZone) {
        gtDropZone.addEventListener('click', () => gtInput.click());
    }

    // Gestion drag and drop
    ['dragover', 'dragleave', 'drop'].forEach(event => {
        dropZone.addEventListener(event, preventDefaults);
        if (gtDropZone) gtDropZone.addEventListener(event, preventDefaults);
    });

    dropZone.addEventListener('dragover', () => highlightDropZone(dropZone));
    dropZone.addEventListener('dragleave', () => unhighlightDropZone(dropZone));
    dropZone.addEventListener('drop', handleDrop);

    if (gtDropZone) {
        gtDropZone.addEventListener('dragover', () => highlightDropZone(gtDropZone));
        gtDropZone.addEventListener('dragleave', () => unhighlightDropZone(gtDropZone));
        gtDropZone.addEventListener('drop', handleGtDrop);
    }

    if (gtInput) {
        gtInput.addEventListener('change', handleGtSelect);
    }

    // Bouton de traitement
    document.getElementById('processBtn').addEventListener('click', processImage);

    // Gestion des boutons de navigation
    document.querySelectorAll('.sidebar-btn').forEach(btn => {
        btn.addEventListener('click', switchProcessType);
    });

    // Upload de modèle personnalisé
    document.getElementById('uploadModelBtn').addEventListener('click', () => {
        document.getElementById('modelUpload').click();
    });

    document.getElementById('modelUpload').addEventListener('change', handleModelUpload);

    const toggleGtBtn = document.getElementById('toggleGtBtn');
    if (toggleGtBtn) {
        toggleGtBtn.addEventListener('click', toggleGtUpload);
    }

    // Gestionnaire pour le bouton de téléchargement du rapport
    const downloadBtn = document.getElementById('downloadReportBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadReport);
    }

    // PDF download for classification report
    const downloadResultsBtn = document.getElementById('downloadResultsBtn');
    if (downloadResultsBtn) {
        downloadResultsBtn.addEventListener('click', async function () {
            const report = document.getElementById('reportContent').textContent;
            const imageUrl = document.getElementById('originalResult').src;

            let relativeImageUrl = imageUrl;
            if (imageUrl.startsWith(window.location.origin)) {
                relativeImageUrl = imageUrl.replace(window.location.origin, '');
            }

            const response = await fetch('/download-classification-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    report: report,
                    image_url: relativeImageUrl
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'rapport_classification.pdf';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                alert(t('download_pdf_error', 'Erreur lors du téléchargement du PDF'));
            }
        });
    }
}

function toggleGtUpload() {
    const gtSection = document.getElementById('gtUploadSection');
    if (!gtSection) return;

    gtSection.classList.toggle('hidden');

    const btn = document.getElementById('toggleGtBtn');
    if (!btn) return;

    if (gtSection.classList.contains('hidden')) {
        btn.textContent = t('upload_gt_image', '📤 Uploader une image vérité terrain');
    } else {
        btn.textContent = t('hide_gt_image', '✖️ Masquer la vérité terrain');
    }
}

function handleGtDrop(e) {
    preventDefaults(e);
    unhighlightDropZone(document.getElementById('gtDropZone'));

    const dt = e.dataTransfer;
    const files = dt.files;
    document.getElementById('gtInput').files = files;
    handleGtSelect({ target: { files } });
}

function handleGtSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    const gtDropZone = document.getElementById('gtDropZone');
    if (gtDropZone) {
        gtDropZone.classList.add('upload-success');
        setTimeout(() => gtDropZone.classList.remove('upload-success'), 2000);
    }

    const status = document.getElementById('gtStatus');
    if (status) {
        status.classList.remove('hidden');
        setTimeout(() => status.classList.add('hidden'), 2000);
    }
}

function highlightDropZone(element) {
    element.classList.add('dragover');
}

function unhighlightDropZone(element) {
    element.classList.remove('dragover');
}

function switchProcessType(e) {
    document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));
    e.currentTarget.classList.add('active');
    const processType = e.currentTarget.dataset.type;
    loadProcessingView(processType);
    resetImageDisplays();
}

function resetImageDisplays() {
    const transparent = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
    document.getElementById('originalResult').src = transparent;
    document.getElementById('processedResult').src = transparent;

    const reportSection = document.getElementById('reportSection');
    if (reportSection) {
        reportSection.style.display = 'none';
    }
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    preventDefaults(e);
    unhighlightDropZone(document.getElementById('dropZone'));

    const dt = e.dataTransfer;
    const files = dt.files;
    document.getElementById('imageInput').files = files;
    handleFileSelect({ target: { files } });
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file || !file.type.startsWith('image/')) {
        alert(t('invalid_image', 'Veuillez télécharger une image valide'));
        resetFileInput();
        return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
        const img = new Image();
        img.onload = function () {
            const dimensionsElement = document.getElementById('inputDimensions');
            const sizeElement = document.getElementById('inputSize');

            if (dimensionsElement) {
                dimensionsElement.textContent = `${this.width}px × ${this.height}px`;
            }
            if (sizeElement) {
                sizeElement.textContent = `${(file.size / 1024).toFixed(1)} KB`;
            }

            document.getElementById('originalResult').src = e.target.result;
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);

    showUploadSuccess();
}

function showUploadSuccess() {
    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;

    dropZone.classList.add('upload-success');

    const status = document.getElementById('imageStatus');
    if (status) {
        status.classList.remove('hidden');
        setTimeout(() => status.classList.add('hidden'), 2000);
    }

    setTimeout(() => dropZone.classList.remove('upload-success'), 2000);
}

function resetFileInput() {
    document.getElementById('imageInput').value = '';
}

async function processImage() {
    const imageInput = document.getElementById('imageInput');
    const file = imageInput.files[0];
    const modelId = document.getElementById('modelSelect').value;
    const activeBtn = document.querySelector('.sidebar-btn.active');
    const processType = activeBtn ? activeBtn.dataset.type : 'segmentation';

    if (!file || !modelId) {
        alert(t('select_image_and_model', 'Veuillez sélectionner une image et un modèle'));
        return;
    }

    toggleLoading(true);

    try {
        const formData = new FormData();
        formData.append('image', file);
        formData.append('model_id', modelId);

        const gtInput = document.getElementById('gtInput');
        if (gtInput && gtInput.files[0]) {
            formData.append('ground_truth', gtInput.files[0]);
        }

        const endpoint = processType === 'segmentation' ? '/process-image' : '/classify-image';
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `${t('http_error_status', 'Erreur HTTP ! statut :')} ${response.status}`);
        }

        const result = await response.json();
        console.log('Server Response:', result);

        if (result.error) {
            throw new Error(result.error);
        }

        document.getElementById('originalResult').src = result.original || result.original_image_url;
        document.getElementById('processedResult').src = result.processed || result.processed_image_url;

        if (processType === 'segmentation') {
            if (result.metrics) {
                const metrics = result.metrics;
                updateMetricElement('iou', metrics.iou);
                updateMetricElement('dice', metrics.dice);
                updateMetricElement('precision', metrics.precision);
                updateMetricElement('recall', metrics.recall);
                updateMetricElement('accuracy', metrics.accuracy);
            }
        } else {
            if (result.healthy_probability !== undefined) {
                document.getElementById('healthyBar').textContent =
                    `${t('healthy', 'Healthy:')} ${safeToFixed(result.healthy_probability, 1)}%`;
            }
            if (result.unhealthy_probability !== undefined) {
                document.getElementById('unhealthyBar').textContent =
                    `${t('unhealthy', 'Unhealthy:')} ${safeToFixed(result.unhealthy_probability, 1)}%`;
            }

            if (result.report) {
                const reportContent = document.getElementById('reportContent');
                if (reportContent) {
                    reportContent.textContent = result.report;
                }
                const reportSection = document.getElementById('reportSection');
                if (reportSection) {
                    reportSection.style.display = 'block';
                }
            }
        }
    } catch (error) {
        handleProcessingError(error);
    } finally {
        toggleLoading(false);
    }
}

function updateMetricElement(id, value) {
    const element = document.getElementById(id);
    if (element && value !== undefined) {
        element.textContent = (value * 100).toFixed(1) + '%';
    }
}

function downloadReport() {
    const reportContentElement = document.getElementById('reportContent');
    if (!reportContentElement || !reportContentElement.textContent.trim()) {
        alert(t('no_report_to_download', 'Aucun rapport disponible à télécharger'));
        return;
    }

    const reportContent = reportContentElement.textContent;
    const blob = new Blob([reportContent], { type: 'text/plain; charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `rapport_classification_${new Date().toISOString().slice(0, 10)}.txt`;
    a.style.display = 'none';

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    alert(t('report_downloaded_success', 'Rapport téléchargé avec succès'));
}

function toggleLoading(isLoading) {
    const btn = document.getElementById('processBtn');
    if (!btn) return;

    let spinner = btn.querySelector('.spinner');
    let btnText = btn.querySelector('.btn-text');

    if (!btnText) {
        const originalText = btn.textContent;
        btn.innerHTML = `<span class="btn-text">${originalText}</span>`;
        btnText = btn.querySelector('.btn-text');
    }

    if (isLoading) {
        btn.disabled = true;
        btnText.textContent = t('processing', 'Traitement...');

        if (!spinner) {
            spinner = document.createElement('span');
            spinner.className = 'spinner';
            spinner.innerHTML = '&nbsp;<i class="fas fa-circle-notch fa-spin"></i>';
            btn.appendChild(spinner);
        }
    } else {
        btn.disabled = false;
        btnText.textContent = t('process_image', "Traiter l'image");

        if (spinner && btn.contains(spinner)) {
            btn.removeChild(spinner);
        }
    }
}

function handleProcessingError(error) {
    console.error(t('processing_error_console', 'Erreur de traitement:'), error);
    alert(`${t('processing_failed', 'Échec du traitement :')} ${error.message}`);
    resetImageDisplays();
    resetFileInput();
}

function loadProcessingView(processType) {
    const gtSection = document.getElementById('gtUploadSection');
    const reportSection = document.getElementById('reportSection');
    const metricsSection = document.getElementById('metricsSection');

    if (processType === 'segmentation') {
        if (gtSection) gtSection.classList.remove('hidden');
        if (metricsSection) metricsSection.style.display = 'block';
        if (reportSection) reportSection.style.display = 'none';
    } else {
        if (gtSection) gtSection.classList.add('hidden');
        if (metricsSection) metricsSection.style.display = 'none';
    }

    if (gtSection) {
        gtSection.style.display = processType === 'segmentation' ? 'block' : 'none';
    }

    fetchModels(processType);
}

async function fetchModels(processType) {
    try {
        console.log(`${t('fetching_models', 'Récupération des modèles')} ${processType}...`);
        const response = await fetch(`/get-models?type=${processType}`);

        if (!response.ok) {
            throw new Error(`${t('error_fetching_models', 'Erreur lors de la récupération des modèles')} (${response.status})`);
        }

        const data = await response.json();
        console.log('Models received:', data.models);

        if (data.models?.length > 0) {
            populateModelDropdown(data.models);
        } else {
            alert(t('no_models_available', 'Aucun modèle disponible'));
            populateModelDropdown([]);
        }
    } catch (error) {
        console.error(t('models_loading_error_console', 'Erreur de chargement des modèles:'), error);
        alert(`${t('error', 'Erreur:')} ${error.message}`);
    }
}

function populateModelDropdown(models) {
    const dropdown = document.getElementById('modelSelect');
    if (!dropdown) return;

    dropdown.innerHTML = `<option value="">${t('select_model', 'Sélectionner un modèle')}</option>`;

    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.model_name;
        dropdown.appendChild(option);
    });
}

async function handleModelUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('model', file);

    try {
        const response = await fetch('/upload-model', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error(t('upload_failed', "Échec de l'upload"));

        alert(t('model_uploaded_success', 'Modèle uploadé avec succès !'));
        const activeType = document.querySelector('.sidebar-btn.active').dataset.type;
        fetchModels(activeType);

    } catch (error) {
        console.error(t('upload_error_console', "Erreur d'upload:"), error);
        alert(`${t('model_upload_error', "Erreur lors de l'upload du modèle:")} ${error.message}`);
    } finally {
        e.target.value = '';
    }
}
document.addEventListener('DOMContentLoaded', () => {
    initializeEventHandlers();
    resetImageDisplays();
    loadProcessingView('segmentation');
});

function t(key, fallback) {
    return (window.I18N && Object.prototype.hasOwnProperty.call(window.I18N, key))
        ? window.I18N[key]
        : fallback;
}

// Fonction pour formater les nombres en toute sécurité
function safeToFixed(value, decimals) {
    if (typeof value === 'undefined' || value === null) {
        return '0.0';
    }
    const num = typeof value === 'string' ? parseFloat(value.replace('%', '')) : value;
    return isNaN(num) ? '0.0' : num.toFixed(decimals);
}

function initializeEventHandlers() {
    // Gestion du téléchargement d'image
    const dropZone = document.getElementById('dropZone');
    const imageInput = document.getElementById('imageInput');

    dropZone.addEventListener('click', () => imageInput.click());
    const gtInput = document.getElementById('gtInput');
    imageInput.addEventListener('change', handleFileSelect);

    // Gestion du click pour la vérité terrain
    const gtDropZone = document.getElementById('gtDropZone');
    if (gtDropZone) {
        gtDropZone.addEventListener('click', () => gtInput.click());
    }

    // Gestion drag and drop
    ['dragover', 'dragleave', 'drop'].forEach(event => {
        dropZone.addEventListener(event, preventDefaults);
        if (gtDropZone) gtDropZone.addEventListener(event, preventDefaults);
    });

    dropZone.addEventListener('dragover', () => highlightDropZone(dropZone));
    dropZone.addEventListener('dragleave', () => unhighlightDropZone(dropZone));
    dropZone.addEventListener('drop', handleDrop);

    if (gtDropZone) {
        gtDropZone.addEventListener('dragover', () => highlightDropZone(gtDropZone));
        gtDropZone.addEventListener('dragleave', () => unhighlightDropZone(gtDropZone));
        gtDropZone.addEventListener('drop', handleGtDrop);
    }

    if (gtInput) {
        gtInput.addEventListener('change', handleGtSelect);
    }

    // Bouton de traitement
    document.getElementById('processBtn').addEventListener('click', processImage);

    // Gestion des boutons de navigation
    document.querySelectorAll('.sidebar-btn').forEach(btn => {
        btn.addEventListener('click', switchProcessType);
    });

    // Upload de modèle personnalisé
    document.getElementById('uploadModelBtn').addEventListener('click', () => {
        document.getElementById('modelUpload').click();
    });

    document.getElementById('modelUpload').addEventListener('change', handleModelUpload);

    const toggleGtBtn = document.getElementById('toggleGtBtn');
    if (toggleGtBtn) {
        toggleGtBtn.addEventListener('click', toggleGtUpload);
    }

    // Gestionnaire pour le bouton de téléchargement du rapport
    const downloadBtn = document.getElementById('downloadReportBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadReport);
    }

    // PDF download for classification report
    const downloadResultsBtn = document.getElementById('downloadResultsBtn');
    if (downloadResultsBtn) {
        downloadResultsBtn.addEventListener('click', async function () {
            const report = document.getElementById('reportContent').textContent;
            const imageUrl = document.getElementById('originalResult').src;

            let relativeImageUrl = imageUrl;
            if (imageUrl.startsWith(window.location.origin)) {
                relativeImageUrl = imageUrl.replace(window.location.origin, '');
            }

            const response = await fetch('/download-classification-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    report: report,
                    image_url: relativeImageUrl
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'rapport_classification.pdf';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                alert(t('download_pdf_error', 'Erreur lors du téléchargement du PDF'));
            }
        });
    }
}

function toggleGtUpload() {
    const gtSection = document.getElementById('gtUploadSection');
    if (!gtSection) return;

    gtSection.classList.toggle('hidden');

    const btn = document.getElementById('toggleGtBtn');
    if (!btn) return;

    if (gtSection.classList.contains('hidden')) {
        btn.textContent = t('upload_gt_image', '📤 Uploader une image vérité terrain');
    } else {
        btn.textContent = t('hide_gt_image', '✖️ Masquer la vérité terrain');
    }
}

function handleGtDrop(e) {
    preventDefaults(e);
    unhighlightDropZone(document.getElementById('gtDropZone'));

    const dt = e.dataTransfer;
    const files = dt.files;
    document.getElementById('gtInput').files = files;
    handleGtSelect({ target: { files } });
}

function handleGtSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    const gtDropZone = document.getElementById('gtDropZone');
    if (gtDropZone) {
        gtDropZone.classList.add('upload-success');
        setTimeout(() => gtDropZone.classList.remove('upload-success'), 2000);
    }

    const status = document.getElementById('gtStatus');
    if (status) {
        status.classList.remove('hidden');
        setTimeout(() => status.classList.add('hidden'), 2000);
    }
}

function highlightDropZone(element) {
    element.classList.add('dragover');
}

function unhighlightDropZone(element) {
    element.classList.remove('dragover');
}

function switchProcessType(e) {
    document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));
    e.currentTarget.classList.add('active');
    const processType = e.currentTarget.dataset.type;
    loadProcessingView(processType);
    resetImageDisplays();
}

function resetImageDisplays() {
    const transparent = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
    document.getElementById('originalResult').src = transparent;
    document.getElementById('processedResult').src = transparent;

    const reportSection = document.getElementById('reportSection');
    if (reportSection) {
        reportSection.style.display = 'none';
    }
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    preventDefaults(e);
    unhighlightDropZone(document.getElementById('dropZone'));

    const dt = e.dataTransfer;
    const files = dt.files;
    document.getElementById('imageInput').files = files;
    handleFileSelect({ target: { files } });
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file || !file.type.startsWith('image/')) {
        alert(t('invalid_image', 'Veuillez télécharger une image valide'));
        resetFileInput();
        return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
        const img = new Image();
        img.onload = function () {
            const dimensionsElement = document.getElementById('inputDimensions');
            const sizeElement = document.getElementById('inputSize');

            if (dimensionsElement) {
                dimensionsElement.textContent = `${this.width}px × ${this.height}px`;
            }
            if (sizeElement) {
                sizeElement.textContent = `${(file.size / 1024).toFixed(1)} KB`;
            }

            document.getElementById('originalResult').src = e.target.result;
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);

    showUploadSuccess();
}

function showUploadSuccess() {
    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;

    dropZone.classList.add('upload-success');

    const status = document.getElementById('imageStatus');
    if (status) {
        status.classList.remove('hidden');
        setTimeout(() => status.classList.add('hidden'), 2000);
    }

    setTimeout(() => dropZone.classList.remove('upload-success'), 2000);
}

function resetFileInput() {
    document.getElementById('imageInput').value = '';
}

async function processImage() {
    const imageInput = document.getElementById('imageInput');
    const file = imageInput.files[0];
    const modelId = document.getElementById('modelSelect').value;
    const activeBtn = document.querySelector('.sidebar-btn.active');
    const processType = activeBtn ? activeBtn.dataset.type : 'segmentation';

    if (!file || !modelId) {
        alert(t('select_image_and_model', 'Veuillez sélectionner une image et un modèle'));
        return;
    }

    toggleLoading(true);

    try {
        const formData = new FormData();
        formData.append('image', file);
        formData.append('model_id', modelId);

        const gtInput = document.getElementById('gtInput');
        if (gtInput && gtInput.files[0]) {
            formData.append('ground_truth', gtInput.files[0]);
        }

        const endpoint = processType === 'segmentation' ? '/process-image' : '/classify-image';
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `${t('http_error_status', 'Erreur HTTP ! statut :')} ${response.status}`);
        }

        const result = await response.json();
        console.log('Server Response:', result);

        if (result.error) {
            throw new Error(result.error);
        }

        document.getElementById('originalResult').src = result.original || result.original_image_url;
        document.getElementById('processedResult').src = result.processed || result.processed_image_url;

        if (processType === 'segmentation') {
            if (result.metrics) {
                const metrics = result.metrics;
                updateMetricElement('iou', metrics.iou);
                updateMetricElement('dice', metrics.dice);
                updateMetricElement('precision', metrics.precision);
                updateMetricElement('recall', metrics.recall);
                updateMetricElement('accuracy', metrics.accuracy);
            }
        } else {
            if (result.healthy_probability !== undefined) {
                document.getElementById('healthyBar').textContent =
                    `${t('healthy', 'Healthy:')} ${safeToFixed(result.healthy_probability, 1)}%`;
            }
            if (result.unhealthy_probability !== undefined) {
                document.getElementById('unhealthyBar').textContent =
                    `${t('unhealthy', 'Unhealthy:')} ${safeToFixed(result.unhealthy_probability, 1)}%`;
            }

            if (result.report) {
                const reportContent = document.getElementById('reportContent');
                if (reportContent) {
                    reportContent.textContent = result.report;
                }
                const reportSection = document.getElementById('reportSection');
                if (reportSection) {
                    reportSection.style.display = 'block';
                }
            }
        }
    } catch (error) {
        handleProcessingError(error);
    } finally {
        toggleLoading(false);
    }
}

function updateMetricElement(id, value) {
    const element = document.getElementById(id);
    if (element && value !== undefined) {
        element.textContent = (value * 100).toFixed(1) + '%';
    }
}

function downloadReport() {
    const reportContentElement = document.getElementById('reportContent');
    if (!reportContentElement || !reportContentElement.textContent.trim()) {
        alert(t('no_report_to_download', 'Aucun rapport disponible à télécharger'));
        return;
    }

    const reportContent = reportContentElement.textContent;
    const blob = new Blob([reportContent], { type: 'text/plain; charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `rapport_classification_${new Date().toISOString().slice(0, 10)}.txt`;
    a.style.display = 'none';

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    alert(t('report_downloaded_success', 'Rapport téléchargé avec succès'));
}

function toggleLoading(isLoading) {
    const btn = document.getElementById('processBtn');
    if (!btn) return;

    let spinner = btn.querySelector('.spinner');
    let btnText = btn.querySelector('.btn-text');

    if (!btnText) {
        const originalText = btn.textContent;
        btn.innerHTML = `<span class="btn-text">${originalText}</span>`;
        btnText = btn.querySelector('.btn-text');
    }

    if (isLoading) {
        btn.disabled = true;
        btnText.textContent = t('processing', 'Traitement...');

        if (!spinner) {
            spinner = document.createElement('span');
            spinner.className = 'spinner';
            spinner.innerHTML = '&nbsp;<i class="fas fa-circle-notch fa-spin"></i>';
            btn.appendChild(spinner);
        }
    } else {
        btn.disabled = false;
        btnText.textContent = t('process_image', "Traiter l'image");

        if (spinner && btn.contains(spinner)) {
            btn.removeChild(spinner);
        }
    }
}

function handleProcessingError(error) {
    console.error(t('processing_error_console', 'Erreur de traitement:'), error);
    alert(`${t('processing_failed', 'Échec du traitement :')} ${error.message}`);
    resetImageDisplays();
    resetFileInput();
}

function loadProcessingView(processType) {
    const gtSection = document.getElementById('gtUploadSection');
    const reportSection = document.getElementById('reportSection');
    const metricsSection = document.getElementById('metricsSection');

    if (processType === 'segmentation') {
        if (gtSection) gtSection.classList.remove('hidden');
        if (metricsSection) metricsSection.style.display = 'block';
        if (reportSection) reportSection.style.display = 'none';
    } else {
        if (gtSection) gtSection.classList.add('hidden');
        if (metricsSection) metricsSection.style.display = 'none';
    }

    if (gtSection) {
        gtSection.style.display = processType === 'segmentation' ? 'block' : 'none';
    }

    fetchModels(processType);
}

async function fetchModels(processType) {
    try {
        console.log(`${t('fetching_models', 'Récupération des modèles')} ${processType}...`);
        const response = await fetch(`/get-models?type=${processType}`);

        if (!response.ok) {
            throw new Error(`${t('error_fetching_models', 'Erreur lors de la récupération des modèles')} (${response.status})`);
        }

        const data = await response.json();
        console.log('Models received:', data.models);

        if (data.models?.length > 0) {
            populateModelDropdown(data.models);
        } else {
            alert(t('no_models_available', 'Aucun modèle disponible'));
            populateModelDropdown([]);
        }
    } catch (error) {
        console.error(t('models_loading_error_console', 'Erreur de chargement des modèles:'), error);
        alert(`${t('error', 'Erreur:')} ${error.message}`);
    }
}

function populateModelDropdown(models) {
    const dropdown = document.getElementById('modelSelect');
    if (!dropdown) return;

    dropdown.innerHTML = `<option value="">${t('select_model', 'Sélectionner un modèle')}</option>`;

    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.model_name;
        dropdown.appendChild(option);
    });
}

async function handleModelUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('model', file);

    try {
        const response = await fetch('/upload-model', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error(t('upload_failed', "Échec de l'upload"));

        alert(t('model_uploaded_success', 'Modèle uploadé avec succès !'));
        const activeType = document.querySelector('.sidebar-btn.active').dataset.type;
        fetchModels(activeType);

    } catch (error) {
        console.error(t('upload_error_console', "Erreur d'upload:"), error);
        alert(`${t('model_upload_error', "Erreur lors de l'upload du modèle:")} ${error.message}`);
    } finally {
        e.target.value = '';
    }
    
}