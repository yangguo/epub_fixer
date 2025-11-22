#!/usr/bin/env python3
"""CLI entrypoint for the OpenAI Agent SDK variant."""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from .agent import OpenAIEpubAgent
from .config import DEFAULT_MAX_TURNS, DEFAULT_MODEL, DEFAULT_TEMPERATURE
from .tools import apply_rule_based_fix, validate_epub


def derive_output_path(input_epub: str, output_arg: Optional[str]) -> str:
    """Match apply_rule_based_fix's default output naming."""
    if output_arg:
        return output_arg
    stem, ext = os.path.splitext(input_epub)
    suffix = "" if stem.endswith("_fixed") else "_fixed"
    return f"{stem}{suffix}{ext}"


def _ensure_fixed_copy(input_epub: str, target_output: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Ensure we have a fixed copy to validate/follow-up on.
    Returns the path we should continue with plus the fixer result (if we had to run it).
    """
    if os.path.exists(target_output):
        return target_output, None

    fix_result = apply_rule_based_fix(input_epub, output_path=target_output)
    output_path = fix_result.get("output_path") or target_output
    if fix_result.get("success") and os.path.exists(output_path):
        return output_path, fix_result

    return input_epub, fix_result


def _run_openai_followups(
    agent: OpenAIEpubAgent,
    epub_path: str,
    base_goal: Optional[str],
    max_attempts: int,
    initial_error_count: int,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Attempt OpenAI-driven follow-up runs to burn down remaining errors.
    """
    followups: List[Dict[str, Any]] = []
    prev_errors: Optional[int] = initial_error_count
    final_validation: Optional[Dict[str, Any]] = None

    for attempt in range(1, max_attempts + 1):
        followup_goal = (
            f"{base_goal or ''}\nContinue fixing remaining EPUB errors."
            f" Attempt {attempt}/{max_attempts}."
        ).strip()
        logging.info("🔁 OpenAI follow-up attempt %s/%s ...", attempt, max_attempts)
        attempt_result = agent.run(epub_path, output_path=epub_path, goal=followup_goal)

        final_validation = validate_epub(epub_path)
        if not final_validation.get("success"):
            logging.warning("Validation failed after follow-up attempt; stopping.")
            followups.append(
                {"attempt": attempt, "result": attempt_result, "validation": final_validation}
            )
            break

        error_count = final_validation.get("error_count") or 0
        logging.info("   Remaining errors after follow-up: %s", error_count)

        followups.append(
            {"attempt": attempt, "result": attempt_result, "validation": final_validation}
        )

        if not final_validation.get("has_errors"):
            break

        if prev_errors is not None and error_count >= prev_errors:
            logging.info("   No further progress; stopping follow-ups.")
            break

        prev_errors = error_count

    return followups, final_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the OpenAI Agent SDK EPUB fixer.")
    parser.add_argument("input_epub", help="Path to the EPUB file to process.")
    parser.add_argument(
        "-o",
        "--output",
        help="Optional output path for the fixed EPUB.",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help=f"OpenAI model to use (default: env OPENAI_MODEL or {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default: {DEFAULT_TEMPERATURE}).",
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (or set OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--base-url",
        help="Optional OpenAI base URL (or set OPENAI_BASE_URL).",
    )
    parser.add_argument(
        "--org",
        help="Optional OpenAI organization id (or set OPENAI_ORG / OPENAI_ORGANIZATION).",
    )
    parser.add_argument(
        "--project",
        help="Optional OpenAI project id (or set OPENAI_PROJECT).",
    )
    parser.add_argument(
        "--api-mode",
        choices=["responses", "chat_completions"],
        help="API surface to use (default: from OPENAI_API_MODE or 'responses').",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=DEFAULT_MAX_TURNS,
        help=f"Maximum tool/assistant turns (default: {DEFAULT_MAX_TURNS}).",
    )
    parser.add_argument(
        "--goal",
        help="Optional goal or context to pass to the agent.",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Print raw JSON output instead of a summary.",
    )
    parser.add_argument(
        "--no-continue",
        dest="continue_on_errors",
        action="store_false",
        help="Do not keep fixing/validating when errors remain after the agent run.",
    )
    parser.add_argument(
        "--max-followups",
        type=int,
        default=3,
        help="Maximum number of follow-up custom agent attempts (default: 3).",
    )
    parser.set_defaults(continue_on_errors=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output_path = derive_output_path(args.input_epub, args.output)

    try:
        agent = OpenAIEpubAgent(
            model=args.model,
            temperature=args.temperature,
            max_turns=args.max_turns,
            api_key=args.api_key,
            base_url=args.base_url,
            organization=args.org,
            project=args.project,
            api_mode=args.api_mode,
        )
    except Exception as exc:  # pragma: no cover - defensive
        print(f"❌ Could not initialize OpenAI agent: {exc}")
        sys.exit(1)

    result = agent.run(args.input_epub, output_path=output_path, goal=args.goal)

    # Ensure we have a fixed EPUB to continue working on (agent might have stopped early)
    work_epub, fixer_result = _ensure_fixed_copy(args.input_epub, output_path)
    if fixer_result and not fixer_result.get("success"):
        logging.warning(
            "Rule-based fixer fallback failed: %s",
            "; ".join(fixer_result.get("errors") or ["unknown error"]),
        )
    validation: Optional[Dict[str, Any]] = None
    followups: List[Dict[str, Any]] = []
    final_validation: Optional[Dict[str, Any]] = None

    if work_epub and os.path.exists(work_epub):
        validation = validate_epub(work_epub)
        final_validation = validation

        if (
            args.continue_on_errors
            and validation.get("success")
            and validation.get("has_errors")
        ):
            logging.info(
                "Continuing after agent run — %s errors remain.",
                validation.get("error_count"),
            )

            followups, final_validation = _run_openai_followups(
                agent,
                work_epub,
                base_goal=args.goal,
                max_attempts=max(args.max_followups, 1),
                initial_error_count=validation.get("error_count") or 0,
            )
            if final_validation is None:
                final_validation = validation
        elif validation and not validation.get("success"):
            logging.warning("Validation failed to run; skipping follow-ups.")
    else:
        logging.warning(
            "No fixed EPUB found at %s. Using input file for status.",
            work_epub or output_path,
        )
        if os.path.exists(args.input_epub):
            final_validation = validate_epub(args.input_epub)

    if args.as_json:
        payload = dict(result)
        payload.update(
            {
                "output_path": work_epub,
                "fixer_result": fixer_result,
                "validation": final_validation,
                "followups": followups,
            }
        )
        success_flag = payload.get("success", False)
        if final_validation:
            success_flag = (
                success_flag
                and final_validation.get("success", False)
                and not final_validation.get("has_errors", False)
            )
        else:
            success_flag = False
        print(json.dumps(payload, indent=2))
        sys.exit(0 if success_flag else 1)

    overall_success = result.get("success", False)
    if final_validation:
        overall_success = (
            overall_success
            and final_validation.get("success", False)
            and not final_validation.get("has_errors", False)
        )
    else:
        overall_success = False

    status = "SUCCESS" if overall_success else "FAILED"
    print(f"Status: {status}")
    print(f"Model: {result.get('model')}")
    print(f"Turns: {result.get('turns')}")

    reply = result.get("reply") or ""
    if reply:
        print("\nAssistant reply:\n")
        print(reply.strip())

    tool_trace = result.get("transcript") or []
    if tool_trace:
        last_tools = [entry for entry in tool_trace if entry.get("tool_calls")]
        if last_tools:
            print("\nTool calls:")
            for entry in last_tools:
                for call in entry["tool_calls"]:
                    name = call.get("name", "unknown")
                    print(f"- {name}: {call.get('result')}")

    if final_validation:
        print("\nFinal validation:")
        print(
            f"- Errors: {final_validation.get('error_count')}, "
            f"Warnings: {final_validation.get('warning_count')}"
        )
        if followups:
            print("\nFollow-ups (OpenAI agent):")
            for entry in followups:
                attempt = entry.get("attempt")
                res = entry.get("result", {})
                validation = entry.get("validation") or {}
                summary = f"success={res.get('success')}, turns={res.get('turns')}"
                if res.get("errors"):
                    summary += f", errors={len(res.get('errors') or [])}"
                if validation:
                    summary += (
                        f", val_errors={validation.get('error_count')}, "
                        f"val_warnings={validation.get('warning_count')}"
                    )
                print(f"- Attempt {attempt}: {summary}")

    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()
