// user-dashboard.js - Version complète avec segmentation et classification
document.addEventListener('DOMContentLoaded', () => {
    initializeEventHandlers();
    resetImageDisplays();
    const initialMode = window.initialMode || 'classification';
    if (initialMode === 'adaptation') {
        showAdaptationView();
    } else {
        setProcessingMode(initialMode);
        loadProcessingView(initialMode);
    }
});

function setProcessingMode(mode) {
    document.querySelectorAll('#processingView .sidebar-btn[data-type]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === mode);
    });
    window.currentMode = mode;
}

function setDashboardUrlMode(mode) {
    const url = new URL(window.location.href);
    if (url.searchParams.get('mode') === mode) return;
    url.searchParams.set('mode', mode);
    history.pushState(null, '', url);
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
    
    gtInput.addEventListener('change', handleGtSelect);
    
    // Bouton de traitement
    document.getElementById('processBtn').addEventListener('click', processImage);

    // Gestion des boutons de navigation
    document.querySelectorAll('#processingView .sidebar-btn[data-type]').forEach(btn => {
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
    document.getElementById('downloadResultsBtn').addEventListener('click', async function() {
        const report = document.getElementById('reportContent').textContent;
        const imageUrl = document.getElementById('originalResult').src;

        // Get relative image path (if needed)
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
            alert("Erreur lors du téléchargement du PDF");
        }
    });
}

function toggleGtUpload() {
    const gtSection = document.getElementById('gtUploadSection');
    if (!gtSection) return;
    
    gtSection.classList.toggle('hidden');
    
    // Optionnel: Changer le texte du bouton
    const btn = document.getElementById('toggleGtBtn');
    if (gtSection.classList.contains('hidden')) {
        btn.textContent = '📤 Uploader une image vérité terrain';
    } else {
        btn.textContent = '✖️ Masquer la vérité terrain';
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
    const button = e.currentTarget || e.target.closest('.sidebar-btn');
    if (!button || !button.dataset || !button.dataset.type) return;
    const processType = button.dataset.type;
    setProcessingMode(processType);
    resetImageDisplays();
    loadProcessingView(processType);
}

function resetImageDisplays() {
    const transparent = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
    document.getElementById('originalResult').src = transparent;
    document.getElementById('processedResult').src = transparent;
    
    // Masquer la section de rapport pour la classification
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
        alert('Veuillez télécharger une image valide');
        resetFileInput();
        return;
    }

    // Lire les métadonnées de l'image
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const dimensionsElement = document.getElementById('inputDimensions');
            const sizeElement = document.getElementById('inputSize');
            
            if (dimensionsElement) {
                dimensionsElement.textContent = `${this.width}px × ${this.height}px`;
            }
            if (sizeElement) {
                sizeElement.textContent = `${(file.size/1024).toFixed(1)} KB`;
            }
            
            // Afficher l'image originale
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
    const processType = document.querySelector('.sidebar-btn.active').dataset.type;
    
    if (!file || !modelId) {
        alert('Veuillez sélectionner une image et un modèle');
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
            throw new Error(errorText || `Erreur HTTP ! statut : ${response.status}`);
        }

        const result = await response.json();
        console.log('Server Response:', result);
        
        if (result.error) {
            throw new Error(result.error);
        }

        // Afficher les résultats
        document.getElementById('originalResult').src = result.original || result.original_image_url;
        document.getElementById('processedResult').src = result.processed || result.processed_image_url;
        
        if (processType === 'segmentation') {
            // Mettre à jour les métriques de segmentation
            if (result.metrics) {
                const metrics = result.metrics;
                updateMetricElement('iou', metrics.iou);
                updateMetricElement('dice', metrics.dice);
                updateMetricElement('precision', metrics.precision);
                updateMetricElement('recall', metrics.recall);
                updateMetricElement('accuracy', metrics.accuracy);
            }
        } else {
            // Mettre à jour les résultats de classification
            if (result.healthy_probability !== undefined) {
                document.getElementById('healthyBar').textContent = 
                    `Healthy: ${safeToFixed(result.healthy_probability, 1)}%`;
            }
            if (result.unhealthy_probability !== undefined) {
                document.getElementById('unhealthyBar').textContent = 
                    `Unhealthy: ${safeToFixed(result.unhealthy_probability, 1)}%`;
            }
            
            // Affichage du rapport
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
        alert("Aucun rapport disponible à télécharger");
        return;
    }

    const reportContent = reportContentElement.textContent;
    const blob = new Blob([reportContent], { type: 'text/plain; charset=utf-8' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `rapport_classification_${new Date().toISOString().slice(0,10)}.txt`;
    a.style.display = 'none';
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    alert("Rapport téléchargé avec succès");
}

function toggleLoading(isLoading) {
    const btn = document.getElementById('processBtn');
    if (!btn) return;

    let spinner = btn.querySelector('.spinner');
    let btnText = btn.querySelector('.btn-text');
    
    if (!btnText) {
        // Si .btn-text n'existe pas, on enveloppe le texte existant
        const originalText = btn.textContent;
        btn.innerHTML = `<span class="btn-text">${originalText}</span>`;
        btnText = btn.querySelector('.btn-text');
    }

    if (isLoading) {
        btn.disabled = true;
        btnText.textContent = 'Traitement...';
        
        if (!spinner) {
            spinner = document.createElement('span');
            spinner.className = 'spinner';
            spinner.innerHTML = '&nbsp;<i class="fas fa-circle-notch fa-spin"></i>';
            btn.appendChild(spinner);
        }
    } else {
        btn.disabled = false;
        btnText.textContent = 'Traiter l\'image';
        
        if (spinner && btn.contains(spinner)) {
            btn.removeChild(spinner);
        }
    }
}

function handleProcessingError(error) {
    console.error('Erreur de traitement:', error);
    alert(`Échec du traitement : ${error.message}`);
    resetImageDisplays();
    resetFileInput();
}

function loadProcessingView(processType) {
    const categoryTitle = document.querySelector('.current-category');
    
    // Masquer/afficher les éléments spécifiques au type de traitement
    const gtSection = document.getElementById('gtUploadSection');
    const reportSection = document.getElementById('reportSection');
    const metricsSection = document.getElementById('metricsSection');
    const segmentationResult = document.getElementById('segmentationResult');
    const classificationResult = document.getElementById('classificationResult');
    
    if (processType === 'segmentation') {
        if (gtSection) gtSection.classList.remove('hidden');
        if (metricsSection) metricsSection.style.display = 'block';
        if (reportSection) reportSection.style.display = 'none';
        if (segmentationResult) segmentationResult.style.display = 'block';
        if (classificationResult) classificationResult.style.display = 'none';
    } else {
        if (gtSection) gtSection.classList.add('hidden');
        if (metricsSection) metricsSection.style.display = 'none';
        if (segmentationResult) segmentationResult.style.display = 'none';
        if (classificationResult) classificationResult.style.display = 'block';
    }
    
    if (gtSection) {
        gtSection.style.display = processType === 'segmentation' ? 'block' : 'none';
    }
    fetchModels(processType);
}

async function fetchModels(processType) {
    try {
        if (processType !== 'classification' && processType !== 'segmentation') {
            processType = 'classification';
        }
        console.log(`Récupération des modèles ${processType}...`);
        const response = await fetch(`/get-models?type=${processType}`);
        
        if (!response.ok) {
            throw new Error(`Erreur ${response.status} lors de la récupération des modèles`);
        }

        const data = await response.json();
        const models = Array.isArray(data) ? data : (data.models || []);
        console.log("Modèles reçus:", models);

        if (models.length > 0) {
            populateModelDropdown(models);
        } else {
            alert("Aucun modèle disponible");
            populateModelDropdown([]);
        }
    } catch (error) {
        console.error("Erreur de chargement des modèles:", error);
        alert(`Erreur: ${error.message}`);
    }
}

function populateModelDropdown(models) {
    const dropdown = document.getElementById('modelSelect');
    if (!dropdown) return;
    
    dropdown.innerHTML = '<option value="">Sélectionner un modèle</option>';

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
        
        if (!response.ok) throw new Error('Échec de l\'upload');
        
        alert('Modèle uploadé avec succès !');
        const activeBtn = document.querySelector('.sidebar-btn.active');
        const activeType = (activeBtn && activeBtn.dataset && activeBtn.dataset.type)
            ? activeBtn.dataset.type
            : 'classification';
        fetchModels(activeType);
        
    } catch (error) {
        console.error('Erreur d\'upload:', error);
        alert("Erreur lors de l'upload du modèle: " + error.message);
    } finally {
        e.target.value = '';
    }
}







/* ================================================================
   adaptation.js — BassarCare | Fonctionnalité Adaptation du Modèle
   À placer dans : static/js/adaptation.js
   ================================================================ */

'use strict';

/* ──────────────────────────────────────────────────────────────────
   STATE
──────────────────────────────────────────────────────────────────── */
const adaptState = {
  file:          null,   // Fichier ZIP sélectionné
  task:          'classification', // 'classification' | 'segmentation'
  baseModelId:   '',
  baseModelFile: null,
  baseModelName: 'Nouveau modèle (from scratch)',
  history:       [],     // chargé depuis localStorage
  activeJob:     null,
  currentPoller: null,
  pendingRelaunch: false,
  currentAdaptModelPath: null,
  currentAdaptModelName: null,
  charts: {
    loss: null,
    acc:  null
  }
};

/* ──────────────────────────────────────────────────────────────────
   NAVIGATION ENTRE VUES
──────────────────────────────────────────────────────────────────── */
function showAdaptationView() {
  setDashboardUrlMode('adaptation');
  const pv = document.getElementById('processingView');
  const av = document.getElementById('adaptationView');
  if (pv) pv.style.display = 'none';
  if (av) {
    av.style.display = 'flex';
    adaptLoadHistory();
    adaptRenderHistory();
    resumeActiveAdaptationJob();
  }
  // Mettre à jour les boutons actifs de la sidebar (vue principale)
  document.querySelectorAll('#processingView .sidebar-btn').forEach(b => {
    b.classList.remove('active');
    if (b.classList.contains('adapt-sidebar-btn')) b.classList.add('active');
  });
}

function showProcessingView() {
  const pv = document.getElementById('processingView');
  const av = document.getElementById('adaptationView');
  if (av) av.style.display = 'none';
  if (pv) pv.style.display = 'flex';
}

/* ──────────────────────────────────────────────────────────────────
   SÉLECTION DU TYPE DE TÂCHE (toggle Classification / Segmentation)
──────────────────────────────────────────────────────────────────── */
function selectAdaptTask(task) {
  adaptState.task = task;

  const btnCls = document.getElementById('btnTaskCls');
  const btnSeg = document.getElementById('btnTaskSeg');
  if (!btnCls || !btnSeg) return;

  btnCls.classList.toggle('active', task === 'classification');
  btnSeg.classList.toggle('active', task === 'segmentation');
  updateAdaptStructureHint(task);
}

function updateAdaptStructureHint(task) {
  const hintPre = document.getElementById('adaptStructurePre');
  if (!hintPre) return;

  if (task === 'segmentation') {
    hintPre.textContent = `dataset.zip/
├── train/
│   ├── images/
│   └── masks/
└── test/
    ├── images/
    └── masks/`;
  } else {
    hintPre.textContent = `dataset.zip/
├── train/
│   ├── glaucoma/
│   └── normal/
└── test/
    ├── glaucoma/
    └── normal/`;
  }
}

/* ──────────────────────────────────────────────────────────────────
   SLIDER TAUX D'APPRENTISSAGE  (valeur logarithmique 0.00001 → 0.1)
──────────────────────────────────────────────────────────────────── */
function updateLR(val) {
  // val ∈ [1, 100]  →  LR ∈ [0.00001, 0.1]
  const min = Math.log10(0.00001);  // -5
  const max = Math.log10(0.1);      // -1
  const lr = Math.pow(10, min + (val - 1) / 99 * (max - min));
  const formatted = lr < 0.001
    ? lr.toExponential(1)
    : lr.toFixed(4).replace(/\.?0+$/, '');
  const lrValEl = document.getElementById('lrVal');
  if (lrValEl) lrValEl.textContent = formatted;
}

/* ──────────────────────────────────────────────────────────────────
   GESTION DU FICHIER ZIP
──────────────────────────────────────────────────────────────────── */
function handleAdaptFileSelect(input) {
  if (input.files && input.files[0]) {
    _setAdaptFile(input.files[0]);
    const hint = document.getElementById('adaptRelaunchHint');
    if (hint) hint.remove();
    if (adaptState.pendingRelaunch) {
      adaptState.pendingRelaunch = false;
      setTimeout(() => launchAdaptation(), 150);
    }
  }
}

function handleAdaptDrop(event) {
  event.preventDefault();
  const dz = document.getElementById('adaptDropZone');
  if (dz) dz.classList.remove('dragover');

  const file = event.dataTransfer.files[0];
  if (!file) return;

  if (!file.name.toLowerCase().endsWith('.zip')) {
    _adaptShowDropError('Seuls les fichiers .zip sont acceptés.');
    return;
  }
  _setAdaptFile(file);
}

function _setAdaptFile(file) {
  adaptState.file = file;

  // Mise à jour visuelle zone de drop
  const dz        = document.getElementById('adaptDropZone');
  const dropTitle = document.getElementById('adaptDropTitle');
  if (dz) dz.classList.add('has-file');
  if (dropTitle) dropTitle.textContent = 'Fichier sélectionné ✓';

  // Afficher les infos
  const infoEl    = document.getElementById('adaptFileInfo');
  const nameEl    = document.getElementById('adaptFileName');
  const sizeEl    = document.getElementById('adaptFileSize');
  if (infoEl) infoEl.style.display = 'flex';
  if (nameEl) nameEl.textContent  = file.name;
  if (sizeEl) sizeEl.textContent  = (file.size / 1024 / 1024).toFixed(2) + ' Mo';
}

function _adaptShowDropError(msg) {
  const dz = document.getElementById('adaptDropZone');
  if (!dz) return;
  dz.style.borderColor = '#dc2626';
  dz.style.background  = '#fef2f2';
  const dropTitle = document.getElementById('adaptDropTitle');
  if (dropTitle) { dropTitle.textContent = '⚠ ' + msg; dropTitle.style.color = '#dc2626'; }
  setTimeout(() => {
    dz.style.borderColor = '';
    dz.style.background  = '';
    if (dropTitle) { dropTitle.textContent = "Uploader votre dossier d'images"; dropTitle.style.color = ''; }
  }, 3000);
}

function resetAdaptFile() {
  adaptState.file = null;
  adaptState.pendingRelaunch = false;
  const dz        = document.getElementById('adaptDropZone');
  const dropTitle = document.getElementById('adaptDropTitle');
  const infoEl    = document.getElementById('adaptFileInfo');
  const fileInput = document.getElementById('adaptDatasetFile');
  if (dz)        { dz.classList.remove('has-file'); }
  if (dropTitle) { dropTitle.textContent = "Uploader votre dossier d'images"; }
  if (infoEl)    { infoEl.style.display = 'none'; }
  if (fileInput) { fileInput.value = ''; }
}

/* ──────────────────────────────────────────────────────────────────
   RÉINITIALISER TOUT LE FORMULAIRE
──────────────────────────────────────────────────────────────────── */
function resetAdaptForm() {
  resetAdaptFile();
  resetBaseModelFile();
  selectAdaptTask('classification');

  const sel   = document.getElementById('adaptBaseModel');
  const name  = document.getElementById('adaptModelName');
  const epR   = document.getElementById('epochsRange');
  const lrR   = document.getElementById('lrRange');
  const baR   = document.getElementById('batchRange');
  const epV   = document.getElementById('epochsVal');
  const lrV   = document.getElementById('lrVal');
  const baV   = document.getElementById('batchVal');

  if (sel)  sel.value  = '';
  if (name) name.value = '';
  if (epR)  { epR.value = 20; if (epV) epV.textContent = '20'; }
  if (lrR)  { lrR.value = 10; updateLR(10); }
  if (baR)  { baR.value = 16; if (baV) baV.textContent = '16'; }

  // Masquer zones progression / résultat
  const progSec  = document.getElementById('adaptProgressSection');
  const resModule = document.getElementById('adaptResultModule');
  const resZone  = document.getElementById('adaptResultZone');
  const launchBtn = document.getElementById('adaptLaunchBtn');
  const cancelBtn = document.getElementById('adaptCancelBtn');
  if (progSec)   progSec.style.display  = 'none';
  if (resModule) resModule.style.display = 'none';
  if (resZone)   { resZone.innerHTML = ''; }
  if (launchBtn) { launchBtn.disabled = false; launchBtn.innerHTML = _launchBtnHTML(); }
  if (cancelBtn) { cancelBtn.style.display = 'none'; cancelBtn.disabled = false; cancelBtn.textContent = 'Arreter adaptation'; }
}

function handleBaseModelFileSelect(input) {
  if (!input || !input.files || !input.files[0]) return;

  const file = input.files[0];
  const lower = file.name.toLowerCase();
  if (!lower.endsWith('.pth') && !lower.endsWith('.pt')) {
    _adaptAlert('Veuillez sélectionner un fichier modèle .pth ou .pt');
    input.value = '';
    return;
  }

  adaptState.baseModelFile = file;
  const modelSelect = document.getElementById('adaptBaseModel');
  if (modelSelect) modelSelect.value = '';

  const info = document.getElementById('adaptBaseModelFileInfo');
  const name = document.getElementById('adaptBaseModelFileName');
  const size = document.getElementById('adaptBaseModelFileSize');
  if (info) info.style.display = 'flex';
  if (name) name.textContent = file.name;
  if (size) size.textContent = (file.size / 1024 / 1024).toFixed(2) + ' Mo';
}

function resetBaseModelFile() {
  adaptState.baseModelFile = null;
  const input = document.getElementById('adaptBaseModelFile');
  const info = document.getElementById('adaptBaseModelFileInfo');
  if (input) input.value = '';
  if (info) info.style.display = 'none';
}

function _launchBtnHTML() {
  return `<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
    <polygon points="5 3 19 12 5 21 5 3"/></svg>Lancer l'adaptation`;
}

/* ──────────────────────────────────────────────────────────────────
   LANCEMENT DE L'ADAPTATION
──────────────────────────────────────────────────────────────────── */
function launchAdaptation() {
  /* ── Validation ─────────────────────────────── */
  if (!adaptState.file) {
    _adaptAlert('Veuillez sélectionner un fichier ZIP de dataset avant de lancer.'); return;
  }
  const modelName = (document.getElementById('adaptModelName') || {}).value || '';
  if (!modelName.trim()) {
    _adaptAlert("Veuillez saisir un nom pour le modèle adapté."); return;
  }

  /* ── UI en état "chargement" ─────────────────── */
  const launchBtn  = document.getElementById('adaptLaunchBtn');
  const cancelBtn  = document.getElementById('adaptCancelBtn');
  const progSec    = document.getElementById('adaptProgressSection');
  const resModule  = document.getElementById('adaptResultModule');
  const resZone    = document.getElementById('adaptResultZone');

  if (launchBtn) {
    launchBtn.disabled = true;
    launchBtn.innerHTML = `<span class="adapt-spinner"></span>En cours…`;
  }
  if (cancelBtn) {
    cancelBtn.style.display = 'inline-flex';
    cancelBtn.disabled = false;
    cancelBtn.textContent = 'Arreter adaptation';
  }
  if (progSec) progSec.style.display = 'block';
  if (resModule) resModule.style.display = 'none';
  if (resZone) { resZone.innerHTML = ''; }
  _setAdaptationLongRunningHint();

  _updateAdaptProgress(2, 'Initialisation du job...', '');

  /* ── Envoi réel au backend ───────────────────── */
  const formData = new FormData();
  formData.append('dataset',      adaptState.file);
  formData.append('task',         adaptState.task);
  formData.append('model_name',   modelName.trim());
  formData.append('base_model',   (document.getElementById('adaptBaseModel') || {}).value || '');
  if (adaptState.baseModelFile) {
    formData.append('base_model_file', adaptState.baseModelFile);
  }
  formData.append('epochs',       (document.getElementById('epochsRange')   || {}).value || 20);
  formData.append('lr',           (document.getElementById('lrVal')         || {}).textContent || '0.001');
  formData.append('batch_size',   (document.getElementById('batchRange')    || {}).value || 16);

  fetch('/adapt_model', { method: 'POST', body: formData })
    .then(async r => {
      let payload = null;
      try {
        payload = await r.json();
      } catch (_) {
        payload = null;
      }
      if (!r.ok) {
        const msg = (payload && (payload.message || payload.error)) || `Erreur HTTP ${r.status}`;
        throw new Error(msg);
      }
      return payload || {};
    })
    .then(data => {
      const jobId = data.job_id;
      if (!jobId) {
        throw new Error("Aucun job_id retourné par le serveur.");
      }
      _saveActiveAdaptJob(jobId, modelName.trim());
      _pollAdaptationJob(jobId, modelName);
    })
    .catch(err => {
      const msg = err.message || "Erreur inconnue pendant l'adaptation.";
      _updateAdaptProgress(100, 'Erreur', '');
      setTimeout(() => _finishAdaptation(modelName, false, msg, null), 200);
    });
}

function _updateAdaptProgress(pct, label, sub) {
  const fill  = document.getElementById('adaptProgressBarFill');
  const pctEl = document.getElementById('adaptProgressPct');
  const lblEl = document.getElementById('adaptProgressLabel');
  const subEl = document.getElementById('adaptProgressSub');
  if (fill)  fill.style.width   = `${pct}%`;
  if (pctEl) pctEl.textContent  = `${pct}%`;
  if (lblEl) lblEl.textContent  = label || '';
  if (subEl && typeof sub !== 'undefined') subEl.textContent = sub || '';
}

function _pollAdaptationJob(jobId, modelName) {
  if (adaptState.currentPoller) {
    clearInterval(adaptState.currentPoller);
    adaptState.currentPoller = null;
  }

  let pollCount = 0;
  const maxPolls = 3600; // ~2h at 2s interval

  const poll = async () => {
    pollCount += 1;
    if (pollCount > maxPolls) {
      if (adaptState.currentPoller) clearInterval(adaptState.currentPoller);
      adaptState.currentPoller = null;
      _clearActiveAdaptJob(jobId);
      _updateAdaptProgress(100, 'Erreur', '');
      _finishAdaptation(modelName, false, "Timeout de suivi du job d'adaptation.", null);
      return;
    }

    try {
      const response = await fetch(`/adapt_model_status/${jobId}`);
      if (response.status === 404) {
        if (adaptState.currentPoller) clearInterval(adaptState.currentPoller);
        adaptState.currentPoller = null;
        _clearActiveAdaptJob(jobId);
        _updateAdaptProgress(100, 'Erreur', '');
        _finishAdaptation(modelName, false, "Le job d'adaptation est introuvable. Il a peut-être été terminé après un redémarrage du serveur.", null);
        return;
      }
      if (!response.ok) {
        throw new Error(`Erreur suivi job (${response.status})`);
      }
      const data = await response.json();

      const parsedProgress = Number(data.progress);
      const progress = Number.isFinite(parsedProgress) ? parsedProgress : 0;
      const message = data.message || 'Entraînement en cours...';
      _updateAdaptProgress(Math.min(Math.max(progress, 0), 100), message, `Job: ${jobId.slice(0, 8)}`);

      if (data.done) {
        if (adaptState.currentPoller) clearInterval(adaptState.currentPoller);
        adaptState.currentPoller = null;
        _clearActiveAdaptJob(jobId);
        const canceled = data.canceled === true;
        const success = !canceled && data.result_success !== false;
        _updateAdaptProgress(100, canceled ? 'Arrete' : (success ? 'Terminé !' : 'Erreur'), '');
        setTimeout(() => _finishAdaptation(
          modelName,
          success,
          data.message || '',
          data.history || null,
          data.model_path || null,
          canceled
        ), 250);
      }
    } catch (_) {
      // ignore transient poll failures; keep polling
    }
  };

  poll();
  adaptState.currentPoller = setInterval(poll, 2000);
}

async function cancelAdaptation() {
  const active = _loadActiveAdaptJob();
  if (!active || !active.jobId) {
    _adaptAlert("Aucune adaptation en cours a arreter.");
    return;
  }

  const cancelBtn = document.getElementById('adaptCancelBtn');
  if (cancelBtn) {
    cancelBtn.disabled = true;
    cancelBtn.textContent = 'Arret...';
  }
  _updateAdaptProgress(
    99,
    'Arret demande...',
    `Job: ${active.jobId.slice(0, 8)} - attente de l'arret cote serveur`
  );

  try {
    const response = await fetch(`/adapt_model_cancel/${active.jobId}`, {
      method: 'POST',
      headers: { 'Accept': 'application/json' }
    });
    if (response.status === 404) {
      throw new Error("La route d'arret n'est pas encore chargee par Flask. Arrete le serveur avec Ctrl+C puis relance-le.");
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.success === false) {
      throw new Error(data.message || `Erreur HTTP ${response.status}`);
    }

    if (data.already_done) {
      _clearActiveAdaptJob(active.jobId);
      if (cancelBtn) cancelBtn.style.display = 'none';
      _updateAdaptProgress(100, data.message || 'Job deja termine', '');
      return;
    }

    _updateAdaptProgress(
      99,
      data.message || 'Arret demande...',
      'Le processus va s arreter au prochain batch.'
    );
  } catch (err) {
    if (cancelBtn) {
      cancelBtn.disabled = false;
      cancelBtn.textContent = 'Arreter adaptation';
    }
    _adaptAlert(err.message || "Impossible d'arreter l'adaptation.");
  }
}

function _setAdaptationLongRunningHint() {
  const subEl = document.getElementById('adaptProgressSub');
  if (!subEl) return;
  subEl.textContent = "Entraînement en cours... cela peut prendre plusieurs minutes selon votre machine.";
}

/* ──────────────────────────────────────────────────────────────────
   RÉSULTAT FINAL
──────────────────────────────────────────────────────────────────── */
function _finishAdaptation(modelName, success, message, metricHistory, modelPath, canceled = false) {
  const resModule = document.getElementById('adaptResultModule');
  const resZone   = document.getElementById('adaptResultZone');
  const launchBtn = document.getElementById('adaptLaunchBtn');
  const cancelBtn = document.getElementById('adaptCancelBtn');

  if (resModule) resModule.style.display = 'block';
  if (cancelBtn) {
    cancelBtn.style.display = 'none';
    cancelBtn.disabled = false;
    cancelBtn.textContent = 'Arreter adaptation';
  }

  if (success) {
    adaptState.currentAdaptModelPath = modelPath || null;
    adaptState.currentAdaptModelName = modelName || null;

    resZone.innerHTML = `
      <div class="adapt-result-success">
        <div class="adapt-result-success-icon">
          <svg width="18" height="18" fill="none" stroke="#fff" stroke-width="2.5" viewBox="0 0 24 24">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <div>
          <h4>Entraînement terminé avec succès !</h4>
          <p>Le modèle <strong>${_escHtml(modelName)}</strong> a été adapté et sauvegardé.
          ${message ? '<br><em>' + _escHtml(message) + '</em>' : ''}</p>
          ${modelPath ? `<p style="margin-top:0.35rem; font-size:0.86rem;">
            .pth : <code>${_escHtml(modelPath)}</code>
          </p>` : ''}
          <button class="adapt-result-reload-btn" onclick="location.reload()">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            Actualiser le tableau de bord
          </button>

          <div class="adapt-action-row" style="margin-top:0.95rem;">
            <button type="button" class="adapt-btn-reset" onclick="adaptRelaunchCurrentAdaptation()">
              Relancer l'adaptation
            </button>
            ${modelPath ? `
              <button type="button" class="adapt-btn-reset" onclick="adaptDownloadCurrentModel()">
                Télécharger model
              </button>
            ` : ''}
          </div>
        </div>
      </div>`;

    _renderAdaptationCharts(metricHistory);

    // Enregistrer dans l'historique
    _adaptAddHistory(modelName, adaptState.task, 'success', {
      model_path: modelPath,
      metricHistory: metricHistory
    });

  } else {
    resZone.innerHTML = `
      <div class="adapt-result-error">
        <h4>${canceled ? 'Adaptation arretee' : "Erreur lors de l'entraînement"}</h4>
        <p>${_escHtml(message || 'Une erreur est survenue. Vérifiez le format du dataset.')}</p>
      </div>`;

    _adaptAddHistory(modelName, adaptState.task, 'error', {
      error_message: message
    });

    // Réactiver le bouton en cas d'erreur
    if (launchBtn) {
      launchBtn.disabled = false;
      launchBtn.innerHTML = _launchBtnHTML();
    }
  }
}

function _renderAdaptationCharts(metricHistory) {
  if (!metricHistory || typeof Chart === 'undefined') return;

  const trainLoss = Array.isArray(metricHistory.train_loss) ? metricHistory.train_loss : [];
  const valLoss = Array.isArray(metricHistory.val_loss) ? metricHistory.val_loss : [];
  const trainAcc = Array.isArray(metricHistory.train_acc) ? metricHistory.train_acc : [];
  const valAcc = Array.isArray(metricHistory.val_acc) ? metricHistory.val_acc : [];
  const epochsCount = Math.max(trainLoss.length, valLoss.length, trainAcc.length, valAcc.length);
  if (epochsCount === 0) return;

  const labels = Array.from({ length: epochsCount }, (_, i) => `Epoch ${i + 1}`);
  const resZone = document.getElementById('adaptResultZone');
  if (!resZone) return;

  resZone.insertAdjacentHTML('beforeend', `
    <div class="adapt-charts-block">
      <h4 class="adapt-charts-title">Courbes d'entraînement</h4>
      <div class="adapt-charts-grid">
        <div class="adapt-chart-card">
          <h5 class="adapt-chart-label">Loss (train / validation)</h5>
          <div class="adapt-chart-wrap">
            <canvas id="adaptLossChart"></canvas>
          </div>
        </div>
        <div class="adapt-chart-card">
          <h5 class="adapt-chart-label">Accuracy (train / validation)</h5>
          <div class="adapt-chart-wrap">
            <canvas id="adaptAccChart"></canvas>
          </div>
        </div>
      </div>
    </div>
  `);

  if (adaptState.charts.loss) adaptState.charts.loss.destroy();
  if (adaptState.charts.acc) adaptState.charts.acc.destroy();

  const lossCtx = document.getElementById('adaptLossChart');
  const accCtx = document.getElementById('adaptAccChart');
  if (!lossCtx || !accCtx) return;

  adaptState.charts.loss = new Chart(lossCtx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Train loss', data: trainLoss, borderColor: '#0ea5e9', backgroundColor: 'rgba(14,165,233,0.15)', tension: 0.25 },
        { label: 'Val loss', data: valLoss, borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,0.15)', tension: 0.25 }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });

  adaptState.charts.acc = new Chart(accCtx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Train acc (%)', data: trainAcc, borderColor: '#16a34a', backgroundColor: 'rgba(22,163,74,0.15)', tension: 0.25 },
        { label: 'Val acc (%)', data: valAcc, borderColor: '#7c3aed', backgroundColor: 'rgba(124,58,237,0.15)', tension: 0.25 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { min: 0, max: 100 } }
    }
  });
}

/* ──────────────────────────────────────────────────────────────────
   HISTORIQUE  (localStorage)
──────────────────────────────────────────────────────────────────── */
const ADAPT_HISTORY_KEY = 'bassarcare_adapt_history';
const ADAPT_ACTIVE_JOB_KEY = 'bassarcare_active_adapt_job';

function _saveActiveAdaptJob(jobId, modelName) {
  if (!jobId) return;
  adaptState.activeJob = {
    jobId,
    modelName: modelName || 'adapted_model',
    task: adaptState.task,
    startedAt: Date.now()
  };
  try {
    localStorage.setItem(ADAPT_ACTIVE_JOB_KEY, JSON.stringify(adaptState.activeJob));
  } catch (_) {}
}

function _loadActiveAdaptJob() {
  try {
    const raw = localStorage.getItem(ADAPT_ACTIVE_JOB_KEY);
    adaptState.activeJob = raw ? JSON.parse(raw) : null;
  } catch (_) {
    adaptState.activeJob = null;
  }
  return adaptState.activeJob;
}

function _clearActiveAdaptJob(jobId) {
  const active = _loadActiveAdaptJob();
  if (jobId && active && active.jobId && active.jobId !== jobId) return;
  adaptState.activeJob = null;
  try {
    localStorage.removeItem(ADAPT_ACTIVE_JOB_KEY);
  } catch (_) {}
}

function _showAdaptationRunningUi(jobId, modelName, message) {
  const launchBtn = document.getElementById('adaptLaunchBtn');
  const cancelBtn = document.getElementById('adaptCancelBtn');
  const progSec = document.getElementById('adaptProgressSection');
  const resModule = document.getElementById('adaptResultModule');
  const resZone = document.getElementById('adaptResultZone');

  if (launchBtn) {
    launchBtn.disabled = true;
    launchBtn.innerHTML = `<span class="adapt-spinner"></span>En cours…`;
  }
  if (cancelBtn) {
    cancelBtn.style.display = 'inline-flex';
    cancelBtn.disabled = false;
    cancelBtn.textContent = 'Arreter adaptation';
  }
  if (progSec) progSec.style.display = 'block';
  if (resModule) resModule.style.display = 'none';
  if (resZone) resZone.innerHTML = '';

  _updateAdaptProgress(
    0,
    message || 'Reconnexion au job en cours...',
    jobId ? `Job: ${jobId.slice(0, 8)}${modelName ? ' · ' + modelName : ''}` : ''
  );
}

function resumeActiveAdaptationJob() {
  const active = _loadActiveAdaptJob();
  if (!active || !active.jobId) return;

  if (active.task) {
    adaptState.task = active.task;
    if (typeof selectAdaptTask === 'function') selectAdaptTask(active.task);
  }

  _showAdaptationRunningUi(active.jobId, active.modelName);
  _pollAdaptationJob(active.jobId, active.modelName || 'adapted_model');
}

function adaptLoadHistory() {
  try {
    adaptState.history = JSON.parse(localStorage.getItem(ADAPT_HISTORY_KEY) || '[]');
  } catch (_) {
    adaptState.history = [];
  }
}

function _adaptAddHistory(name, task, status, details) {
  adaptLoadHistory();
  const safeDetails = details || {};
  adaptState.history.push({
    id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    name,
    task,
    status, // 'success' | 'error' | 'running'
    model_path: safeDetails.model_path || null,
    metricHistory: safeDetails.metricHistory || null,
    error_message: safeDetails.error_message || null,
    date: new Date().toLocaleString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  });
  // Garder les 20 derniers
  if (adaptState.history.length > 20) adaptState.history.splice(0, adaptState.history.length - 20);
  try {
    localStorage.setItem(ADAPT_HISTORY_KEY, JSON.stringify(adaptState.history));
  } catch (_) {}
  adaptRenderHistory();
}

function adaptRenderHistory() {
  const container = document.getElementById('adaptHistoryList');
  if (!container) return;
  adaptLoadHistory();

  if (!adaptState.history.length) {
    container.innerHTML = `
      <div class="adapt-history-empty">
        <svg width="36" height="36" fill="none" stroke="#cbd5e0" stroke-width="1.5" viewBox="0 0 24 24">
          <polyline points="12 8 12 12 14 14"/>
          <path d="M3.05 11a9 9 0 1 0 .5-4"/>
        </svg>
        <p>Aucun entraînement lancé pour le moment</p>
      </div>`;
    return;
  }

  const items = adaptState.history.map((h, idx) => ({ ...h, _idx: idx })).reverse();
  container.innerHTML = items.map(h => {
    const badgeClass = h.status === 'success' ? 'adapt-badge-success'
                     : h.status === 'running'  ? 'adapt-badge-running'
                     : 'adapt-badge-error';
    const badgeLabel = h.status === 'success' ? '✓ Terminé'
                     : h.status === 'running'  ? '⏳ En cours'
                     : '✗ Échoué';
    const taskLabel  = h.task === 'classification' ? 'Classification' : 'Segmentation';
    const deleteBtn = h.status !== 'running'
      ? `<button class="adapt-history-delete-btn" onclick="event.stopPropagation();adaptDeleteHistoryItem(${h._idx})">Supprimer</button>`
      : '';

    return `
      <div class="adapt-history-item" onclick="adaptShowHistoryDetails(${h._idx})" role="button" tabindex="0">
        <div>
          <p class="adapt-history-name">${_escHtml(h.name)}</p>
          <p class="adapt-history-meta">${taskLabel} · ${h.date}</p>
        </div>
        <div class="adapt-history-actions">
          ${deleteBtn}
          <span class="adapt-badge ${badgeClass}">${badgeLabel}</span>
        </div>
      </div>`;
  }).join('');
}

async function adaptShowHistoryDetails(index) {
  adaptLoadHistory();
  if (index < 0 || index >= adaptState.history.length) return;

  const item = adaptState.history[index];
  if (!item) return;

  const resModule = document.getElementById('adaptResultModule');
  const resZone = document.getElementById('adaptResultZone');
  if (!resModule || !resZone) return;

  resModule.style.display = 'block';

  // Mettre à jour l'état courant (pour relancer / télécharger)
  adaptState.currentAdaptModelPath = item.model_path || null;
  adaptState.currentAdaptModelName = item.name || null;
  if (item.task) {
    adaptState.task = item.task;
    if (typeof selectAdaptTask === 'function') selectAdaptTask(item.task);
  }

  resZone.innerHTML = `
    <div class="adapt-result-success" style="background:#f0fdf4; border-color:#bbf7d0;">
      <div class="adapt-result-success-icon" style="background:#16a34a;">
        <svg width="18" height="18" fill="none" stroke="#fff" stroke-width="2.5" viewBox="0 0 24 24">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </div>
      <div>
        <h4>Détails de la tâche</h4>
        <p><strong>${_escHtml(item.name)}</strong> · ${_escHtml(item.task || '')}</p>
        ${item.model_path ? `<p style="margin-top:0.35rem; font-size:0.86rem;">
          .pth : <code>${_escHtml(item.model_path)}</code>
        </p>` : ''}
        ${item.error_message ? `<p style="margin-top:0.35rem; font-size:0.86rem; color:#b91c1c;">
          ${_escHtml(item.error_message)}
        </p>` : ''}

        <div class="adapt-action-row" style="margin-top:0.95rem;">
          <button type="button" class="adapt-btn-reset" onclick="adaptRelaunchCurrentAdaptation()">
            Relancer l'adaptation
          </button>
          ${item.model_path ? `
            <button type="button" class="adapt-btn-reset" onclick="adaptDownloadCurrentModel()">
              Télécharger model
            </button>
          ` : ''}
        </div>
      </div>
    </div>
  `;

  // Si l'historique n'est pas présent dans localStorage, on le recharge depuis le .pth
  if (!item.metricHistory && item.model_path) {
    resZone.insertAdjacentHTML('beforeend', `
      <div style="margin-top:0.9rem; font-size:0.88rem; color:#64748b;">
        Chargement des courbes depuis le modèle (.pth)...
      </div>
    `);
    try {
      const r = await fetch(`/get-model-history?path=${encodeURIComponent(item.model_path)}`);
      const data = await r.json();
      if (r.ok && data.success && data.history) {
        item.metricHistory = data.history;
        try {
          localStorage.setItem(ADAPT_HISTORY_KEY, JSON.stringify(adaptState.history));
        } catch (_) {}
      }
    } catch (_) {}
  }

  if (item.metricHistory) {
    _renderAdaptationCharts(item.metricHistory);
  } else {
    resZone.insertAdjacentHTML('beforeend', `
      <div style="margin-top:0.9rem; font-size:0.88rem; color:#64748b;">
        Pas de courbes sauvegardées pour cette tâche.
      </div>
    `);
  }
}

function adaptDownloadCurrentModel() {
  if (!adaptState.currentAdaptModelPath) {
    _adaptAlert("Aucun modèle à télécharger pour cette tâche.");
    return;
  }
  window.location.href =
    `/download-adapted-model?path=${encodeURIComponent(adaptState.currentAdaptModelPath)}`;
}

function adaptRelaunchCurrentAdaptation() {
  const nameEl = document.getElementById('adaptModelName');
  if (nameEl) nameEl.value = adaptState.currentAdaptModelName || '';

  if (adaptState.task) {
    if (typeof selectAdaptTask === 'function') selectAdaptTask(adaptState.task);
  }

  if (!adaptState.file) {
    adaptState.pendingRelaunch = true;

    const dz = document.getElementById('adaptDropZone');
    const fileInput = document.getElementById('adaptDatasetFile');
    const dropTitle = document.getElementById('adaptDropTitle');
    const resZone = document.getElementById('adaptResultZone');

    if (dropTitle) {
      dropTitle.textContent = 'Selectionnez le dataset ZIP pour relancer';
    }
    if (dz) {
      dz.style.borderColor = '#0891b2';
      dz.style.background = '#ecfeff';
      dz.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => {
        dz.style.borderColor = '';
        dz.style.background = '';
      }, 3500);
    }
    if (resZone && !document.getElementById('adaptRelaunchHint')) {
      resZone.insertAdjacentHTML('beforeend', `
        <div id="adaptRelaunchHint" style="margin-top:0.75rem;color:#0f766e;font-size:0.92rem;">
          Selectionnez le fichier ZIP du dataset. L'adaptation sera relancee automatiquement.
        </div>
      `);
    }
    if (fileInput) {
      fileInput.click();
    } else {
      _adaptAlert("Veuillez selectionner a nouveau le dataset (ZIP) pour relancer l'adaptation.");
    }
    return;
  }

  launchAdaptation();
}

function adaptDeleteHistoryItem(index) {
  adaptLoadHistory();
  if (index < 0 || index >= adaptState.history.length) return;

  const item = adaptState.history[index];
  if (!item || item.status !== 'error') return;

  adaptState.history.splice(index, 1);
  try {
    localStorage.setItem(ADAPT_HISTORY_KEY, JSON.stringify(adaptState.history));
  } catch (_) {}
  adaptRenderHistory();
}

/* ──────────────────────────────────────────────────────────────────
   UTILITAIRES
──────────────────────────────────────────────────────────────────── */
function _adaptAlert(msg) {
  // Réutilise showError si disponible, sinon alert
  if (typeof showError === 'function') {
    showError(msg);
  } else {
    alert(msg);
  }
}

function _escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ──────────────────────────────────────────────────────────────────
   INIT AU CHARGEMENT
──────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Initialiser le slider LR avec la valeur par défaut
  updateLR(10);

  const baseModelSelect = document.getElementById('adaptBaseModel');
  if (baseModelSelect) {
    baseModelSelect.addEventListener('change', () => {
      if (baseModelSelect.value) {
        resetBaseModelFile();
      }
    });
  }

  // Charger et afficher l'historique (si la vue est visible)
  const av = document.getElementById('adaptationView');
  if (av && av.style.display !== 'none') {
    adaptLoadHistory();
    adaptRenderHistory();
  }

  resumeActiveAdaptationJob();
});

window.addEventListener('pageshow', () => {
  resumeActiveAdaptationJob();
});
