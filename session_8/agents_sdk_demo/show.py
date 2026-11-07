"""Plumbing, not part of the agent: print what the SDK's loop does, in colour, and pace the demo.

🧠 orange = the MODEL decided      ⚙️ teal = our CODE ran      🙋 yellow = a HUMAN decided      🛡️ red = blocked

`Narrator` is a RunHooks object: the SDK calls it at each point of its loop. It only PRINTS. It is how you SEE the
loop that Runner.run() hides, the same think -> act -> observe you wrote by hand in Session 7.
"""
import json
import os

from agents import RunHooks

_ON = "NO_COLOR" not in os.environ
_C = {"model": "\033[38;5;208m", "code": "\033[36m", "human": "\033[33m", "bad": "\033[31m",
      "good": "\033[32m", "dim": "\033[2m", "bold": "\033[1m"}


def paint(kind, text):
    return f"{_C[kind]}{text}\033[0m" if _ON else text


def ask(prompt):
    """input() that treats Ctrl+D / Ctrl+C as an empty answer instead of a traceback."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def banner(text):
    print("\n" + paint("bold", "=" * 78) + "\n" + paint("bold", "  " + text) + "\n" + paint("bold", "=" * 78))


def pause():
    ask(paint("dim", "\n🔍 Press ENTER to continue ➔ "))


def say(text):
    print(f"\n💬 {text}")


def predict(question):
    print(f"\n{paint('human', '🔮 PREDICT')}  {question}")
    pause()


def observe(title, text):
    """One OBSERVE card. Keep to 4 per step: more than that and nobody remembers any of them."""
    print(f"\n{paint('good', '👁  OBSERVE')}  {paint('bold', title)}")
    for line in text.strip().splitlines():
        print(f"           {line}")
    pause()


def customer_says(text):
    print(f"\n{paint('bold', '👤 CUSTOMER')}  {text}")


def agent_says(text):
    print(f"\n{paint('bold', '🤖 AGENT')}     {text}")


def blocked(where, detail):
    print(f"{paint('bad', '🛡️  GUARD')}   [{where}] {detail}")


def compact(obj, limit=300):
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + " …"


class Narrator(RunHooks):
    """Prints each point of the SDK's loop. Pass it as `Runner.run(..., hooks=Narrator())`."""

    def __init__(self):
        self.loops = 0

    async def on_llm_start(self, context, agent, system_prompt, input_items):
        self.loops += 1
        print(paint("bold", f"\n── Loop {self.loops} " + "─" * 58))
        print(paint("dim", f"   [{agent.name}] sending {len(input_items)} items + {len(agent.tools)} tools to the model"))

    async def on_llm_end(self, context, agent, response):
        u = response.usage
        print(paint("dim", f"   model replied · {u.input_tokens} tokens in, {u.output_tokens} out"))
        for item in response.output:
            kind = getattr(item, "type", "")
            if kind == "message":
                text = "".join(getattr(part, "text", "") for part in getattr(item, "content", []) or [])
                if text.strip():
                    print(f"{paint('model', '🧠 THINK')}   {text.strip()}")
            elif kind == "function_call":
                print(f"{paint('model', '🧠 ACT')}     model ASKS for {paint('model', item.name)}({item.arguments})   "
                      + paint("dim", "(nothing has run yet)"))

    async def on_tool_start(self, context, agent, tool):
        print(f"{paint('code', '⚙️  RUN')}     our code runs {tool.name}")

    async def on_tool_end(self, context, agent, tool, result):
        bad = '"error"' in str(result)
        print(f"{paint('bad' if bad else 'code', '👁  OBSERVE')} {compact(result)}   "
              + paint("dim", "-> goes back to the model"))

    async def on_handoff(self, context, from_agent, to_agent):
        print(f"{paint('model', '🔀 HANDOFF')}  {from_agent.name} -> {to_agent.name}")
