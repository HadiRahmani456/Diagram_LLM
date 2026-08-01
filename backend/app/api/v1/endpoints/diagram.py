from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.services.ai_service import AIService, AIMode, DiagramType
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()
ai_service = AIService()

class DiagramRequest(BaseModel):
    text: str
    mode: AIMode = AIMode.ONLINE
    diagram_type: Optional[DiagramType] = None
    language: str = "fa"

class DiagramResponse(BaseModel):
    success: bool
    mode: str
    diagram_type: str
    nodes: list
    edges: list
    mermaid_code: Optional[str] = None
    remaining_requests: Optional[int] = None

@router.post("/generate", response_model=DiagramResponse)
async def generate_diagram(
    request: DiagramRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()
    if current_user.last_request_date is None or current_user.last_request_date.date() != today:
        current_user.requests_today = 0
        current_user.last_request_date = datetime.now()
    
    if not current_user.is_admin and current_user.requests_today >= current_user.daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"محدودیت روزانه شما ({current_user.daily_limit} دیاگرام) به پایان رسیده."
        )
    
    try:
        result = await ai_service.analyze_text(
            text=request.text,
            mode=request.mode,
            diagram_type=request.diagram_type
        )
        
            # فقط اگه از Groq استفاده بشه محدودیت کم بشه
        if result.get("source") == "groq":
            current_user.requests_today += 1
            db.commit()
        
        remaining = None if current_user.is_admin else (current_user.daily_limit - current_user.requests_today)
        
        mermaid_code = generate_mermaid_code(
            nodes=result.get("nodes", []),
            edges=result.get("edges", []),
            diagram_type=request.diagram_type.value if request.diagram_type else "flowchart"
        )
        
        # تبدیل SVG به PNG
        png_base64 = None
        if mermaid_code:
            # اول باید SVG رو از Mermaid بسازیم
            # ولی اینجا فقط mermaid_code داریم، SVG توی فرانت ساخته میشه
            # پس png_base64 رو None می‌ذاریم یا از فرانت می‌گیریم
            pass
        
        return DiagramResponse(
            success=True,
            mode=request.mode,
            diagram_type=result.get("suggested_type", "flowchart"),
            nodes=result.get("nodes", []),
            edges=result.get("edges", []),
            mermaid_code=mermaid_code,
            remaining_requests=remaining,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_mermaid_code(nodes: list, edges: list, diagram_type: str) -> str:
    if not nodes:
        return "graph TD\n    A[No data]"
    
    for node in nodes:
        node["label"] = str(node.get("label", "")).replace('"', "'")[:60]
    
    if diagram_type == "roadmap":
        code = "timeline\n"
        code += "    title نقشه راه\n"
        for node in nodes:
            label = node["label"].replace(":", " ").replace(",", " ")
            code += f"    {label}\n"
        return code
    
    elif diagram_type == "gantt_chart":
        code = "gantt\n"
        code += "    title زمان‌بندی پروژه\n"
        code += "    dateFormat YYYY-MM-DD\n"
        code += "    section مراحل\n"
        from datetime import date, timedelta
        today = date.today()
        for i, node in enumerate(nodes, 1):
            label = node["label"].replace(":", " ").replace(",", " ")
            start = today + timedelta(days=i*3)
            code += f"    {label} :a{i}, {start.isoformat()}, {i+2}d\n"
        return code
    
    else:
        colors = ["#f09433", "#667eea", "#4CAF50", "#ff6b6b", "#4ecdc4", "#9b59b6"]
        code = "graph TD\n"
        for i, node in enumerate(nodes):
            color = colors[i % len(colors)]
            code += f'    {node["id"]}["{node["label"]}"]\n'
            code += f'    style {node["id"]} fill:{color},stroke:#333,stroke-width:2px,color:white\n'
        for i in range(1, len(nodes)):
            code += f'    {nodes[i-1]["id"]} -->|↓| {nodes[i]["id"]}\n'
        return code