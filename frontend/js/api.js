const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:54321/api/v1'
    : 'https://diagram-api-nrt3.onrender.com/api/v1';

async function generateDiagram(mode, text, diagramType) {
    const token = localStorage.getItem('token');
    
    const body = {
        text: text,
        mode: mode,
        diagram_type: diagramType,
        language: 'fa'
    };
    
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/diagram/generate`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(body)
    });
    
    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `خطای سرور (${response.status})`);
    }
    
    return await response.json();
}