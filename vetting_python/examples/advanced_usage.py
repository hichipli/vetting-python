"""
Advanced usage examples for the VETTING framework.

This module demonstrates advanced patterns including custom providers,
complex educational scenarios, multi-turn conversations, and integration patterns.
"""

import asyncio
import json
import os
from typing import List, Dict, Any
from datetime import datetime

from vetting_python import (
    VettingFramework, VettingConfig, ChatMessage, Usage,
    OpenAIProvider, ClaudeProvider
)
from vetting_python.config import VettingConfigBuilder
from vetting_python.utils import CostTracker, MessageUtils, ValidationUtils
from vetting_python.core.models import Provider, ModelConfig


class CustomLoggingProvider(Provider):
    """
    Example of a custom provider that wraps another provider with logging.
    
    This demonstrates how to extend the framework with custom behavior
    while maintaining compatibility with the Provider interface.
    """
    
    def __init__(self, wrapped_provider: Provider, log_file: str = "vetting_requests.log"):
        self.wrapped_provider = wrapped_provider
        self.log_file = log_file
    
    async def generate_response(self, messages: List[ChatMessage], model_config: ModelConfig, system_prompt: str = None):
        """Generate response with logging."""
        start_time = datetime.now()
        
        # Log request
        self._log_request(messages, model_config, system_prompt, start_time)
        
        try:
            # Call wrapped provider
            content, usage, requires_attention = await self.wrapped_provider.generate_response(
                messages, model_config, system_prompt
            )
            
            # Log successful response
            self._log_response(content, usage, requires_attention, start_time)
            
            return content, usage, requires_attention
            
        except Exception as e:
            # Log error
            self._log_error(str(e), start_time)
            raise
    
    def calculate_cost(self, model_id: str, usage: Usage) -> float:
        """Delegate cost calculation to wrapped provider."""
        return self.wrapped_provider.calculate_cost(model_id, usage)
    
    def get_model_aliases(self) -> Dict[str, str]:
        """Get model aliases from wrapped provider."""
        return self.wrapped_provider.get_model_aliases()
    
    def _log_request(self, messages, model_config, system_prompt, timestamp):
        """Log request details."""
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "type": "request",
            "model": model_config.model_id,
            "message_count": len(messages),
            "has_system_prompt": system_prompt is not None,
            "estimated_tokens": MessageUtils.count_tokens_estimate(messages)
        }
        self._write_log(log_entry)
    
    def _log_response(self, content, usage, requires_attention, start_time):
        """Log response details."""
        end_time = datetime.now()
        log_entry = {
            "timestamp": end_time.isoformat(),
            "type": "response",
            "duration_ms": (end_time - start_time).total_seconds() * 1000,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            },
            "requires_attention": requires_attention,
            "response_length": len(content)
        }
        self._write_log(log_entry)
    
    def _log_error(self, error_msg, start_time):
        """Log error."""
        end_time = datetime.now()
        log_entry = {
            "timestamp": end_time.isoformat(),
            "type": "error",
            "duration_ms": (end_time - start_time).total_seconds() * 1000,
            "error": error_msg
        }
        self._write_log(log_entry)
    
    def _write_log(self, entry):
        """Write log entry to file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # Don't fail on logging errors


async def complex_educational_scenario():
    """
    Advanced educational vetting scenario with multiple subjects and adaptive learning.
    """
    print("=== Complex Educational Scenario ===")
    
    provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY", "your-key"))
    framework = VettingFramework(chat_provider=provider)
    
    # Create a comprehensive educational context
    config = (VettingConfigBuilder()
              .vetting_mode()
              .chat_model("gpt-4o-mini", temperature=0.7, max_tokens=400)
              .verification_model("gpt-4o-mini", temperature=0.1, max_tokens=200)
              .max_attempts(3)
              .chat_system_prompt("""
You are an expert tutor specializing in multiple subjects. Your teaching philosophy 
is based on the Socratic method - guide students to discover answers through 
thoughtful questioning rather than direct instruction.

Key principles:
1. Never give direct answers to homework or test questions
2. Ask probing questions that lead students to think critically
3. Build on student responses to guide them toward understanding
4. Encourage connections between different concepts
5. Always end with a question that promotes deeper thinking
              """)
              # Science questions
              .add_context_item(
                  question_text="What happens when you mix baking soda and vinegar?",
                  subject="Chemistry",
                  question_id="chem_001",
                  correct_answer="Chemical reaction producing carbon dioxide gas, water, and sodium acetate",
                  key_concepts=["chemical reaction", "acid-base reaction", "carbon dioxide", "CO2", "sodium bicarbonate", "acetic acid"],
                  explanation="This is a classic acid-base neutralization reaction that produces gas, demonstrating chemical change."
              )
              .add_context_item(
                  question_text="Why do things fall down instead of up?",
                  subject="Physics", 
                  question_id="phys_001",
                  correct_answer="Gravity - the force of attraction between masses",
                  key_concepts=["gravity", "gravitational force", "mass", "acceleration", "9.8 m/s²"],
                  explanation="Gravity is a fundamental force that attracts objects with mass toward each other."
              )
              # Math questions
              .add_context_item(
                  question_text="What is the area of a circle with radius 5?",
                  subject="Mathematics",
                  question_id="math_001", 
                  correct_answer="25π square units or approximately 78.54 square units",
                  key_concepts=["area", "circle", "π", "pi", "radius", "formula", "25π", "78.54"],
                  explanation="Circle area formula is A = πr², so with r=5, A = π(5)² = 25π"
              )
              .safety_features(enable_educational_rules=True, enable_safety_prefix=True)
              .session_info("advanced_edu_001", "student_456")
              .build())
    
    # Simulate a tutoring session with multiple questions
    conversation_scenarios = [
        "I have a science experiment tomorrow. What happens when I mix baking soda and vinegar? I need to know for my lab report.",
        "For my physics homework, why do things fall down? Can you just tell me the answer?",
        "I'm stuck on this math problem. The circle has radius 5, what's the area? I need this for my test.",
        "Can you help me understand the connection between all these topics we've been discussing?"
    ]
    
    conversation_history = []
    
    for i, user_question in enumerate(conversation_scenarios, 1):
        print(f"\n--- Question {i} ---")
        print(f"Student: {user_question}")
        
        # Add user message to conversation
        conversation_history.append(ChatMessage("user", user_question))
        
        try:
            response = await framework.process(conversation_history, config)
            
            print(f"Tutor: {response.content}")
            
            # Add assistant response to conversation
            conversation_history.append(ChatMessage("assistant", response.content))
            
            # Show verification results
            if response.verification_passed:
                print("✓ Educational guidelines followed")
            else:
                print("✗ Educational guidelines violated")
                if response.attempts and response.attempts[-1].verification_output:
                    print(f"  Issue: {response.attempts[-1].verification_output}")
            
            print(f"Attempts: {response.attempt_count}, Tokens: {response.total_usage.total_tokens}, Cost: ${response.total_cost:.4f}")
            
        except Exception as e:
            print(f"Error: {e}")
            break
    
    print(f"\nTotal conversation length: {len(conversation_history)} messages")


async def multi_turn_conversation_with_memory():
    """
    Demonstrate handling long multi-turn conversations with context management.
    """
    print("\n=== Multi-Turn Conversation with Memory Management ===")
    
    provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY", "your-key"))
    framework = VettingFramework(chat_provider=provider)
    
    # Configuration for ongoing conversation
    config = VettingConfig(
        mode="chat",
        chat_model=ModelConfig(
            model_id="gpt-4o-mini",
            temperature=0.8,
            max_tokens=300
        ),
        enable_educational_rules=True,
        session_id="long_conversation_001"
    )
    
    # Simulate a long conversation about a complex topic
    conversation_turns = [
        "Hi! I'm trying to understand machine learning. Can you start with the basics?",
        "That's helpful! What's the difference between supervised and unsupervised learning?",
        "Can you give me some examples of supervised learning algorithms?",
        "How does a decision tree work exactly?",
        "What about neural networks? How are they different from decision trees?",
        "This is getting complex. Can you summarize what we've covered so far?",
        "Great summary! Now I'm curious about deep learning. How does it relate to what we discussed?",
        "What are some real-world applications where I might see these techniques used?",
    ]
    
    conversation_history = []
    total_cost = 0.0
    total_tokens = 0
    
    for i, user_input in enumerate(conversation_turns, 1):
        print(f"\n--- Turn {i} ---")
        print(f"User: {user_input}")
        
        # Add user message
        conversation_history.append(ChatMessage("user", user_input))
        
        # Manage conversation length to avoid token limits
        if MessageUtils.count_tokens_estimate(conversation_history) > 3000:
            print("  [Truncating conversation history to manage token limits]")
            conversation_history = MessageUtils.truncate_conversation(
                conversation_history, 
                max_tokens=2000, 
                preserve_system=True
            )
        
        try:
            response = await framework.process(conversation_history, config)
            
            print(f"Assistant: {response.content}")
            
            # Add assistant response
            conversation_history.append(ChatMessage("assistant", response.content))
            
            # Track metrics
            total_cost += response.total_cost
            total_tokens += response.total_usage.total_tokens
            
            print(f"Turn cost: ${response.total_cost:.4f}, tokens: {response.total_usage.total_tokens}")
            
        except Exception as e:
            print(f"Error: {e}")
            break
    
    print(f"\n--- Conversation Summary ---")
    print(f"Total turns: {len(conversation_turns)}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Total tokens: {total_tokens}")
    print(f"Average cost per turn: ${total_cost/len(conversation_turns):.4f}")
    
    # Analyze conversation
    stats = MessageUtils.get_conversation_stats(conversation_history)
    print(f"Final conversation stats: {stats}")


async def batch_processing_example():
    """
    Demonstrate batch processing of multiple questions with error handling and retries.
    """
    print("\n=== Batch Processing Example ===")
    
    provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY", "your-key"))
    framework = VettingFramework(chat_provider=provider)
    
    # Batch of educational questions to process
    question_batch = [
        {
            "id": "q1",
            "subject": "Math",
            "question": "What is the derivative of x²?",
            "answer": "2x",
            "concepts": ["derivative", "calculus", "power rule"]
        },
        {
            "id": "q2", 
            "subject": "Biology",
            "question": "What is the powerhouse of the cell?",
            "answer": "Mitochondria",
            "concepts": ["mitochondria", "cell organelles", "ATP"]
        },
        {
            "id": "q3",
            "subject": "Chemistry", 
            "question": "What is the chemical formula for water?",
            "answer": "H2O",
            "concepts": ["H2O", "water", "chemical formula", "hydrogen", "oxygen"]
        },
        {
            "id": "q4",
            "subject": "Physics",
            "question": "What is the speed of light?",
            "answer": "299,792,458 meters per second",
            "concepts": ["speed of light", "c", "299792458", "electromagnetic radiation"]
        }
    ]
    
    results = []
    cost_tracker = CostTracker(enable_persistence=False)
    
    print(f"Processing {len(question_batch)} questions...")
    
    for item in question_batch:
        print(f"\nProcessing question {item['id']}: {item['subject']}")
        
        # Create configuration for this question
        config = (VettingConfigBuilder()
                  .vetting_mode()
                  .chat_model("gpt-4o-mini", temperature=0.7)
                  .verification_model("gpt-4o-mini", temperature=0.1)
                  .max_attempts(2)
                  .add_context_item(
                      question_text=item["question"],
                      question_id=item["id"],
                      subject=item["subject"],
                      correct_answer=item["answer"],
                      key_concepts=item["concepts"]
                  )
                  .build())
        
        # Student asking the question directly
        messages = [
            ChatMessage("user", f"Can you tell me the answer to: {item['question']}?")
        ]
        
        try:
            response = await framework.process(messages, config)
            
            # Track costs
            cost_tracker.track_response(response, "openai", provider, provider)
            
            result = {
                "question_id": item["id"],
                "subject": item["subject"],
                "success": True,
                "verification_passed": response.verification_passed,
                "attempt_count": response.attempt_count,
                "tokens": response.total_usage.total_tokens,
                "cost": response.total_cost,
                "response_preview": response.content[:100] + "..." if len(response.content) > 100 else response.content
            }
            
            print(f"✓ Success - Verification: {'PASS' if response.verification_passed else 'FAIL'}")
            print(f"  Response: {result['response_preview']}")
            
        except Exception as e:
            result = {
                "question_id": item["id"], 
                "subject": item["subject"],
                "success": False,
                "error": str(e),
                "tokens": 0,
                "cost": 0.0
            }
            print(f"✗ Failed: {e}")
        
        results.append(result)
    
    # Summary
    print(f"\n--- Batch Processing Summary ---")
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"Successful: {len(successful)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")
    
    if successful:
        avg_cost = sum(r["cost"] for r in successful) / len(successful)
        avg_tokens = sum(r["tokens"] for r in successful) / len(successful)
        verification_pass_rate = sum(1 for r in successful if r.get("verification_passed", False)) / len(successful)
        
        print(f"Average cost per question: ${avg_cost:.4f}")
        print(f"Average tokens per question: {avg_tokens:.1f}")
        print(f"Verification pass rate: {verification_pass_rate:.1%}")
    
    # Cost breakdown
    print(f"\n--- Cost Analysis ---")
    cost_tracker.print_summary()


async def custom_provider_example():
    """
    Demonstrate using a custom provider wrapper for logging and monitoring.
    """
    print("\n=== Custom Provider Example ===")
    
    # Create base provider
    base_provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY", "your-key"))
    
    # Wrap with custom logging provider
    logging_provider = CustomLoggingProvider(base_provider, "custom_provider_example.log")
    
    framework = VettingFramework(chat_provider=logging_provider)
    
    config = VettingConfig(
        mode="chat",
        chat_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.7, max_tokens=150)
    )
    
    test_messages = [
        "What's the weather like today?",
        "Explain quantum computing in simple terms.",
        "What are the benefits of renewable energy?"
    ]
    
    print("Making requests with custom logging provider...")
    
    for i, message in enumerate(test_messages, 1):
        messages = [ChatMessage("user", message)]
        
        try:
            response = await framework.process(messages, config)
            print(f"Request {i}: {len(response.content)} chars, {response.total_usage.total_tokens} tokens")
            
        except Exception as e:
            print(f"Request {i} failed: {e}")
    
    print("Check 'custom_provider_example.log' for detailed request logs.")


async def validation_and_error_handling_example():
    """
    Demonstrate comprehensive validation and error handling patterns.
    """
    print("\n=== Validation and Error Handling Example ===")
    
    provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY", "your-key"))
    framework = VettingFramework(chat_provider=provider)
    
    # Test various validation scenarios
    test_cases = [
        {
            "name": "Valid configuration",
            "config": VettingConfig(
                mode="chat",
                chat_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.7)
            ),
            "messages": [ChatMessage("user", "Hello!")]
        },
        {
            "name": "Invalid temperature",
            "config": VettingConfig(
                mode="chat", 
                chat_model=ModelConfig(model_id="gpt-4o-mini", temperature=3.0)  # Invalid
            ),
            "messages": [ChatMessage("user", "Hello!")]
        },
        {
            "name": "Empty messages",
            "config": VettingConfig(
                mode="chat",
                chat_model=ModelConfig(model_id="gpt-4o-mini")
            ),
            "messages": []  # Invalid
        },
        {
            "name": "Invalid message role",
            "config": VettingConfig(
                mode="chat",
                chat_model=ModelConfig(model_id="gpt-4o-mini")
            ),
            "messages": [ChatMessage("invalid_role", "Hello!")]  # Invalid
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        
        # Validate configuration
        config_validation = ValidationUtils.validate_vetting_config(test_case["config"])
        if not config_validation["valid"]:
            print(f"✗ Config validation failed: {config_validation['issues']}")
            continue
        elif config_validation["warnings"]:
            print(f"⚠ Config warnings: {config_validation['warnings']}")
        
        # Validate messages
        message_validation = ValidationUtils.validate_messages(test_case["messages"])
        if not message_validation["valid"]:
            print(f"✗ Message validation failed: {message_validation['issues']}")
            continue
        elif message_validation["warnings"]:
            print(f"⚠ Message warnings: {message_validation['warnings']}")
        
        # Try to process
        try:
            response = await framework.process(test_case["messages"], test_case["config"])
            print(f"✓ Success: {len(response.content)} chars generated")
            
        except Exception as e:
            print(f"✗ Processing failed: {e}")


async def main():
    """Run all advanced examples."""
    print("VETTING Framework - Advanced Usage Examples")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set your OpenAI API key to run these examples.")
        return
    
    try:
        await complex_educational_scenario()
        await multi_turn_conversation_with_memory()
        await batch_processing_example()
        await custom_provider_example()
        await validation_and_error_handling_example()
        
        print("\n" + "=" * 60)
        print("All advanced examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())