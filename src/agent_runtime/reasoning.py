"""
Agent reasoning and decision-making components.
"""
import asyncio
import logging
import json
import re
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from opentelemetry import trace
from prometheus_client import Counter, Histogram, Gauge
from temporalio import activity

from .context import AgentContext, AgentState
from ..infrastructure.redis_client import RedisClient
from ..infrastructure.model_client import ModelClient

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Metrics
REASONING_OPERATIONS = Counter(
    'agent_reasoning_operations_total',
    'Total number of reasoning operations',
    ['operation', 'status']
)
REASONING_LATENCY = Histogram(
    'agent_reasoning_latency_seconds',
    'Reasoning operation latency',
    ['operation']
)
REASONING_TOKENS = Counter(
    'agent_reasoning_tokens_total',
    'Total number of tokens used in reasoning',
    ['type']  # prompt, completion
)
MEMORY_SIZE = Gauge(
    'agent_memory_size_bytes',
    'Size of agent memory in bytes',
    ['tenant_id']
)

class ReasoningEngine:
    """Advanced reasoning engine for agent decision making."""

    def __init__(self, model_client: ModelClient, memory_client: MemoryClient):
        self.model_client = model_client
        self.memory_client = memory_client
        self.logger = logging.getLogger(__name__)

    async def analyze_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes the current context and extracts key information.
        
        Args:
            context: Current context dictionary
        Returns:
            Dictionary containing analyzed information
        """
        with tracer.start_as_current_span("analyze_context") as span:
            span.set_attribute("context.size", len(str(context)))
            
            # Extract entities and relationships
            entities = await self._extract_entities(context)
            relationships = await self._analyze_relationships(entities)
            
            # Analyze sentiment and urgency
            sentiment = await self._analyze_sentiment(context)
            urgency = await self._determine_urgency(context)
            
            # Generate context summary
            summary = await self._generate_summary(context, entities, relationships)
            
            return {
                "entities": entities,
                "relationships": relationships,
                "sentiment": sentiment,
                "urgency": urgency,
                "summary": summary
            }

    async def _extract_entities(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts named entities from context.
        
        Args:
            context: Current context
        Returns:
            List of extracted entities with metadata
        """
        prompt = self._build_entity_extraction_prompt(context)
        response = await self.model_client.generate(prompt)
        return self._parse_entity_response(response)

    async def _analyze_relationships(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyzes relationships between extracted entities.
        
        Args:
            entities: List of extracted entities
        Returns:
            List of relationships between entities
        """
        relationships = []
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                rel = await self._determine_relationship(entity1, entity2)
                if rel:
                    relationships.append(rel)
        return relationships

    async def _analyze_sentiment(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Analyzes sentiment of the context.
        
        Args:
            context: Current context
        Returns:
            Dictionary with sentiment scores
        """
        prompt = self._build_sentiment_prompt(context)
        response = await self.model_client.generate(prompt)
        return self._parse_sentiment_response(response)

    async def _determine_urgency(self, context: Dict[str, Any]) -> float:
        """Determines the urgency level of the context.
        
        Args:
            context: Current context
        Returns:
            Urgency score between 0 and 1
        """
        factors = [
            await self._check_time_sensitivity(context),
            await self._check_priority_keywords(context),
            await self._check_user_state(context)
        ]
        return sum(factors) / len(factors)

    async def generate_response(self, context: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generates a response based on context and analysis.
        
        Args:
            context: Current context
            analysis: Analysis results
        Returns:
            Generated response
        """
        with tracer.start_as_current_span("generate_response") as span:
            span.set_attribute("analysis.entities", len(analysis["entities"]))
            
            # Retrieve relevant memories
            memories = await self._retrieve_relevant_memories(context, analysis)
            
            # Generate response options
            options = await self._generate_response_options(context, analysis, memories)
            
            # Score and select best response
            scored_options = await self._score_response_options(options, context)
            best_response = max(scored_options, key=lambda x: x["score"])
            
            # Refine selected response
            final_response = await self._refine_response(best_response["response"], context)
            
            return final_response

    async def _retrieve_relevant_memories(self, context: Dict[str, Any], 
                                       analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieves relevant memories based on context and analysis.
        
        Args:
            context: Current context
            analysis: Analysis results
        Returns:
            List of relevant memories
        """
        query = self._build_memory_query(context, analysis)
        memories = await self.memory_client.search(query)
        return self._filter_memories(memories, context)

    async def _generate_response_options(self, context: Dict[str, Any], 
                                      analysis: Dict[str, Any],
                                      memories: List[Dict[str, Any]]) -> List[str]:
        """Generates multiple response options.
        
        Args:
            context: Current context
            analysis: Analysis results
            memories: Retrieved memories
        Returns:
            List of possible responses
        """
        prompt = self._build_response_prompt(context, analysis, memories)
        response = await self.model_client.generate(prompt, num_responses=3)
        return self._parse_response_options(response)

    async def _score_response_options(self, options: List[str], 
                                    context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scores response options based on multiple criteria.
        
        Args:
            options: List of response options
            context: Current context
        Returns:
            List of scored responses
        """
        scored_options = []
        for option in options:
            relevance = await self._score_relevance(option, context)
            coherence = await self._score_coherence(option)
            empathy = await self._score_empathy(option, context)
            
            score = (relevance + coherence + empathy) / 3
            scored_options.append({"response": option, "score": score})
            
        return scored_options

    async def _refine_response(self, response: str, context: Dict[str, Any]) -> str:
        """Refines the selected response for better quality.
        
        Args:
            response: Selected response
            context: Current context
        Returns:
            Refined response
        """
        prompt = self._build_refinement_prompt(response, context)
        refined = await self.model_client.generate(prompt)
        return self._post_process_response(refined)

    async def update_memory(self, context: Dict[str, Any], 
                          analysis: Dict[str, Any],
                          response: str) -> None:
        """Updates memory with new interaction.
        
        Args:
            context: Current context
            analysis: Analysis results
            response: Generated response
        """
        memory_entry = {
            "timestamp": datetime.utcnow(),
            "context": context,
            "analysis": analysis,
            "response": response,
            "metadata": await self._generate_memory_metadata(context, analysis, response)
        }
        
        await self.memory_client.store(memory_entry)
        await self._prune_old_memories()

    def _build_entity_extraction_prompt(self, context: Dict[str, Any]) -> str:
        """Builds prompt for entity extraction."""
        return f"Extract key entities from the following context: {json.dumps(context)}"

    def _parse_entity_response(self, response: str) -> List[Dict[str, Any]]:
        """Parses entity extraction response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse entity response")
            return []

    def _build_sentiment_prompt(self, context: Dict[str, Any]) -> str:
        """Builds prompt for sentiment analysis."""
        return f"Analyze the sentiment of the following context: {json.dumps(context)}"

    def _parse_sentiment_response(self, response: str) -> Dict[str, float]:
        """Parses sentiment analysis response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse sentiment response")
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

    async def _check_time_sensitivity(self, context: Dict[str, Any]) -> float:
        """Checks time sensitivity of context."""
        keywords = ["urgent", "asap", "emergency", "deadline", "immediately"]
        return sum(1 for k in keywords if k in str(context).lower()) / len(keywords)

    async def _check_priority_keywords(self, context: Dict[str, Any]) -> float:
        """Checks for priority keywords in context."""
        keywords = ["important", "critical", "priority", "crucial", "vital"]
        return sum(1 for k in keywords if k in str(context).lower()) / len(keywords)

    async def _check_user_state(self, context: Dict[str, Any]) -> float:
        """Analyzes user state from context."""
        prompt = f"Analyze user state urgency from: {json.dumps(context)}"
        response = await self.model_client.generate(prompt)
        try:
            return float(response)
        except ValueError:
            return 0.5

    def _build_memory_query(self, context: Dict[str, Any], 
                          analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Builds query for memory retrieval."""
        return {
            "entities": analysis["entities"],
            "context_summary": analysis["summary"],
            "timestamp_range": {
                "start": datetime.utcnow() - timedelta(days=30),
                "end": datetime.utcnow()
            }
        }

    def _filter_memories(self, memories: List[Dict[str, Any]], 
                        context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filters and ranks retrieved memories."""
        scored_memories = [
            (memory, self._calculate_memory_relevance(memory, context))
            for memory in memories
        ]
        return [m[0] for m in sorted(scored_memories, key=lambda x: x[1], reverse=True)]

    def _calculate_memory_relevance(self, memory: Dict[str, Any], 
                                  context: Dict[str, Any]) -> float:
        """Calculates relevance score for a memory."""
        # Calculate semantic similarity
        similarity = self._calculate_semantic_similarity(
            str(memory["context"]), 
            str(context)
        )
        
        # Calculate time decay
        age = (datetime.utcnow() - memory["timestamp"]).days
        time_factor = math.exp(-age / 30)  # 30-day half-life
        
        return similarity * time_factor

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculates semantic similarity between two texts."""
        # Implement semantic similarity calculation
        # This could use embeddings, cosine similarity, etc.
        return 0.5  # Placeholder

    def _build_response_prompt(self, context: Dict[str, Any],
                             analysis: Dict[str, Any],
                             memories: List[Dict[str, Any]]) -> str:
        """Builds prompt for response generation."""
        return f"""
        Context: {json.dumps(context)}
        Analysis: {json.dumps(analysis)}
        Relevant Memories: {json.dumps(memories)}
        Generate a response that is:
        1. Relevant to the context
        2. Consistent with past interactions
        3. Appropriate in tone and style
        """

    def _parse_response_options(self, response: str) -> List[str]:
        """Parses multiple response options."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse response options")
            return [response]

    async def _score_relevance(self, response: str, context: Dict[str, Any]) -> float:
        """Scores response relevance."""
        prompt = f"""
        Response: {response}
        Context: {json.dumps(context)}
        Score the relevance from 0 to 1
        """
        score = await self.model_client.generate(prompt)
        try:
            return float(score)
        except ValueError:
            return 0.5

    async def _score_coherence(self, response: str) -> float:
        """Scores response coherence."""
        prompt = f"Score the coherence of this response from 0 to 1: {response}"
        score = await self.model_client.generate(prompt)
        try:
            return float(score)
        except ValueError:
            return 0.5

    async def _score_empathy(self, response: str, context: Dict[str, Any]) -> float:
        """Scores response empathy."""
        prompt = f"""
        Response: {response}
        Context: {json.dumps(context)}
        Score the empathy from 0 to 1
        """
        score = await self.model_client.generate(prompt)
        try:
            return float(score)
        except ValueError:
            return 0.5

    def _build_refinement_prompt(self, response: str, context: Dict[str, Any]) -> str:
        """Builds prompt for response refinement."""
        return f"""
        Original Response: {response}
        Context: {json.dumps(context)}
        Refine this response to be more:
        1. Natural and conversational
        2. Precise and accurate
        3. Well-structured
        """

    def _post_process_response(self, response: str) -> str:
        """Post-processes the refined response."""
        # Remove any special tokens
        response = re.sub(r'<[^>]+>', '', response)
        
        # Normalize whitespace
        response = ' '.join(response.split())
        
        # Ensure proper capitalization
        response = '. '.join(s.capitalize() for s in response.split('. '))
        
        return response.strip()

    async def _generate_memory_metadata(self, context: Dict[str, Any],
                                     analysis: Dict[str, Any],
                                     response: str) -> Dict[str, Any]:
        """Generates metadata for memory storage."""
        return {
            "context_type": await self._determine_context_type(context),
            "response_type": await self._determine_response_type(response),
            "entities": analysis["entities"],
            "sentiment": analysis["sentiment"],
            "importance_score": await self._calculate_importance_score(
                context, analysis, response
            )
        }

    async def _determine_context_type(self, context: Dict[str, Any]) -> str:
        """Determines the type of context."""
        prompt = f"Classify the context type: {json.dumps(context)}"
        return await self.model_client.generate(prompt)

    async def _determine_response_type(self, response: str) -> str:
        """Determines the type of response."""
        prompt = f"Classify the response type: {response}"
        return await self.model_client.generate(prompt)

    async def _calculate_importance_score(self, context: Dict[str, Any],
                                       analysis: Dict[str, Any],
                                       response: str) -> float:
        """Calculates importance score for memory."""
        factors = [
            analysis.get("urgency", 0),
            len(analysis.get("entities", [])) / 10,
            abs(analysis.get("sentiment", {}).get("positive", 0) - 
                analysis.get("sentiment", {}).get("negative", 0))
        ]
        return sum(factors) / len(factors)

    async def _prune_old_memories(self) -> None:
        """Prunes old or less important memories."""
        threshold_date = datetime.utcnow() - timedelta(days=90)
        await self.memory_client.delete_older_than(threshold_date)

class Memory:
    """Agent memory management."""
    
    def __init__(
        self,
        redis: RedisClient,
        tenant_id: str
    ):
        """Initialize memory manager.
        
        Args:
            redis: Redis client
            tenant_id: Tenant ID
        """
        self.redis = redis
        self.tenant_id = tenant_id
        
    async def add_memory(
        self,
        memory_type: str,
        content: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Add new memory.
        
        Args:
            memory_type: Type of memory
            content: Memory content
            ttl: Time-to-live in seconds
        """
        key = f"memory:{self.tenant_id}:{memory_type}:{datetime.utcnow().isoformat()}"
        
        await self.redis.set(
            key,
            content,
            ttl=ttl
        )
        
        # Update memory size metric
        size = len(str(content).encode())
        MEMORY_SIZE.labels(tenant_id=self.tenant_id).inc(size)
    
    async def get_recent_memories(
        self,
        memory_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent memories of specified type.
        
        Args:
            memory_type: Type of memory to retrieve
            limit: Maximum number of memories to return
            
        Returns:
            List of recent memories
        """
        pattern = f"memory:{self.tenant_id}:{memory_type}:*"
        keys = await self.redis.scan(pattern)
        
        memories = []
        for key in sorted(keys, reverse=True)[:limit]:
            memory = await self.redis.get(key)
            if memory:
                memories.append(memory)
        
        return memories
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search memories using semantic search.
        
        Args:
            query: Search query
            memory_type: Optional type filter
            
        Returns:
            List of matching memories
        """
        # TODO: Implement semantic search
        return []
    
    async def clear_memories(
        self,
        memory_type: Optional[str] = None
    ):
        """Clear memories of specified type.
        
        Args:
            memory_type: Type of memories to clear, or all if None
        """
        pattern = (
            f"memory:{self.tenant_id}:{memory_type}:*"
            if memory_type
            else f"memory:{self.tenant_id}:*"
        )
        
        keys = await self.redis.scan(pattern)
        if keys:
            await self.redis.delete(*keys)
            
        # Reset memory size metric
        MEMORY_SIZE.labels(tenant_id=self.tenant_id).set(0)
