
// =========================================================
// IDEADIAGRAM AI — DIAGRAM RENDERER
// =========================================================

let currentMermaidCode = '';
let diagramScale = 1;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let scrollStartX = 0;
let scrollStartY = 0;


// =========================================================
// MERMAID CONFIG
// =========================================================

mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    securityLevel: 'loose',

    themeVariables: {
        primaryColor: '#f1edff',
        primaryTextColor: '#242033',
        primaryBorderColor: '#7c5cff',

        lineColor: '#737b91',

        secondaryColor: '#eefaff',
        tertiaryColor: '#f7f8fc',

        fontFamily: 'Vazirmatn, Segoe UI, Tahoma, Arial',
        fontSize: '15px',

        edgeLabelBackground: '#ffffff'
    },

    flowchart: {
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'basis',
        padding: 25,
        nodeSpacing: 45,
        rankSpacing: 55
    }
});


// =========================================================
// FLOWCHART RENDER
// =========================================================

async function renderDiagram(mermaidCode) {

    const container =
        document.getElementById('diagramContainer');

    if (!container) return;

    container.innerHTML = `
        <div class="diagram-loading">
            <div class="diagram-spinner"></div>
            <span>در حال ساخت دیاگرام...</span>
        </div>
    `;

    try {

        currentMermaidCode = mermaidCode;

        // ID کاملاً یکتا برای جلوگیری از خطای Mermaid
        const renderId =
            'diagram-' +
            Date.now() +
            '-' +
            Math.random()
                .toString(36)
                .substring(2, 8);

        const result =
            await mermaid.render(
                renderId,
                mermaidCode
            );

        container.innerHTML = `
            <div class="diagram-canvas" id="diagramCanvas">
                ${result.svg}
            </div>

            <div class="diagram-zoom">
                <button type="button"
                        onclick="zoomDiagram(0.1)"
                        title="بزرگ‌نمایی">
                    +
                </button>

                <span id="zoomValue">100%</span>

                <button type="button"
                        onclick="zoomDiagram(-0.1)"
                        title="کوچک‌نمایی">
                    −
                </button>

                <button type="button"
                        onclick="resetZoom()"
                        title="بازنشانی">
                    ↺
                </button>
            </div>
        `;

        const svg =
            container.querySelector('svg');

        if (svg) {

            svg.removeAttribute('width');
            svg.removeAttribute('height');

            svg.style.width = 'auto';
            svg.style.height = 'auto';

            svg.style.maxWidth = '100%';

            svg.style.display = 'block';

            svg.style.margin = '0 auto';
        }

        diagramScale = 1;

        setupDiagramInteraction();

        document.getElementById('actions').style.display =
            'grid';

        updateZoomLabel();

    } catch (error) {

        console.error('Mermaid render error:', error);

        container.innerHTML = `
            <div class="diagram-error">
                <div class="error-icon">⚠️</div>

                <strong>
                    خطا در ساخت دیاگرام
                </strong>

                <span>
                    ساختار دریافت‌شده قابل نمایش نیست.
                </span>

                <button type="button"
                        onclick="resetDiagram()">
                    تلاش مجدد
                </button>
            </div>
        `;
    }
}


// =========================================================
// ZOOM
// =========================================================

function zoomDiagram(amount) {

    diagramScale += amount;

    diagramScale =
        Math.max(
            0.5,
            Math.min(2.5, diagramScale)
        );

    applyDiagramScale();
}


function applyDiagramScale() {

    const canvas =
        document.getElementById('diagramCanvas');

    if (!canvas) return;

    canvas.style.transform =
        `scale(${diagramScale})`;

    canvas.style.transformOrigin =
        'center center';

    updateZoomLabel();
}


function updateZoomLabel() {

    const label =
        document.getElementById('zoomValue');

    if (!label) return;

    label.textContent =
        Math.round(diagramScale * 100) + '%';
}


function resetZoom() {

    diagramScale = 1;

    applyDiagramScale();
}


// =========================================================
// MOUSE / WHEEL INTERACTION
// =========================================================

function setupDiagramInteraction() {

    const container =
        document.getElementById('diagramContainer');

    if (!container) return;

    container.addEventListener(
        'wheel',
        handleDiagramWheel,
        {
            passive: false
        }
    );

    container.addEventListener(
        'mousedown',
        startDiagramDrag
    );

    container.addEventListener(
        'mousemove',
        moveDiagramDrag
    );

    container.addEventListener(
        'mouseup',
        stopDiagramDrag
    );

    container.addEventListener(
        'mouseleave',
        stopDiagramDrag
    );
}


function handleDiagramWheel(event) {

    if (!event.ctrlKey) return;

    event.preventDefault();

    zoomDiagram(
        event.deltaY < 0
            ? 0.1
            : -0.1
    );
}


function startDiagramDrag(event) {

    if (event.button !== 0) return;

    const container =
        document.getElementById('diagramContainer');

    if (!container) return;

    isDragging = true;

    container.classList.add('dragging');

    dragStartX = event.clientX;
    dragStartY = event.clientY;

    scrollStartX = container.scrollLeft;
    scrollStartY = container.scrollTop;
}


function moveDiagramDrag(event) {

    if (!isDragging) return;

    const container =
        document.getElementById('diagramContainer');

    if (!container) return;

    const dx =
        event.clientX - dragStartX;

    const dy =
        event.clientY - dragStartY;

    container.scrollLeft =
        scrollStartX - dx;

    container.scrollTop =
        scrollStartY - dy;
}


function stopDiagramDrag() {

    if (!isDragging) return;

    isDragging = false;

    const container =
        document.getElementById('diagramContainer');

    if (container) {
        container.classList.remove('dragging');
    }
}


// =========================================================
// RESET
// =========================================================

function resetDiagram() {

    const container =
        document.getElementById('diagramContainer');

    if (!container) return;

    container.innerHTML = `
        <div class="empty-state">

            <div class="empty-visual">

                <div class="empty-node node-one">
                    <span></span>
                </div>

                <div class="empty-line line-one"></div>

                <div class="empty-node node-two">
                    <span></span>
                </div>

                <div class="empty-line line-two"></div>

                <div class="empty-node node-three">
                    <span></span>
                </div>

            </div>

            <h3>
                دیاگرام اینجا ساخته می‌شود
            </h3>

            <p>
                متن خود را وارد کنید و روی
                <strong>«تولید دیاگرام»</strong>
                بزنید.
            </p>

        </div>
    `;

    currentMermaidCode = '';

    diagramScale = 1;

    document.getElementById('actions').style.display =
        'none';

    hideInfo();
}


// =========================================================
// SVG
// =========================================================

function getDiagramSVG() {

    return document.querySelector(
        '#diagramContainer svg'
    );
}


function downloadSVG() {

    const svg = getDiagramSVG();

    if (!svg) {

        alert('❌ دیاگرامی وجود ندارد!');

        return;
    }

    const svgClone =
        svg.cloneNode(true);

    svgClone.setAttribute(
        'xmlns',
        'http://www.w3.org/2000/svg'
    );

    const blob =
        new Blob(
            [svgClone.outerHTML],
            {
                type: 'image/svg+xml;charset=utf-8'
            }
        );

    downloadBlob(
        blob,
        'ideadiagram.svg'
    );
}


// =========================================================
// PNG
// =========================================================

async function downloadPNG() {

    const svg =
        getDiagramSVG();

    if (!svg) {

        alert('❌ دیاگرامی وجود ندارد!');

        return;
    }

    try {

        const svgClone =
            svg.cloneNode(true);

        svgClone.setAttribute(
            'xmlns',
            'http://www.w3.org/2000/svg'
        );

        const rect =
            svg.getBoundingClientRect();

        const width =
            Math.max(
                800,
                Math.ceil(rect.width)
            );

        const height =
            Math.max(
                500,
                Math.ceil(rect.height)
            );

        svgClone.setAttribute(
            'width',
            width
        );

        svgClone.setAttribute(
            'height',
            height
        );

        const svgData =
            new XMLSerializer()
                .serializeToString(svgClone);

        const blob =
            new Blob(
                [svgData],
                {
                    type: 'image/svg+xml;charset=utf-8'
                }
            );

        const url =
            URL.createObjectURL(blob);

        const image =
            new Image();

        image.onload = function () {

            const scale = 2;

            const canvas =
                document.createElement('canvas');

            canvas.width =
                width * scale;

            canvas.height =
                height * scale;

            const ctx =
                canvas.getContext('2d');

            ctx.fillStyle =
                '#ffffff';

            ctx.fillRect(
                0,
                0,
                canvas.width,
                canvas.height
            );

            ctx.scale(
                scale,
                scale
            );

            ctx.drawImage(
                image,
                0,
                0,
                width,
                height
            );

            URL.revokeObjectURL(url);

            canvas.toBlob(
                function (pngBlob) {

                    downloadBlob(
                        pngBlob,
                        'ideadiagram.png'
                    );

                },
                'image/png'
            );
        };

        image.onerror = function () {

            URL.revokeObjectURL(url);

            alert(
                '❌ خطا در ساخت تصویر PNG'
            );
        };

        image.src = url;

    } catch (error) {

        console.error(error);

        alert(
            '❌ خطا در ساخت PNG'
        );
    }
}


// =========================================================
// COPY MERMAID
// =========================================================

function copyMermaidCode() {

    if (!currentMermaidCode) {

        alert(
            '❌ کد دیاگرامی وجود ندارد!'
        );

        return;
    }

    navigator.clipboard
        .writeText(currentMermaidCode)
        .then(() => {

            alert(
                '✅ کد Mermaid کپی شد!'
            );

        })
        .catch(() => {

            alert(
                '❌ امکان کپی وجود ندارد'
            );
        });
}


// =========================================================
// DOWNLOAD HELPER
// =========================================================

function downloadBlob(blob, filename) {

    if (!blob) return;

    const url =
        URL.createObjectURL(blob);

    const link =
        document.createElement('a');

    link.href = url;

    link.download = filename;

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    setTimeout(
        () => URL.revokeObjectURL(url),
        1000
    );
}


// =========================================================
// GANTT
// =========================================================

function renderGanttChart(nodes) {

    const container =
        document.getElementById(
            'diagramContainer'
        );

    if (!container) return;

    container.innerHTML = `
        <div id="gantt-container"></div>
    `;

    if (typeof Gantt === 'undefined') {

        container.innerHTML = `
            <div class="diagram-loading">
                <div class="diagram-spinner"></div>
                <span>
                    در حال بارگذاری Gantt...
                </span>
            </div>
        `;

        setTimeout(
            () => renderGanttChart(nodes),
            500
        );

        return;
    }

    const tasks =
        nodes.map(
            (node, index) => ({

                id: `task-${index}`,

                name:
                    node.label ||
                    `مرحله ${index + 1}`,

                start:
                    new Date(
                        2026,
                        0,
                        index * 3 + 1
                    )
                    .toISOString()
                    .split('T')[0],

                end:
                    new Date(
                        2026,
                        0,
                        index * 3 + 3 + index
                    )
                    .toISOString()
                    .split('T')[0],

                progress: 0
            })
        );

    new Gantt(
        '#gantt-container',
        tasks,
        {
            view_mode: 'Week',

            bar_height: 34,

            padding: 18,

            date_format: 'YYYY-MM-DD',

            language: 'en'
        }
    );

    document.getElementById('actions').style.display =
        'grid';
}


// =========================================================
// ROADMAP
// =========================================================

async function renderRoadmap(nodes) {

    const container =
        document.getElementById(
            'diagramContainer'
        );

    if (!container) return;

    container.innerHTML = `
        <div class="diagram-loading">
            <div class="diagram-spinner"></div>
            <span>
                در حال ساخت Roadmap...
            </span>
        </div>
    `;

    let code =
        'timeline\n';

    code +=
        '    title نقشه راه\n';

    nodes.forEach(
        (node, index) => {

            code +=
                `    ${index + 1} : ${node.label}\n`;
        }
    );

    try {

        const renderId =
            'roadmap-' +
            Date.now();

        const { svg } =
            await mermaid.render(
                renderId,
                code
            );

        container.innerHTML =
            `<div class="diagram-canvas">
                ${svg}
            </div>`;

        currentMermaidCode =
            code;

        document.getElementById(
            'actions'
        ).style.display =
            'grid';

    } catch (error) {

        console.error(error);

        container.innerHTML = `
            <div class="diagram-error">
                ⚠️ خطا در ساخت Roadmap
            </div>
        `;
    }
}


// =========================================================
// FULLSCREEN
// =========================================================

function toggleFullscreen() {

    const container =
        document.getElementById(
            'diagramContainer'
        );

    if (!container) return;

    if (!document.fullscreenElement) {

        if (container.requestFullscreen) {

            container.requestFullscreen();

        } else if (
            container.webkitRequestFullscreen
        ) {

            container.webkitRequestFullscreen();
        }

    } else {

        if (document.exitFullscreen) {

            document.exitFullscreen();
        }
    }
}

