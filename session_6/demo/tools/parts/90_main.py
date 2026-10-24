

# ═══════════════════════════════════════════════════════════════════════════
# 14. RUN IT
# ═══════════════════════════════════════════════════════════════════════════
import inspect

TITLE = @@TITLE@@
RECAP = @@RECAP@@
NEXT_STEP = @@NEXT@@

#@if v>=1

def child_main() -> None:
    """Entry point of the throw-away process used by the crash scenes."""
    key = sys.argv[sys.argv.index("--child") + 1]
    print(paint(f"   [child process pid {os.getpid()} running scenario {key}]", GREY))
    run_scenario(key, step_mode=False)
#@end


#@if v>=6
REFERENCE = [route_request, build_system_prompt, needs_approval, policy_check, check_output, handle_tool_call, finish, run_agent]
#@else
REFERENCE = [handle_tool_call, run_agent]
#@end


def print_reference() -> None:
    banner("CLEAN REFERENCE · the agent without the teaching")
    explain(f"""
        The scenes above only WATCH the agent. The agent itself is these {len(REFERENCE)} functions plus the tools
        and helpers in sections 3-9. Copy this, not the scenes.
    """)
    for fn in REFERENCE:
        src = inspect.getsource(inspect.unwrap(fn))
        print("\n" + "\n".join(l for l in src.split("\n") if not l.startswith("@traced")))   # tracing decorators are teaching noise here


def main() -> None:
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        return
#@if v>=1
    if "--child" in sys.argv:
        return child_main()
#@end
    banner(TITLE)
    ensure_provider()
    print(f"Model: {model_label()}")
    if PROVIDER == "mock":
        print(paint("⚠️  OFFLINE MOCK by your choice: fine for rehearsal, but NOT a real LLM. For the real thing set GROQ_API_KEY and run again.", YELLOW))
    explain("""
        How to read the console:
          🧠 orange = the MODEL decided   ⚙️  teal = our CODE decided   🙋 yellow = a HUMAN decided   🛡️ red = BLOCKED
        Observe Mode: the demo pauses between steps. ENTER = continue · Ctrl+C = stop (nothing breaks).
    """)
    picked = {int(x) for x in re.findall(r"\d+", os.getenv("DEMO_SCENES", "") or (sys.argv[sys.argv.index("--scenes") + 1] if "--scenes" in sys.argv else ""))}
    chosen = [(i, sc) for i, sc in enumerate(SCENES, 1) if not picked or i in picked]
    print("Scenes today: " + "  ".join(f"{i}·{sc.__name__.split('_', 2)[2]}" for i, sc in chosen)
          + ("" if picked else "     (pick some with --scenes 1,3,4 or DEMO_SCENES=1,3,4)"))
    pause("Ready? ENTER to start")
    reset_world()
#@if v>=5
    setup_tracing()
#@end
    try:
        for _, scene in chosen:
            scene()
        print_reference()
        banner("✅ DONE · what you just saw")
        for line in RECAP:
            print("   •", line)
        print(f"\n➡️  NEXT: {NEXT_STEP}")
        print("\n📂 Before you close: demo_data/ keeps kernmart.db" + (" and agent_state.db" if @@HAS_STATE@@ else "")
              + " for inspection. Delete the folder to start fresh.")
    except KeyboardInterrupt:
        print("\n\n⏹  Stopped by you. Files in demo_data/ are left as they are.")
    except LLMError as e:
        print(f"\n❌ Model problem: {e}\n   Tips: check your API key / network · LLM_PROVIDER=mock to rehearse offline · LLM_CACHE=on replays recorded answers.")
    except Exception as e:
        if os.getenv("DEMO_DEBUG"):
            raise
        print(f"\n❌ Unexpected {type(e).__name__}: {e}\n   (run with DEMO_DEBUG=1 to see the full traceback)")


if __name__ == "__main__":
    main()
