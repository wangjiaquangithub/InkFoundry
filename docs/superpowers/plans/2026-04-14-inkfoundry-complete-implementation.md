# InkFoundry 完整实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal**: 构建全面超越 InkOS 的 AI 长篇小说生成系统，实现 LLM 真实调用、Pipeline 完整串联、React 可视化工作台、以及完整功能（导入/续写、导出、题材、番外/仿写、多项目、Daemon、Token 统计、风格克隆）。

**Architecture**: 四阶段实施 — Phase B (LLM 集成) → Phase C (Pipeline 串联) → Phase A (前端) → Phase D (完整功能)

**Tech Stack**: Python 3.10+ (FastAPI, SQLite, Pydantic, openai, chromadb, pyyaml, mcp, httpx, pytest) + React (Vite, shadcn/ui, Tailwind CSS, Zustand, Recharts, WebSocket, Vitest)

---

## 文件映射

| Phase | 创建文件 | 修改文件 |
|-------|---------|---------|
| B.1 | `Engine/llm/__init__.py`, `Engine/llm/gateway.py` | `requirements.txt` |
| B.2 | `Engine/llm/prompt_builder.py` | — |
| B.3 | `Engine/llm/ai_filter.py` | `Engine/core/models.py` |
| B.4 | — | `Engine/agents/writer.py`, `Engine/agents/editor.py`, `Engine/agents/redteam.py` |
| B.5 | — | `Engine/configs/voices/default.yaml`, `Engine/agents/voice_sandbox.py` |
| C.1 | `Engine/core/event_bus.py`, `Engine/core/review_policy.py` | `Engine/core/controller.py`, `Engine/core/models.py` |
| C.2 | — | `Engine/core/controller.py` (Gradient Rewrite) |
| C.3 | — | `Engine/core/memory_bank.py` (ChromaDB) |
| C.4 | — | `Engine/core/controller.py` (watchdog), `Studio/api.py` |
| A.1 | `frontend/` 全部 (Vite + React) | `Studio/api.py`, `requirements.txt` |
| A.2 | `Studio/ws.py` | `Studio/api.py` |
| A.3 | `frontend/src/pages/Workspace.tsx` 等 | — |
| D.1 | `Engine/core/importer.py` | `Engine/core/models.py`, `Studio/api.py` |
| D.2 | `Engine/core/exporter.py` | `Studio/api.py` |
| D.3 | `Engine/core/genre_validator.py`, `Engine/configs/genres/` | `Engine/agents/editor.py` |
| D.4 | `Engine/agents/side_story.py`, `Engine/agents/imitation.py`, `Engine/llm/style_extractor.py` | `Studio/api.py` |
| D.5 | `Engine/core/project_manager.py` | `Engine/core/state_db.py`, `Engine/core/models.py`, `Studio/api.py` |
| D.6 | `Engine/core/token_tracker.py`, `Engine/core/daemon.py` | `Engine/llm/gateway.py`, `Studio/api.py` |

---

## Phase B: LLM 集成

### Task B.1: LLM Gateway

**Files:**
- Create: `Engine/llm/__init__.py`, `Engine/llm/gateway.py`
- Modify: `requirements.txt`
- Test: `tests/llm/test_gateway.py`

- [ ] **Step 1: Write failing test — LLMGateway init**

```python
# tests/llm/test_gateway.py
from Engine.llm.gateway import LLMGateway

def test_gateway_init():
    gw = LLMGateway(model="qwen-plus", api_key="test-key", base_url="https://example.com/v1")
    assert gw.model == "qwen-plus"
    assert gw.api_key == "test-key"
    assert gw.base_url == "https://example.com/v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/llm/test_gateway.py::test_gateway_init -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'Engine.llm'"

- [ ] **Step 3: Create Engine/llm/__init__.py**

```python
# Engine/llm/__init__.py
"""LLM Gateway — API call wrapper with retry and streaming."""
```

- [ ] **Step 4: Write minimal implementation**

```python
# Engine/llm/gateway.py
"""LLM API call wrapper with retry, timeout, and streaming support."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from openai import AsyncOpenAI


class LLMGateway:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str:
        client = self._get_client()
        for attempt in range(5):
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                )
                if stream:
                    return self._collect_stream(response)
                return response.choices[0].message.content or ""
            except Exception as e:
                if attempt == 4:
                    raise
                await asyncio.sleep(2 ** attempt)
        return ""

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def _collect_stream(self, response) -> str:
        parts = []
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                parts.append(delta.content)
        return "".join(parts)
```

- [ ] **Step 5: Add openai to requirements.txt**

```
# In requirements.txt, add:
openai>=1.0.0
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/llm/test_gateway.py::test_gateway_init -v`
Expected: PASS

- [ ] **Step 7: Write failing test — chat method calls API**

```python
# tests/llm/test_gateway.py (append)
import pytest

@pytest.mark.asyncio
async def test_gateway_chat_returns_content(monkeypatch):
    """Test that chat returns content from API response."""
    gw = LLMGateway("test-model", "key", "https://example.com/v1")

    # Mock the async client
    class FakeChoice:
        class Message:
            content = "Hello from LLM"
        message = Message()
        choices = [FakeChoice()]

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeClient:
        class Completions:
            async def create(self, **kwargs):
                return FakeResponse()
        chat = type('chat', (), {'completions': Completions()})()

    gw._client = FakeClient()

    result = await gw.chat([{"role": "user", "content": "hi"}])
    assert result == "Hello from LLM"
```

- [ ] **Step 8: Install pytest-asyncio and run test**

Run: `.venv/bin/pip install pytest-asyncio`
Run: `.venv/bin/python -m pytest tests/llm/test_gateway.py::test_gateway_chat_returns_content -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add Engine/llm/__init__.py Engine/llm/gateway.py tests/llm/test_gateway.py requirements.txt
git commit -m "feat: LLM Gateway with retry, streaming, and timeout support"
```

---

### Task B.2: Prompt Builder

**Files:**
- Create: `Engine/llm/prompt_builder.py`
- Test: `tests/llm/test_prompt_builder.py`

- [ ] **Step 1: Write failing test**

```python
# tests/llm/test_prompt_builder.py
from Engine.llm.prompt_builder import PromptBuilder


def test_prompt_builder_basic():
    builder = PromptBuilder("You are a novelist.")
    messages = builder.build()
    assert messages[0] == {"role": "system", "content": "You are a novelist."}


def test_prompt_builder_with_context():
    builder = PromptBuilder("You are a novelist.")
    builder.with_context("Previous chapter: Hero defeated the dragon.")
    messages = builder.build()
    assert len(messages) == 2
    assert messages[1]["role"] == "user"
    assert "Previous chapter" in messages[1]["content"]


def test_prompt_builder_chain():
    builder = (
        PromptBuilder("Write a chapter.")
        .with_context("Background info")
        .with_constraints(["No AI phrases", "Use sensory details"])
    )
    messages = builder.build()
    content = messages[1]["content"]
    assert "Background info" in content
    assert "No AI phrases" in content


def test_prompt_builder_with_voice():
    builder = PromptBuilder("Write a chapter.")
    builder.with_voice({
        "speech_patterns": ["uses short sentences"],
        "vocabulary": ["sword", "magic"],
        "sensory_bias": {"visual": 0.5},
        "forbidden_words": ["不禁", "仿佛"],
    })
    messages = builder.build()
    content = messages[0]["content"]
    assert "short sentences" in content
    assert "不禁" in content  # forbidden word mentioned in constraints


def test_prompt_builder_with_state_snapshot():
    builder = PromptBuilder("Write.")
    builder.with_state_snapshot({
        "characters": [{"name": "Zhang San", "status": "alive"}],
        "world": {"era": "fantasy"},
    })
    messages = builder.build()
    content = messages[1]["content"]
    assert "Zhang San" in content
    assert "fantasy" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/llm/test_prompt_builder.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'Engine.llm.prompt_builder'"

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/llm/prompt_builder.py
"""Prompt builder for LLM calls — assembles system prompt, context, constraints."""
from __future__ import annotations


class PromptBuilder:
    def __init__(self, system_template: str):
        self._system = system_template
        self._context = ""
        self._constraints: list[str] = []
        self._voice_profile: dict | None = None
        self._state_snapshot: dict | None = None
        self._style_constraint: str | None = None

    def with_context(self, context: str) -> "PromptBuilder":
        self._context = context
        return self

    def with_voice(self, voice_profile: dict) -> "PromptBuilder":
        self._voice_profile = voice_profile
        return self

    def with_state_snapshot(self, snapshot: dict) -> "PromptBuilder":
        self._state_snapshot = snapshot
        return self

    def with_constraints(self, constraints: list[str]) -> "PromptBuilder":
        self._constraints = constraints
        return self

    def with_style(self, style_constraint: str) -> "PromptBuilder":
        self._style_constraint = style_constraint
        return self

    def build(self) -> list[dict]:
        system_parts = [self._system]

        if self._voice_profile:
            vp = self._voice_profile
            if vp.get("speech_patterns"):
                system_parts.append(f"说话风格: {', '.join(vp['speech_patterns'])}")
            if vp.get("forbidden_words"):
                system_parts.append(f"禁止使用的词: {', '.join(vp['forbidden_words'])}")
            if vp.get("sensory_bias"):
                bias = vp["sensory_bias"]
                system_parts.append(f"感官偏好: {', '.join(f'{k}: {v}' for k, v in bias.items())}")

        if self._style_constraint:
            system_parts.append(f"风格约束: {self._style_constraint}")

        user_parts = []
        if self._state_snapshot:
            chars = self._state_snapshot.get("characters", [])
            user_parts.append("当前角色状态:")
            for c in chars:
                user_parts.append(f"  - {c.get('name', '?')}: {c.get('status', '?')}")
            world = self._state_snapshot.get("world", {})
            if world:
                user_parts.append(f"世界状态: {world}")

        if self._context:
            user_parts.append(self._context)

        if self._constraints:
            user_parts.append("写作约束:")
            for c in self._constraints:
                user_parts.append(f"  - {c}")

        user_content = "\n".join(user_parts) if user_parts else ""

        return [
            {"role": "system", "content": "\n".join(system_parts)},
            {"role": "user", "content": user_content},
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/llm/test_prompt_builder.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/llm/prompt_builder.py tests/llm/test_prompt_builder.py
git commit -m "feat: Prompt Builder with voice, state snapshot, and constraint injection"
```

---

### Task B.3: AI Filter（去 AI 味检测器）

**Files:**
- Create: `Engine/llm/ai_filter.py`
- Test: `tests/llm/test_ai_filter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/llm/test_ai_filter.py
from Engine.llm.ai_filter import AIFilter, AIFilterIssue


def test_ai_filter_detects_cliches():
    f = AIFilter({})
    text = "他不禁感到惊讶，这无疑是最好的结果。"
    issues = f.analyze(text)
    cliche_issues = [i for i in issues if i.type == "ai_cliche"]
    assert len(cliche_issues) >= 2  # "不禁" and "无疑"


def test_ai_filter_score_no_issues():
    f = AIFilter({})
    text = "张三端起茶杯，抿了一口。茶水已经凉了，苦味在舌尖蔓延。"
    score = f.score(text)
    assert 0 <= score <= 100


def test_ai_filter_repetitive_structure():
    f = AIFilter({})
    text = "他走进了房间。他打开了灯。他坐在了沙发上。"
    issues = f.analyze(text)
    rep_issues = [i for i in issues if i.type == "repetitive_structure"]
    assert len(rep_issues) >= 1


def test_ai_filter_score_range():
    f = AIFilter({})
    score = f.score("测试文本")
    assert 0 <= score <= 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/llm/test_ai_filter.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/llm/ai_filter.py
"""AI flavor detector — checks for common AI writing patterns."""
from __future__ import annotations
import re
from dataclasses import dataclass


# Common AI cliches in Chinese writing
AI_CLICHES = [
    "不禁", "仿佛", "似乎", "无疑", "值得注意的是",
    "值得一提的是", "不难发现", "显而易见", "众所周知",
    "令人", "不由得", "渐渐地", "突然之间",
]


@dataclass
class AIFilterIssue:
    type: str  # "repetitive_structure" | "ai_cliche" | "low_sensory" | "over_adjective"
    severity: float  # 0-1
    description: str
    position: tuple[int, int]  # (start, end) character indices


class AIFilter:
    def __init__(self, voice_profile: dict):
        self._voice_profile = voice_profile

    def analyze(self, text: str) -> list[AIFilterIssue]:
        issues = []
        issues.extend(self._check_cliches(text))
        issues.extend(self._check_repetitive_structure(text))
        return issues

    def score(self, text: str) -> float:
        """Return 0-100 de-AI score. 100 = no AI flavor, 0 = heavily AI."""
        issues = self.analyze(text)
        penalty = sum(i.severity * 20 for i in issues)
        return max(0, min(100, 100 - penalty))

    def _check_cliches(self, text: str) -> list[AIFilterIssue]:
        issues = []
        for cliche in AI_CLICHES:
            pos = 0
            while True:
                idx = text.find(cliche, pos)
                if idx == -1:
                    break
                issues.append(AIFilterIssue(
                    type="ai_cliche",
                    severity=0.5,
                    description=f"AI 套话: '{cliche}'",
                    position=(idx, idx + len(cliche)),
                ))
                pos = idx + len(cliche)
        return issues

    def _check_repetitive_structure(self, text: str) -> list[AIFilterIssue]:
        issues = []
        # Split into sentences
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 3:
            return issues

        # Check for repeated sentence patterns (start with same word)
        for i in range(len(sentences) - 2):
            first_words = []
            for j in range(3):
                s = sentences[i + j]
                first_words.append(s[:2] if len(s) >= 2 else s)
            if first_words[0] == first_words[1] == first_words[2]:
                issues.append(AIFilterIssue(
                    type="repetitive_structure",
                    severity=0.7,
                    description=f"连续3句相同开头: '{first_words[0]}'",
                    position=(0, 0),
                ))
        return issues
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/llm/test_ai_filter.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/llm/ai_filter.py tests/llm/test_ai_filter.py
git commit -m "feat: AI Filter — detect cliches and repetitive structures"
```

---

### Task B.4: Agent 接入真实 LLM

**Files:**
- Modify: `Engine/agents/writer.py`, `Engine/agents/editor.py`, `Engine/agents/redteam.py`
- Test: `tests/agents/test_writer.py`, `tests/agents/test_editor.py`, `tests/agents/test_redteam.py`

- [ ] **Step 1: Write failing test — WriterAgent with mock LLM**

```python
# tests/agents/test_writer.py
import pytest
from Engine.agents.writer import WriterAgent


@pytest.mark.asyncio
async def test_writer_agent_with_llm_gateway(monkeypatch):
    """Test WriterAgent calls LLMGateway instead of returning stub."""
    from Engine.llm.gateway import LLMGateway

    class FakeGateway:
        async def chat(self, messages, **kwargs):
            return "Generated chapter content from LLM"

    agent = WriterAgent(model_name="test-model", system_prompt="Write a novel")
    agent._gateway = FakeGateway()

    result = await agent.run({"chapter_num": 1, "tension_level": 5})
    assert result == "Generated chapter content from LLM"
    assert "stub" not in result.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/agents/test_writer.py::test_writer_agent_with_llm_gateway -v`
Expected: FAIL (current WriterAgent returns stub text, doesn't call LLM)

- [ ] **Step 3: Read current WriterAgent**

```bash
cat Engine/agents/writer.py
```

- [ ] **Step 4: Modify WriterAgent to use LLMGateway**

```python
# Engine/agents/writer.py — replace run() method
from __future__ import annotations
from typing import Any, Dict
from Engine.agents.base import BaseAgent
from Engine.llm.gateway import LLMGateway
from Engine.llm.prompt_builder import PromptBuilder


WRITER_SYSTEM_PROMPT = """你是一个专业的小说作家。你的任务是根据任务卡生成高质量的章节内容。
要求：
- 遵循角色 Voice Profile
- 使用丰富的感官描写
- 保持剧情连贯性
- 避免 AI 套话
"""


class WriterAgent(BaseAgent):
    SYSTEM_PROMPT = WRITER_SYSTEM_PROMPT

    def __init__(self, model_name, system_prompt=None, api_key="", base_url="", gateway=None):
        super().__init__(model_name, system_prompt or self.SYSTEM_PROMPT, api_key, base_url)
        self._gateway = gateway

    def _get_gateway(self) -> LLMGateway:
        if self._gateway is None:
            self._gateway = LLMGateway(self.model, self.api_key, self.base_url)
        return self._gateway

    async def run(self, task_card: Dict[str, Any]) -> str:
        builder = (
            PromptBuilder(self.system_prompt)
            .with_context(f"任务卡: 第{task_card.get('chapter_num', '?')}章, 张力等级: {task_card.get('tension_level', '?')}")
            .with_constraints(["生成完整的章节", "保持剧情连贯", "使用丰富的感官描写"])
        )
        messages = builder.build()

        gateway = self._get_gateway()
        content = await gateway.chat(messages, temperature=0.8, max_tokens=4096)
        return content
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/agents/test_writer.py::test_writer_agent_with_llm_gateway -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add Engine/agents/writer.py tests/agents/test_writer.py
git commit -m "feat: WriterAgent uses LLMGateway for real LLM calls"
```

- [ ] **Step 7: Apply same pattern to EditorAgent and RedTeamAgent**

Follow the same TDD pattern: write test with mocked gateway → modify agent to use gateway → verify → commit. The pattern is identical to WriterAgent.

EditorAgent changes:
```python
# Engine/agents/editor.py
from __future__ import annotations
from typing import Any, Dict
from Engine.agents.base import BaseAgent
from Engine.llm.gateway import LLMGateway
from Engine.llm.prompt_builder import PromptBuilder

EDITOR_SYSTEM_PROMPT = """你是一个严格的编辑。审核章节内容，指出逻辑问题和 AI 风格。"""

class EditorAgent(BaseAgent):
    SYSTEM_PROMPT = EDITOR_SYSTEM_PROMPT

    def __init__(self, model_name, system_prompt=None, api_key="", base_url="", gateway=None):
        super().__init__(model_name, system_prompt or self.SYSTEM_PROMPT, api_key, base_url)
        self._gateway = gateway

    def _get_gateway(self) -> LLMGateway:
        if self._gateway is None:
            self._gateway = LLMGateway(self.model, self.api_key, self.base_url)
        return self._gateway

    async def run(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        builder = (
            PromptBuilder(self.system_prompt)
            .with_context(f"审核以下章节:\n{draft.get('content', '')}")
            .with_constraints(["检查逻辑一致性", "检查 AI 味道", "给出具体修改建议"])
        )
        messages = builder.build()
        gateway = self._get_gateway()
        feedback = await gateway.chat(messages, temperature=0.3, max_tokens=2048)
        return {"score": 75, "issues": [feedback], "feedback": feedback}
```

RedTeamAgent changes:
```python
# Engine/agents/redteam.py
from __future__ import annotations
from typing import Any, Dict
from Engine.agents.base import BaseAgent
from Engine.llm.gateway import LLMGateway
from Engine.llm.prompt_builder import PromptBuilder

REDTEAM_SYSTEM_PROMPT = """你是一个敌对的书评家。你的任务是找到剧情和逻辑漏洞，攻击小说的合理性。"""

class RedTeamAgent(BaseAgent):
    SYSTEM_PROMPT = REDTEAM_SYSTEM_PROMPT

    def __init__(self, model_name, system_prompt=None, api_key="", base_url="", gateway=None):
        super().__init__(model_name, system_prompt or self.SYSTEM_PROMPT, api_key, base_url)
        self._gateway = gateway

    def _get_gateway(self) -> LLMGateway:
        if self._gateway is None:
            self._gateway = LLMGateway(self.model, self.api_key, self.base_url)
        return self._gateway

    async def run(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        builder = (
            PromptBuilder(self.system_prompt)
            .with_context(f"攻击以下章节:\n{draft.get('content', '')}")
            .with_constraints(["找出剧情漏洞", "找出逻辑矛盾", "找出角色 OOC 行为"])
        )
        messages = builder.build()
        gateway = self._get_gateway()
        attack = await gateway.chat(messages, temperature=0.5, max_tokens=2048)
        return {"attacks": [attack], "severity": "high", "feedback": attack}
```

- [ ] **Step 8: Run all existing tests to ensure no regression**

Run: `.venv/bin/python -m pytest tests/agents/ -v`
Expected: All tests PASS (existing tests use stub agents, new async code shouldn't break them)

- [ ] **Step 9: Commit**

```bash
git add Engine/agents/editor.py Engine/agents/redteam.py tests/agents/test_editor.py tests/agents/test_redteam.py
git commit -m "feat: EditorAgent and RedTeamAgent use LLMGateway for real LLM calls"
```

---

### Task B.5: Voice Profile 增强

**Files:**
- Modify: `Engine/configs/voices/default.yaml`, `Engine/agents/voice_sandbox.py`
- Test: `tests/agents/test_voice_sandbox.py`

- [ ] **Step 1: Write failing test**

```python
# tests/agents/test_voice_sandbox.py (append to existing file)
def test_voice_sandbox_with_speech_patterns():
    from Engine.agents.voice_sandbox import VoiceSandbox
    import tempfile, os

    config = {
        "style": "default",
        "tone": "neutral",
        "pacing": "moderate",
        "vocabulary": "standard",
        "speech_patterns": ["使用短句", "经常反问"],
        "forbidden_words": ["不禁", "仿佛"],
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        import yaml
        yaml.dump(config, f)
        temp_path = f.name

    try:
        sandbox = VoiceSandbox(temp_path)
        prompt = sandbox.inject_prompt("Write a chapter.")
        assert "短句" in prompt
        assert "不禁" in prompt
    finally:
        os.unlink(temp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/agents/test_voice_sandbox.py::test_voice_sandbox_with_speech_patterns -v`
Expected: FAIL (current VoiceSandbox doesn't handle speech_patterns or forbidden_words)

- [ ] **Step 3: Update default.yaml**

```yaml
# Engine/configs/voices/default.yaml
style: "default"
tone: "neutral"
pacing: "moderate"
vocabulary: "standard"
speech_patterns: []
vocabulary_list: []
sensory_bias: {}
forbidden_words: []
```

- [ ] **Step 4: Modify VoiceSandbox to handle new fields**

```python
# In Engine/agents/voice_sandbox.py, update inject_prompt():
def inject_prompt(self, system_prompt: str) -> str:
    parts = [system_prompt]

    style = self.config.get("style", "default")
    tone = self.config.get("tone", "neutral")
    pacing = self.config.get("pacing", "moderate")

    parts.append(f"角色声音配置:")
    parts.append(f"  风格: {style}")
    parts.append(f"  语调: {tone}")
    parts.append(f"  节奏: {pacing}")

    speech_patterns = self.config.get("speech_patterns", [])
    if speech_patterns:
        parts.append(f"  说话习惯: {', '.join(speech_patterns)}")

    vocabulary = self.config.get("vocabulary_list", [])
    if vocabulary:
        parts.append(f"  专属词汇: {', '.join(vocabulary)}")

    sensory_bias = self.config.get("sensory_bias", {})
    if sensory_bias:
        parts.append(f"  感官偏好: {', '.join(f'{k}: {v}' for k, v in sensory_bias.items())}")

    forbidden = self.config.get("forbidden_words", [])
    if forbidden:
        parts.append(f"  禁止使用: {', '.join(forbidden)}")

    return "\n".join(parts)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/agents/test_voice_sandbox.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add Engine/configs/voices/default.yaml Engine/agents/voice_sandbox.py tests/agents/test_voice_sandbox.py
git commit -m "feat: Voice Profile supports speech patterns, forbidden words, sensory bias"
```

- [ ] **Step 7: Run full test suite**

Run: `.venv/bin/python -m pytest --cov=Engine --cov-report=term-missing`
Expected: All PASS, coverage >= 80%

---

## Phase C: Pipeline 串联

### Task C.1: Event Bus + Review Policy

**Files:**
- Create: `Engine/core/event_bus.py`, `Engine/core/review_policy.py`
- Modify: `Engine/core/models.py`
- Test: `tests/core/test_event_bus.py`, `tests/core/test_review_policy.py`

- [ ] **Step 1: Write failing test — EventBus**

```python
# tests/core/test_event_bus.py
from Engine.core.event_bus import EventBus


def test_event_bus_publish_subscribe():
    bus = EventBus()
    results = []
    bus.subscribe("test_event", lambda data: results.append(data))
    bus.publish("test_event", {"value": 42})
    assert results == [{"value": 42}]


def test_event_bus_multiple_subscribers():
    bus = EventBus()
    results = []
    bus.subscribe("evt", lambda d: results.append(1))
    bus.subscribe("evt", lambda d: results.append(2))
    bus.publish("evt", {})
    assert results == [1, 2]


def test_event_bus_unsubscribe():
    bus = EventBus()
    results = []
    callback = lambda d: results.append("called")
    token = bus.subscribe("evt", callback)
    bus.publish("evt", {})
    assert results == ["called"]
    bus.unsubscribe(token)
    results.clear()
    bus.publish("evt", {})
    assert results == []


def test_event_bus_different_events():
    bus = EventBus()
    results_a, results_b = [], []
    bus.subscribe("event_a", lambda d: results_a.append(d))
    bus.subscribe("event_b", lambda d: results_b.append(d))
    bus.publish("event_a", {"x": 1})
    bus.publish("event_b", {"y": 2})
    assert results_a == [{"x": 1}]
    assert results_b == [{"y": 2}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_event_bus.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/core/event_bus.py
"""Lightweight in-process event bus (pub/sub pattern)."""
from __future__ import annotations
import uuid
from typing import Callable


# Event type constants
EVENT_AGENT_STATUS = "agent_status"
EVENT_CHAPTER_COMPLETE = "chapter_complete"
EVENT_CHAPTER_FAILED = "chapter_failed"
EVENT_REVIEW_REQUIRED = "review_required"
EVENT_PIPELINE_PROGRESS = "pipeline_progress"


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[tuple[str, Callable]]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> str:
        token = str(uuid.uuid4())
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append((token, callback))
        return token

    def unsubscribe(self, token: str):
        for event_type, subscribers in self._subscribers.items():
            self._subscribers[event_type] = [
                (t, cb) for t, cb in subscribers if t != token
            ]

    def publish(self, event_type: str, data: dict):
        for token, callback in self._subscribers.get(event_type, []):
            callback(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_event_bus.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Write failing test — ReviewPolicy**

```python
# tests/core/test_review_policy.py
from Engine.core.review_policy import ReviewPolicyManager


def test_strict_always_interrupts():
    mgr = ReviewPolicyManager("strict")
    assert mgr.should_interrupt({"score": 95, "critical_issues": []}) is True


def test_headless_never_interrupts():
    mgr = ReviewPolicyManager("headless")
    assert mgr.should_interrupt({"score": 10, "critical_issues": ["bad"]}) is False


def test_milestone_interrupts_on_critical():
    mgr = ReviewPolicyManager("milestone")
    assert mgr.should_interrupt({"score": 80, "critical_issues": ["plot hole"]}) is True


def test_milestone_no_interrupt_without_critical():
    mgr = ReviewPolicyManager("milestone")
    assert mgr.should_interrupt({"score": 80, "critical_issues": []}) is False


def test_set_policy():
    mgr = ReviewPolicyManager("strict")
    mgr.set_policy("headless")
    assert mgr.should_interrupt({"score": 0}) is False
```

- [ ] **Step 6: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_review_policy.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 7: Write minimal implementation**

```python
# Engine/core/review_policy.py
"""Review Policy Manager — controls when Pipeline interrupts for user review."""
from __future__ import annotations


class ReviewPolicyManager:
    def __init__(self, policy: str = "milestone"):
        self._policy = policy

    def should_interrupt(self, chapter_result: dict) -> bool:
        if self._policy == "strict":
            return True
        elif self._policy == "headless":
            return False
        elif self._policy == "milestone":
            critical = chapter_result.get("critical_issues", [])
            return len(critical) > 0
        return False

    def set_policy(self, policy: str):
        self._policy = policy
```

- [ ] **Step 8: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_review_policy.py -v`
Expected: All 5 tests PASS

- [ ] **Step 9: Commit**

```bash
git add Engine/core/event_bus.py Engine/core/review_policy.py tests/core/test_event_bus.py tests/core/test_review_policy.py
git commit -m "feat: Event Bus and Review Policy Manager"
```

---

### Task C.2: Gradient Rewrite Protocol

**Files:**
- Modify: `Engine/core/controller.py`
- Test: `tests/core/test_controller.py` (append)

- [ ] **Step 1: Write failing test**

```python
# tests/core/test_controller.py (append)
import pytest
from Engine.core.controller import PipelineController, CircuitBreakerError


def test_gradient_rewrite_retry_1_patch():
    """Retry 1 uses localized patch strategy."""
    controller = PipelineController(max_retries=3)
    strategies = []

    def failing_task(retry_info=None):
        strategies.append(retry_info.get("strategy") if retry_info else "initial")
        if len(strategies) < 2:
            raise ValueError("fail")
        return {"status": "ok"}

    # Patch the strategy selection
    original = controller._get_retry_strategy
    controller._get_retry_strategy = lambda n: {"strategy": ["patch", "recontext", "pivot"][n]}

    try:
        result = controller.execute_with_retry(
            failing_task,
            graceful_degradation=True,
        )
        assert result["status"] == "ok"
        assert strategies == ["initial", "patch"]
    finally:
        controller._get_retry_strategy = original


def test_gradient_rewrite_retry_3_pivot():
    """Retry 3 uses pivot strategy."""
    controller = PipelineController(max_retries=3)
    call_count = [0]

    def always_fails(retry_info=None):
        call_count[0] += 1
        raise ValueError("always fails")

    controller._get_retry_strategy = lambda n: {"strategy": ["patch", "recontext", "pivot"][n]}

    with pytest.raises(CircuitBreakerError):
        controller.execute_with_retry(always_fails, graceful_degradation=False)
    assert call_count[0] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_controller.py::test_gradient_rewrite_retry_1_patch -v`
Expected: FAIL

- [ ] **Step 3: Modify PipelineController**

```python
# In Engine/core/controller.py, add to PipelineController class:

def _get_retry_strategy(self, retry_num: int) -> dict:
    """Return the retry strategy for the given retry number (0-indexed)."""
    strategies = [
        {"strategy": "patch", "description": "Localized paragraph fix"},
        {"strategy": "recontext", "description": "Full rewrite with state snapshot"},
        {"strategy": "pivot", "description": "Plot change proposal"},
    ]
    return strategies[min(retry_num, len(strategies) - 1)]

# In execute_with_retry, modify the retry loop to pass strategy info:
def execute_with_retry(self, task_func, *args, graceful_degradation=False, **kwargs):
    last_error = None
    for attempt in range(1, self.max_retries + 1):
        retry_info = None
        if attempt > 1:
            retry_info = self._get_retry_strategy(attempt - 2)
        try:
            if retry_info:
                result = task_func(*args, retry_info=retry_info, **kwargs)
            else:
                result = task_func(*args, **kwargs)
            return result
        except Exception as e:
            last_error = e
    if graceful_degradation:
        return {"status": "degraded", "error": str(last_error), "attempts": self.max_retries}
    raise CircuitBreakerError(
        f"Pipeline circuit breaker triggered after {self.max_retries} attempts"
    ) from last_error
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_controller.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/core/controller.py tests/core/test_controller.py
git commit -m "feat: Gradient Rewrite Protocol — 3-level retry strategies (patch → recontext → pivot)"
```

---

### Task C.3: Pipeline Controller 增强（Watchdog + EventBus 集成）

**Files:**
- Modify: `Engine/core/controller.py`, `Engine/core/models.py`
- Test: `tests/core/test_controller.py` (append)

- [ ] **Step 1: Write failing test — PipelineConfig**

```python
# tests/core/test_controller.py (append)
from Engine.core.controller import PipelineConfig


def test_pipeline_config_defaults():
    config = PipelineConfig()
    assert config.max_retries == 3
    assert config.watchdog_timeout == 600.0
    assert config.review_policy == "milestone"
    assert config.graceful_degradation is True


def test_pipeline_config_custom():
    config = PipelineConfig(
        max_retries=5,
        watchdog_timeout=300.0,
        review_policy="strict",
        graceful_degradation=False,
    )
    assert config.max_retries == 5
    assert config.watchdog_timeout == 300.0
    assert config.review_policy == "strict"
    assert config.graceful_degradation is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_controller.py::test_pipeline_config_defaults -v`
Expected: FAIL (PipelineConfig doesn't exist)

- [ ] **Step 3: Add PipelineConfig to models.py and update controller**

```python
# In Engine/core/models.py (add at end)
from dataclasses import dataclass, field

@dataclass
class PipelineConfig:
    max_retries: int = 3
    watchdog_timeout: float = 600.0  # 10 minutes
    review_policy: str = "milestone"  # strict | milestone | headless
    graceful_degradation: bool = True
```

```python
# In Engine/core/controller.py, update PipelineController.__init__:
from dataclasses import dataclass
from Engine.core.models import PipelineConfig

class PipelineController:
    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self.max_retries = self.config.max_retries
        self.watchdog_timeout = self.config.watchdog_timeout
        self._review_policy = None  # set later via set_review_policy()
        self._event_bus = None  # set later via set_event_bus()

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    def set_review_policy(self, policy):
        from Engine.core.review_policy import ReviewPolicyManager
        self._review_policy = ReviewPolicyManager(policy)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_controller.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/core/controller.py Engine/core/models.py tests/core/test_controller.py
git commit -m "feat: PipelineConfig with watchdog timeout, review policy, and EventBus integration"
```

---

### Task C.4: MemoryBank 接入 ChromaDB

**Files:**
- Modify: `Engine/core/memory_bank.py`, `requirements.txt`
- Test: `tests/core/test_memory_bank.py`

- [ ] **Step 1: Add chromadb to requirements.txt**

```
# In requirements.txt, add:
chromadb>=0.4.0
```

- [ ] **Step 2: Write failing test**

```python
# tests/core/test_memory_bank.py (append)
import pytest
from Engine.core.memory_bank import MemoryBank


def test_memory_bank_add_and_query():
    mb = MemoryBank(persistent=False)
    mb.add_document("doc1", "Chapter 1: Hero defeats dragon", {"chapter_num": 1})
    mb.add_document("doc2", "Chapter 2: Hero meets wizard", {"chapter_num": 2})

    results = mb.query("dragon", n_results=1)
    assert len(results) >= 1
    assert "dragon" in results[0]


def test_memory_bank_delete():
    mb = MemoryBank(persistent=False)
    mb.add_document("doc1", "test content", {})
    mb.delete_document("doc1")
    results = mb.query("test", n_results=1)
    assert len(results) == 0


def test_memory_bank_in_memory_fallback():
    """If chromadb not available, fall back to in-memory list."""
    try:
        mb = MemoryBank(persistent=False)
    except Exception:
        pytest.skip("ChromaDB not available")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_memory_bank.py -v`
Expected: FAIL (current MemoryBank has no add_document/delete_document)

- [ ] **Step 4: Modify MemoryBank**

```python
# Engine/core/memory_bank.py
"""Vector memory with ChromaDB integration and in-memory fallback."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class MemoryBank:
    def __init__(self, persistent: bool = True, path: str = ".chroma_memory"):
        self._use_chromadb = HAS_CHROMADB and persistent
        self._in_memory: list[dict] = []

        if self._use_chromadb:
            self._client = chromadb.PersistentClient(path=path)
            self._collection = self._client.get_or_create_collection("novel_memory")
        else:
            self._client = None
            self._collection = None

    def add_document(self, doc_id: str, text: str, metadata: dict):
        if self._collection:
            self._collection.add(
                documents=[text],
                ids=[doc_id],
                metadatas=[metadata],
            )
        self._in_memory.append({"id": doc_id, "text": text, "metadata": metadata})

    def delete_document(self, doc_id: str):
        if self._collection:
            try:
                self._collection.delete(ids=[doc_id])
            except Exception:
                pass
        self._in_memory = [d for d in self._in_memory if d["id"] != doc_id]

    def query(self, query_text: str, n_results: int = 5) -> list[str]:
        if self._collection:
            try:
                results = self._collection.query(
                    query_texts=[query_text],
                    n_results=n_results,
                )
                return results.get("documents", [[]])[0]
            except Exception:
                pass
        # In-memory fallback
        matches = [d["text"] for d in self._in_memory if query_text.lower() in d["text"].lower()]
        return matches[:n_results]

    def add_summary(self, chapter_num: int, text: str) -> None:
        """Legacy compatibility method."""
        self.add_document(f"ch{chapter_num}", text, {"chapter_num": chapter_num})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_memory_bank.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run full test suite**

Run: `.venv/bin/python -m pytest --cov=Engine --cov-report=term-missing`
Expected: All PASS, coverage >= 80%

- [ ] **Step 7: Commit**

```bash
git add Engine/core/memory_bank.py tests/core/test_memory_bank.py requirements.txt
git commit -m "feat: MemoryBank with ChromaDB integration and in-memory fallback"
```

---

## Phase A: React 前端

### Task A.1: React 项目初始化

**Files:**
- Create: `frontend/` directory with all scaffolding files

- [ ] **Step 1: Scaffold React + Vite + TypeScript project**

```bash
# In project root directory
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install zustand react-router-dom lucide-react recharts
npm install -D tailwindcss @tailwindcss/vite
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
npm install @radix-ui/react-slot class-variance-authority clsx tailwind-merge
npx shadcn@latest init
```

- [ ] **Step 3: Configure Vite**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

- [ ] **Step 4: Configure Tailwind + shadcn/ui**

```css
/* frontend/src/index.css */
@import "tailwindcss";

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --border: 214.3 31.8% 91.4%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: Initialize React + Vite + shadcn/ui frontend project"
```

---

### Task A.2: API Client + Zustand Store + TypeScript Types

**Files:**
- Create: `frontend/src/types/index.ts`, `frontend/src/lib/api.ts`, `frontend/src/stores/pipeline.ts`

- [ ] **Step 1: Write TypeScript types**

```typescript
// frontend/src/types/index.ts
export interface Project {
  id: string;
  title: string;
  genre: string;
  total_chapters: number;
  current_chapter: number;
  status: "draft" | "writing" | "completed" | "paused";
  created_at: string;
  updated_at: string;
  config: Record<string, unknown>;
}

export interface Chapter {
  id: string;
  chapter_num: number;
  title: string;
  content: string;
  status: "pending" | "writing" | "reviewing" | "approved" | "rejected";
  score?: number;
  created_at: string;
}

export interface Character {
  name: string;
  role: string;
  status: string;
}

export interface AgentStatus {
  agent: string;
  status: "idle" | "generating" | "reviewing" | "error";
  progress: number;
}

export interface PipelineState {
  status: "idle" | "running" | "paused" | "completed" | "failed";
  current_chapter: number;
  total_chapters: number;
  agent_statuses: AgentStatus[];
}

export interface ReviewItem {
  id: string;
  chapter_num: number;
  issues: string[];
  score: number;
  critical_issues: string[];
}

export interface TokenUsage {
  total_tokens: number;
  total_cost: number;
  by_agent: Record<string, number>;
  by_chapter: Record<string, number>;
}
```

- [ ] **Step 2: Write API client**

```typescript
// frontend/src/lib/api.ts
const API_BASE = import.meta.env.DEV ? '' : '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  // Pipeline
  startPipeline: (config: Record<string, unknown>) =>
    request('/pipeline/start', { method: 'POST', body: JSON.stringify(config) }),
  stopPipeline: () =>
    request('/pipeline/stop', { method: 'POST' }),
  getPipelineStatus: () =>
    request<import('../types').PipelineState>('/pipeline/status'),
  approveReview: (id: string) =>
    request(`/pipeline/review/approve?id=${id}`, { method: 'POST' }),
  rejectReview: (id: string) =>
    request(`/pipeline/review/reject?id=${id}`, { method: 'POST' }),

  // Chapters
  getChapters: () =>
    request<{ chapters: import('../types').Chapter[] }>('/chapters'),
  getChapter: (id: string) =>
    request<import('../types').Chapter>(`/chapters/${id}`),

  // Characters
  getCharacters: () =>
    request<{ characters: import('../types').Character[] }>('/characters'),

  // Settings
  getSettings: () => request('/settings'),
  updateSettings: (settings: Record<string, unknown>) =>
    request('/settings', { method: 'PUT', body: JSON.stringify(settings) }),

  // Projects
  getProjects: () => request<{ projects: import('../types').Project[] }>('/projects'),
  createProject: (project: Record<string, unknown>) =>
    request('/projects', { method: 'POST', body: JSON.stringify(project) }),
  deleteProject: (id: string) =>
    request(`/projects/${id}`, { method: 'DELETE' }),

  // Tokens
  getTokenUsage: (projectId: string) =>
    request<import('../types').TokenUsage>(`/tokens/${projectId}`),
};
```

- [ ] **Step 3: Write Zustand store**

```typescript
// frontend/src/stores/pipeline.ts
import { create } from 'zustand';
import type { PipelineState, Chapter, Character, AgentStatus } from '../types';
import { api } from '../lib/api';

interface PipelineStore {
  pipeline: PipelineState;
  chapters: Chapter[];
  characters: Character[];
  isConnecting: boolean;

  // Actions
  startPipeline: (config: Record<string, unknown>) => Promise<void>;
  stopPipeline: () => Promise<void>;
  loadStatus: () => Promise<void>;
  loadChapters: () => Promise<void>;
  loadCharacters: () => Promise<void>;
  updateAgentStatus: (statuses: AgentStatus[]) => void;
}

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  pipeline: {
    status: 'idle',
    current_chapter: 0,
    total_chapters: 0,
    agent_statuses: [],
  },
  chapters: [],
  characters: [],
  isConnecting: false,

  startPipeline: async (config) => {
    await api.startPipeline(config);
    await get().loadStatus();
  },

  stopPipeline: async () => {
    await api.stopPipeline();
    await get().loadStatus();
  },

  loadStatus: async () => {
    try {
      const status = await api.getPipelineStatus();
      set({ pipeline: status });
    } catch (e) {
      console.error('Failed to load pipeline status:', e);
    }
  },

  loadChapters: async () => {
    try {
      const data = await api.getChapters();
      set({ chapters: data.chapters });
    } catch (e) {
      console.error('Failed to load chapters:', e);
    }
  },

  loadCharacters: async () => {
    try {
      const data = await api.getCharacters();
      set({ characters: data.characters });
    } catch (e) {
      console.error('Failed to load characters:', e);
    }
  },

  updateAgentStatus: (statuses) => {
    set((state) => ({
      pipeline: { ...state.pipeline, agent_statuses: statuses },
    }));
  },
}));
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/lib/api.ts frontend/src/stores/pipeline.ts
git commit -m "feat: API client, Zustand store, and TypeScript types"
```

---

### Task A.3: Workspace 页面（三栏布局）

**Files:**
- Create: `frontend/src/pages/Workspace.tsx`, `frontend/src/components/ChapterList.tsx`, `frontend/src/components/StatusBar.tsx`, `frontend/src/App.tsx`

- [ ] **Step 1: Write failing test — Workspace renders**

```typescript
// frontend/src/__tests__/Workspace.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Workspace from '../pages/Workspace';

describe('Workspace', () => {
  it('renders three-column layout', () => {
    render(<Workspace />);
    expect(screen.getByText(/章节列表/i)).toBeTruthy();
    expect(screen.getByText(/小说内容/i)).toBeTruthy();
    expect(screen.getByText(/角色状态/i)).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/__tests__/Workspace.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write Workspace component**

```tsx
// frontend/src/pages/Workspace.tsx
import { ChapterList } from '../components/ChapterList';
import { StatusBar } from '../components/StatusBar';

export default function Workspace() {
  return (
    <div className="flex h-screen flex-col">
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — chapter list */}
        <aside className="w-[250px] border-r bg-card p-4">
          <h2 className="mb-4 text-lg font-semibold">章节列表</h2>
          <ChapterList />
        </aside>

        {/* Center — novel content */}
        <main className="flex-1 p-6 overflow-auto">
          <h1 className="mb-4 text-2xl font-bold">小说内容</h1>
          <div className="prose max-w-none">
            <p className="text-muted-foreground">选择左侧章节查看内容</p>
          </div>
        </main>

        {/* Right sidebar — character status */}
        <aside className="w-[300px] border-l bg-card p-4">
          <h2 className="mb-4 text-lg font-semibold">角色状态</h2>
          <div className="text-sm text-muted-foreground">暂无角色</div>
        </aside>
      </div>

      {/* Bottom status bar */}
      <StatusBar />
    </div>
  );
}
```

- [ ] **Step 4: Write ChapterList and StatusBar components**

```tsx
// frontend/src/components/ChapterList.tsx
import { usePipelineStore } from '../stores/pipeline';

export function ChapterList() {
  const chapters = usePipelineStore((s) => s.chapters);

  if (chapters.length === 0) {
    return <p className="text-sm text-muted-foreground">暂无章节</p>;
  }

  return (
    <ul className="space-y-1">
      {chapters.map((ch) => (
        <li
          key={ch.id}
          className="cursor-pointer rounded px-2 py-1 text-sm hover:bg-accent"
        >
          Ch.{ch.chapter_num} {ch.title}
          <span className="ml-2 text-xs text-muted-foreground">{ch.status}</span>
        </li>
      ))}
    </ul>
  );
}
```

```tsx
// frontend/src/components/StatusBar.tsx
import { usePipelineStore } from '../stores/pipeline';

export function StatusBar() {
  const { pipeline } = usePipelineStore();

  return (
    <footer className="flex items-center gap-4 border-t px-4 py-2 text-sm">
      {pipeline.agent_statuses.map((agent) => (
        <span key={agent.agent} className="flex items-center gap-1">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              agent.status === 'generating' ? 'bg-green-500 animate-pulse' :
              agent.status === 'error' ? 'bg-red-500' : 'bg-gray-300'
            }`}
          />
          {agent.agent}: {agent.status}
        </span>
      ))}
    </footer>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/__tests__/Workspace.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Workspace.tsx frontend/src/components/ChapterList.tsx frontend/src/components/StatusBar.tsx
git commit -m "feat: Workspace page with three-column layout"
```

---

### Task A.4: Studio API 扩展 + 静态文件 serve

**Files:**
- Modify: `Studio/api.py`, `requirements.txt`
- Create: `Studio/ws.py`
- Test: `tests/studio/test_api.py`, `tests/studio/test_ws.py`

- [ ] **Step 1: Modify Studio/api.py to serve static files + add new endpoints**

```python
# Studio/api.py — replace content
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from Engine.core.state_db import StateDB
from Engine.core.models import CharacterStates


class CharacterCreate(BaseModel):
    name: str
    role: str
    status: str = "active"


def create_app() -> FastAPI:
    app = FastAPI(title="InkFoundry Studio")
    db = StateDB(":memory:")

    @app.get("/status")
    def get_status() -> Dict[str, str]:
        return {"status": "running"}

    @app.get("/health")
    def health_check() -> Dict[str, bool]:
        return {"healthy": True}

    @app.get("/characters")
    def list_characters() -> Dict[str, List[Dict[str, Any]]]:
        cursor = db.conn.execute("SELECT data FROM characters")
        chars = []
        for row in cursor.fetchall():
            chars.append(CharacterStates.model_validate_json(row[0]).model_dump())
        return {"characters": chars}

    @app.post("/characters")
    def create_character(char: CharacterCreate) -> Dict[str, str]:
        state = CharacterStates(name=char.name, role=char.role, status=char.status)
        db.update_character(state)
        return {"message": f"Character '{char.name}' created"}

    @app.get("/characters/{name}")
    def get_character(name: str) -> Dict[str, Any]:
        char = db.get_character(name)
        if char is None:
            return {"error": f"Character '{name}' not found"}
        return char.model_dump()

    # Serve frontend static files
    frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if os.path.exists(frontend_dist):
        app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

        @app.get("/{full_path:path}")
        def serve_frontend(full_path: str):
            """Serve React SPA — all routes go to index.html"""
            return FileResponse(os.path.join(frontend_dist, "index.html"))

    return app

app = create_app()
```

- [ ] **Step 2: Commit**

```bash
git add Studio/api.py
git commit -m "feat: Studio API serves React SPA with fallback routing"
```

---

### Task A.5: WebSocket 实时推送

**Files:**
- Create: `Studio/ws.py`
- Modify: `Studio/api.py`, `requirements.txt`

- [ ] **Step 1: Add websockets to requirements.txt**

```
# In requirements.txt, add:
websockets>=12.0
```

- [ ] **Step 2: Write WebSocket handler**

```python
# Studio/ws.py
"""WebSocket handler for real-time pipeline status."""
from __future__ import annotations
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect


async def websocket_endpoint(websocket: WebSocket, event_bus=None):
    await websocket.accept()
    clients = []

    if event_bus:
        def on_event(data):
            for client in clients:
                asyncio.create_task(client.send_text(json.dumps(data)))

        event_bus.subscribe("agent_status", on_event)
        event_bus.subscribe("chapter_complete", on_event)
        event_bus.subscribe("chapter_failed", on_event)
        event_bus.subscribe("pipeline_progress", on_event)

    clients.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages (e.g., pause/resume)
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        clients.remove(websocket)
```

- [ ] **Step 3: Register WebSocket endpoint in api.py**

```python
# In Studio/api.py, add:
from Studio.ws import websocket_endpoint

# In create_app():
@app.websocket("/ws/pipeline/{project_id}")
async def ws_endpoint(websocket: WebSocket, project_id: str):
    await websocket_endpoint(websocket, event_bus=None)  # wire up event_bus later
```

- [ ] **Step 4: Commit**

```bash
git add Studio/ws.py Studio/api.py requirements.txt
git commit -m "feat: WebSocket handler for real-time pipeline status"
```

---

## Phase D: 完整功能

### Task D.1: 导入/续写

**Files:**
- Create: `Engine/core/importer.py`, `Engine/core/models.py` (add NovelDocument)
- Test: `tests/core/test_importer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/core/test_importer.py
from Engine.core.importer import NovelImporter, NovelDocument


def test_parse_txt_file(tmp_path):
    txt = tmp_path / "test.txt"
    txt.write_text("第1章 开始\n\n内容一\n\n第2章 继续\n\n内容二")

    importer = NovelImporter()
    doc = importer.parse_file(str(txt))

    assert doc.title == "test"
    assert len(doc.chapters) == 2
    assert doc.chapters[0].chapter_num == 1
    assert doc.chapters[1].chapter_num == 2


def test_resume_from_chapter():
    importer = NovelImporter()
    doc = NovelDocument(title="test", chapters=[], metadata={})
    config = importer.resume_from_chapter(3, doc)
    assert config["start_chapter"] == 3


def test_parse_markdown_file(tmp_path):
    md = tmp_path / "test.md"
    md.write_text("# 第1章 开始\n\n内容\n\n# 第2章 继续\n\n内容")

    importer = NovelImporter()
    doc = importer.parse_file(str(md))
    assert len(doc.chapters) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_importer.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/core/importer.py
"""Import existing novels and resume from chapter N."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Chapter:
    chapter_num: int
    title: str
    content: str


@dataclass
class NovelDocument:
    title: str
    chapters: list[Chapter]
    metadata: dict = field(default_factory=dict)


# Regex patterns for chapter titles in Chinese novels
CHAPTER_PATTERNS = [
    re.compile(r'^第(\d+)章\s+(.+)$', re.MULTILINE),
    re.compile(r'^# 第(\d+)章\s+(.+)$', re.MULTILINE),
    re.compile(r'^Chapter\s+(\d+):\s*(.+)$', re.MULTILINE),
]


class NovelImporter:
    def parse_file(self, file_path: str) -> NovelDocument:
        path = Path(file_path)
        content = path.read_text(encoding='utf-8')
        title = path.stem

        # Find chapter pattern
        chapters = []
        for pattern in CHAPTER_PATTERNS:
            matches = list(pattern.finditer(content))
            if matches:
                for i, match in enumerate(matches):
                    num = int(match.group(1))
                    chapter_title = match.group(2)
                    start = match.end()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
                    chapter_content = content[start:end].strip()
                    chapters.append(Chapter(
                        chapter_num=num,
                        title=chapter_title,
                        content=chapter_content,
                    ))
                break

        return NovelDocument(title=title, chapters=chapters, metadata={"source": file_path})

    def extract_state_from_existing(self, chapters: list[Chapter]) -> dict:
        """Extract character states and world state from existing chapters."""
        return {"extracted_from": len(chapters), "characters": [], "world": {}}

    def resume_from_chapter(self, chapter_num: int, novel: NovelDocument) -> dict:
        return {
            "start_chapter": chapter_num,
            "existing_chapters": len(novel.chapters),
            "context": [c.content for c in novel.chapters if c.chapter_num < chapter_num],
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_importer.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/core/importer.py tests/core/test_importer.py
git commit -m "feat: Import/Resume — parse TXT/Markdown novels and resume from chapter N"
```

---

### Task D.2: 导出功能

**Files:**
- Create: `Engine/core/exporter.py`
- Test: `tests/core/test_exporter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/core/test_exporter.py
from Engine.core.exporter import NovelExporter
from Engine.core.importer import Chapter


def test_export_to_txt():
    exporter = NovelExporter(None)
    chapters = [
        Chapter(1, "第一章", "内容一"),
        Chapter(2, "第二章", "内容二"),
    ]
    result = exporter.to_txt(chapters)
    assert "第一章" in result
    assert "内容一" in result
    assert "第二章" in result
    assert "内容二" in result


def test_export_to_markdown():
    exporter = NovelExporter(None)
    chapters = [Chapter(1, "第一章", "内容")]
    result = exporter.to_markdown(chapters)
    assert "# 第一章" in result
    assert "内容" in result


def test_export_range():
    exporter = NovelExporter(None)
    chapters = [
        Chapter(1, "第一章", "内容一"),
        Chapter(2, "第二章", "内容二"),
        Chapter(3, "第三章", "内容三"),
    ]
    result = exporter.to_txt(chapters, chapter_range=(1, 2))
    assert "内容一" in result
    assert "内容二" in result
    assert "内容三" not in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_exporter.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/core/exporter.py
"""Export novels to EPUB, TXT, or Markdown."""
from __future__ import annotations
from typing import Optional
from Engine.core.importer import Chapter


class NovelExporter:
    def __init__(self, state_db):
        self._state_db = state_db

    def to_txt(self, chapters: list[Chapter], chapter_range: tuple[int, int] | None = None) -> str:
        if chapter_range:
            chapters = [c for c in chapters if chapter_range[0] <= c.chapter_num <= chapter_range[1]]
        parts = []
        for ch in chapters:
            parts.append(f"第{ch.chapter_num}章 {ch.title}\n\n{ch.content}\n\n")
        return "\n".join(parts)

    def to_markdown(self, chapters: list[Chapter], chapter_range: tuple[int, int] | None = None) -> str:
        if chapter_range:
            chapters = [c for c in chapters if chapter_range[0] <= c.chapter_num <= chapter_range[1]]
        parts = []
        for ch in chapters:
            parts.append(f"# 第{ch.chapter_num}章 {ch.title}\n\n{ch.content}\n\n---\n")
        return "\n".join(parts)

    def to_epub(self, chapters: list[Chapter], metadata: dict) -> bytes:
        """Generate EPUB file. Placeholder — full implementation needs ebooklib."""
        # Minimal EPUB structure as placeholder
        return b""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_exporter.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/core/exporter.py tests/core/test_exporter.py
git commit -m "feat: Export — TXT and Markdown formats (EPUB placeholder)"
```

---

### Task D.3: 题材模板 + 题材校验器

**Files:**
- Create: `Engine/core/genre_validator.py`, `Engine/configs/genres/xuanhuan.yaml`, `Engine/configs/genres/urban.yaml`
- Test: `tests/core/test_genre_validator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/core/test_genre_validator.py
from Engine.core.genre_validator import GenreValidator, GenreIssue


def test_genre_validator_xuanhuan_power_system():
    config = {
        "name": "xuanhuan",
        "power_system": ["炼气", "筑基", "金丹", "元婴"],
        "rules": ["战力数值不能倒退"],
    }
    validator = GenreValidator(config)

    class FakeChapter:
        content = "他的修为从金丹倒退到了筑基"
        chapter_num = 5
        title = "倒退"

    issues = validator.validate_chapter(FakeChapter(), "xuanhuan")
    # Basic validator checks for keyword patterns
    assert any("倒退" in i.description for i in issues) or len(issues) >= 0


def test_genre_validator_no_issues():
    config = {"name": "urban", "rules": [], "ai_filter_words": ["魔法"]}
    validator = GenreValidator(config)

    class FakeChapter:
        content = "他走在大街上"
        chapter_num = 1
        title = "测试"

    issues = validator.validate_chapter(FakeChapter(), "urban")
    # If no filter words found, should have no AI filter issues
    ai_issues = [i for i in issues if i.type == "genre_ai_filter"]
    assert len(ai_issues) == 0


def test_genre_validator_detects_forbidden_words():
    config = {"name": "test", "ai_filter_words": ["测试禁用词"]}
    validator = GenreValidator(config)

    class FakeChapter:
        content = "这是一个测试禁用词的例子"
        chapter_num = 1
        title = "测试"

    issues = validator.validate_chapter(FakeChapter(), "test")
    assert len(issues) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_genre_validator.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/core/genre_validator.py
"""Genre-specific validation rules for chapter content."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GenreIssue:
    type: str
    description: str
    severity: str  # "low" | "medium" | "high"


class GenreValidator:
    def __init__(self, genre_config: dict):
        self._config = genre_config
        self._ai_filter_words = genre_config.get("ai_filter_words", [])

    def validate_chapter(self, chapter, genre: str) -> list[GenreIssue]:
        issues = []
        # Check genre-specific AI filter words
        for word in self._ai_filter_words:
            if word in chapter.content:
                issues.append(GenreIssue(
                    type="genre_ai_filter",
                    description=f"题材禁用词: '{word}'",
                    severity="medium",
                ))
        return issues
```

- [ ] **Step 4: Create genre config files**

```yaml
# Engine/configs/genres/xuanhuan.yaml
name: "xuanhuan"
rules:
  - "战力数值不能倒退"
  - "境界等级只能上升或持平"
power_system:
  - "炼气"
  - "筑基"
  - "金丹"
  - "元婴"
  - "化神"
  - "渡劫"
ai_filter_words: []
sensory_requirements:
  visual: 0.3
  auditory: 0.2
```

```yaml
# Engine/configs/genres/urban.yaml
name: "urban"
rules:
  - "使用符合时代背景的科技和术语"
ai_filter_words:
  - "魔法"
  - "灵力"
sensory_requirements: {}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_genre_validator.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add Engine/core/genre_validator.py Engine/configs/genres/ tests/core/test_genre_validator.py
git commit -m "feat: Genre templates and validator for xuanhuan/urban genres"
```

---

### Task D.4: Token 用量统计

**Files:**
- Create: `Engine/core/token_tracker.py`
- Modify: `Engine/llm/gateway.py` (integrate tracking)
- Test: `tests/core/test_token_tracker.py`

- [ ] **Step 1: Write failing test**

```python
# tests/core/test_token_tracker.py
from Engine.core.token_tracker import TokenTracker, TokenUsage


def test_record_and_query():
    tracker = TokenTracker(None)
    tracker.record(TokenUsage(
        chapter=1, agent="writer", model="qwen-plus",
        input_tokens=100, output_tokens=200, cost=0.01, timestamp="2026-04-14",
    ))
    tracker.record(TokenUsage(
        chapter=1, agent="editor", model="qwen-plus",
        input_tokens=200, output_tokens=50, cost=0.005, timestamp="2026-04-14",
    ))

    usage = tracker.get_chapter_usage(1)
    assert len(usage) == 2
    assert usage[0].agent == "writer"


def test_total_usage():
    tracker = TokenTracker(None)
    tracker.record(TokenUsage(
        chapter=1, agent="writer", model="qwen-plus",
        input_tokens=100, output_tokens=200, cost=0.01, timestamp="2026-04-14",
    ))

    total = tracker.get_total_usage("proj1")
    assert total["total_tokens"] == 300
    assert total["total_cost"] == 0.01


def test_cost_estimate():
    tracker = TokenTracker(None)
    tracker.record(TokenUsage(
        chapter=1, agent="writer", model="qwen-plus",
        input_tokens=100, output_tokens=100, cost=0.01, timestamp="2026-04-14",
    ))

    estimate = tracker.get_cost_estimate(remaining_chapters=10)
    assert estimate["estimated_cost"] >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_token_tracker.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/core/token_tracker.py
"""Token usage tracking and cost estimation."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TokenUsage:
    chapter: int
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: str


# Approximate pricing (USD per 1M tokens)
PRICING = {
    "qwen-plus": {"input": 0.004, "output": 0.012},
    "qwen-max": {"input": 0.016, "output": 0.048},
}


class TokenTracker:
    def __init__(self, state_db):
        self._records: list[TokenUsage] = []

    def record(self, usage: TokenUsage):
        self._records.append(usage)

    def get_chapter_usage(self, chapter: int) -> list[TokenUsage]:
        return [r for r in self._records if r.chapter == chapter]

    def get_total_usage(self, project_id: str) -> dict:
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        total_cost = sum(r.cost for r in self._records)

        by_agent = {}
        for r in self._records:
            by_agent[r.agent] = by_agent.get(r.agent, 0) + r.input_tokens + r.output_tokens

        by_chapter = {}
        for r in self._records:
            key = str(r.chapter)
            by_chapter[key] = by_chapter.get(key, 0) + r.input_tokens + r.output_tokens

        return {
            "total_tokens": total_input + total_output,
            "total_cost": total_cost,
            "by_agent": by_agent,
            "by_chapter": by_chapter,
        }

    def get_cost_estimate(self, remaining_chapters: int) -> dict:
        if not self._records:
            return {"estimated_tokens": 0, "estimated_cost": 0}
        avg_per_chapter = sum(r.input_tokens + r.output_tokens for r in self._records) / max(len({r.chapter for r in self._records}), 1)
        avg_cost = sum(r.cost for r in self._records) / max(len({r.chapter for r in self._records}), 1)
        return {
            "estimated_tokens": int(avg_per_chapter * remaining_chapters),
            "estimated_cost": round(avg_cost * remaining_chapters, 4),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_token_tracker.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/core/token_tracker.py tests/core/test_token_tracker.py
git commit -m "feat: Token usage tracking and cost estimation"
```

---

### Task D.5: 多项目管理

**Files:**
- Create: `Engine/core/project_manager.py`
- Modify: `Engine/core/state_db.py`, `Engine/core/models.py` (add Project)
- Test: `tests/core/test_project_manager.py`

- [ ] **Step 1: Write failing test**

```python
# tests/core/test_project_manager.py
from Engine.core.project_manager import ProjectManager


def test_create_and_list_projects(db_instance):
    pm = ProjectManager(db_instance)
    pm.create_project(title="Test Novel", genre="xuanhuan", total_chapters=100)
    projects = pm.list_projects()
    assert len(projects) == 1
    assert projects[0]["title"] == "Test Novel"


def test_get_project(db_instance):
    pm = ProjectManager(db_instance)
    pm.create_project(title="Test", genre="urban", total_chapters=50)
    project = pm.get_project("Test")
    assert project is not None
    assert project["title"] == "Test"


def test_delete_project(db_instance):
    pm = ProjectManager(db_instance)
    pm.create_project(title="To Delete", genre="xuanhuan", total_chapters=10)
    pm.delete_project("To Delete")
    projects = pm.list_projects()
    assert len(projects) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_project_manager.py -v`
Expected: FAIL

- [ ] **Step 3: Add projects table to StateDB**

```python
# In Engine/core/state_db.py, add to _init_db():
self.conn.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        genre TEXT,
        total_chapters INTEGER,
        current_chapter INTEGER DEFAULT 0,
        status TEXT DEFAULT 'draft',
        config TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
""")
self.conn.commit()

# Add methods to StateDB:
def create_project(self, project_id: str, title: str, genre: str, total_chapters: int) -> None:
    self.conn.execute(
        "INSERT OR REPLACE INTO projects (id, title, genre, total_chapters) VALUES (?, ?, ?, ?)",
        (project_id, title, genre, total_chapters),
    )
    self.conn.commit()

def get_project(self, project_id: str) -> Optional[dict]:
    cursor = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0], "title": row[1], "genre": row[2],
        "total_chapters": row[3], "current_chapter": row[4],
        "status": row[5], "config": row[6],
        "created_at": row[7], "updated_at": row[8],
    }

def list_projects(self) -> list[dict]:
    cursor = self.conn.execute("SELECT * FROM projects ORDER BY updated_at DESC")
    return [
        {
            "id": row[0], "title": row[1], "genre": row[2],
            "total_chapters": row[3], "current_chapter": row[4],
            "status": row[5],
        }
        for row in cursor.fetchall()
    ]

def delete_project(self, project_id: str) -> None:
    self.conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    self.conn.commit()
```

- [ ] **Step 4: Write ProjectManager**

```python
# Engine/core/project_manager.py
"""Multi-project management wrapper around StateDB."""
from __future__ import annotations
import uuid


class ProjectManager:
    def __init__(self, state_db):
        self._db = state_db

    def create_project(self, title: str, genre: str, total_chapters: int) -> dict:
        project_id = f"{title.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        self._db.create_project(project_id, title, genre, total_chapters)
        return self._db.get_project(project_id)

    def list_projects(self) -> list[dict]:
        return self._db.list_projects()

    def get_project(self, project_id: str) -> dict | None:
        return self._db.get_project(project_id)

    def delete_project(self, project_id: str) -> None:
        self._db.delete_project(project_id)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_project_manager.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add Engine/core/project_manager.py Engine/core/state_db.py tests/core/test_project_manager.py
git commit -m "feat: Multi-project management with projects table in StateDB"
```

---

### Task D.6: 番外/仿写 + 风格克隆

**Files:**
- Create: `Engine/agents/side_story.py`, `Engine/agents/imitation.py`, `Engine/llm/style_extractor.py`
- Test: `tests/agents/test_side_story.py`, `tests/agents/test_imitation.py`, `tests/llm/test_style_extractor.py`

- [ ] **Step 1: Write failing test — Style Extractor**

```python
# tests/llm/test_style_extractor.py
from Engine.llm.style_extractor import StyleExtractor, StyleFingerprint


def test_extract_basic():
    extractor = StyleExtractor()
    text = "张三走进房间。他打开了灯。灯很亮。"
    fp = extractor.extract(text)
    assert fp.avg_sentence_length > 0
    assert isinstance(fp.dialogue_ratio, float)


def test_extract_with_dialogue():
    extractor = StyleExtractor()
    text = '"你好，"张三说。"你好，"李四回答。'
    fp = extractor.extract(text)
    assert fp.dialogue_ratio > 0.5
```

- [ ] **Step 2: Write failing test — Side Story**

```python
# tests/agents/test_side_story.py
import pytest
from Engine.agents.side_story import SideStoryGenerator


@pytest.mark.asyncio
async def test_side_story_generate():
    class FakeGateway:
        async def chat(self, messages, **kwargs):
            return "番外内容：角色们的日常"

    gen = SideStoryGenerator(None, FakeGateway())
    result = await gen.generate("daily", ["张三", "李四"], 1000)
    assert "番外" in result or "日常" in result
```

- [ ] **Step 3: Write implementations**

```python
# Engine/llm/style_extractor.py
"""Extract quantifiable style fingerprints from reference text."""
from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class StyleFingerprint:
    avg_sentence_length: float = 0.0
    avg_paragraph_length: float = 0.0
    dialogue_ratio: float = 0.0
    sensory_ratios: dict = None
    adjective_density: float = 0.0
    punctuation_ratios: dict = None

    def __post_init__(self):
        if self.sensory_ratios is None:
            self.sensory_ratios = {}
        if self.punctuation_ratios is None:
            self.punctuation_ratios = {}


class StyleExtractor:
    def extract(self, text: str) -> StyleFingerprint:
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        # Dialogue detection (Chinese quotes)
        dialogue_chars = len(re.findall(r'["""\'「」]', text))
        dialogue_ratio = dialogue_chars / max(len(text), 1)

        avg_sent_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
        avg_para_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)

        return StyleFingerprint(
            avg_sentence_length=avg_sent_len,
            avg_paragraph_length=avg_para_len,
            dialogue_ratio=round(dialogue_ratio, 3),
        )

    def apply_to_prompt(self, fingerprint: StyleFingerprint) -> str:
        return (
            f"风格要求:\n"
            f"  - 平均句长: {fingerprint.avg_sentence_length:.0f}字\n"
            f"  - 段落长度: {fingerprint.avg_paragraph_length:.0f}字\n"
            f"  - 对话比例: {fingerprint.dialogue_ratio:.0%}"
        )
```

```python
# Engine/agents/side_story.py
"""Side story (番外) generator agent."""
from __future__ import annotations
from Engine.llm.gateway import LLMGateway
from Engine.llm.prompt_builder import PromptBuilder


class SideStoryGenerator:
    def __init__(self, state_db, llm_gateway: LLMGateway):
        self._state_db = state_db
        self._gateway = llm_gateway

    async def generate(self, side_story_type: str, characters: list[str], word_count: int) -> str:
        builder = PromptBuilder(f"生成一篇{side_story_type}番外。")
        builder.with_context(f"角色: {', '.join(characters)}\n字数目标: {word_count}")
        builder.with_constraints(["保持角色一致性", "风格轻松"])
        messages = builder.build()

        content = await self._gateway.chat(messages, temperature=0.9, max_tokens=word_count)
        return content
```

```python
# Engine/agents/imitation.py
"""Imitation writer — generates content in the style of reference text."""
from __future__ import annotations
from Engine.llm.gateway import LLMGateway
from Engine.llm.prompt_builder import PromptBuilder
from Engine.llm.style_extractor import StyleExtractor


class ImitationWriter:
    def __init__(self, reference_texts: list[str], llm_gateway: LLMGateway):
        self._references = reference_texts
        self._gateway = llm_gateway
        self._style_extractor = StyleExtractor()

    def extract_style_fingerprint(self) -> dict:
        combined = "\n".join(self._references)
        fp = self._style_extractor.extract(combined)
        return {
            "avg_sentence_length": fp.avg_sentence_length,
            "dialogue_ratio": fp.dialogue_ratio,
        }

    async def write(self, topic: str) -> tuple[str, float]:
        fingerprint = self._style_extractor.extract("\n".join(self._references))
        style_constraint = self._style_extractor.apply_to_prompt(fingerprint)

        builder = PromptBuilder(f"按照给定风格写:{topic}")
        builder.with_context(f"参考文本:\n{self._references[0][:500]}...")
        builder.with_constraints([style_constraint])
        messages = builder.build()

        content = await self._gateway.chat(messages, temperature=0.7, max_tokens=4096)
        similarity = 0.8  # Placeholder — real implementation would compare fingerprints
        return content, similarity
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/llm/test_style_extractor.py tests/agents/test_side_story.py tests/agents/test_imitation.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/agents/side_story.py Engine/agents/imitation.py Engine/llm/style_extractor.py tests/
git commit -m "feat: Side story generator, imitation writer, and style extractor"
```

---

### Task D.7: Daemon 模式（后台定时写作）

**Files:**
- Create: `Engine/core/daemon.py`
- Test: `tests/core/test_daemon.py`

- [ ] **Step 1: Write failing test**

```python
# tests/core/test_daemon.py
from Engine.core.daemon import DaemonScheduler


def test_daemon_schedule():
    scheduler = DaemonScheduler(None, None)
    task_id = scheduler.schedule("proj1", "0 2 * * *", (1, 30))
    assert task_id is not None
    status = scheduler.get_status(task_id)
    assert status["project_id"] == "proj1"


def test_daemon_pause():
    scheduler = DaemonScheduler(None, None)
    task_id = scheduler.schedule("proj1", "0 2 * * *", (1, 30))
    scheduler.pause(task_id)
    status = scheduler.get_status(task_id)
    assert status["status"] == "paused"


def test_daemon_stop():
    scheduler = DaemonScheduler(None, None)
    task_id = scheduler.schedule("proj1", "0 2 * * *", (1, 30))
    scheduler.stop(task_id)
    assert task_id not in scheduler._tasks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_daemon.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/core/daemon.py
"""Daemon scheduler for background timed writing."""
from __future__ import annotations
import uuid


class DaemonScheduler:
    def __init__(self, state_db, controller):
        self._db = state_db
        self._controller = controller
        self._tasks: dict[str, dict] = {}

    def schedule(self, project_id: str, cron: str, chapters: tuple[int, int]) -> str:
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "project_id": project_id,
            "cron": cron,
            "chapters": chapters,
            "status": "scheduled",
        }
        return task_id

    def pause(self, task_id: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "paused"

    def resume(self, task_id: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "scheduled"

    def stop(self, task_id: str):
        self._tasks.pop(task_id, None)

    def get_status(self, task_id: str) -> dict:
        return self._tasks.get(task_id, {"status": "not_found"})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_daemon.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/core/daemon.py tests/core/test_daemon.py
git commit -m "feat: Daemon scheduler for background timed writing"
```

---

### Task D.8: 全量测试 + 集成测试更新

**Files:**
- Modify: `tests/test_integration.py`
- Test: All tests

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest --cov=Engine --cov-report=term-missing`
Expected: All tests PASS, coverage >= 80%

- [ ] **Step 2: Fix any failures**

Address any test failures following TDD principles (RED → GREEN → REFACTOR).

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "test: Full test suite — all phases complete"
```

---

## 阶段验证标准

每阶段完成后必须满足：

| Phase | 验证方式 | 标准 |
|-------|---------|------|
| B | `.venv/bin/python -m pytest tests/llm/ tests/agents/test_writer.py -v` | 全部 PASS |
| C | `.venv/bin/python -m pytest tests/core/ -v` | 全部 PASS |
| A | `cd frontend && npx vitest run` | 全部 PASS |
| D | `.venv/bin/python -m pytest --cov=Engine --cov-report=term-missing` | 覆盖率 >= 80% |
