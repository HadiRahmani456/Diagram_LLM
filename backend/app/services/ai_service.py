from typing import Dict, List, Optional
from enum import Enum
from openai import AsyncOpenAI
import aiohttp
import json
import re
from app.core.config import settings


class AIMode(str, Enum):
    ONLINE = "online"      # Groq
    COLAB = "colab"        # Google Colab
    LOCAL = "local"        # Local heuristic engine


class DiagramType(str, Enum):
    FLOWCHART = "flowchart"
    ROADMAP = "roadmap"
    GANTT_CHART = "gantt_chart"


class AIService:
    """Diagram generation service with three independent engines.

    online -> Groq
    colab  -> user's Colab endpoint
    local  -> deterministic local parser (no API/model required)
    """

    def __init__(self):
        self.colab_url = settings.COLAB_API_URL

        self.groq_client = None

        if settings.GROQ_API_KEY:
            self.groq_client = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            print("✅ Groq client initialized")
        else:
            print("⚠️ GROQ_API_KEY not configured - Groq engine disabled")

    async def analyze_text(self, text: str, mode: AIMode, diagram_type=None):
        text = (text or "").strip()
        if not text:
            raise ValueError("متن ورودی نمی‌تواند خالی باشد.")

        dtype = diagram_type.value if isinstance(diagram_type, DiagramType) else (diagram_type or "flowchart")

        if mode == AIMode.ONLINE:
            result = await self._try_groq(text, dtype)
            if self._is_valid_result(result):
                result["source"] = "groq"
                print("✅ Engine: Groq")
                return result
            raise RuntimeError("Groq در دسترس نیست یا نتوانست دیاگرام معتبری تولید کند.")

        if mode == AIMode.COLAB:
            result = await self._try_colab(text, dtype)
            if self._is_valid_result(result):
                result["source"] = "colab"
                print("✅ Engine: Colab")
                return result
            raise RuntimeError("Colab در دسترس نیست یا نتوانست دیاگرام معتبری تولید کند.")

        if mode == AIMode.LOCAL:
            result = self._smart_parse(text, dtype)
            result["source"] = "local"
            print("✅ Engine: Local")
            return result

        raise ValueError(f"حالت پردازش نامعتبر است: {mode}")

    @staticmethod
    def _is_valid_result(result: Optional[Dict]) -> bool:
        return bool(result and len(result.get("nodes", [])) >= 2)

    async def _try_groq(self, text: str, diagram_type: str) -> Optional[Dict]:
        if self.groq_client is None:
            print("⚠️ Groq engine is unavailable because GROQ_API_KEY is missing")
            return None
        is_fa = self._is_persian(text)

        if is_fa:
            prompt = f"""متن زیر را برای ساخت یک دیاگرام {diagram_type} تحلیل کن.

متن:
{text}

بین ۵ تا ۱۰ گره معنادار استخراج کن. روابط واقعی بین مراحل را مشخص کن.
برای flowchart از process / decision / start / end استفاده کن.
برای roadmap از milestone استفاده کن.
برای gantt_chart از task استفاده کن.

فقط JSON معتبر و بدون Markdown برگردان:
{{
  "nodes": [
    {{"id":"1","label":"...","type":"process"}}
  ],
  "edges": [
    {{"from":"1","to":"2","label":"بعد از آن"}}
  ],
  "suggested_type":"{diagram_type}"
}}"""
        else:
            prompt = f"""Analyze the following text and create a {diagram_type} diagram.

Text:
{text}

Extract 5-10 meaningful nodes and real relationships. Return only valid JSON.
Use process/decision/start/end for flowcharts, milestone for roadmaps and task for Gantt.

{{
  "nodes": [{{"id":"1","label":"...","type":"process"}}],
  "edges": [{{"from":"1","to":"2","label":"next"}}],
  "suggested_type":"{diagram_type}"
}}"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.35,
                max_tokens=1400
            )
            content = response.choices[0].message.content or ""
            print(f"🤖 Groq: {content[:150]}...")
            return self._parse_json(content, diagram_type)
        except Exception as e:
            print(f"❌ Groq: {e}")
            return None

    async def _try_colab(self, text: str, diagram_type: str) -> Optional[Dict]:
        if not self.colab_url:
            print("⚠️ Colab URL is not configured")
            return None

        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.colab_url.rstrip('/')}/generate",
                    json={"text": text, "diagram_type": diagram_type},
                    headers={"ngrok-skip-browser-warning": "true"}
                ) as resp:
                    if resp.status != 200:
                        print(f"❌ Colab HTTP {resp.status}")
                        return None

                    data = await resp.json(content_type=None)
                    raw = data.get("response", data.get("result", data.get("data", "")))
                    if isinstance(raw, dict):
                        return self._parse_json(json.dumps(raw), diagram_type)

                    print(f"🚀 Colab: {str(raw)[:100]}...")
                    return self._parse_json(str(raw), diagram_type)
        except Exception as e:
            print(f"❌ Colab: {e}")
            return None

    def _is_persian(self, text: str) -> bool:
        return bool(re.search(r"[\u0600-\u06FF]", text))

    def _parse_json(self, content: str, diagram_type: str) -> Optional[Dict]:
        content = (content or "").strip()
        if not content:
            return None

        if "```" in content:
            blocks = re.findall(r"```(?:json)?\s*(.*?)```", content, flags=re.S | re.I)
            if blocks:
                content = blocks[0].strip()

        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(content[start:end])
                if isinstance(data, dict) and "nodes" in data:
                    nodes = []
                    for node in data.get("nodes", []):
                        label = str(node.get("label", "")).strip()
                        if len(label) > 2:
                            nodes.append({
                                "id": str(len(nodes) + 1),
                                "label": label[:100],
                                "type": node.get("type", "process")
                            })

                    edges = self._normalize_edges(data.get("edges", []), len(nodes))
                    if len(nodes) >= 2:
                        return {
                            "nodes": nodes,
                            "edges": edges,
                            "suggested_type": data.get("suggested_type") or diagram_type
                        }

                # Accept simple key/value JSON as a fallback.
                nodes = []
                for key, value in data.items() if isinstance(data, dict) else []:
                    label = value.get("description", value.get("توضیحات", key)) if isinstance(value, dict) else str(value)
                    label = str(label).strip()
                    if len(label) > 2:
                        nodes.append({"id": str(len(nodes) + 1), "label": label[:100], "type": "process"})
                if len(nodes) >= 2:
                    return self._steps_to_diagram(nodes, diagram_type)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        # Last chance: turn non-empty lines into nodes.
        lines = []
        for line in content.splitlines():
            line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
            if len(line) > 3 and "`" not in line:
                lines.append(line)

        if len(lines) >= 2:
            nodes = [{"id": str(i + 1), "label": line[:100], "type": "process"} for i, line in enumerate(lines[:10])]
            return self._steps_to_diagram(nodes, diagram_type)

        return None

    @staticmethod
    def _normalize_edges(edges: list, node_count: int) -> List[Dict]:
        normalized = []
        for edge in edges or []:
            try:
                source = int(str(edge.get("from", "")))
                target = int(str(edge.get("to", "")))
            except (ValueError, TypeError):
                continue
            if 1 <= source <= node_count and 1 <= target <= node_count and source != target:
                normalized.append({
                    "from": str(source),
                    "to": str(target),
                    "label": str(edge.get("label", ""))[:30]
                })
        return normalized or [
            {"from": str(i), "to": str(i + 1), "label": "بعدی"}
            for i in range(1, node_count)
        ]

    def _get_prompt(self, text: str, diagram_type: str, is_fa: bool = True) -> str:
        return f"هدف: {text}\nنوع دیاگرام: {diagram_type}\nخروجی را به JSON شامل nodes و edges تبدیل کن."

    # -----------------------------
    # Local engine
    # -----------------------------

    def _smart_parse(self, text: str, diagram_type: str = "flowchart") -> Dict:
        if diagram_type == "roadmap":
            return self._local_roadmap(text)
        if diagram_type == "gantt_chart":
            return self._local_gantt(text)

        sentences = self._extract_local_steps(text)
        if len(sentences) < 2:
            sentences = self._extract_entities(text)
        if len(sentences) < 2:
            sentences = self._fallback_local_steps(text)

        nodes = []
        for i, step in enumerate(sentences[:10], 1):
            node_type = "process"
            if i == 1:
                node_type = "start"
            elif i == min(len(sentences), 10):
                node_type = "end"
            if re.search(r"اگر|در صورت|شرط|if|when", step, re.I):
                node_type = "decision"
            nodes.append({"id": str(i), "label": step[:100], "type": node_type})

        edges = []
        for i in range(1, len(nodes)):
            edges.append({"from": str(i), "to": str(i + 1), "label": "بعدی"})

        return {
            "nodes": nodes,
            "edges": edges,
            "suggested_type": "flowchart"
        }

    def _extract_local_steps(self, text: str) -> List[str]:
        # First split explicit sequence words, then sentence punctuation.
        normalized = re.sub(r"\s+", " ", text.strip())
        sequence_pattern = r"\s*(?:ابتدا|اول|نخست|سپس|بعد|بعد از آن|در ادامه|پس از آن|در نهایت|در آخر|آخر)\s*[:،,-]?\s*"
        parts = re.split(sequence_pattern, normalized, flags=re.I)
        if len(parts) == 1:
            parts = re.split(r"[.!؟؛]+|\s+[و,]\s+", normalized)

        cleaned = []
        for part in parts:
            part = re.sub(r"^(می‌خواهم|میخوام|قصد دارم|لازم است|باید)\s*", "", part.strip())
            part = part.strip(" ،,.-")
            if len(part) >= 4 and part not in cleaned:
                cleaned.append(part)
        return cleaned

    def _extract_entities(self, text: str) -> List[str]:
        # A deterministic fallback that still reflects the user's actual text.
        candidates = re.split(r"[،,؛;]|\s+و\s+|\s+سپس\s+", text)
        candidates = [re.sub(r"^(می‌خواهم|میخوام|قصد دارم)\s*", "", x.strip()) for x in candidates]
        return [x for x in candidates if len(x) >= 4][:8]

    def _fallback_local_steps(self, text: str) -> List[str]:
        subject = text[:70].strip().rstrip(".!؟")
        return [
            f"تعریف هدف: {subject}",
            "بررسی نیازمندی‌ها و منابع",
            "طراحی راهکار و برنامه اجرا",
            "اجرای مراحل اصلی",
            "بررسی نتیجه و اصلاح",
            "تحویل و ارزیابی نهایی"
        ]

    def _local_roadmap(self, text: str) -> Dict:
        steps = self._extract_local_steps(text)
        if len(steps) < 2:
            steps = self._fallback_local_steps(text)
        nodes = [
            {"id": str(i), "label": f"مرحله {i}: {step[:85]}", "type": "milestone"}
            for i, step in enumerate(steps[:8], 1)
        ]
        return {
            "nodes": nodes,
            "edges": [{"from": str(i), "to": str(i + 1), "label": "بعدی"} for i in range(1, len(nodes))],
            "suggested_type": "roadmap"
        }

    def _local_gantt(self, text: str) -> Dict:
        steps = self._extract_local_steps(text)
        if len(steps) < 2:
            steps = self._fallback_local_steps(text)
        nodes = [
            {"id": str(i), "label": f"{step[:75]} — {i + 1} روز", "type": "task"}
            for i, step in enumerate(steps[:8], 1)
        ]
        return {
            "nodes": nodes,
            "edges": [{"from": str(i), "to": str(i + 1), "label": "بعدی"} for i in range(1, len(nodes))],
            "suggested_type": "gantt_chart"
        }

    def _steps_to_diagram(self, nodes: List[Dict], diagram_type: str) -> Dict:
        return {
            "nodes": nodes,
            "edges": [
                {"from": str(i), "to": str(i + 1), "label": "بعدی"}
                for i in range(1, len(nodes))
            ],
            "suggested_type": diagram_type
        }
