package board

import (
	"context"
	"errors"
	"log/slog"

	"github.com/gofrs/uuid/v5"
	"gitlab.skypicker.com/platform/experimental/agents/gateways/pkg/board/repository"
	"gitlab.skypicker.com/platform/experimental/agents/gateways/pkg/genkit"
)

type Service struct {
	repo      repository.Repository
	genkitSvc *genkit.Service
}

type Request struct {
	Task repository.Task
}
type Response struct {
	Task repository.Task
}

func NewService(repo repository.Repository, genkitSvc *genkit.Service) *Service {
	return &Service{repo: repo, genkitSvc: genkitSvc}
}

func (s *Service) CreateTask(ctx context.Context, req Request) (Response, error) {
	if req.Task.ID == "" {
		id, err := uuid.NewV4()
		if err != nil {
			return Response{}, err
		}
		req.Task.ID = id.String()
	}
	task, err := s.repo.CreateTask(ctx, req.Task)
	if err != nil {
		task, err = s.repo.GetTask(ctx, req.Task.ID)
		if err != nil {
			return Response{}, err
		}
		task.Messages = append(task.Messages, repository.Message{
			Content: req.Task.Messages[len(req.Task.Messages)-1].Content,
			Type:    "user",
		})
	}
	if len(task.Messages) == 0 {
		return Response{}, errors.New("task has no messages")
	}
	res, err := s.genkitSvc.SendRequest(ctx, &genkit.Request{
		Data: genkit.RequestData{
			SessionKey: task.ID,
			Message:    task.Messages[len(task.Messages)-1].Content,
		},
	})
	if err != nil {
		slog.Error("error sending request to genkit", "error", err)
		task.Status = "ERROR"
	} else {
		task.Messages = append(task.Messages, repository.Message{
			Content: res.Result,
			Type:    "assistant",
		})
		task.Status = "OK"
	}
	if task, err = s.repo.UpdateTask(ctx, task); err != nil {
		return Response{}, err
	}

	return Response{
		Task: task,
	}, nil
}
