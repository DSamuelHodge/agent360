"""
Example usage of Temporal workflows in Agent360.
"""

import asyncio
import logging
from typing import Dict, Any
from uuid import uuid4

from src.infrastructure.temporal_workflow import TemporalService

logger = logging.getLogger(__name__)

async def run_example_workflow():
    """Run example workflow."""
    # Initialize Temporal service
    service = TemporalService(
        host='localhost',
        port=7233,
        namespace='agent360'
    )
    
    try:
        # Connect to Temporal
        await service.connect()
        
        # Start worker in background
        worker_task = asyncio.create_task(
            service.start_worker(task_queue='agent360-tasks')
        )
        
        # Prepare workflow input
        workflow_id = f"workflow-{uuid4()}"
        input_data = {
            'tasks': [
                {
                    'type': 'llm_request',
                    'parameters': {
                        'prompt': 'What is the capital of France?',
                        'model': 'gpt-4'
                    }
                },
                {
                    'type': 'tool_execution',
                    'parameters': {
                        'tool': 'rest_tool',
                        'method': 'GET',
                        'url': 'https://api.example.com/data'
                    }
                },
                {
                    'type': 'data_processing',
                    'parameters': {
                        'operation': 'transform',
                        'format': 'json'
                    }
                }
            ]
        }
        
        # Execute workflow
        logger.info(f"Starting workflow {workflow_id}")
        result = await service.execute_workflow(
            workflow_id=workflow_id,
            input_data=input_data
        )
        logger.info(f"Workflow completed: {result}")
        
        # Query workflow state
        state = await service.get_workflow_state(workflow_id)
        logger.info(f"Final workflow state: {state}")
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise
        
    finally:
        # Cleanup
        await service.close()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_example_workflow())
