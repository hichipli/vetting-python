"""
Command-line interface for the VETTING framework.

Provides basic CLI functionality for testing and demonstration purposes.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Dict, Any

from . import VettingFramework, VettingConfig, ChatMessage, OpenAIProvider
from .config import VettingSettings, VettingConfigBuilder


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="VETTING Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic chat
  vetting-cli chat "Hello, how does photosynthesis work?"
  
  # Educational vetting
  vetting-cli vetting "What is 2+2?" --context '{"question": "What is 2+2?", "answer": "4"}'
  
  # Cost summary
  vetting-cli cost-summary
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Run in chat mode")
    chat_parser.add_argument("message", help="Message to send to the chat model")
    chat_parser.add_argument("--model", default="gpt-4o-mini", help="Model to use")
    chat_parser.add_argument("--temperature", type=float, default=0.7, help="Temperature")
    chat_parser.add_argument("--max-tokens", type=int, default=1024, help="Max tokens")
    
    # Vetting command
    vetting_parser = subparsers.add_parser("vetting", help="Run in vetting mode")
    vetting_parser.add_argument("message", help="Message to send")
    vetting_parser.add_argument("--chat-model", default="gpt-4o-mini", help="Chat model")
    vetting_parser.add_argument("--verification-model", default="gpt-4o-mini", help="Verification model")
    vetting_parser.add_argument("--max-attempts", type=int, default=3, help="Max verification attempts")
    vetting_parser.add_argument("--context", help="JSON context with question and answer")
    
    # Cost summary command
    subparsers.add_parser("cost-summary", help="Show cost tracking summary")
    
    # Version command
    subparsers.add_parser("version", help="Show version information")
    
    return parser


async def run_chat_command(args) -> Dict[str, Any]:
    """Run a chat command."""
    try:
        # Setup provider
        settings = VettingSettings.from_env()
        if not settings.validate():
            return {"error": "Settings validation failed. Check your API keys."}
        
        provider = settings.get_provider_instance(settings.default_provider)
        framework = VettingFramework(chat_provider=provider)
        
        # Create config
        config = VettingConfig(
            mode="chat",
            chat_model={
                "model_id": args.model,
                "temperature": args.temperature,
                "max_tokens": args.max_tokens
            }
        )
        
        # Process message
        messages = [ChatMessage("user", args.message)]
        response = await framework.process(messages, config)
        
        return {
            "success": True,
            "response": response.content,
            "usage": response.total_usage.__dict__ if response.total_usage else {},
            "cost": response.total_cost,
            "model_used": response.chat_model_used,
            "requires_attention": response.requires_attention
        }
        
    except Exception as e:
        return {"error": str(e)}


async def run_vetting_command(args) -> Dict[str, Any]:
    """Run a vetting command."""
    try:
        # Setup provider
        settings = VettingSettings.from_env()
        if not settings.validate():
            return {"error": "Settings validation failed. Check your API keys."}
        
        provider = settings.get_provider_instance(settings.default_provider)
        framework = VettingFramework(chat_provider=provider)
        
        # Build config
        config_builder = (VettingConfigBuilder()
                         .vetting_mode()
                         .chat_model(args.chat_model)
                         .verification_model(args.verification_model)
                         .max_attempts(args.max_attempts))
        
        # Add context if provided
        if args.context:
            try:
                context_data = json.loads(args.context)
                config_builder.add_context_item(
                    question_text=context_data.get("question", ""),
                    correct_answer=context_data.get("answer"),
                    key_concepts=context_data.get("key_concepts", [])
                )
            except json.JSONDecodeError:
                return {"error": "Invalid JSON in --context argument"}
        
        config = config_builder.build()
        
        # Process message
        messages = [ChatMessage("user", args.message)]
        response = await framework.process(messages, config)
        
        return {
            "success": True,
            "response": response.content,
            "verification_passed": response.verification_passed,
            "attempt_count": response.attempt_count,
            "stop_reason": response.stop_reason.value if response.stop_reason else None,
            "usage": response.total_usage.__dict__ if response.total_usage else {},
            "cost": response.total_cost,
            "requires_attention": response.requires_attention
        }
        
    except Exception as e:
        return {"error": str(e)}


def run_cost_summary_command() -> Dict[str, Any]:
    """Show cost tracking summary."""
    try:
        from .utils import CostTracker
        
        cost_tracker = CostTracker(enable_persistence=True)
        summary = cost_tracker.get_summary()
        
        return {
            "success": True,
            "total_cost": summary.total_cost,
            "total_requests": summary.total_requests,
            "total_tokens": summary.total_tokens,
            "average_cost_per_request": summary.average_cost_per_request,
            "provider_breakdown": summary.provider_breakdown,
            "model_breakdown": summary.model_breakdown
        }
        
    except Exception as e:
        return {"error": str(e)}


def run_version_command() -> Dict[str, Any]:
    """Show version information."""
    from . import __version__
    
    return {
        "success": True,
        "version": __version__,
        "python_version": sys.version,
        "platform": sys.platform
    }


async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == "chat":
        result = await run_chat_command(args)
    elif args.command == "vetting":
        result = await run_vetting_command(args)
    elif args.command == "cost-summary":
        result = run_cost_summary_command()
    elif args.command == "version":
        result = run_version_command()
    else:
        result = {"error": f"Unknown command: {args.command}"}
    
    # Output result
    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    else:
        # Pretty print successful results
        if args.command in ["chat", "vetting"]:
            print(f"Response: {result['response']}")
            if "verification_passed" in result:
                status = "✓" if result["verification_passed"] else "✗"
                print(f"Verification: {status} (attempts: {result['attempt_count']})")
            if result.get("requires_attention"):
                print("⚠️  Response requires attention")
            print(f"Cost: ${result['cost']:.4f}")
            if result.get("usage", {}).get("total_tokens"):
                print(f"Tokens: {result['usage']['total_tokens']}")
        else:
            print(json.dumps(result, indent=2))


def cli_main():
    """Entry point for console script."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()