"""AgentDojo integration: custom Defense B pipeline element + Together backend.

Two classes intended to plug into AgentDojo's `AgentPipeline`:

- `V121JudgeDefense`: a `BasePipelineElement` subclass that applies the v1.21
  §3.2 Sonnet judge to the agent's conversation. If the judge returns
  HIJACKED (or AMBIGUOUS, collapsed conservatively), raises `AbortAgentError`
  to halt the agent's execution. This is "Defense B" inside AgentDojo's
  framework.

- `TogetherLLM`: subclass of `OpenAILLM` that points at Together AI's
  OpenAI-compatible endpoint. Lets us use Llama 3.3 70B Instruct Turbo and
  Qwen 3 235B-A22B-Instruct as agents inside AgentDojo without forking the
  framework.

Driver script: `scripts/run_agentdojo_eval.py` builds the pipeline and runs
suites with these classes.
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Optional

from openai import OpenAI

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.errors import AbortAgentError
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.types import ChatMessage, get_text_content_as_str

from src.defense_b.judge import ClaudeJudge


class V121JudgeDefense(BasePipelineElement):
    """Defense B as an AgentDojo pipeline element.

    Applies operational_definitions.md §3.2 v1.21 (text-level) OR v1.24
    (tool-call-aware) Sonnet 4.6 judge to the agent's conversation so far.
    If the judge classifies the conversation as HIJACKED (or AMBIGUOUS,
    collapsed conservatively), raises AbortAgentError to halt the agent.

    Placement in the pipeline: inside the ToolsExecutionLoop, BEFORE the
    ToolsExecutor. This way the judge inspects each proposed tool-call
    message and can abort BEFORE the tool's side effects execute, which
    is the only way Defense B can actually prevent action-level hijack
    (as opposed to detecting it post-hoc).

    Args:
        judge: a `ClaudeJudge` instance.
        rubric_version: "v1.21" for text-level rubric; "v1.24" for the
            tool-call-aware variant designed for AgentDojo. Default "v1.24"
            since AgentDojo evaluation is the primary use of this class.
        raise_on_hijack: whether to raise `AbortAgentError` on HIJACKED verdict.
        collapse_ambiguous_as_hijacked: whether AMBIGUOUS verdicts count as
            HIJACKED for the abort decision. Default True.
        log: optional list to which detection records are appended for analysis.
    """

    def __init__(
        self,
        judge: ClaudeJudge | None = None,
        rubric_version: str = "v1.24",
        raise_on_hijack: bool = True,
        collapse_ambiguous_as_hijacked: bool = True,
        log: list | None = None,
    ) -> None:
        self.judge = judge if judge is not None else ClaudeJudge()
        self.rubric_version = rubric_version
        self.raise_on_hijack = raise_on_hijack
        self.collapse_ambiguous_as_hijacked = collapse_ambiguous_as_hijacked
        self.log = log if log is not None else []

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        agent_response = self._build_agent_response(messages)
        if not agent_response:
            # No assistant action yet; nothing to judge
            return query, runtime, env, messages, extra_args

        if self.rubric_version == "v1.24":
            result = self.judge.judge_v124(
                user_prompt=query,
                agent_response=agent_response,
                operator_intent=query,
            )
        else:
            result = self.judge.judge_v121(
                user_prompt=query,
                agent_response=agent_response,
                dataset="agentdojo",
                operator_intent=query,
            )

        verdict = (result.get("verdict") or "").upper()
        categories = result.get("hijack_categories") or []
        reason = result.get("reason") or ""

        self.log.append({
            "query": query,
            "verdict": verdict,
            "hijack_categories": categories,
            "reason": reason,
        })

        hijack_classes = {"HIJACKED"}
        if self.collapse_ambiguous_as_hijacked:
            hijack_classes.add("AMBIGUOUS")

        if self.raise_on_hijack and verdict in hijack_classes:
            cat_str = ",".join(categories) if isinstance(categories, list) else str(categories)
            raise AbortAgentError(
                f"Defense B v1.21 aborted execution: verdict={verdict} "
                f"categories={cat_str} reason={reason[:200]}",
                list(messages),
                env,
            )
        return query, runtime, env, messages, extra_args

    def _build_agent_response(self, messages: Sequence[ChatMessage]) -> str:
        """Concatenate assistant text + tool calls into a single judgeable string.

        AgentDojo's v1.21 judge expects an agent_response string. For
        tool-using agents, we serialise the assistant's full action sequence:
        each assistant message contributes its text content and any tool calls
        as inline annotations.
        """
        parts: list[str] = []
        for m in messages:
            if m.get("role") != "assistant":
                continue
            content = m.get("content", "")
            content_text = get_text_content_as_str(content) if content else ""
            tool_calls = m.get("tool_calls") or []
            for tc in tool_calls:
                # Defensive: tool_calls may be FunctionCall objects or dicts
                fn_name = (
                    getattr(tc, "function", None)
                    and getattr(tc.function, "name", None)
                    or (tc.get("function", {}).get("name") if isinstance(tc, dict) else None)
                    or "<unknown_tool>"
                )
                fn_args = (
                    getattr(tc, "function", None)
                    and getattr(tc.function, "arguments", None)
                    or (tc.get("function", {}).get("arguments") if isinstance(tc, dict) else None)
                    or ""
                )
                parts.append(f"[tool_call] {fn_name}({fn_args})")
            if content_text:
                parts.append(content_text)
        return "\n".join(parts)


class TogetherLLM(OpenAILLM):
    """LLM pipeline element via Together AI's OpenAI-compatible endpoint.

    Used to plug Llama 3.3 70B Instruct Turbo and other Together-hosted
    models into AgentDojo without forking the framework. Together's chat
    completions API speaks the OpenAI protocol verbatim, so we can reuse
    OpenAILLM's tool-calling logic.

    Args:
        model: Together model identifier (e.g. "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "Qwen/Qwen3-235B-A22B-Instruct-2507-tput").
        temperature: sampling temperature. Default 0.0 to match the rest of the project.
    """

    def __init__(
        self,
        model: str,
        temperature: float | None = 0.0,
    ) -> None:
        client = OpenAI(
            api_key=os.environ["TOGETHER_API_KEY"],
            base_url="https://api.together.xyz/v1",
        )
        super().__init__(
            client=client,
            model=model,
            reasoning_effort=None,
            temperature=temperature,
        )


class OpenRouterLLM(OpenAILLM):
    """LLM pipeline element via OpenRouter's OpenAI-compatible endpoint.

    Used to plug Mistral Large 2 and DeepSeek V3 into AgentDojo without
    forking the framework. OpenRouter speaks the OpenAI protocol verbatim.

    Args:
        model: OpenRouter model identifier (e.g. "mistralai/mistral-large-2411",
            "deepseek/deepseek-chat-v3-0324").
        temperature: sampling temperature. Default 0.0.
    """

    def __init__(
        self,
        model: str,
        temperature: float | None = 0.0,
    ) -> None:
        client = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )
        super().__init__(
            client=client,
            model=model,
            reasoning_effort=None,
            temperature=temperature,
        )
