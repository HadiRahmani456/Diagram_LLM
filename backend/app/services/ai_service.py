from typing import Dict, List, Optional
from enum import Enum
from openai import AsyncOpenAI
import aiohttp
import json
import re
import os
from app.core.config import settings

class AIMode(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"

class DiagramType(str, Enum):
    FLOWCHART = "flowchart"
    ROADMAP = "roadmap"
    GANTT_CHART = "gantt_chart"

class AIService:
    def __init__(self):
        self.groq_client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        self.colab_url = settings.COLAB_API_URL
        
    async def analyze_text(self, text, mode, diagram_type=None):
        dtype = diagram_type.value if diagram_type else "flowchart"
    
        if mode == AIMode.ONLINE:
            result = await self._try_groq(text, dtype)
            if result: return result
    
        # Colab GPU (همیشه آنلاین)
        result = await self._try_colab(text, dtype)
        if result and len(result.get("nodes", [])) > 1:
            return result
    
        return self._smart_parse(text, dtype)
    
    async def _try_groq(self, text: str, diagram_type: str) -> Optional[Dict]:
        is_fa = self._is_persian(text)
        
        if is_fa:
            prompt = f"""متن زیر را به ۵ تا ۸ مرحله منطقی و جزئی بشکن. برای هر مرحله توضیح کوتاه بنویس.

    متن: "{text}"

    مثال برای "ساخت کارگاه نجاری" (۷ مرحله):
    {{"nodes":[{{"id":"1","label":"انتخاب محل و اخذ مجوزها","type":"process"}},{{"id":"2","label":"طراحی نقشه کارگاه","type":"process"}},{{"id":"3","label":"تهیه تجهیزات و ابزارآلات","type":"process"}},{{"id":"4","label":"ساخت دیوارها و سقف","type":"process"}},{{"id":"5","label":"نصب پنجره‌ها و درها","type":"process"}},{{"id":"6","label":"تأمین روشنایی و برق‌کشی","type":"process"}},{{"id":"7","label":"راه‌اندازی و شروع تولید","type":"process"}}],"edges":[{{"from":"1","to":"2","label":"←"}},{{"from":"2","to":"3","label":"←"}},{{"from":"3","to":"4","label":"←"}},{{"from":"4","to":"5","label":"←"}},{{"from":"5","to":"6","label":"←"}},{{"from":"6","to":"7","label":"←"}}],"suggested_type":"{diagram_type}"}}

    برای متن بالا، ۵ تا ۸ مرحله با جزئیات و با suggested_type="{diagram_type}" بنویس. فقط JSON:"""
        else:
            prompt = f"""Break this into 5-8 detailed steps. suggested_type must be "{diagram_type}".

    Text: "{text}"

    Example with 7 steps for "Build a workshop":
    {{"nodes":[{{"id":"1","label":"Choose location and get permits","type":"process"}},{{"id":"2","label":"Design workshop layout","type":"process"}},...],"edges":[{{"from":"1","to":"2","label":"next"}},...],"suggested_type":"{diagram_type}"}}

    Return ONLY JSON with suggested_type="{diagram_type}":"""
        
        try:
            response = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1000
            )
            content = response.choices[0].message.content
            print(f"🤖 Groq: {content[:150]}...")
            return self._parse_json(content)
        except Exception as e:
            print(f"❌ Groq: {e}")
        return None
    
    async def _try_colab(self, text: str, diagram_type: str) -> Optional[Dict]:
        if not self.colab_url:
            return None
        
        prompt = self._get_prompt(text, diagram_type, True)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.colab_url}/generate",
                    json={"text": text, "diagram_type": diagram_type},
                    headers={"ngrok-skip-browser-warning": "true"},
                    timeout=60
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"🚀 Colab: {data.get('response', '')[:100]}...")
                        return self._parse_json(data.get("response", ""))
        except Exception as e:
            print(f"❌ Colab: {e}")
        return None
    
    def _is_persian(self, text: str) -> bool:
        persian = set('ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی')
        return bool(persian & set(text))
    
    def _parse_json(self, content: str) -> Optional[Dict]:
        content = content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"): content = content[4:]
        
        # اول سعی کن JSON پارس کنه
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(content[start:end])
                if "nodes" in data:
                    nodes = [n for n in data["nodes"] if n.get("label", "").strip() and len(n.get("label", "").strip()) > 2]
                    for i, node in enumerate(nodes, 1): node["id"] = str(i)
                    edges = [{"from": str(i), "to": str(i+1), "label": "←"} for i in range(1, len(nodes))]
                    return {"nodes": nodes, "edges": edges, "suggested_type": "flowchart"}
            except:
                pass
        
        # اگه JSON نبود، خط‌ها رو پارس کن
        lines = content.split('\n')
        nodes = []
        for line in lines:
            line = line.strip()
            # حذف ** و - و شماره‌ها
            line = re.sub(r'\*\*|-#|\*|^\d+\.\s*|^\-\s*', '', line).strip()
            if line and len(line) > 3 and '`' not in line:
                nodes.append(line)
        
        if len(nodes) > 1:
            nodes = [{"id": str(i+1), "label": n[:80], "type": "process"} for i, n in enumerate(nodes)]
            edges = [{"from": str(i), "to": str(i+1), "label": "←"} for i in range(1, len(nodes))]
            return {"nodes": nodes, "edges": edges, "suggested_type": "flowchart"}
        
        return None
    def _get_prompt(self, text: str, diagram_type: str, is_fa: bool) -> str:
        
        prompts = {
            "flowchart": f"""هدف "{text}" را به ۶ تا ۱۰ مرحله متوالی بشکن. فقط JSON:
{{"nodes":[{{"id":"1","label":"مرحله ۱","type":"process"}},...],"edges":[{{"from":"1","to":"2","label":"←"}},...],"suggested_type":"flowchart"}}""",
            
            "roadmap": f"""برای "{text}" یک نقشه راه زمانی با ۵ تا ۸ مرحله با تاریخ بنویس. فقط JSON:
{{"nodes":[{{"id":"1","label":"ماه ۱: ...","type":"milestone"}},{{"id":"2","label":"ماه ۲: ...","type":"milestone"}},...],"edges":[{{"from":"1","to":"2","label":"←"}},...],"suggested_type":"roadmap"}}""",
            
            "gantt_chart": f"""پروژه "{text}" را به ۵ تا ۸ وظیفه با مدت زمان تقریبی بشکن. فقط JSON:
{{"nodes":[{{"id":"1","label":"وظیفه ۱ (۳ روز)","type":"task"}},{{"id":"2","label":"وظیفه ۲ (۵ روز)","type":"task"}},...],"edges":[{{"from":"1","to":"2","label":"←"}},...],"suggested_type":"gantt_chart"}}"""
        }
        
        return prompts.get(diagram_type, prompts["flowchart"])
    def _smart_parse(self, text: str, diagram_type: str = "flowchart") -> Dict:
        steps = self._split_by_keywords(text)
        if len(steps) <= 1: steps = self._suggest_steps(text)
        return self._steps_to_diagram(steps, diagram_type)
    
    def _split_by_keywords(self, text: str) -> List[str]:
        keywords = ['ابتدا', 'اول', 'سپس', 'بعد', 'در ادامه', 'پس از آن', 'در نهایت', 'آخر']
        pattern = '|'.join(keywords)
        text = re.sub(rf'\s*({pattern})\s*', '|||', text)
        text = re.sub(r'[،,]\s*', '|||', text)
        steps = []
        for part in text.split('|||'):
            part = part.strip()
            part = re.sub(r'^(می‌خواهم|میخوام|قصد دارم)\s+', '', part)
            if len(part) > 1 and part not in steps: steps.append(part)
        return steps
    
    def _suggest_steps(self, text: str) -> List[str]:
        return ["برنامه‌ریزی", "طراحی", "اجرا", "بررسی", "ارائه"]
    
    def _steps_to_diagram(self, steps: List[str], diagram_type: str = "flowchart") -> Dict:
        nodes, edges = [], []
        for i, step in enumerate(steps, 1):
            nodes.append({"id": str(i), "label": step[:80], "type": "process"})
            if i > 1: edges.append({"from": str(i-1), "to": str(i), "label": "←"})
        return {"nodes": nodes, "edges": edges, "suggested_type": diagram_type}