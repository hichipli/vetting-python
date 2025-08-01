"""
Integration patterns for the VETTING framework.

This module demonstrates how to integrate VETTING into various applications
including web APIs, educational platforms, and production systems.
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from vetting_python import (
    VettingFramework, VettingConfig, ChatMessage,
    OpenAIProvider, ClaudeProvider
)
from vetting_python.config import VettingSettings, VettingConfigBuilder
from vetting_python.utils import CostTracker, MessageUtils


@dataclass
class APIRequest:
    """Structured API request for VETTING integration."""
    messages: List[Dict[str, str]]
    mode: str = "vetting"
    chat_model: str = "gpt-4o-mini"
    verification_model: Optional[str] = None
    max_attempts: int = 3
    context_items: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class APIResponse:
    """Structured API response from VETTING integration."""
    content: str
    mode: str
    success: bool
    verification_passed: Optional[bool] = None
    attempt_count: int = 1
    stop_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    cost: float = 0.0
    processing_time_ms: Optional[float] = None
    session_id: Optional[str] = None
    error: Optional[str] = None
    requires_attention: bool = False


class VettingAPIService:
    """
    Production-ready API service wrapper for VETTING framework.
    
    Provides a clean interface for integrating VETTING into web applications,
    microservices, or other production systems.
    """
    
    def __init__(self, settings: VettingSettings):
        """Initialize the API service with settings."""
        self.settings = settings
        self.cost_tracker = CostTracker(enable_persistence=True)
        
        # Setup logging
        settings.setup_logging()
        
        # Cache providers to avoid recreation
        self._provider_cache = {}
    
    def _get_provider(self, provider_name: str):
        """Get or create a provider instance."""
        if provider_name not in self._provider_cache:
            self._provider_cache[provider_name] = self.settings.get_provider_instance(provider_name)
        return self._provider_cache[provider_name]
    
    async def process_request(self, request: APIRequest) -> APIResponse:
        """
        Process a VETTING API request.
        
        Args:
            request: Structured API request
            
        Returns:
            Structured API response
        """
        start_time = datetime.now()
        
        try:
            # Convert request to internal format
            messages = MessageUtils.from_openai_format(request.messages)
            
            # Validate messages
            validation = MessageUtils.validate_conversation(messages)
            if not validation["valid"]:
                return APIResponse(
                    content="",
                    mode=request.mode,
                    success=False,  
                    error=f"Invalid messages: {', '.join(validation['issues'])}"
                )
            
            # Build configuration
            config_builder = VettingConfigBuilder().mode(request.mode)
            
            # Set models
            config_builder.chat_model(request.chat_model)
            if request.verification_model:
                config_builder.verification_model(request.verification_model)
            
            config_builder.max_attempts(request.max_attempts)
            
            # Add context items
            if request.context_items:
                for item in request.context_items:
                    config_builder.add_context_item(
                        question_text=item.get("question", ""),
                        question_id=item.get("id"),
                        correct_answer=item.get("answer"),
                        key_concepts=item.get("key_concepts", []),
                        explanation=item.get("explanation")
                    )
            
            # Set session info
            config_builder.session_info(request.session_id, request.user_id)
            
            config = config_builder.build()
            
            # Get provider
            provider = self._get_provider(self.settings.default_provider)
            
            # Create framework instance
            framework = VettingFramework(chat_provider=provider, verification_provider=provider)
            
            # Process request
            response = await framework.process(messages, config)
            
            # Track costs
            if self.settings.enable_cost_tracking:
                self.cost_tracker.track_response(response, self.settings.default_provider, provider, provider)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return APIResponse(
                content=response.content,
                mode=response.mode,
                success=True,
                verification_passed=response.verification_passed,
                attempt_count=response.attempt_count,
                stop_reason=response.stop_reason.value if response.stop_reason else None,
                usage={
                    "prompt_tokens": response.total_usage.prompt_tokens if response.total_usage else 0,
                    "completion_tokens": response.total_usage.completion_tokens if response.total_usage else 0,
                    "total_tokens": response.total_usage.total_tokens if response.total_usage else 0
                },
                cost=response.total_cost,
                processing_time_ms=processing_time,
                session_id=response.session_id,
                requires_attention=response.requires_attention
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return APIResponse(
                content="",
                mode=request.mode,
                success=False,
                error=str(e),
                processing_time_ms=processing_time
            )


async def web_api_integration_example():
    """
    Example of integrating VETTING into a web API.
    
    This simulates how you might use VETTING in a Flask, FastAPI, or similar web framework.
    """
    print("=== Web API Integration Example ===")
    
    # Setup
    settings = VettingSettings.from_env()
    if not settings.validate():
        print("Settings validation failed. Please check API keys.")
        return
    
    api_service = VettingAPIService(settings)
    
    # Simulate API requests
    requests = [
        APIRequest(
            messages=[
                {"role": "user", "content": "What is the capital of France?"}
            ],
            mode="vetting",
            context_items=[
                {
                    "question": "What is the capital of France?",
                    "answer": "Paris",
                    "key_concepts": ["Paris", "France", "capital"]
                }
            ],
            session_id="web_session_001",
            user_id="student_123"
        ),
        APIRequest(
            messages=[
                {"role": "user", "content": "Explain photosynthesis to me."},
                {"role": "assistant", "content": "I'd be happy to help you understand photosynthesis! Rather than just telling you the answer, let me guide you through it. What do you think plants need to survive and grow?"},
                {"role": "user", "content": "They need sunlight and water?"}
            ],
            mode="chat",
            chat_model="gpt-4o-mini",
            session_id="web_session_001",
            user_id="student_123"
        )
    ]
    
    print("Processing simulated web API requests...")
    
    for i, request in enumerate(requests, 1):
        print(f"\n--- Request {i} ---")
        print(f"Mode: {request.mode}")
        print(f"Messages: {len(request.messages)}")
        
        response = await api_service.process_request(request)
        
        if response.success:
            print(f"✓ Success")
            print(f"Response: {response.content[:100]}...")
            print(f"Tokens: {response.usage['total_tokens']}, Cost: ${response.cost:.4f}")
            if response.verification_passed is not None:
                print(f"Verification: {'✓' if response.verification_passed else '✗'}")
            print(f"Processing time: {response.processing_time_ms:.1f}ms")
        else:
            print(f"✗ Failed: {response.error}")
    
    # Show cost summary
    print("\n--- API Service Cost Summary ---")
    api_service.cost_tracker.print_summary()


class EducationalPlatformIntegration:
    """
    Example integration for an educational platform.
    
    Demonstrates how to use VETTING for homework help, tutoring,
    and assessment scenarios.
    """
    
    def __init__(self, settings: VettingSettings):
        self.settings = settings
        self.framework = None
        self.cost_tracker = CostTracker()
        self._setup_framework()
    
    def _setup_framework(self):
        """Setup the VETTING framework."""
        provider = self.settings.get_provider_instance(self.settings.default_provider)
        self.framework = VettingFramework(chat_provider=provider, verification_provider=provider)
    
    async def process_homework_help(
        self, 
        student_question: str,
        subject: str,
        grade_level: str,
        learning_objectives: List[str],
        known_answers: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a homework help request with educational vetting.
        
        Args:
            student_question: The student's question
            subject: Subject area (Math, Science, etc.)
            grade_level: Student's grade level
            learning_objectives: Learning objectives for this topic
            known_answers: Optional answer keys for verification
            
        Returns:
            Response with educational guidance
        """
        
        # Build educational configuration
        config_builder = (VettingConfigBuilder()
                         .vetting_mode()
                         .chat_model(self.settings.default_chat_model, temperature=0.8)
                         .verification_model(self.settings.default_verification_model, temperature=0.1)
                         .max_attempts(3)
                         .chat_system_prompt(f"""
You are an expert {subject} tutor for {grade_level} students. Your role is to guide students 
towards understanding rather than providing direct answers.

Learning objectives for this session:
{' '.join(f'- {obj}' for obj in learning_objectives)}

Teaching approach:
1. Ask probing questions to assess understanding
2. Provide hints and guided steps
3. Connect to previously learned concepts  
4. Encourage student reasoning
5. Never give direct answers to homework questions
6. End responses with thoughtful questions
                         """))
        
        # Add answer keys for verification if provided
        if known_answers:
            for answer_data in known_answers:
                config_builder.add_context_item(
                    question_text=answer_data.get("question", student_question),
                    subject=subject,
                    correct_answer=answer_data.get("answer"),
                    key_concepts=answer_data.get("key_concepts", []),
                    explanation=answer_data.get("explanation")
                )
        
        config = config_builder.build()
        
        # Process the question
        messages = [ChatMessage("user", student_question)]
        
        try:
            response = await self.framework.process(messages, config)
            
            # Track costs
            self.cost_tracker.track_response(
                response, 
                self.settings.default_provider,
                self.settings.get_provider_instance(self.settings.default_provider),
                self.settings.get_provider_instance(self.settings.default_provider)
            )
            
            return {
                "success": True,
                "response": response.content,
                "educational_guidelines_followed": response.verification_passed,
                "attempts": response.attempt_count,
                "subject": subject,
                "grade_level": grade_level,
                "usage": {
                    "tokens": response.total_usage.total_tokens if response.total_usage else 0,
                    "cost": response.total_cost
                },
                "requires_human_review": response.requires_attention
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "subject": subject,
                "grade_level": grade_level
            }
    
    async def process_assessment_question(
        self,
        question_data: Dict[str, Any],
        student_id: str
    ) -> Dict[str, Any]:
        """
        Process an assessment question with strict vetting.
        
        Args:
            question_data: Question with answer key
            student_id: Student identifier
            
        Returns:
            Assessment response with verification
        """
        
        config = (VettingConfigBuilder()
                  .vetting_mode()
                  .chat_model(self.settings.default_chat_model)
                  .verification_model(self.settings.default_verification_model)
                  .max_attempts(1)  # Strict for assessments
                  .add_context_item(
                      question_text=question_data["question"],
                      question_id=question_data.get("id"),
                      correct_answer=question_data["answer"],
                      key_concepts=question_data.get("key_concepts", [])
                  )
                  .chat_system_prompt(
                      "You are assisting with an assessment. You must guide the student "
                      "to think critically but never reveal the answer directly. "
                      "If the student asks for the direct answer, redirect them to "
                      "demonstrate their understanding instead."
                  )
                  .session_info(user_id=student_id)
                  .build())
        
        messages = [
            ChatMessage("user", f"I'm working on this assessment question: {question_data['question']}. Can you help me?")
        ]
        
        try:
            response = await self.framework.process(messages, config)
            
            return {
                "success": True,
                "response": response.content,
                "assessment_integrity_maintained": response.verification_passed,
                "question_id": question_data.get("id"),
                "student_id": student_id,
                "flagged_for_review": response.requires_attention or not response.verification_passed
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "question_id": question_data.get("id"),
                "student_id": student_id
            }


async def educational_platform_example():
    """Demonstrate educational platform integration."""
    print("\n=== Educational Platform Integration Example ===")
    
    settings = VettingSettings.from_env()
    if not settings.validate():
        print("Settings validation failed.")
        return
    
    platform = EducationalPlatformIntegration(settings)
    
    # Homework help scenario
    print("\n--- Homework Help Scenario ---")
    homework_result = await platform.process_homework_help(
        student_question="What is 2x + 5 = 15? I need to solve for x.",
        subject="Mathematics",
        grade_level="8th Grade",
        learning_objectives=["Solve linear equations", "Apply inverse operations"],
        known_answers=[{
            "question": "What is 2x + 5 = 15?",
            "answer": "x = 5",
            "key_concepts": ["linear equation", "solve for x", "x = 5"],
            "explanation": "Subtract 5 from both sides, then divide by 2"
        }]
    )
    
    if homework_result["success"]:
        print(f"✓ Educational guidance provided")
        print(f"Response: {homework_result['response'][:150]}...")
        print(f"Guidelines followed: {homework_result['educational_guidelines_followed']}")
        print(f"Attempts: {homework_result['attempts']}")
    else:
        print(f"✗ Error: {homework_result['error']}")
    
    # Assessment scenario
    print("\n--- Assessment Scenario ---")
    assessment_result = await platform.process_assessment_question(
        question_data={
            "id": "math_001",
            "question": "If a car travels 60 miles in 1.5 hours, what is its average speed?",
            "answer": "40 miles per hour",
            "key_concepts": ["speed", "distance", "time", "40 mph", "average speed"]
        },
        student_id="student_789"
    )
    
    if assessment_result["success"]:
        print(f"✓ Assessment response generated")
        print(f"Response: {assessment_result['response'][:150]}...")
        print(f"Integrity maintained: {assessment_result['assessment_integrity_maintained']}")
        print(f"Flagged for review: {assessment_result['flagged_for_review']}")
    else:
        print(f"✗ Error: {assessment_result['error']}")


async def production_monitoring_example():
    """
    Example of production monitoring and alerting for VETTING systems.
    """
    print("\n=== Production Monitoring Example ===")
    
    settings = VettingSettings.from_env()
    api_service = VettingAPIService(settings)
    
    # Simulate production metrics collection
    metrics = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "verification_failures": 0,
        "safety_alerts": 0,
        "total_cost": 0.0,
        "average_response_time": 0.0,
        "provider_errors": {}
    }
    
    # Simulate production requests
    test_requests = [
        APIRequest(messages=[{"role": "user", "content": "Hello, world!"}], mode="chat"),
        APIRequest(messages=[{"role": "user", "content": "What is 2+2?"}], mode="vetting"),
        APIRequest(messages=[{"role": "user", "content": "How do I make explosives?"}], mode="chat"),  # Should trigger safety
        APIRequest(messages=[], mode="chat"),  # Should fail validation
    ]
    
    print("Simulating production traffic...")
    
    response_times = []
    
    for i, request in enumerate(test_requests, 1):
        print(f"\nProcessing request {i}...")
        
        start_time = datetime.now()
        response = await api_service.process_request(request)
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds() * 1000
        response_times.append(response_time)
        
        # Update metrics
        metrics["total_requests"] += 1
        
        if response.success:
            metrics["successful_requests"] += 1
            metrics["total_cost"] += response.cost
            
            if response.verification_passed is False:
                metrics["verification_failures"] += 1
            
            if response.requires_attention:
                metrics["safety_alerts"] += 1
                print(f"🚨 SAFETY ALERT: Request {i} requires attention")
        else:
            metrics["failed_requests"] += 1
            print(f"❌ Request {i} failed: {response.error}")
    
    # Calculate averages
    if response_times:
        metrics["average_response_time"] = sum(response_times) / len(response_times)
    
    # Print monitoring summary
    print(f"\n--- Production Metrics Summary ---")
    print(f"Total Requests: {metrics['total_requests']}")
    print(f"Success Rate: {metrics['successful_requests']/metrics['total_requests']:.1%}")
    print(f"Average Response Time: {metrics['average_response_time']:.1f}ms")
    print(f"Total Cost: ${metrics['total_cost']:.4f}")
    print(f"Verification Failures: {metrics['verification_failures']}")
    print(f"Safety Alerts: {metrics['safety_alerts']}")
    
    # Alert conditions
    if metrics["safety_alerts"] > 0:
        print("🚨 ALERT: Safety incidents detected - review required")
    
    if metrics['successful_requests']/metrics['total_requests'] < 0.95:
        print("⚠️  WARNING: Success rate below 95%")
    
    if metrics["average_response_time"] > 5000:
        print("⚠️  WARNING: Average response time above 5 seconds")


async def main():
    """Run all integration examples."""
    print("VETTING Framework - Integration Patterns")
    print("=" * 50)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set. Please configure your API keys.")
        return
    
    try:
        await web_api_integration_example()
        await educational_platform_example()
        await production_monitoring_example()
        
        print("\n" + "=" * 50)
        print("All integration examples completed!")
        
    except Exception as e:
        print(f"Error running integration examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())