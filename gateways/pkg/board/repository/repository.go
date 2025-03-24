package repository

import "context"

type Task struct {
	ID       string
	Messages []Message
	Status   string
}

type Message struct {
	Type    string
	Content string
}

type Repository interface {
	CreateTask(ctx context.Context, task Task) (Task, error)
	GetTask(ctx context.Context, id string) (Task, error)
	UpdateTask(ctx context.Context, task Task) (Task, error)
	DeleteTask(ctx context.Context, id string) error
}
