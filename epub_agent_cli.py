#!/usr/bin/env python3
"""CLI for EPUB Agent System with Claude LLM Brain"""

import argparse
import sys
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent_system.orchestrator import Orchestrator
from agent_system.agent_config import setup_logging, get_agent, create_llm_brain, DEFAULT_WORKFLOW

def main():
    parser = argparse.ArgumentParser(description="EPUB Agent System with Claude LLM")
    parser.add_argument("input_epub", help="Input EPUB file")
    parser.add_argument("-o", "--output", help="Output EPUB file")
    parser.add_argument("-w", "--workflow", nargs="+", help=f"Workflow (default: {' '.join(DEFAULT_WORKFLOW)}) - available agents: validation, fixing, custom_fixing, drm_removal")
    parser.add_argument("--drm", action="store_true", help="Include DRM removal")
    parser.add_argument("--llm", action="store_true", help="Enable Claude LLM brain")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY)")
    parser.add_argument("--model", help="Claude model name (or set CLAUDE_MODEL)")
    parser.add_argument("--base-url", help="Custom API base URL (or set ANTHROPIC_BASE_URL)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--max-attempts", type=int, default=5, help="Maximum number of fixing attempts (default: 5)")
    
    args = parser.parse_args()
    setup_logging()

    llm_brain = None
    if args.llm:
        print("🧠 Initializing Claude LLM brain...")
        llm_brain = create_llm_brain(
            api_key=args.api_key,
            model=args.model,
            base_url=args.base_url
        )
        if llm_brain:
            model_info = args.model or os.getenv("CLAUDE_MODEL") or "claude-3-5-sonnet-20241022"
            print(f"✓ LLM brain initialized (model: {model_info})")
            if args.base_url or os.getenv("ANTHROPIC_BASE_URL"):
                url = args.base_url or os.getenv("ANTHROPIC_BASE_URL")
                print(f"  Using custom URL: {url}")
        else:
            print("❌ LLM initialization failed. Using rule-based mode.")
    
    workflow = args.workflow or DEFAULT_WORKFLOW.copy()
    if args.drm:
        workflow.insert(-1, "drm_removal")

    agents = [get_agent(name, llm_brain) for name in workflow]
    
    orchestrator = Orchestrator(llm_brain=llm_brain)
    orchestrator.set_workflow(agents)
    
    print(f"🔧 Workflow: {' -> '.join(workflow)}\\n")
    result = orchestrator.run_workflow(args.input_epub, args.output, max_attempts=args.max_attempts)

    print(f"\n{'='*60}")
    print(f"Status: {'✓ SUCCESS' if result['success'] else '✗ FAILED'}")
    if result['output']:
        print(f"Output: {result['output']}")
    
    # Summary of validation results
    first_validation = None
    last_validation = None
    for entry in result["workflow"]:
        if entry['agent'] == 'validation':
            if first_validation is None:
                first_validation = entry['result']
            last_validation = entry['result']
    
    if first_validation and last_validation:
        initial_errors = first_validation.get('error_count', 0)
        final_errors = last_validation.get('error_count', 0)
        if initial_errors > 0:
            print(f"\n📊 Results: {initial_errors} errors → {final_errors} errors")
            if final_errors < initial_errors:
                print(f"   ✓ Fixed {initial_errors - final_errors} errors!")
            if final_errors == 0:
                print(f"   🎉 All errors fixed!")
    
    for entry in result["workflow"]:
        status = "✓" if entry["result"]["success"] else "✗"
        print(f"\n{status} {entry['agent']}")
        if 'error_count' in entry['result']:
            print(f"   Errors: {entry['result']['error_count']}, Warnings: {entry['result']['warning_count']}")
    
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()
