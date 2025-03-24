import uuid
from typing import Optional
from .repository import Repository, Task, Message

class TaskService:
    """Service for managing tasks"""
    
    def __init__(self, repository: Repository):
        self.repository = repository
    
    async def create_task(self, content: str, task_id: Optional[str] = None) -> Task:
        """Create a new task with the given content"""
        if not task_id:
            task_id = str(uuid.uuid4())
            
        task = Task(
            id=task_id,
            messages=[Message(type="user", content=content)],
            status="PENDING"
        )
        
        try:
            return await self.repository.create_task(task)
        except ValueError:
            # If task exists, get it and append the new message
            existing_task = await self.repository.get_task(task_id)
            existing_task.messages.append(Message(type="user", content=content))
            return await self.repository.update_task(existing_task)
    
    async def process_task(self, task_id: str, response: str) -> Task:
        """Process a task with the given response"""
        task = await self.repository.get_task(task_id)
        task.messages.append(Message(type="assistant", content=response))
        task.status = "COMPLETED"
        return await self.repository.update_task(task)
    
    async def get_task(self, task_id: str) -> Task:
        """Get a task by ID"""
        return await self.repository.get_task(task_id)
    
    async def delete_task(self, task_id: str) -> None:
        """Delete a task by ID"""
        await self.repository.delete_task(task_id) 