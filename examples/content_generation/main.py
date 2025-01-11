"""
Example content generation bot implementation using Agent360.
Generates various types of content with proper formatting and style.
"""
from typing import Dict, Any, List, Optional
import asyncio
import logging
from src.agent_runtime.orchestrator import Orchestrator
from src.agent_runtime.model_service import ModelServiceFactory
from src.tools.base import ToolRegistry
from src.tools.rag_tool import RAGTool
from src.tools.rest_tool import RESTTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentGenerationBot:
    """Example content generation bot using Agent360."""
    
    def __init__(self, config: Dict[str, Any]):
        # Initialize model service
        self.model_service = ModelServiceFactory.create_model_service(
            "openai",
            {"model": "gpt-4"}
        )
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        
        # Configure tools
        self._setup_tools(config)
        
        # Initialize orchestrator
        self.orchestrator = Orchestrator(
            self.model_service,
            self.tool_registry
        )
        
    def _setup_tools(self, config: Dict[str, Any]):
        """Setup required tools."""
        # RAG tool for knowledge base
        rag_tool = RAGTool(
            config["cassandra_session"],
            config["cassandra_keyspace"],
            "content_knowledge"
        )
        self.tool_registry.register_tool(rag_tool)
        
        # REST tool for external resources
        rest_tool = RESTTool()
        self.tool_registry.register_tool(rest_tool)
        
    async def generate_content(
        self,
        prompt: str,
        content_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate content based on prompt and type.
        
        Args:
            prompt: Content generation prompt
            content_type: Type of content to generate
            parameters: Additional parameters for generation
            
        Returns:
            Generated content with metadata
        """
        parameters = parameters or {}
        input_data = {
            "query": prompt,
            "tools": ["rag_tool", "rest_tool"],
            "parameters": {
                "content_type": content_type,
                **parameters
            }
        }
        
        try:
            # Process generation request
            result = await self.orchestrator.process_step(input_data)
            
            # Format content
            formatted_content = await self._format_content(
                result["content"],
                content_type,
                parameters.get("format_options", {})
            )
            
            return {
                "content": formatted_content,
                "metadata": result.get("metadata", {}),
                "suggestions": result.get("suggestions", []),
                "references": result.get("references", [])
            }
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise
            
    async def _format_content(
        self,
        content: str,
        content_type: str,
        format_options: Dict[str, Any]
    ) -> str:
        """Format content based on type and options."""
        try:
            if content_type == "blog_post":
                return self._format_blog_post(content, format_options)
            elif content_type == "social_media":
                return self._format_social_media(content, format_options)
            elif content_type == "technical_doc":
                return self._format_technical_doc(content, format_options)
            else:
                return content
                
        except Exception as e:
            logger.error(f"Error formatting content: {str(e)}")
            return content
            
    def _format_blog_post(
        self,
        content: str,
        options: Dict[str, Any]
    ) -> str:
        """Format blog post content."""
        template = """
# {title}

{metadata}

{content}

{tags}

{call_to_action}
        """
        
        metadata = f"""
*Author: {options.get('author', 'Anonymous')}*
*Published: {options.get('date', 'Draft')}*
*Reading time: {options.get('reading_time', '5 min')}*
        """
        
        tags = "\n".join([f"#{tag}" for tag in options.get('tags', [])])
        
        return template.format(
            title=options.get('title', 'Untitled'),
            metadata=metadata,
            content=content,
            tags=tags,
            call_to_action=options.get('call_to_action', '')
        )
        
    def _format_social_media(
        self,
        content: str,
        options: Dict[str, Any]
    ) -> str:
        """Format social media content."""
        platform = options.get('platform', 'generic')
        
        if platform == 'twitter':
            # Ensure content fits tweet length
            content = content[:280]
            # Add hashtags
            hashtags = " ".join([f"#{tag}" for tag in options.get('tags', [])])
            content = f"{content}\n\n{hashtags}"
            
        elif platform == 'linkedin':
            # Add professional formatting
            content = f"{options.get('headline', '')}\n\n{content}"
            if options.get('include_call_to_action'):
                content += f"\n\n{options.get('call_to_action', '')}"
                
        return content
        
    def _format_technical_doc(
        self,
        content: str,
        options: Dict[str, Any]
    ) -> str:
        """Format technical documentation."""
        template = """
# {title}

## Overview
{overview}

## Technical Details
{content}

## Examples
{examples}

## References
{references}
        """
        
        return template.format(
            title=options.get('title', 'Technical Documentation'),
            overview=options.get('overview', ''),
            content=content,
            examples=options.get('examples', 'No examples provided.'),
            references="\n".join(options.get('references', []))
        )
        
async def main():
    # Configuration
    config = {
        "cassandra_session": None,  # Initialize in production
        "cassandra_keyspace": "content"
    }
    
    # Initialize bot
    bot = ContentGenerationBot(config)
    
    # Example content generation
    examples = [
        {
            "prompt": "Write a blog post about AI in healthcare",
            "content_type": "blog_post",
            "parameters": {
                "format_options": {
                    "author": "AI Expert",
                    "tags": ["AI", "Healthcare", "Technology"],
                    "call_to_action": "Subscribe to our newsletter!"
                }
            }
        },
        {
            "prompt": "Create a tweet about machine learning",
            "content_type": "social_media",
            "parameters": {
                "format_options": {
                    "platform": "twitter",
                    "tags": ["ML", "AI", "Tech"]
                }
            }
        }
    ]
    
    # Generate content
    for example in examples:
        try:
            result = await bot.generate_content(
                example["prompt"],
                example["content_type"],
                example["parameters"]
            )
            logger.info(f"Generated content: {result['content'][:100]}...")
            logger.info(f"Metadata: {result['metadata']}")
        except Exception as e:
            logger.error(f"Failed to generate content: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
