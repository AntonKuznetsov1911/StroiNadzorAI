# Makefile для StroiNadzorAI

.PHONY: help install dev test lint format clean docker-build docker-up docker-down migrate

# Цвета для вывода
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help:  ## Показать эту справку
	@echo "${BLUE}StroiNadzorAI - Available commands:${NC}"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${GREEN}%-15s${NC} %s\n", $$1, $$2}'

install:  ## Установить зависимости
	@echo "${BLUE}Installing dependencies...${NC}"
	pip install -r requirements.txt
	@echo "${GREEN}✓ Dependencies installed${NC}"

dev:  ## Установить dev зависимости
	@echo "${BLUE}Installing dev dependencies...${NC}"
	pip install -r requirements.txt
	pip install black flake8 mypy pytest pytest-cov
	@echo "${GREEN}✓ Dev dependencies installed${NC}"

test:  ## Запустить тесты
	@echo "${BLUE}Running tests...${NC}"
	pytest tests/ -v --cov=src --cov-report=term-missing
	@echo "${GREEN}✓ Tests completed${NC}"

test-unit:  ## Запустить только unit тесты
	@echo "${BLUE}Running unit tests...${NC}"
	pytest tests/unit/ -v
	@echo "${GREEN}✓ Unit tests completed${NC}"

lint:  ## Проверить код линтерами
	@echo "${BLUE}Running linters...${NC}"
	flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503
	mypy src/ --ignore-missing-imports
	@echo "${GREEN}✓ Linting completed${NC}"

format:  ## Форматировать код
	@echo "${BLUE}Formatting code...${NC}"
	black src/ tests/
	isort src/ tests/
	@echo "${GREEN}✓ Code formatted${NC}"

clean:  ## Очистить временные файлы
	@echo "${BLUE}Cleaning...${NC}"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "${GREEN}✓ Cleaned${NC}"

docker-build:  ## Собрать Docker образ
	@echo "${BLUE}Building Docker image...${NC}"
	docker-compose build
	@echo "${GREEN}✓ Docker image built${NC}"

docker-up:  ## Запустить все сервисы
	@echo "${BLUE}Starting services...${NC}"
	docker-compose up -d
	@echo "${GREEN}✓ Services started${NC}"
	@echo "Bot: docker-compose logs -f bot"
	@echo "API: http://localhost:8000/docs"

docker-down:  ## Остановить все сервисы
	@echo "${BLUE}Stopping services...${NC}"
	docker-compose down
	@echo "${GREEN}✓ Services stopped${NC}"

docker-logs:  ## Показать логи
	docker-compose logs -f

docker-restart:  ## Перезапустить сервисы
	@echo "${BLUE}Restarting services...${NC}"
	docker-compose restart
	@echo "${GREEN}✓ Services restarted${NC}"

migrate:  ## Запустить миграции БД
	@echo "${BLUE}Running migrations...${NC}"
	alembic upgrade head
	@echo "${GREEN}✓ Migrations completed${NC}"

migrate-create:  ## Создать новую миграцию
	@read -p "Enter migration name: " name; \
	alembic revision --autogenerate -m "$$name"

db-init:  ## Инициализировать БД
	@echo "${BLUE}Initializing database...${NC}"
	python -c "from src.database import init_db; init_db()"
	@echo "${GREEN}✓ Database initialized${NC}"

run-bot:  ## Запустить бота (без Docker)
	@echo "${BLUE}Starting bot...${NC}"
	python -m src.bot.bot_main

run-api:  ## Запустить API (без Docker)
	@echo "${BLUE}Starting API...${NC}"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

monitoring-up:  ## Запустить мониторинг (Prometheus + Grafana)
	@echo "${BLUE}Starting monitoring...${NC}"
	docker-compose --profile monitoring up -d
	@echo "${GREEN}✓ Monitoring started${NC}"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"

prod-deploy:  ## Production deployment
	@echo "${BLUE}Deploying to production...${NC}"
	@echo "${RED}WARNING: This will restart production services${NC}"
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		git pull && \
		docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build; \
		echo "${GREEN}✓ Deployed to production${NC}"; \
	else \
		echo "Deployment cancelled"; \
	fi

backup-db:  ## Создать бэкап БД
	@echo "${BLUE}Creating database backup...${NC}"
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U stroinadzor stroinadzor > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "${GREEN}✓ Backup created in backups/${NC}"

restore-db:  ## Восстановить БД из бэкапа
	@echo "${BLUE}Available backups:${NC}"
	@ls -1 backups/*.sql
	@read -p "Enter backup filename: " backup; \
	docker-compose exec -T postgres psql -U stroinadzor stroinadzor < backups/$$backup
	@echo "${GREEN}✓ Database restored${NC}"

check:  ## Полная проверка (lint + test)
	@echo "${BLUE}Running full check...${NC}"
	@make lint
	@make test
	@echo "${GREEN}✓ All checks passed${NC}"

version:  ## Показать версию
	@echo "${BLUE}StroiNadzorAI v3.0.0${NC}"
	@python --version
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$(docker-compose --version)"
