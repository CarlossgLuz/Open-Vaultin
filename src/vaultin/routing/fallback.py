from __future__ import annotations

import re

from vaultin.routing.jev import RouteProposal, TaskInput


class FallbackRouter:
    def route(self, task: TaskInput) -> RouteProposal:
        text = task.text.casefold()

        if re.search(r"\b(security|vulnerability|vulnerabil|cve|cwe|sast|sca|dast|appsec|threat)\b", text):
            return RouteProposal(task_type="security-review", domains=["security"], risk="high", agents=["security-reviewer"], skills=[], workflow="security-review", confidence=1.0, source="fallback")
        if re.search(r"\b(frontend|react|next\.js|css|ui|interface)\b", text):
            return RouteProposal(task_type="implementation", domains=["frontend"], risk="medium", agents=["frontend-engineer"], skills=[], workflow="implementation", confidence=1.0, source="fallback")
        if re.search(r"\b(backend|api|python|typescript|node|bug|fix|failing)\b", text):
            return RouteProposal(task_type="implementation", domains=["software"], risk="medium", agents=["software-engineer"], skills=[], workflow="implementation", confidence=1.0, source="fallback")
        if re.search(r"\b(infra|infrastructure|docker|kubernetes|k8s|terraform|linux|server|network)\b", text):
            return RouteProposal(task_type="platform", domains=["platform"], risk="high", agents=["platform-engineer"], skills=[], workflow="platform-change", confidence=1.0, source="fallback")
        if re.search(r"\b(test|tests|qa|quality)\b", text):
            return RouteProposal(task_type="qa", domains=["qa"], risk="medium", agents=["qa-engineer"], skills=[], workflow="qa", confidence=1.0, source="fallback")
        if re.search(r"\b(review|code review|pull request|\bpr\b)\b", text):
            return RouteProposal(task_type="code-review", domains=["engineering"], risk="medium", agents=["code-reviewer"], skills=[], workflow="code-review", confidence=1.0, source="fallback")
        if re.search(r"\b(release|version|semver)\b", text):
            return RouteProposal(task_type="release", domains=["release"], risk="high", agents=["release-manager"], skills=[], workflow="release", confidence=1.0, source="fallback")
        if re.search(r"\b(document|documentation|docs|knowledge|memory|vault)\b", text):
            return RouteProposal(task_type="knowledge", domains=["knowledge"], risk="low", agents=["knowledge-curator"], skills=[], workflow="knowledge", confidence=1.0, source="fallback")
        return RouteProposal(task_type="exploration", domains=["unknown"], risk="low", agents=["explorer"], skills=[], workflow="exploration", confidence=1.0, source="fallback")
