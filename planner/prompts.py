
FAST_PROMPT = """
Summarize the remediation plan: {plan}.
Output strictly one sentence following this format:
"Executing [Action] on [Container] (Cluster [ID]) to resolve [Severity] [Metric] usage."
No other text.
"""

DETAILED_PROMPT = """
You are an AIOps expert explaining a remediation plan for a Kubernetes system.
Your task is to clearly explain *why* the proposed actions were chosen.

Rules:
1. Explain the rationale behind the actions.
2. Reference the affected cluster and container.
3. Be concise but informative (max 3 sentences).

Planner Decision:
{plan}
"""

#Dictionary to map config names to prompt variables
AVAILABLE_PROMPTS = {
    "fast": FAST_PROMPT,
    "detailed": DETAILED_PROMPT
}