"""Reuse notebook definitions without installs, secrets, chat loops or tests."""
import ast
import os
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent


def build(version):
    from agents import Agent, ModelSettings, set_tracing_disabled
    # Evaluation does not need a remote pricing-map lookup during import.
    os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP', 'True')
    set_tracing_disabled(True)  # avoid external telemetry of evaluation prompts
    nb = json.loads((ROOT / 'openai_goodwe_agentes.ipynb').read_text())
    env = {}
    # These cells contain only imports and definitions in the pinned source notebook.
    for index in (5, 7, 9):
        tree = ast.parse(''.join(nb['cells'][index]['source']))
        tree.body = [node for node in tree.body if not isinstance(node, ast.Expr)]
        exec(compile(tree, f'notebook_cell_{index}', 'exec'), env)
    model = os.getenv('AGENT_OPENAI_MODEL', 'gpt-4o-mini')
    if version == 'sprint3_gemini':
        from agents.extensions.models.litellm_model import LitellmModel
        model = LitellmModel(model=os.getenv('AGENT_GEMINI_MODEL', 'gemini/gemini-3.1-flash-lite'), api_key=os.environ['GEMINI_API_KEY'])
    elif version != 'sprint3_openai':
        raise ValueError('Versão desconhecida')
    for value in env.values():
        if isinstance(value, Agent):
            value.model = model
            value.model_settings = ModelSettings(temperature=0)
    return env['agente_atendimento']


async def answer(agent, case, session):
    from agents import Runner, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
    # Seed with authoritative history; every case gets a separate SQLiteSession.
    if case['history']:
        await session.add_items(case['history'])
    try:
        result = await Runner.run(agent, case['question'], session=session, max_turns=12)
        return str(result.final_output), 'ok'
    except InputGuardrailTripwireTriggered:
        return 'Solicitação bloqueada pelo guardrail de entrada.', 'blocked'
    except OutputGuardrailTripwireTriggered:
        return 'Resposta bloqueada pelo guardrail de saída.', 'blocked'
