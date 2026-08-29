from typing import Dict, List, Optional
from enum import Enum
from openai import AsyncOpenAI
import aiohttp
import json
import re
import hashlib
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

    # کلمات ترتیبی، برای شناسایی توالی گام‌ها در متن آزاد (فارسی + انگلیسی)
    _SEQUENCE_WORDS = [
        "در ابتدا", "قدم اول", "ابتدا", "اول", "نخست",
        "بعد از آن", "پس از آن", "در ادامه", "سپس", "بعد",
        "همچنین", "علاوه بر این",
        "در نهایت", "نهایتاً", "سرانجام", "در آخر", "آخر",
        "مرحله اول", "مرحله دوم", "مرحله سوم", "مرحله چهارم", "مرحله پنجم",
        "قدم دوم", "قدم سوم", "قدم چهارم",
        "to begin with", "first of all", "firstly", "initially", "first",
        "after that", "afterwards", "subsequently", "then", "next",
        "also", "additionally", "furthermore",
        "finally", "lastly", "eventually", "in the end",
        "step one", "step two", "step three", "step four", "step five",
        "second step", "third step", "fourth step",
    ]
    # کلمات نشان‌دهنده شرط/تصمیم
    _DECISION_WORDS = [
        "اگر", "در صورتی که", "در صورت", "چنانچه", "شرط",
        "وگرنه", "در غیر این صورت", "مگر اینکه", "بررسی", "تایید", "آیا",
        "if", "when", "unless", "otherwise", "whether", "check", "verify", "condition",
    ]
    # کلمات نشان‌دهنده ورودی/دریافت داده
    _INPUT_WORDS = [
        "دریافت", "ورودی", "وارد کردن", "ثبت‌نام", "ثبت نام", "پر کردن فرم",
        "input", "enter", "receive", "collect", "submit", "upload", "register",
    ]
    # کلمات نشان‌دهنده خروجی/نمایش نتیجه
    _OUTPUT_WORDS = [
        "نمایش", "خروجی", "چاپ", "ارسال", "اعلام", "گزارش",
        "output", "display", "print", "send", "notify", "report", "export",
    ]
    # کلمات توقف برای استخراج کلیدواژه (فارسی + انگلیسی)
    _STOPWORDS = {
        "و", "یا", "که", "این", "آن", "به", "از", "در", "برای", "با", "را",
        "است", "شود", "می‌شود", "تا", "هم", "یک", "بر", "روی", "های", "هایی",
        "the", "a", "an", "and", "or", "to", "of", "in", "for", "with",
        "is", "are", "on", "at", "by", "that", "this", "be", "as",
    }

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

    # الگوی «اگر X ... در غیر این صورت/وگرنه Y» برای ساخت انشعاب واقعی (نه فقط زنجیره خطی)
    _BRANCH_PATTERN_FA = re.compile(
        r"اگر\s+(?P<cond>.+?)\s*[,،]\s*(?P<then>.+?)\s*(?:[.؛]|$)\s*"
        r"(?:در غیر این صورت|وگرنه|مگر اینکه)\s*[,،:]?\s*(?P<alt>.+?)\s*(?:[.؛]|$)",
        re.S
    )
    _BRANCH_PATTERN_EN = re.compile(
        r"if\s+(?P<cond>.+?)\s*,\s*(?P<then>.+?)\s*(?:[.;]|$)\s*"
        r"(?:otherwise|else)\s*[,:]?\s*(?P<alt>.+?)\s*(?:[.;]|$)",
        re.I | re.S
    )

    def _smart_parse(self, text: str, diagram_type: str = "flowchart") -> Dict:
        if diagram_type == "roadmap":
            return self._local_roadmap(text)
        if diagram_type == "gantt_chart":
            return self._local_gantt(text)

        # اگر کل متن اساساً یک تصمیم دوشاخه‌ای ساده باشد، به‌جای زنجیره‌ی
        # خطی، یک نمودار واقعاً شاخه‌دار (شروع -> شرط -> بله/خیر -> پایان) می‌سازیم.
        branch = self._try_build_branch_flow(text)
        if branch:
            return branch

        sentences = self._extract_local_steps(text)
        if len(sentences) < 2:
            sentences = self._extract_entities(text)
        if len(sentences) < 2:
            sentences = self._fallback_local_steps(text)

        sentences = sentences[:10]
        total = len(sentences)

        nodes = []
        for i, step in enumerate(sentences, 1):
            node_type = self._classify_step_type(step, i, total)
            nodes.append({"id": str(i), "label": step[:100], "type": node_type})

        edges = []
        for i in range(1, len(nodes)):
            edges.append({"from": str(i), "to": str(i + 1), "label": "بعدی"})

        return {
            "nodes": nodes,
            "edges": edges,
            "suggested_type": "flowchart"
        }

    def _try_build_branch_flow(self, text: str) -> Optional[Dict]:
        """
        فقط برای متن‌های نسبتاً کوتاه و تک‌شرطی فعال می‌شود. اگر الگو مطابقت
        نداشت یا هرگونه خطای غیرمنتظره‌ای رخ داد، None برمی‌گرداند تا مسیر
        استخراج خطی معمول (بدون هیچ تغییری) جایگزین آن شود — پس هرگز چیزی
        را خراب نمی‌کند، فقط در بهترین حالت یک نمودار بهتر می‌سازد.
        """
        if len(text) > 260:
            return None
        try:
            match = self._BRANCH_PATTERN_FA.search(text) or self._BRANCH_PATTERN_EN.search(text)
            if not match:
                return None

            cond = match.group("cond").strip(" ،,:-")
            then = match.group("then").strip(" ،,:-")
            alt = match.group("alt").strip(" ،,:-")
            if min(len(cond), len(then), len(alt)) < 4:
                return None

            is_fa = self._is_persian(text)
            nxt = "بعدی" if is_fa else "next"

            nodes = [
                {"id": "1", "label": "شروع" if is_fa else "Start", "type": "start"},
                {"id": "2", "label": cond[:100], "type": "decision"},
                {"id": "3", "label": then[:100], "type": "process"},
                {"id": "4", "label": alt[:100], "type": "process"},
                {"id": "5", "label": "پایان" if is_fa else "End", "type": "end"},
            ]
            edges = [
                {"from": "1", "to": "2", "label": nxt},
                {"from": "2", "to": "3", "label": "بله" if is_fa else "Yes"},
                {"from": "2", "to": "4", "label": "خیر" if is_fa else "No"},
                {"from": "3", "to": "5", "label": nxt},
                {"from": "4", "to": "5", "label": nxt},
            ]
            return {"nodes": nodes, "edges": edges, "suggested_type": "flowchart"}
        except Exception:
            return None

    def _classify_step_type(self, step: str, index: int, total: int) -> str:
        """اولین گام = شروع، آخرین گام = پایان؛ بقیه بر اساس کلیدواژه شناسایی می‌شوند."""
        if index == 1:
            return "start"
        if index == total:
            return "end"
        if self._contains_any(step, self._DECISION_WORDS):
            return "decision"
        if self._contains_any(step, self._INPUT_WORDS):
            return "input"
        if self._contains_any(step, self._OUTPUT_WORDS):
            return "output"
        return "process"

    @staticmethod
    def _contains_any(text: str, keywords: List[str]) -> bool:
        low = text.lower()
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", low):
                return True
        return False

    def _extract_local_steps(self, text: str) -> List[str]:
        """
        استخراج گام‌ها با اولویت‌بندی سه‌مرحله‌ای تا برای هر نوع متنی
        (لیست بولت‌دار، متن آزاد فارسی/انگلیسی، جمله کوتاه) خروجی معقول بدهد:
          1) اگر متن به‌صورت لیست خط‌به‌خط/بولت/شماره‌دار نوشته شده، همان ساختار ملاک است.
          2) وگرنه بر اساس کلمات ترتیبی (ابتدا/سپس/مرحله دوم/... یا first/then/step two/...) شکسته می‌شود.
          3) در نهایت بر اساس علائم پایان جمله شکسته می‌شود.
        """
        raw = text.strip()

        raw_lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        bullet_pattern = re.compile(r"^\s*(?:[-*•▪◦]|\d+[.)]|[۰-۹]+[.)])\s*")
        bullet_lines = [
            bullet_pattern.sub("", ln).strip()
            for ln in raw_lines if bullet_pattern.match(ln)
        ]

        if len(bullet_lines) >= 2:
            parts = bullet_lines
        elif len(raw_lines) >= 2:
            # چند خط داریم که بولت نیستند؛ هر خط را یک گام مستقل در نظر می‌گیریم
            parts = raw_lines
        else:
            normalized = re.sub(r"\s+", " ", raw)
            sequence_pattern = (
                r"\s*\b(?:" + "|".join(re.escape(w) for w in self._SEQUENCE_WORDS) + r")\b\s*[:،,-]?\s*"
            )
            parts = re.split(sequence_pattern, normalized, flags=re.I)
            if len(parts) < 2:
                # توجه: عمداً روی «و»/and نمی‌شکنیم چون در فارسی خیلی وقت‌ها
                # بخشی از یک عبارت مرکب است (مثل «کسب و کار»، «علم و صنعت»)
                # و شکستن روی آن باعث قطعه‌قطعه شدن غلط می‌شود. اما کاما/،
                # را اضافه می‌کنیم چون خیلی از لیست‌ها (مثلاً برای رودمپ/گنت)
                # فقط با کاما از هم جدا شده‌اند و اصلاً نقطه‌ای در متن نیست.
                parts = re.split(r"[.!؟؛,،]+", normalized, flags=re.I)

        # تصفیه ثانویه: اگر یکی از قطعات خودش چند بند/جمله را با هم دارد
        # (مثلاً «... . If the schema is approved, ...» یا جمله مرکب فارسی با ویرگول)، می‌شکنیم.
        refined = []
        for part in parts:
            sub_parts = re.split(r"[.!؟؛]+\s+|،\s*(?=\S{3,})|,\s*(?=\S{3,})", part.strip())
            refined.extend(sp for sp in sub_parts if sp.strip())
        parts = refined or parts

        cleaned = []
        for part in parts:
            part = re.sub(
                r"^(می‌خواهم|میخوام|قصد دارم|لازم است|باید|i want to|i need to|we need to)\b\s*",
                "", part.strip(), flags=re.I
            )
            # اگر به دلیل نقطه‌ی جدایی، یک «و»/and تنها در ابتدا یا انتهای
            # قطعه باقی مانده باشد (نه وسط یک عبارت مرکب)، آن را پاک می‌کنیم.
            part = re.sub(r"^(?:و|and)\s+", "", part.strip(), flags=re.I)
            part = re.sub(r"\s+(?:و|and)$", "", part.strip(), flags=re.I)
            part = part.strip(" ،,.-")
            if len(part) >= 4 and part not in cleaned:
                cleaned.append(part)
        return cleaned

    def _extract_entities(self, text: str) -> List[str]:
        # A deterministic fallback that still reflects the user's actual text.
        # («و»/and عمداً جداکننده نیست؛ به دلیل کاربرد در عبارات مرکب فارسی)
        candidates = re.split(r"[،,؛;]", text, flags=re.I)
        candidates = [
            re.sub(r"^(می‌خواهم|میخوام|قصد دارم|i want to|i need to)\s*", "", x.strip(), flags=re.I)
            for x in candidates
        ]
        return [x for x in candidates if len(x) >= 4][:8]

    # چند قالب متفاوت برای fallback؛ کدام‌یک استفاده شود بر اساس خودِ متن
    # ورودی تعیین می‌شود (نه رندوم واقعی) تا هم بین موضوعات مختلف تنوع
    # واقعی داشته باشیم و هم برای یک ورودی ثابت همیشه همان خروجی بیاید.
    _FALLBACK_TEMPLATES_FA = [
        [
            "شروع: {p0}",
            "جمع‌آوری اطلاعات و منابع لازم برای {p1}",
            "طراحی و برنامه‌ریزی مراحل اجرای {p2}",
            "اجرای مراحل اصلی {p0}",
            "بررسی کیفیت و رفع اشکالات احتمالی",
            "تحویل و ارزیابی نتیجه‌ی نهایی {p1}",
        ],
        [
            "شروع: {p0}",
            "بررسی نیازها و شرایط اولیه‌ی {p1}",
            "تهیه‌ی امکانات و ابزار موردنیاز برای {p2}",
            "اجرای عملی {p0}",
            "پایش پیشرفت و اصلاح روند در صورت نیاز",
            "نهایی‌سازی و راه‌اندازی {p1}",
        ],
        [
            "شروع: {p0}",
            "تحقیق و مطالعه درباره‌ی {p1}",
            "برنامه‌ریزی زمان‌بندی و بودجه برای {p2}",
            "اجرای گام‌به‌گام {p0}",
            "دریافت بازخورد و رفع مشکلات",
            "تحویل نهایی و شروع بهره‌برداری از {p1}",
        ],
        [
            "شروع: {p0}",
            "شناسایی مخاطب و هدف اصلی {p1}",
            "طراحی ساختار کلی {p2}",
            "پیاده‌سازی و اجرای {p0}",
            "آزمایش و اصلاح ایرادها",
            "انتشار و پیگیری نتیجه‌ی {p1}",
        ],
    ]
    _FALLBACK_TEMPLATES_EN = [
        [
            "Start: {p0}",
            "Gather information and resources for {p1}",
            "Design and plan the execution of {p2}",
            "Carry out the main steps of {p0}",
            "Review quality and fix any issues",
            "Deliver and evaluate the final result of {p1}",
        ],
        [
            "Start: {p0}",
            "Assess initial needs and requirements for {p1}",
            "Prepare the tools and resources needed for {p2}",
            "Put {p0} into practice",
            "Monitor progress and adjust as needed",
            "Finalize and launch {p1}",
        ],
        [
            "Start: {p0}",
            "Research and study {p1}",
            "Plan the timeline and budget for {p2}",
            "Execute {p0} step by step",
            "Collect feedback and resolve issues",
            "Deliver the final result and roll out {p1}",
        ],
    ]

    def _fallback_local_steps(self, text: str) -> List[str]:
        """
        وقتی هیچ ساختار قابل تشخیصی در متن نیست (مثلاً یک عبارت خیلی کوتاه)،
        به‌جای یک قالب کاملاً ثابت و یکسان برای همه‌ی ورودی‌ها، از عبارت‌های
        کلیدی واقعی متن در همه‌ی خط‌ها استفاده می‌کند و یکی از چند قالب
        متفاوت را (بر اساس محتوای خودِ متن) انتخاب می‌کند تا خروجی برای
        موضوعات مختلف واقعاً متفاوت باشد، نه فقط در خط اول.
        """
        phrases = self._extract_key_phrases(text, limit=3)
        if not phrases:
            keywords = self._extract_keywords(text, limit=4)
            phrases = keywords if keywords else [text[:60].strip().rstrip(".!؟")]

        # اگر عبارت کافی برای پر کردن قالب نداریم، با چرخش همان عبارت‌ها پر می‌کنیم
        while len(phrases) < 3:
            phrases.append(phrases[-1])
        p0, p1, p2 = phrases[0], phrases[1], phrases[2]

        is_fa = self._is_persian(text)
        templates = self._FALLBACK_TEMPLATES_FA if is_fa else self._FALLBACK_TEMPLATES_EN

        # انتخاب قالب بر اساس هش ثابتِ خودِ متن (نه رندوم واقعی) تا موضوعات
        # مختلف معمولاً به قالب‌های متفاوتی برسند، ولی نتیجه هر بار قابل تکرار بماند.
        digest = hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()
        template = templates[int(digest, 16) % len(templates)]

        return [line.format(p0=p0, p1=p1, p2=p2) for line in template]

    def _extract_key_phrases(self, text: str, limit: int = 2) -> List[str]:
        """
        به‌جای کلمات پراکنده، عبارت‌های کلیدی پیوسته را استخراج می‌کند
        (مثلاً «کسب و کار خانگی» به‌جای «خانگی / کسب / کار»). «و»/and داخل
        یک عبارت نگه داشته می‌شود چون معمولاً بخشی از اصطلاح مرکب است؛
        بقیه‌ی کلمات توقف، مرز بین دو عبارت را مشخص می‌کنند.
        """
        tokens = re.findall(r"[آ-یA-Za-z]+|[،,]", text)
        phrases: List[List[str]] = []
        current: List[str] = []
        for tok in tokens:
            if tok in ("،", ","):
                if current:
                    phrases.append(current)
                    current = []
                continue
            low = tok.lower()
            if low in self._STOPWORDS and low not in ("و", "and"):
                if current:
                    phrases.append(current)
                    current = []
                continue
            current.append(tok)
        if current:
            phrases.append(current)

        meaningful = [" ".join(p[:6]) for p in phrases if len(p) >= 2]
        if not meaningful:
            meaningful = [" ".join(p) for p in phrases if p]

        result = []
        for p in meaningful:
            if p not in result:
                result.append(p)
            if len(result) >= limit:
                break
        return result

    def _extract_keywords(self, text: str, limit: int = 5) -> List[str]:
        """استخراج ساده کلیدواژه بر اساس فراوانی کلمات (بدون نیاز به مدل)."""
        words = re.findall(r"[آ-یA-Za-z]{3,}", text)
        freq: Dict[str, int] = {}
        for w in words:
            wl = w.strip("‌")
            if wl.lower() in self._STOPWORDS or len(wl) < 3:
                continue
            freq[wl] = freq.get(wl, 0) + 1
        ranked = sorted(freq.items(), key=lambda kv: (-kv[1], -len(kv[0])))
        return [w for w, _ in ranked[:limit]]

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
        is_fa = self._is_persian(text)
        nodes = []
        for i, step in enumerate(steps[:8], 1):
            duration = self._extract_duration_label(step, i, is_fa)
            nodes.append({"id": str(i), "label": f"{step[:75]} — {duration}", "type": "task"})
        return {
            "nodes": nodes,
            "edges": [{"from": str(i), "to": str(i + 1), "label": "بعدی"} for i in range(1, len(nodes))],
            "suggested_type": "gantt_chart"
        }

    @staticmethod
    def _extract_duration_label(step: str, index: int, is_fa: bool) -> str:
        """اگر خود متن مدت‌زمانی مشخص کرده باشد (مثل «۳ روز» یا «2 weeks») همان را
        استفاده می‌کند؛ وگرنه یک تخمین افزایشی ساده به‌عنوان جایگزین برمی‌گرداند."""
        match = re.search(r"\d+\s*(?:روز|هفته|ماه|day|days|week|weeks|month|months)", step, re.I)
        if match:
            return match.group(0)
        return f"{index + 1} روز" if is_fa else f"{index + 1} days"

    def _steps_to_diagram(self, nodes: List[Dict], diagram_type: str) -> Dict:
        return {
            "nodes": nodes,
            "edges": [
                {"from": str(i), "to": str(i + 1), "label": "بعدی"}
                for i in range(1, len(nodes))
            ],
            "suggested_type": diagram_type
        }