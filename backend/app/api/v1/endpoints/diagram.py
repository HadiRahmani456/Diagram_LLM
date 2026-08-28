
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from app.services.ai_service import AIService, AIMode, DiagramType
from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User


router = APIRouter()
ai_service = AIService()


# =========================================================
# REQUEST / RESPONSE
# =========================================================

class DiagramRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=5000)
    mode: AIMode = AIMode.ONLINE
    diagram_type: Optional[DiagramType] = None
    language: str = "fa"


class DiagramResponse(BaseModel):
    success: bool
    mode: str
    engine: str
    diagram_type: str
    nodes: list
    edges: list
    mermaid_code: Optional[str] = None
    remaining_requests: Optional[int] = None


# =========================================================
# GENERATE DIAGRAM
# =========================================================

@router.post("/generate", response_model=DiagramResponse)
async def generate_diagram(
    request: DiagramRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()

    if (
        current_user.last_request_date is None
        or current_user.last_request_date.date() != today
    ):
        current_user.requests_today = 0
        current_user.last_request_date = datetime.now()

    # فقط Groq سهمیه روزانه را مصرف می‌کند
    if (
        request.mode == AIMode.ONLINE
        and not current_user.is_admin
        and current_user.requests_today >= current_user.daily_limit
    ):
        raise HTTPException(
            status_code=429,
            detail=(
                f"محدودیت روزانه شما "
                f"({current_user.daily_limit} دیاگرام) "
                "به پایان رسیده. برای ادامه از Colab یا Local استفاده کنید."
            )
        )

    try:

        result = await ai_service.analyze_text(
            text=request.text,
            mode=request.mode,
            diagram_type=request.diagram_type
        )

        # مصرف سهمیه فقط برای Groq
        if result.get("source") == "groq":
            current_user.requests_today += 1
            db.commit()

        remaining = (
            None
            if current_user.is_admin
            else max(
                0,
                current_user.daily_limit -
                current_user.requests_today
            )
        )

        diagram_type = (
            result.get("suggested_type")
            or (
                request.diagram_type.value
                if request.diagram_type
                else "flowchart"
            )
        )

        nodes = normalize_nodes(
            result.get("nodes", [])
        )

        edges = normalize_edges(
            result.get("edges", []),
            nodes
        )

        mermaid_code = generate_mermaid_code(
            nodes=nodes,
            edges=edges,
            diagram_type=diagram_type
        )

        return DiagramResponse(
            success=True,
            mode=request.mode.value,
            engine=result.get(
                "source",
                request.mode.value
            ),
            diagram_type=diagram_type,
            nodes=nodes,
            edges=edges,
            mermaid_code=mermaid_code,
            remaining_requests=remaining
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except RuntimeError as e:

        raise HTTPException(
            status_code=503,
            detail=str(e)
        )

    except Exception as e:

        print(
            f"❌ Diagram generation error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="خطایی هنگام تولید دیاگرام رخ داد."
        )


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_nodes(nodes: list) -> list:
    """
    داده‌های خروجی AI را یکدست می‌کند.
    """

    normalized = []

    for index, node in enumerate(nodes):

        if not isinstance(node, dict):
            continue

        node_id = str(
            node.get("id")
            or f"n{index + 1}"
        )

        label = str(
            node.get("label")
            or node.get("name")
            or f"مرحله {index + 1}"
        ).strip()

        node_type = normalize_node_type(
            node.get("type", "process")
        )

        normalized.append({
            "id": sanitize_id(node_id),
            "label": label,
            "type": node_type
        })

    # اگر AI هیچ Start نساخته باشد،
    # اولین Node را شروع می‌کنیم.
    if normalized:

        has_start = any(
            n["type"] == "start"
            for n in normalized
        )

        has_end = any(
            n["type"] == "end"
            for n in normalized
        )

        if not has_start:
            normalized[0]["type"] = "start"

        if len(normalized) > 1 and not has_end:
            normalized[-1]["type"] = "end"

    return normalized


def normalize_node_type(value) -> str:

    value = str(
        value or "process"
    ).lower().strip()

    mapping = {

        "start": "start",
        "begin": "start",
        "beginning": "start",

        "end": "end",
        "finish": "end",
        "stop": "end",

        "decision": "decision",
        "condition": "decision",
        "if": "decision",

        "input": "input",
        "output": "output",
        "io": "input_output",
        "input_output": "input_output",

        "process": "process",
        "action": "process",
        "task": "process",
        "step": "process"
    }

    return mapping.get(
        value,
        "process"
    )


def normalize_edges(
    edges: list,
    nodes: list
) -> list:

    valid_ids = {
        node["id"]
        for node in nodes
    }

    normalized = []

    for edge in edges:

        if not isinstance(edge, dict):
            continue

        source = (
            edge.get("from")
            or edge.get("source")
        )

        target = (
            edge.get("to")
            or edge.get("target")
        )

        if not source or not target:
            continue

        source = sanitize_id(
            str(source)
        )

        target = sanitize_id(
            str(target)
        )

        if (
            source not in valid_ids
            or target not in valid_ids
        ):
            continue

        label = str(
            edge.get("label") or ""
        ).strip()

        normalized.append({
            "from": source,
            "to": target,
            "label": label
        })

    return normalized


# =========================================================
# MERMAID HELPERS
# =========================================================

def sanitize_id(value: str) -> str:

    value = str(value or "")

    result = ""

    for char in value:

        if (
            char.isalnum()
            or char == "_"
        ):
            result += char

    if not result:
        result = "node"

    if result[0].isdigit():
        result = "n_" + result

    return result


def _safe_label(
    value: str,
    max_length: int = 80
) -> str:

    value = str(
        value or ""
    )

    value = (
        value
        .replace('"', "'")
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )

    return value[:max_length]


# =========================================================
# MERMAID GENERATOR
# =========================================================

def generate_mermaid_code(
    nodes: list,
    edges: list,
    diagram_type: str
) -> str:

    if not nodes:

        return (
            "flowchart TD\n"
            "    A[داده‌ای برای نمایش وجود ندارد]"
        )

    # =====================================================
    # ROADMAP
    # =====================================================

    if diagram_type == "roadmap":

        code = (
            "timeline\n"
            "    title نقشه راه پروژه\n"
        )

        for index, node in enumerate(
            nodes,
            1
        ):

            label = _safe_label(
                node.get(
                    "label",
                    f"مرحله {index}"
                ),
                90
            )

            label = (
                label
                .replace(":", " - ")
            )

            code += (
                f"    مرحله {index} : "
                f"{label}\n"
            )

        return code

    # =====================================================
    # GANTT
    # =====================================================

    if diagram_type == "gantt_chart":

        code = (
            "gantt\n"
            "    title زمان‌بندی پروژه\n"
            "    dateFormat YYYY-MM-DD\n"
            "    axisFormat %d %b\n"
            "    section مراحل\n"
        )

        today = date.today()

        for index, node in enumerate(
            nodes,
            1
        ):

            label = _safe_label(
                node.get(
                    "label",
                    f"وظیفه {index}"
                ),
                70
            )

            label = (
                label
                .replace(":", " - ")
            )

            start = (
                today +
                timedelta(
                    days=(index - 1) * 3
                )
            )

            duration = index + 2

            code += (
                f"    {label} "
                f":task{index}, "
                f"{start.isoformat()}, "
                f"{duration}d\n"
            )

        return code

    # =====================================================
    # FLOWCHART
    # =====================================================

    code = (
        "flowchart TD\n"
        "    %% IdeaDiagram AI Flowchart\n"
    )

    # -----------------------------------------------------
    # NODES
    # -----------------------------------------------------

    for node in nodes:

        node_id = sanitize_id(
            node.get("id", "node")
        )

        label = _safe_label(
            node.get(
                "label",
                "مرحله"
            ),
            90
        )

        node_type = node.get(
            "type",
            "process"
        )

        # Start
        if node_type == "start":

            code += (
                f'    {node_id}(["{label}"])\n'
            )

        # End
        elif node_type == "end":

            code += (
                f'    {node_id}(["{label}"])\n'
            )

        # Decision
        elif node_type == "decision":

            code += (
                f'    {node_id}{{"{label}"}}\n'
            )

        # Input / Output
        elif node_type in {
            "input",
            "output",
            "input_output"
        }:

            code += (
                f'    {node_id}[/"{label}"/]\n'
            )

        # Process
        else:

            code += (
                f'    {node_id}["{label}"]\n'
            )

    # -----------------------------------------------------
    # EDGES
    # -----------------------------------------------------

    for edge in edges:

        source = sanitize_id(
            edge.get("from", "")
        )

        target = sanitize_id(
            edge.get("to", "")
        )

        if not source or not target:
            continue

        label = _safe_label(
            edge.get("label", ""),
            30
        )

        # استانداردسازی برچسب تصمیم
        label_lower = label.lower()

        if label_lower in {
            "yes",
            "true",
            "بله",
            "درست"
        }:
            label = "بله"

        elif label_lower in {
            "no",
            "false",
            "خیر",
            "غلط"
        }:
            label = "خیر"

        if label:

            code += (
                f"    {source} "
                f"--> |{label}| "
                f"{target}\n"
            )

        else:

            code += (
                f"    {source} "
                f"--> "
                f"{target}\n"
            )

    # -----------------------------------------------------
    # STYLES
    # -----------------------------------------------------

    code += "\n"

    code += (
        "    classDef startEnd "
        "fill:#ede9fe,"
        "stroke:#7c3aed,"
        "color:#312e81,"
        "stroke-width:2px;\n"
    )

    code += (
        "    classDef process "
        "fill:#eff6ff,"
        "stroke:#3b82f6,"
        "color:#172554,"
        "stroke-width:1.5px;\n"
    )

    code += (
        "    classDef decision "
        "fill:#fffbeb,"
        "stroke:#f59e0b,"
        "color:#78350f,"
        "stroke-width:2px;\n"
    )

    code += (
        "    classDef io "
        "fill:#ecfeff,"
        "stroke:#06b6d4,"
        "color:#164e63,"
        "stroke-width:1.5px;\n"
    )

    # -----------------------------------------------------
    # APPLY CLASSES
    # -----------------------------------------------------

    start_end = [
        n["id"]
        for n in nodes
        if n["type"] in {
            "start",
            "end"
        }
    ]

    decisions = [
        n["id"]
        for n in nodes
        if n["type"] == "decision"
    ]

    io_nodes = [
        n["id"]
        for n in nodes
        if n["type"] in {
            "input",
            "output",
            "input_output"
        }
    ]

    processes = [
        n["id"]
        for n in nodes
        if n["type"] == "process"
    ]

    if start_end:

        code += (
            "    class "
            + ",".join(start_end)
            + " startEnd;\n"
        )

    if processes:

        code += (
            "    class "
            + ",".join(processes)
            + " process;\n"
        )

    if decisions:

        code += (
            "    class "
            + ",".join(decisions)
            + " decision;\n"
        )

    if io_nodes:

        code += (
            "    class "
            + ",".join(io_nodes)
            + " io;\n"
        )

    return code

