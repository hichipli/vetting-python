"""
Cost tracking and analysis utilities for the VETTING framework.

This module provides comprehensive cost tracking across different providers
and models, with detailed breakdowns and reporting capabilities.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from ..core.models import Usage, VettingResponse


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a single request."""
    provider: str
    model_id: str
    usage: Usage
    input_cost: float
    output_cost: float
    total_cost: float
    timestamp: str
    request_type: str  # "chat" or "verification"


@dataclass
class CostSummary:
    """Summary of costs across multiple requests."""
    total_cost: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0
    provider_breakdown: Dict[str, float] = field(default_factory=dict)
    model_breakdown: Dict[str, float] = field(default_factory=dict)
    daily_costs: Dict[str, float] = field(default_factory=dict)
    average_cost_per_request: float = 0.0
    average_tokens_per_request: float = 0.0
    
    def update_averages(self):
        """Update calculated averages."""
        if self.total_requests > 0:
            self.average_cost_per_request = self.total_cost / self.total_requests
            self.average_tokens_per_request = self.total_tokens / self.total_requests


class CostTracker:
    """
    Comprehensive cost tracking system for VETTING framework usage.
    
    Tracks costs across providers, models, and time periods with detailed
    reporting and analysis capabilities.
    """
    
    def __init__(self, enable_persistence: bool = True, storage_path: Optional[str] = None):
        """
        Initialize the cost tracker.
        
        Args:
            enable_persistence: Whether to persist cost data to disk
            storage_path: Path to store cost data (defaults to ~/.vetting/costs/)
        """
        self.enable_persistence = enable_persistence
        self.cost_history: List[CostBreakdown] = []
        
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path.home() / ".vetting" / "costs"
        
        if enable_persistence:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_history()
    
    def track_response(
        self,
        response: VettingResponse,
        provider_name: str,
        chat_provider_instance,
        verification_provider_instance=None
    ):
        """
        Track costs from a VettingResponse.
        
        Args:
            response: The VettingResponse to track
            provider_name: Name of the provider used
            chat_provider_instance: Instance of the chat provider
            verification_provider_instance: Instance of the verification provider (optional)
        """
        timestamp = datetime.now().isoformat()
        
        # Track chat costs
        if response.chat_usage:
            chat_cost_breakdown = CostBreakdown(
                provider=provider_name,
                model_id=response.chat_model_used or "unknown",
                usage=response.chat_usage,
                input_cost=(response.chat_usage.prompt_tokens / 1000) * self._get_input_price(
                    chat_provider_instance, response.chat_model_used or "unknown"
                ),
                output_cost=(response.chat_usage.completion_tokens / 1000) * self._get_output_price(
                    chat_provider_instance, response.chat_model_used or "unknown"
                ),
                total_cost=chat_provider_instance.calculate_cost(
                    response.chat_model_used or "unknown", response.chat_usage
                ),
                timestamp=timestamp,
                request_type="chat"
            )
            self.cost_history.append(chat_cost_breakdown)
        
        # Track verification costs
        if response.verification_usage and verification_provider_instance:
            verification_cost_breakdown = CostBreakdown(
                provider=provider_name,
                model_id=response.verification_model_used or "unknown",
                usage=response.verification_usage,
                input_cost=(response.verification_usage.prompt_tokens / 1000) * self._get_input_price(
                    verification_provider_instance, response.verification_model_used or "unknown"
                ),
                output_cost=(response.verification_usage.completion_tokens / 1000) * self._get_output_price(
                    verification_provider_instance, response.verification_model_used or "unknown"
                ),
                total_cost=verification_provider_instance.calculate_cost(
                    response.verification_model_used or "unknown", response.verification_usage
                ),
                timestamp=timestamp,
                request_type="verification"
            )
            self.cost_history.append(verification_cost_breakdown)
        
        # Persist if enabled
        if self.enable_persistence:
            self._save_history()
    
    def _get_input_price(self, provider_instance, model_id: str) -> float:
        """Get input price per 1K tokens for a model."""
        try:
            if hasattr(provider_instance, 'MODEL_PRICING'):
                resolved_model = provider_instance._resolve_model_alias(model_id)
                if resolved_model in provider_instance.MODEL_PRICING:
                    return provider_instance.MODEL_PRICING[resolved_model][0]
        except:
            pass
        return 0.0
    
    def _get_output_price(self, provider_instance, model_id: str) -> float:
        """Get output price per 1K tokens for a model."""
        try:
            if hasattr(provider_instance, 'MODEL_PRICING'):
                resolved_model = provider_instance._resolve_model_alias(model_id)
                if resolved_model in provider_instance.MODEL_PRICING:
                    return provider_instance.MODEL_PRICING[resolved_model][1]
        except:
            pass
        return 0.0
    
    def get_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> CostSummary:
        """
        Get cost summary with optional filtering.
        
        Args:
            start_date: Filter costs from this date (ISO format)
            end_date: Filter costs to this date (ISO format)
            provider: Filter by provider name
            model: Filter by model ID
            
        Returns:
            CostSummary object with aggregated data
        """
        filtered_costs = self._filter_costs(start_date, end_date, provider, model)
        
        summary = CostSummary()
        
        for cost in filtered_costs:
            summary.total_cost += cost.total_cost
            summary.total_requests += 1
            summary.total_tokens += cost.usage.total_tokens
            
            # Provider breakdown
            if cost.provider not in summary.provider_breakdown:
                summary.provider_breakdown[cost.provider] = 0.0
            summary.provider_breakdown[cost.provider] += cost.total_cost
            
            # Model breakdown
            if cost.model_id not in summary.model_breakdown:
                summary.model_breakdown[cost.model_id] = 0.0
            summary.model_breakdown[cost.model_id] += cost.total_cost
            
            # Daily breakdown
            date_key = cost.timestamp.split('T')[0]  # Extract date part
            if date_key not in summary.daily_costs:
                summary.daily_costs[date_key] = 0.0
            summary.daily_costs[date_key] += cost.total_cost
        
        summary.update_averages()
        return summary
    
    def _filter_costs(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        provider: Optional[str],
        model: Optional[str]
    ) -> List[CostBreakdown]:
        """Filter cost history based on criteria."""
        filtered = self.cost_history
        
        if start_date:
            filtered = [c for c in filtered if c.timestamp >= start_date]
        
        if end_date:
            filtered = [c for c in filtered if c.timestamp <= end_date]
        
        if provider:
            filtered = [c for c in filtered if c.provider == provider]
        
        if model:
            filtered = [c for c in filtered if c.model_id == model]
        
        return filtered
    
    def get_top_costs(self, limit: int = 10, by: str = "total") -> List[Dict[str, Any]]:
        """
        Get top costs by various criteria.
        
        Args:
            limit: Number of results to return
            by: Sort criteria ("total", "provider", "model", "tokens")
            
        Returns:
            List of cost information dictionaries
        """
        if by == "provider":
            summary = self.get_summary()
            items = [(provider, cost) for provider, cost in summary.provider_breakdown.items()]
            items.sort(key=lambda x: x[1], reverse=True)
            return [{"name": name, "cost": cost, "type": "provider"} for name, cost in items[:limit]]
        
        elif by == "model":
            summary = self.get_summary()
            items = [(model, cost) for model, cost in summary.model_breakdown.items()]
            items.sort(key=lambda x: x[1], reverse=True)
            return [{"name": name, "cost": cost, "type": "model"} for name, cost in items[:limit]]
        
        elif by == "tokens":
            sorted_costs = sorted(self.cost_history, key=lambda x: x.usage.total_tokens, reverse=True)
            return [
                {
                    "model": cost.model_id,
                    "tokens": cost.usage.total_tokens,
                    "cost": cost.total_cost,
                    "timestamp": cost.timestamp,
                    "type": "request"
                }
                for cost in sorted_costs[:limit]
            ]
        
        else:  # by total cost
            sorted_costs = sorted(self.cost_history, key=lambda x: x.total_cost, reverse=True)
            return [
                {
                    "model": cost.model_id,
                    "cost": cost.total_cost,
                    "tokens": cost.usage.total_tokens,
                    "timestamp": cost.timestamp,
                    "type": "request"
                }
                for cost in sorted_costs[:limit]
            ]
    
    def export_csv(self, file_path: str):
        """Export cost history to CSV file."""
        import csv
        
        with open(file_path, 'w', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'provider', 'model_id', 'request_type',
                'prompt_tokens', 'completion_tokens', 'total_tokens',
                'input_cost', 'output_cost', 'total_cost'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for cost in self.cost_history:
                writer.writerow({
                    'timestamp': cost.timestamp,
                    'provider': cost.provider,
                    'model_id': cost.model_id,
                    'request_type': cost.request_type,
                    'prompt_tokens': cost.usage.prompt_tokens,
                    'completion_tokens': cost.usage.completion_tokens,
                    'total_tokens': cost.usage.total_tokens,
                    'input_cost': cost.input_cost,
                    'output_cost': cost.output_cost,
                    'total_cost': cost.total_cost
                })
    
    def _save_history(self):
        """Save cost history to disk."""
        if not self.enable_persistence:
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = self.storage_path / f"costs_{today}.json"
        
        # Load existing data for today
        existing_data = []
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
            except:
                pass
        
        # Add new costs from today
        today_costs = [
            cost for cost in self.cost_history
            if cost.timestamp.startswith(today)
        ]
        
        # Convert to dict format for JSON serialization
        serialized_costs = []
        for cost in today_costs:
            serialized_costs.append({
                'provider': cost.provider,
                'model_id': cost.model_id,
                'usage': {
                    'prompt_tokens': cost.usage.prompt_tokens,
                    'completion_tokens': cost.usage.completion_tokens,
                    'total_tokens': cost.usage.total_tokens
                },
                'input_cost': cost.input_cost,
                'output_cost': cost.output_cost,
                'total_cost': cost.total_cost,
                'timestamp': cost.timestamp,
                'request_type': cost.request_type
            })
        
        # Merge with existing data (avoiding duplicates by timestamp)
        existing_timestamps = {item.get('timestamp') for item in existing_data}
        new_costs = [cost for cost in serialized_costs if cost['timestamp'] not in existing_timestamps]
        
        all_costs = existing_data + new_costs
        
        with open(file_path, 'w') as f:
            json.dump(all_costs, f, indent=2)
    
    def _load_history(self):
        """Load cost history from disk."""
        if not self.enable_persistence or not self.storage_path.exists():
            return
        
        # Load all cost files
        for file_path in self.storage_path.glob("costs_*.json"):
            try:
                with open(file_path, 'r') as f:
                    cost_data = json.load(f)
                
                for item in cost_data:
                    usage = Usage(**item['usage'])
                    cost_breakdown = CostBreakdown(
                        provider=item['provider'],
                        model_id=item['model_id'],
                        usage=usage,
                        input_cost=item['input_cost'],
                        output_cost=item['output_cost'],
                        total_cost=item['total_cost'],
                        timestamp=item['timestamp'],
                        request_type=item['request_type']
                    )
                    self.cost_history.append(cost_breakdown)
            except Exception as e:
                print(f"Warning: Could not load cost file {file_path}: {e}")
    
    def clear_history(self):
        """Clear all cost history."""
        self.cost_history.clear()
        
        if self.enable_persistence:
            # Remove all cost files
            for file_path in self.storage_path.glob("costs_*.json"):
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Warning: Could not delete cost file {file_path}: {e}")
    
    def print_summary(self, **kwargs):
        """Print a formatted cost summary."""
        summary = self.get_summary(**kwargs)
        
        print("=== VETTING Framework Cost Summary ===")
        print(f"Total Cost: ${summary.total_cost:.4f}")
        print(f"Total Requests: {summary.total_requests}")
        print(f"Total Tokens: {summary.total_tokens:,}")
        print(f"Average Cost per Request: ${summary.average_cost_per_request:.4f}")
        print(f"Average Tokens per Request: {summary.average_tokens_per_request:.1f}")
        
        if summary.provider_breakdown:
            print("\n--- Cost by Provider ---")
            for provider, cost in sorted(summary.provider_breakdown.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / summary.total_cost) * 100 if summary.total_cost > 0 else 0
                print(f"{provider}: ${cost:.4f} ({percentage:.1f}%)")
        
        if summary.model_breakdown:
            print("\n--- Cost by Model ---")
            for model, cost in sorted(summary.model_breakdown.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / summary.total_cost) * 100 if summary.total_cost > 0 else 0
                print(f"{model}: ${cost:.4f} ({percentage:.1f}%)")
        
        if summary.daily_costs:
            print("\n--- Daily Costs ---")
            for date, cost in sorted(summary.daily_costs.items()):
                print(f"{date}: ${cost:.4f}")
        
        print("=" * 38)