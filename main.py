import sys
from src.agent import agent_instance, extract_token_usage
from src.schemas import Context

def main():
    print("=" * 60)
    print("   RoutedRAG Agent CLI (Beenden mit: /end oder exit)")
    print("=" * 60)

    config = {"configurable": {"thread_id": "cli_session"}}
    context = Context(user_role="default")

    while True:
        try:
            user_input = input("\nDu: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAuf Wiedersehen!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["/end", "exit", "quit"]:
            print("CLI beendet. Auf Wiedersehen!")
            break

        try:
            response = agent_instance.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
                context=context,
            )

            assistant_msg = response["messages"][-1]
            print(f"\nAssistent:\n{assistant_msg.content}")

            tokens = extract_token_usage(response)
            model_info = getattr(context, "selected_model", "")
            print(f"\n[Modell: {model_info} | Input: {tokens['prompt_tokens']} | Output: {tokens['completion_tokens']} | Gesamt: {tokens['total_tokens']} Tokens]")

        except Exception as e:
            print(f"\nFehler bei der Ausführung: {e}")

if __name__ == "__main__":
    main()
