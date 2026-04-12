/**
 * Editor de Vídeo IA - JavaScript Client
 * Gerencia interações do usuário, uploads e monitoramento de processamento
 */

// Estado da aplicação
let appState = {
    videoPath: null,
    videoFile: null,
    isProcessing: false,
    logoPath: null,  // Caminhos padrão configurados no servidor
    audioPath: null
};

const videoInput = document.getElementById('video-input');
const videoName = document.getElementById('video-name');
const processBtn = document.getElementById('process-btn');
const progressContainer = document.getElementById('progress-container');
const statusMessage = document.getElementById('status-message');
const successSection = document.getElementById('success-section');
const successMessage = document.getElementById('success-message');
const videoPreview = document.getElementById('video-preview');
const trimStart = document.getElementById('trim-start');
const trimEnd = document.getElementById('trim-end');
const outputName = document.getElementById('output-name');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');

// ============================================
// Event Listeners
// ============================================

videoInput.addEventListener('change', handleVideoSelect);
processBtn.addEventListener('click', handleProcessClick);

// ============================================
// Upload Handlers
// ============================================

async function handleVideoSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    appState.videoFile = file;
    videoName.textContent = `✓ ${file.name}`;
    
    // Criar preview do vídeo
    const reader = new FileReader();
    reader.onload = (e) => {
        videoPreview.src = e.target.result;
    };
    reader.readAsDataURL(file);

    // Upload para o servidor
    await uploadFile(file, 'video', 'videoPath');
}

async function uploadFile(file, fieldName, stateKey) {
    try {
        // Preparar FormData
        const formData = new FormData();
        formData.append(fieldName, file);

        // Endpoint baseado no tipo de arquivo
        let endpoint = '/api/upload';
        if (fieldName === 'logo') {
            endpoint = '/api/select-logo';
        }

        // Enviar arquivo
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            showError(`Erro no upload: ${error.error}`);
            return;
        }

        const data = await response.json();
        appState[stateKey] = data.path;
        
        console.log(`✓ ${fieldName} salvo:`, data.path);

    } catch (error) {
        showError(`Erro ao fazer upload: ${error.message}`);
    }
}

// ============================================
// Process Handler
// ============================================

async function handleProcessClick() {
    // Validar inputs
    if (!appState.videoPath) {
        showError('Por favor, selecione um vídeo principal');
        return;
    }

    const outputFileName = outputName.value.trim();
    if (!outputFileName) {
        showError('Por favor, defina um nome para o arquivo de saída');
        return;
    }

    // Desabilitar botão
    appState.isProcessing = true;
    processBtn.disabled = true;
    
    // Mostrar progress bar
    progressContainer.style.display = 'block';
    successSection.style.display = 'none';
    updateProgress(0);

    try {
        // Dados para enviar
        const processingData = {
            video_path: appState.videoPath,
            trim_start: parseInt(trimStart.value) || 0,
            trim_end: parseInt(trimEnd.value) || 0,
            output_name: outputFileName
        };

        // Enviar requisição de processamento
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(processingData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erro ao processar vídeo');
        }

        const result = await response.json();
        console.log('✓ Processamento iniciado:', result);

        // Monitorar progresso
        monitorProgress(outputFileName);

    } catch (error) {
        showError(`Erro: ${error.message}`);
        progressContainer.style.display = 'none';
        appState.isProcessing = false;
        processBtn.disabled = false;
    }
}

// ============================================
// Status Monitoring
// ============================================

async function monitorProgress(outputFileName) {
    const maxAttempts = 1200; // 20 minutos com polling de 1s
    let attempts = 0;
    let simulatedProgress = 15;

    const checkStatus = async () => {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();

            if (status.status === 'processing') {
                // Mostrar mensagem realista durante processamento
                console.log('Status:', status);
                statusMessage.textContent = status.message || 'Codificando vídeo... (pode levar vários minutos)';
                
                // Incrementar progresso suavemente (15% -> 95%)
                if (simulatedProgress < 95) {
                    // Incremento aleatório pequeno (1-3%)
                    simulatedProgress += Math.random() * 2 + 1;
                    simulatedProgress = Math.min(simulatedProgress, 95);
                }
                
                updateProgress(Math.round(simulatedProgress));
                
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 1000);
                } else {
                    showError('Processamento excedeu tempo limite (20 minutos). Verifique o tamanho do vídeo.');
                    progressContainer.style.display = 'none';
                    appState.isProcessing = false;
                    processBtn.disabled = false;
                }
            } else if (status.status === 'completed') {
                progressContainer.style.display = 'none';
                successSection.style.display = 'block';
                
                // Mostrar mensagem de sucesso com caminho
                successMessage.textContent = status.message || 'Seu vídeo foi salvo em ~/Desktop/videos_formatados/';
                
                appState.isProcessing = false;
                processBtn.disabled = false;
            } else if (status.status === 'error') {
                progressContainer.style.display = 'none';
                showError(status.message || 'Erro desconhecido durante processamento');
                appState.isProcessing = false;
                processBtn.disabled = false;
            } else {
                // idle or unknown status
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 1000);
                }
            }

        } catch (error) {
            console.error('Erro ao verificar status:', error);
            // Continuar tentando se houver erro de conexão
            attempts++;
            if (attempts < 10) {
                setTimeout(checkStatus, 2000);
            } else {
                showError(`Erro de conexão persistente: ${error.message}`);
                progressContainer.style.display = 'none';
                appState.isProcessing = false;
                processBtn.disabled = false;
            }
        }
    };

    // Iniciar monitoramento
    checkStatus();
}

// ============================================
// UI Helpers
// ============================================

function updateProgress(percentage) {
    // Garantir que está entre 0 e 100
    percentage = Math.max(0, Math.min(100, Math.round(percentage)));
    
    // Atualizar barra visual
    progressFill.style.width = percentage + '%';
    
    // Atualizar texto com número limpo (sem decimais)
    progressText.textContent = percentage + '%';
    
    // Mostrar número na barra se espaço
    if (percentage > 10) {
        progressFill.textContent = percentage + '%';
    } else {
        progressFill.textContent = '';
    }
}

function showError(message) {
    alert('❌ ' + message);
    console.error(message);
}

// ============================================
// Inicialização
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('✓ Editor de Vídeo IA carregado');
    
    // Definir valor padrão animado
    outputName.placeholder = 'video_editado.mp4';
});

// Prevenir comportamentos padrão para drag-and-drop (opcional, para implementar depois)
document.addEventListener('dragover', (e) => {
    e.preventDefault();
}, false);

document.addEventListener('drop', (e) => {
    e.preventDefault();
}, false);
