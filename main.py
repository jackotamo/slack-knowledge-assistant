"""Command-line entry point: python main.py --search-only 'your question'."""
import argparse
import sys
from assistant.config import load_config
from assistant.generator import OpenAIGenerator
from assistant.loader import load_passages
from assistant.search import search
from assistant.service import AssistantService
from assistant.presentation import describe_source


def main():
    parser = argparse.ArgumentParser(description="Ask questions about fictional sample SOPs.")
    parser.add_argument("question", nargs="?", help="Question (quote multi-word questions)")
    parser.add_argument("--search-only", action="store_true", help="Retrieve passages without OpenAI")
    args = parser.parse_args()
    try:
        question = args.question if args.question is not None else input("Question: ")
        if not question.strip():
            parser.error("Please enter a nonempty question.")
        config = load_config()
        passages = load_passages(config.sop_dir)
        if args.search_only:
            sources = search(question, passages, config.top_k)
            if not sources:
                print("No relevant SOP passages found.")
            for source in sources:
                print(describe_source(source))
                print(f"  Keyword score: {source.score:.2f}\n{source.passage.text.strip()}\n")
        else:
            service = AssistantService(passages, OpenAIGenerator(config.api_key, config.model), config.top_k)
            answer = service.answer_question(question)
            print(answer.text)
            if answer.sources:
                print("\nSources:")
                for source in answer.sources:
                    print(describe_source(source))
        return 0
    except (EOFError, KeyboardInterrupt):
        return 130
    except Exception as error:
        # Avoid printing API request data, secrets, or a beginner-unfriendly traceback.
        if isinstance(error, (ValueError, OSError)):
            print(f"Error: {error}", file=sys.stderr)
        else:
            print(f"Answer generation failed ({type(error).__name__}). Check connectivity, API key, and model access.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
