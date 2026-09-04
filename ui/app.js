/**
 * Editor de Vídeo IA - PyWebView Client
 * Comunica diretamente com a API Python via pywebview.api
 */

let videoPath = null;

const selectVideoBtn = document.getElementById('select-video-btn');
const videoName = document.getElementById('video-name');
const processBtn = document.getElementById('process-btn');
const progressContainer = document.getElementById('progress-container');
const statusMessage = document.getElementById('status-message');
const videoPreview = document.getElementById('video-preview');
const trimStart = document.getElementById('trim-start');
const trimEnd = document.getElementById('trim-end');
const outputName = document.getElementById('output-name');
const noBackgroundSong = document.getElementById('no-background-song');
const noSubtitles = document.getElementById('no-subtitles');
const subtitlePosition = document.getElementById('subtitle-position');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const resultContainer = document.getElementById('result-container');
const resultBox = document.getElementById('result-box');
const resultMessage = document.getElementById('result-message');

// ============================================
// Selecionar Vídeo (via diálogo nativo)
// ============================================

selectVideoBtn.addEventListener('click', async function () {
    try {
        const result = await pywebview.api.select_video();
        if (result.success) {
            videoPath = result.path;
            videoName.textContent = '✓ ' + result.name;

            // Preview via media server local
            videoPreview.src = result.preview_url;

            processBtn.disabled = false;
        }
    } catch (e) {
        alert('Erro ao selecionar vídeo: ' + e);
    }
});

// ============================================
// Processar Vídeo
// ============================================

processBtn.addEventListener('click', async function () {
    if (!videoPath) {
        alert('Por favor, selecione um vídeo primeiro');
        return;
    }

    const outName = outputName.value.trim() || 'video_editado';
    const tStart = parseInt(trimStart.value) || 0;
    const tEnd = parseInt(trimEnd.value) || 0;
    const noAudio = noBackgroundSong.checked;
    const wantSubtitles = !noSubtitles.checked;
    const subPosition = subtitlePosition.value;

    // Desabilitar botão e mostrar progresso
    processBtn.disabled = true;
    resultContainer.style.display = 'none';
    progressContainer.style.display = 'block';
    updateProgress(5, 'Iniciando...');

    try {
        const result = await pywebview.api.process_video(videoPath, tStart, tEnd, outName, noAudio, wantSubtitles, subPosition);

        if (!result.success) {
            progressContainer.style.display = 'none';
            showResult('error', result.error);
            processBtn.disabled = false;
            return;
        }

        // Monitorar progresso
        monitorProgress();

    } catch (e) {
        progressContainer.style.display = 'none';
        showResult('error', '' + e);
        processBtn.disabled = false;
    }
});

// ============================================
// Monitorar Progresso
// ============================================

let simulatedProgress = 15;

async function monitorProgress() {
    simulatedProgress = 15;

    const check = async () => {
        try {
            const status = await pywebview.api.get_status();

            if (status.status === 'processing') {
                // Incrementar progresso suavemente
                if (simulatedProgress < 95) {
                    simulatedProgress += Math.random() * 2 + 1;
                    simulatedProgress = Math.min(simulatedProgress, 95);
                }
                updateProgress(Math.round(simulatedProgress), status.message);
                setTimeout(check, 1000);

            } else if (status.status === 'completed') {
                updateProgress(100, 'Concluído!');
                setTimeout(async () => {
                    progressContainer.style.display = 'none';
                    showResult('success', status.message || 'Vídeo salvo com sucesso!');
                    processBtn.disabled = false;

                    // Trocar o preview para mostrar o vídeo editado (resultado final)
                    try {
                        const preview = await pywebview.api.get_result_preview_url();
                        if (preview.success) {
                            videoPreview.src = preview.preview_url;
                            videoPreview.load();
                        }
                    } catch (e) {
                        console.error('Erro ao carregar preview do vídeo editado:', e);
                    }
                }, 500);

            } else if (status.status === 'error') {
                progressContainer.style.display = 'none';
                showResult('error', status.message || 'Erro desconhecido');
                processBtn.disabled = false;
            } else {
                setTimeout(check, 1000);
            }

        } catch (e) {
            console.error('Erro ao verificar status:', e);
            setTimeout(check, 2000);
        }
    };

    check();
}

// ============================================
// UI Helpers
// ============================================

function updateProgress(percentage, message) {
    percentage = Math.max(0, Math.min(100, Math.round(percentage)));
    progressFill.style.width = percentage + '%';
    progressText.textContent = percentage + '%';
    if (percentage > 10) {
        progressFill.textContent = percentage + '%';
    } else {
        progressFill.textContent = '';
    }
    if (message) {
        statusMessage.textContent = message;
    }
}

function showResult(type, message) {
    resultContainer.style.display = 'block';
    resultBox.className = 'result-box result-' + type;
    resultMessage.textContent = (type === 'success' ? '✓ ' : '✗ ') + message;
}
