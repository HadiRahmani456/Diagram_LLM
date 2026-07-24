// توابع کمکی عمومی

function showError(message) {
    const error = document.getElementById('error');
    error.textContent = '❌ ' + message;
    error.classList.add('active');
}

function hideError() {
    const error = document.getElementById('error');
    error.textContent = '';
    error.classList.remove('active');
}

function showLoading() {
    document.getElementById('loading').classList.add('active');
    document.getElementById('generateBtn').disabled = true;
}

function hideLoading() {
    document.getElementById('loading').classList.remove('active');
    document.getElementById('generateBtn').disabled = false;
}

function getInputData() {
    const text = document.getElementById('textInput').value.trim();
    const diagramType = document.getElementById('diagramType').value || null;
    return { text, diagramType };
}

function showInfo(mode, remaining) {
    const infoRow = document.getElementById('infoRow');
    infoRow.style.display = 'flex';
    
    document.getElementById('modeBadge').textContent = 
        mode === 'online' ? '☁️ آنلاین' : '💻 آفلاین';
    
    const remainingBadge = document.getElementById('remainingBadge');
    if (remaining !== null && remaining !== undefined) {
        remainingBadge.textContent = `🎯 ${remaining} درخواست باقی‌مانده`;
        remainingBadge.style.display = 'inline-block';
    } else {
        remainingBadge.style.display = 'none';
    }
}

function hideInfo() {
    document.getElementById('infoRow').style.display = 'none';
}

// نمونه‌های آماده (می‌تونیم بعداً استفاده کنیم)
const SAMPLE_TEXTS = [
    'می‌خواهم یک فروشگاه اینترنتی راه‌اندازی کنم. ابتدا تحقیق بازار، سپس طراحی سایت، بعد بازاریابی و فروش',
    'ساخت اپلیکیشن',
    'می‌خواهم یک استارتاپ راه‌اندازی کنم. اول اعتبارسنجی ایده، بعد ساخت تیم، توسعه MVP و جذب سرمایه'
];