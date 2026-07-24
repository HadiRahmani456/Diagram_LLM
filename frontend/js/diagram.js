let currentMermaidCode = '';

mermaid.initialize({ 
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' }
});

async function renderDiagram(mermaidCode) {
    const container = document.getElementById('diagramContainer');
    container.innerHTML = '';
    
    try {
        const { svg } = await mermaid.render('mermaid-diagram', mermaidCode);
        container.innerHTML = svg;
        currentMermaidCode = mermaidCode;
        
        // بزرگ کردن SVG
        const svgEl = container.querySelector('svg');
        if (svgEl) {
            svgEl.style.width = '100%';
            svgEl.style.height = 'auto';
            svgEl.style.minHeight = '400px';
        }
        
        document.getElementById('actions').style.display = 'flex';
    } catch (err) {
        container.innerHTML = '<p style="color: red;">خطا در رندر دیاگرام</p>';
    }
}

function resetDiagram() {
    document.getElementById('diagramContainer').innerHTML = '<p class="placeholder-text">دیاگرام شما اینجا نمایش داده می‌شود...</p>';
    currentMermaidCode = '';
    document.getElementById('actions').style.display = 'none';
    hideInfo();
}

function getDiagramSVG() {
    return document.querySelector('#diagramContainer svg');
}

function downloadSVG() {
    const svg = getDiagramSVG();
    if (!svg) return;
    const blob = new Blob([svg.outerHTML], { type: 'image/svg+xml' });
    downloadBlob(blob, 'diagram.svg');
}

async function downloadPNG() {
    const container = document.getElementById('diagramContainer');
    const svg = container?.querySelector('svg');
    if (!svg) { alert('❌ دیاگرامی وجود ندارد!'); return; }
    
    try {
        const svgClone = svg.cloneNode(true);
        svgClone.style.cssText = 'position:absolute;top:0;left:0;visibility:hidden';
        document.body.appendChild(svgClone);
        
        const bbox = svgClone.getBBox();
        const padding = 30;
        const width = bbox.width + bbox.x + padding * 2;
        const height = bbox.height + bbox.y + padding * 2;
        document.body.removeChild(svgClone);
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = width;
        canvas.height = height;
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, width, height);
        
        const svgData = new XMLSerializer().serializeToString(svg);
        const img = new Image();
        
        img.onload = function() {
            ctx.drawImage(img, padding - bbox.x, padding - bbox.y);
            const link = document.createElement('a');
            link.download = 'diagram.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        };
        
        img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
    } catch (err) {
        alert('❌ خطا در ساخت PNG');
    }
}

function copyMermaidCode() {
    if (currentMermaidCode) {
        navigator.clipboard.writeText(currentMermaidCode)
            .then(() => alert('✅ کد کپی شد!'))
            .catch(() => alert('❌ خطا'));
    }
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
function renderGanttChart(nodes) {
    const container = document.getElementById('diagramContainer');
    container.innerHTML = '<div id="gantt-container"></div>';
    
    if (typeof Gantt === 'undefined') {
        container.innerHTML = '<p style="color:orange">⚠️ گانت در حال بارگذاری...</p>';
        setTimeout(() => renderGanttChart(nodes), 500);
        return;
    }
    
    const tasks = nodes.map((node, i) => ({
        id: `t${i}`,
        name: node.label,
        start: new Date(2026, 0, i*3+1).toISOString().split('T')[0],
        end: new Date(2026, 0, i*3+3+i).toISOString().split('T')[0],
        progress: 0
    }));
    
    new Gantt("#gantt-container", tasks, {
        view_mode: 'Week',
        bar_height: 30,
        date_format: 'YYYY-MM-DD'
    });
    
    document.getElementById('actions').style.display = 'flex';
}

function renderRoadmap(nodes) {
    const container = document.getElementById('diagramContainer');
    container.innerHTML = '';
    
    // Roadmap با Mermaid timeline
    let code = "timeline\n";
    code += "    title نقشه راه\n";
    nodes.forEach(n => {
        code += `    ${n.label}\n`;
    });
    
    try {
        mermaid.render('roadmap-diagram', code).then(({svg}) => {
            container.innerHTML = svg;
            currentMermaidCode = code;
            document.getElementById('actions').style.display = 'flex';
        });
    } catch(e) {
        container.innerHTML = '<p>خطا</p>';
    }
}
function toggleFullscreen() {
    const container = document.getElementById('diagramContainer');
    if (container.requestFullscreen) {
        container.requestFullscreen();
    } else if (container.webkitRequestFullscreen) {
        container.webkitRequestFullscreen();
    }
}