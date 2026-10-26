"""Prompt construction (FunSearch best-shot style), prefill, and program extraction with FunSearch's trim."""
from __future__ import annotations

import ast
import os

TASK_DOCSTRING = (
    "Builds a short closed tour for the Travelling Salesman Problem by greedy construction. The tour starts at "
    "city 0. At every step select_next_node is called with the current city, the destination city (city 0, where "
    "the tour ends), the set of unvisited cities and the n x n numpy array of Euclidean distances, and it returns "
    "the next city to visit, one element of unvisited_nodes. When no city is left the tour returns to city 0. "
    "Instances have 50 to 100 cities uniform in the unit square; shorter total tour length is better."
)
IMPORTS = "import numpy as np\nimport math\n"
SIG = "(current_node, destination_node, unvisited_nodes, distance_matrix):"
SPEC_DOC = "Return the next city to visit: one element of unvisited_nodes."
STOPS = ["```", "\ndef ", "\nclass ", "\nif __name__"]
MODEL_ID = "Qwen/Qwen3-8B-FP8"
MODEL_REV = "220b46e3b2180893580a4454f21f22d3ebb187d3"

_TOK = None


def tokenizer():
    global _TOK
    if _TOK is None:
        from transformers import AutoTokenizer

        _TOK = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REV)
    return _TOK


def _doc(i: int) -> str:
    return SPEC_DOC if i == 0 else f"Improved version of select_next_node_v{i - 1}."


def render_parent(body: str, i: int) -> str:
    return f'def select_next_node_v{i}{SIG}\n    """{_doc(i)}"""\n{body.rstrip()}\n'


def instruction(k: int, idea: bool) -> str:
    if not idea:
        return f"Write select_next_node_v{k}."
    if k == 1:
        return "Write select_next_node_v1 based on an idea different from the function above."
    return f"Write select_next_node_v{k} based on an idea different from both functions above."


def user_turn(parent_bodies: list[str], idea: bool = False) -> str:
    """parent_bodies sorted ascending by score (the WORSE first), already chosen by the database."""
    k = len(parent_bodies)
    parents = "\n\n".join(render_parent(b, i) for i, b in enumerate(parent_bodies))
    return f"{TASK_DOCSTRING}\n\n```python\n{IMPORTS}\n\n{parents}```\n\n{instruction(k, idea)}"


def prefill(k: int) -> str:
    return f'```python\ndef select_next_node_v{k}{SIG}\n    """Improved version of select_next_node_v{k - 1}."""\n'


def render_prompt(parent_bodies: list[str], idea: bool = False) -> tuple[str, list[int]]:
    """Full text (chat template, thinking off, plus the prefill) and its token ids (no special tokens added)."""
    tok = tokenizer()
    k = len(parent_bodies)
    text = tok.apply_chat_template([{"role": "user", "content": user_turn(parent_bodies, idea)}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)
    text = text + prefill(k)
    ids = tok(text, add_special_tokens=False)["input_ids"]
    return text, ids


def nosel_prompt() -> tuple[str, list[int]]:
    from baselines import NN_PROGRAM

    return render_prompt([nn_body(NN_PROGRAM)], idea=False)


def nn_body(program: str) -> str:
    """The body text (after the docstring, comments kept) of the program's select_next_node function."""
    tree = ast.parse(program)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "select_next_node")
    first = fn.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        start = first.end_lineno  # 1-based last line of the docstring
    else:
        start = fn.lineno  # header line (single-line header assumed)
    lines = program.split("\n")
    return "\n".join(lines[start:fn.end_lineno]).rstrip() + "\n"


def cut_at_stops(text: str) -> tuple[str, bool]:
    """Cut a generation at the first stop string (stops are also applied by the server)."""
    pos = [text.find(s) for s in STOPS if s in text]
    if pos:
        return text[:min(pos)], True
    return text, False


def program_from_body(body: str, k: int) -> str:
    return f'{IMPORTS}\n\ndef select_next_node{SIG}\n    """Improved version of select_next_node_v{k - 1}."""\n{body}'


def _n_body_statements(code: str) -> int:
    tree = ast.parse(code)
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "select_next_node"), None)
    if fn is None:
        return 0
    stmts = fn.body
    if stmts and isinstance(stmts[0], ast.Expr) and isinstance(stmts[0].value, ast.Constant):
        stmts = stmts[1:]
    return len(stmts)


def extract(generated: str, k: int) -> dict:
    """body = generated text up to the stop; program = imports + header + docstring + body; FunSearch trim."""
    body, _ = cut_at_stops(generated)
    body = body.rstrip() + "\n" if body.strip() else ""
    if not body.strip():
        return {"program": None, "body": "", "label": "no_code", "trimmed_lines": 0}
    lines = body.rstrip("\n").split("\n")
    for cut in range(len(lines), 0, -1):
        b = "\n".join(lines[:cut]) + "\n"
        prog = program_from_body(b, k)
        try:
            ok = _n_body_statements(prog) >= 1
        except SyntaxError:
            continue
        if ok:
            return {"program": prog, "body": b, "label": None, "trimmed_lines": len(lines) - cut}
    return {"program": None, "body": body, "label": "syntax_error", "trimmed_lines": len(lines)}


if __name__ == "__main__":  # quick manual check
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from baselines import NN_PROGRAM

    t, ids = render_prompt([nn_body(NN_PROGRAM)])
    print(t)
    print(len(ids))
