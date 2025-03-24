from dataclasses import dataclass
from typing import List, Optional
from contextlib import asynccontextmanager

@dataclass
class Message:
    type: str
    content: str

@dataclass
class Task:
    id: str
    messages: List[Message]
    status: str

class Repository:
    """Interface for task management"""
    
    async def create_task(self, task: Task) -> Task:
        """Create a new task"""
        raise NotImplementedError
    
    async def get_task(self, task_id: str) -> Task:
        """Get a task by ID"""
        raise NotImplementedError
    
    async def update_task(self, task: Task) -> Task:
        """Update an existing task"""
        raise NotImplementedError
    
    async def delete_task(self, task_id: str) -> None:
        """Delete a task by ID"""
        raise NotImplementedError 