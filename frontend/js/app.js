let currentMode = 'online';

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.engine-card:not(.disabled)').forEach(card => {
        card.addEventListener('click', function() {
            currentMode = this.dataset.mode;

            document.querySelectorAll('.engine-card').forEach(c => c.classList.remove('active'));
            this.classList.add('active');

            const descriptions = {
                online: 'Groq برای تولید سریع و هوشمند دیاگرام انتخاب شده است.',
                colab: 'Colab بدون مصرف سهمیه Groq، دیاگرام را از مدل مستقر روی Colab تولید می‌کند.',
                local: 'Local بدون API و بدون اینترنت، ساختار متن را روی سرور خود پروژه تحلیل می‌کند.'
            };

            const description = document.getElementById('engineDescription');
            if (description) description.textContent = descriptions[currentMode] || '';
        });
    });

    document.getElementById('generateBtn').addEventListener('click', handleGenerate);
    document.getElementById('downloadSvgBtn').addEventListener('click', downloadSVG);
    document.getElementById('downloadPngBtn').addEventListener('click', downloadPNG);
    document.getElementById('copyCodeBtn').addEventListener('click', copyMermaidCode);
    document.getElementById('fullscreenBtn').addEventListener('click', toggleFullscreen);
});

async function handleGenerate() {
    const { text, diagramType } = getInputData();
    if (!text) {
        showError('لطفاً یک متن وارد کنید!');
        return;
    }

    hideError();
    resetDiagram();
    showLoading();
    setOutputStatus('در حال تحلیل و ساخت دیاگرام...', true);

    try {
        const data = await generateDiagram(currentMode, text, diagramType);

        if (!data.mermaid_code) {
            throw new Error('کد دیاگرام از سرور دریافت نشد.');
        }

        await renderDiagram(data.mermaid_code);
        showInfo(data.engine || data.mode, data.remaining_requests);
        updateEngineMeta(data.engine || data.mode);
        setOutputStatus('دیاگرام با موفقیت ساخته شد', true);
    } catch (err) {
        showError(err.message);
        setOutputStatus('تولید دیاگرام ناموفق بود', false);
        resetDiagram();
    } finally {
        hideLoading();
    }
}

function updateEngineMeta(engine) {
    const names = {
        groq: 'Groq AI',
        colab: 'Colab AI',
        local: 'Local Engine',
        online: 'Groq AI'
    };

    const element = document.getElementById('outputEngine');
    if (element) element.textContent = names[engine] || engine;
}
