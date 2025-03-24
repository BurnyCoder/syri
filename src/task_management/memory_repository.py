import asyncio
from typing import Dict
from .repository import Repository, Task

class MemoryRepository(Repository):
    """In-memory implementation of the task repository"""
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
    
    async def create_task(self, task: Task) -> Task:
        async with self._lock:
            if task.id in self._tasks:
                raise ValueError(f"Task with ID {task.id} already exists")
            self._tasks[task.id] = task
            return task
    
    async def get_task(self, task_id: str) -> Task:
        async with self._lock:
            if task_id not in self._tasks:
                raise ValueError(f"Task with ID {task_id} not found")
            return self._tasks[task_id]
    
    async def update_task(self, task: Task) -> Task:
        async with self._lock:
            if task.id not in self._tasks:
                raise ValueError(f"Task with ID {task.id} not found")
            self._tasks[task.id] = task
            return task
    
    async def delete_task(self, task_id: str) -> None:
        async with self._lock:
            if task_id not in self._tasks:
                raise ValueError(f"Task with ID {task_id} not found")
            del self._tasks[task_id] 