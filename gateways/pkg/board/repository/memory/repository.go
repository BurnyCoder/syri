package memory

import (
	"context"
	"fmt"
	"sync"

	"gitlab.skypicker.com/platform/experimental/agents/gateways/pkg/board/repository"
)

type Repository struct {
	mu    sync.RWMutex
	tasks map[string]repository.Task
}

func NewRepository() *Repository {
	return &Repository{
		tasks: make(map[string]repository.Task),
	}
}

func (r *Repository) CreateTask(ctx context.Context, t repository.Task) (repository.Task, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, exists := r.tasks[t.ID]; exists {
		return repository.Task{}, fmt.Errorf("task with ID %s already exists", t.ID)
	}

	r.tasks[t.ID] = t
	return t, nil
}

func (r *Repository) GetTask(ctx context.Context, id string) (repository.Task, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	t, exists := r.tasks[id]
	if !exists {
		return repository.Task{}, fmt.Errorf("task with ID %s not found", id)
	}

	return t, nil
}

func (r *Repository) UpdateTask(ctx context.Context, t repository.Task) (repository.Task, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, exists := r.tasks[t.ID]; !exists {
		return repository.Task{}, fmt.Errorf("task with ID %s not found", t.ID)
	}

	r.tasks[t.ID] = t
	return t, nil
}

func (r *Repository) DeleteTask(ctx context.Context, id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, exists := r.tasks[id]; !exists {
		return fmt.Errorf("task with ID %s not found", id)
	}

	delete(r.tasks, id)
	return nil
}
