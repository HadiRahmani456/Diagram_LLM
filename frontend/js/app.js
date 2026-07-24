let currentMode = 'online';

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            currentMode = this.dataset.mode;
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    document.getElementById('generateBtn').addEventListener('click', handleGenerate);
    document.getElementById('downloadSvgBtn').addEventListener('click', downloadSVG);
    document.getElementById('downloadPngBtn').addEventListener('click', downloadPNG);
    document.getElementById('copyCodeBtn').addEventListener('click', copyMermaidCode);
    document.getElementById('fullscreenBtn').addEventListener('click', toggleFullscreen);
});

function updateModeButtons() {
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === currentMode);
    });
}

async function handleGenerate() {
    const { text, diagramType } = getInputData();
    if (!text) { showError('لطفاً یک متن وارد کنید!'); return; }
    
    hideError();
    resetDiagram();
    showLoading();
    
    try {
        const data = await generateDiagram(currentMode, text, diagramType);
        if (data.mermaid_code) {
            await renderDiagram(data.mermaid_code);
        }
        showInfo(data.mode, data.remaining_requests);
    } catch (err) {
        showError(err.message);
        resetDiagram();
    } finally {
        hideLoading();
    }
}