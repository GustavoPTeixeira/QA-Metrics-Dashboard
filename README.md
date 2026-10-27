# QA Metrics Dashboard

> **Strategic Engineering Quality Governance Platform for Historical Defect Tracking & Test Telemetry**  
> *Specification Ref: QA-GOV-2026-v1.0 • Release: v1.0.0*

## 🎯 Visão Geral
O **QA Metrics Dashboard** é uma plataforma de governança de qualidade open-source projetada para transformar dados brutos de bug trackers (**Jira Cloud**, **GitHub Issues**, **Azure DevOps Boards**) e de execuções de testes em CI/CD (JUnit, Allure, Playwright, Pytest) em insights acionáveis para liderança técnica (VPs, Diretores, Quality Leads).

A plataforma responde a 5 perguntas críticas:
1. **MTTR & Idade de Defeitos:** Com que rapidez triamos e corrigimos bugs por severidade?
2. **Taxa de Reabertura (Cohort-Based):** Nossas correções estão gerando regressões?
3. **Pass Rate Final vs. Flakiness Index:** Os desenvolvedores podem confiar nos sinais dos testes automatizados?
4. **Densidade de Defeitos por Módulo:** Quais subsistemas da aplicação concentram o maior risco?
5. **Escape Rate:** Quais defeitos escaparam para produção?

---

## 🗺️ Roadmap de Entrega e Progresso (v1.0.0 Completo)

### Fase 0: Estrutura Base & Tooling
- [x] Criação da estrutura do repositório (`backend/`, `frontend/`, `docs/`)
- [x] Configuração de ambiente virtual (`.venv`) e empacotamento (`pyproject.toml`)
- [x] Configuração de suite de testes com `pytest`

### Fase 1a: Core de Domínio & Modelo de Dados
- [x] Enums de Domínio (`Severity` com cálculo de peso de risco, `IssueStatus`, `FoundIn`, `TestStatus`)
- [x] Modelos de Gestão de Defeitos em SQLAlchemy:
  - [x] `Module` (Taxonomia e Squads proprietárias)
  - [x] `Issue` (Defeitos normalizados)
  - [x] `IssueTransition` (Auditoria e fonte da verdade para MTTR e reaberturas)
- [x] Testes unitários e de integração (Roundtrip & constraints de unicidade)
- [x] Enums e Modelos de Telemetria de Testes:
  - [x] `TestStatus`
  - [x] `TestRun` (Execuções agregadas com garantia de idempotência)
  - [x] `TestCase` (Cenários individuais com hash SHA-256 determinístico)
  - [x] `TestAttempt` (Tentativas e retries de testes)
  - [x] `ScenarioAlias` (Rastreabilidade de testes renomeados)
- [x] Migrações com Alembic & Enforçamento de UTC

### Fase 1b: Gerador de Dados Sintéticos (Golden Dataset)
- [x] CLI para gerar dados simulados reprodutíveis (60 e 120 dias) com métricas conhecidas:
  - [x] Contrato determinístico com expectativas matemáticas imutáveis (`golden_dataset.py`)
  - [x] Gerador de módulos, defeitos, transições de status e telemetria de testes (`generator.py`)
  - [x] Comando executável via terminal (`python -m app.seeds.cli`)
  - [x] Testes unitários do gerador contra o gabarito com 100% de sucesso (`test_seeds.py`)

### Fase 2: Motor de Métricas & Lógica de Negócio (TDD)
- [x] Cálculo de MTTR (Primeira Resolução vs Lead Time Total) e Violações de SLA por Severidade
- [x] Idade de Defeitos em Aberto (P50/P90) com enforçamento de UTC
- [x] Reopen Rate baseado em coortes (`IssueTransition`) com denominação preservada
- [x] Escape Rate (Defeitos encontrados em produção)
- [x] Taxa de Passagem de Testes (First Attempt vs Final Pass)
- [x] Flakiness Index e Regra de Quarentena de Testes ("Hall of Shame")
- [x] Defect Risk Score & Densidade de Defeitos por Módulo (com Matriz Heatmap)
- [x] 100% de cobertura de testes unitários nas métricas

### Fase 3: API REST (FastAPI), Métricas & Ingestão Idempotente
- [x] Endpoints analíticos para consumo do Frontend:
  - [x] `GET /api/metrics/kpis` (Linha executiva com MTTR, Reopen, Pass Rate, Flakiness, Escape Rate)
  - [x] `GET /api/metrics/heatmap` (Matriz Módulo x Severidade)
  - [x] `GET /api/metrics/quarantine` (Candidatos ao Hall of Shame de testes instáveis)
  - [x] `GET /api/metrics/issues` (Stream unificado de tickets e boards)
- [x] Endpoints de Ingestão de Telemetria com Idempotência Estrita:
  - [x] `POST /api/ingest/test-run` (Ingestão de relatórios de testes de CI/CD, detecção automática de flakiness e retries)
  - [x] `POST /api/ingest/issue` (Ingestão de bugs e tracking de transições de status)
- [x] Segurança de Ingestão via token no header `X-API-Key`
- [x] Tratamento de concorrência com `StaticPool` e supressão de warnings no pytest
- [x] 100% de cobertura em testes de API e integração

### Fase 4: Dashboard UI (Frontend)
- [x] Setup da aplicação Next.js (App Router, TypeScript, Tailwind CSS v4, Lucide Icons)
- [x] Cliente HTTP tipado (`src/lib/api.ts`) com busca paralela (`Promise.all`) e verificação de saúde da API
- [x] Linha de 6 KPIs Executivos (`KpiGrid.tsx` e `KpiCard.tsx`) com tamanho de amostra `(n)` e avaliação de SLA
- [x] Heatmap de Risco (`RiskHeatmap.tsx`): Matriz colorimétrica Severidade × Módulo
- [x] Tabela interativa de Quarentena ("Hall of Shame" em `QuarantineTable.tsx`) com isolamento em 1 clique
- [x] Explorador de Boards e Conector Interativo (`BoardExplorer.tsx`) para Jira Cloud, GitHub Issues e Azure DevOps
- [x] Filtro temporal dinâmico no cabeçalho (`Header.tsx` com janelas de 30, 60, 90 e 120 dias)

### Fase 5: Integrações Reais & Alertas
- [x] Conectores e Adapters para Webhooks e APIs do **Jira Cloud**, **GitHub Issues** e **Azure DevOps Boards** (`app/integrations/connectors.py`)
- [x] Sincronização ativa de Boards (`POST /api/webhooks/sync/jira`, `POST /api/webhooks/sync/github`, `POST /api/webhooks/sync/azure-devops`)
- [x] Motor de Notificações e Alertas em formato **Slack Block Kit** (`app/integrations/alerts.py`):
  - [x] Alertas instantâneos de incidentes P1 (`PRODUCTION_CRITICAL_DEFECT`)
  - [x] Alertas de governança para violações de SLA (`SLA_BREACH`) e quarentena de testes instáveis (`FLAKY_QUARANTINE`)
- [x] Suite completa de testes de integração (`test_integrations.py` — 46 testes totais passando)

### Fase 6: Prontidão Open-Source & Containers
- [x] Licenciamento Open-Source (`LICENSE` — MIT)
- [x] Guia de contribuição e arquitetura (`Contributing.md`)
- [x] Containerização completa (`backend/Dockerfile`, `frontend/Dockerfile` e `docker-compose.yml` para execução com 1 comando)

---

## 🔌 Especificação da API REST

A API do backend fornece contratos tipados e documentados automaticamente pelo Swagger / OpenAPI:

| Método | Endpoint | Descrição | Autenticação |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Health check da API | Pública |
| `GET` | `/api/metrics/kpis` | Métricas executivas com janela configurável (`?window_days=60`) | Pública |
| `GET` | `/api/metrics/heatmap` | Matriz de densidade de defeitos (Módulo x Severidade) | Pública |
| `GET` | `/api/metrics/quarantine` | Testes instáveis recomendados para quarentena (Hall of Shame) | Pública |
| `GET` | `/api/metrics/issues` | Lista unificada de tickets (Jira, GitHub, Azure DevOps) | Pública |
| `POST` | `/api/ingest/test-run` | Ingestão idempotente de relatórios de testes de CI/CD | `X-API-Key` |
| `POST` | `/api/ingest/issue` | Ingestão ou atualização de defeitos (contrato canônico) | `X-API-Key` |
| `POST` | `/api/webhooks/github` | Webhook nativo do GitHub Issues com alerta P1 automático | `X-API-Key` |
| `POST` | `/api/webhooks/jira` | Webhook nativo do Jira com mapeamento de prioridade/status | `X-API-Key` |
| `POST` | `/api/webhooks/azure-devops` | Webhook nativo do Azure DevOps Boards (Service Hooks) | `X-API-Key` |
| `POST` | `/api/webhooks/sync/jira` | Importação e sincronização direta de Boards do Jira Cloud via REST API | `X-API-Key` |
| `POST` | `/api/webhooks/sync/github` | Importação e sincronização direta de Issues de repositórios GitHub | `X-API-Key` |
| `POST` | `/api/webhooks/sync/azure-devops` | Importação e sincronização direta de Work Items do Azure DevOps | `X-API-Key` |
| `POST` | `/api/webhooks/alerts/evaluate` | Avalia violações de SLA e quarentena e dispara alertas Slack | `X-API-Key` |

Documentação interativa disponível localmente em: `http://localhost:8000/docs`

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Propósito |
| :--- | :--- | :--- |
| **Backend** | Python 3.14+, FastAPI, SQLAlchemy 2.0, Pydantic v2 | API de ingestão de alta performance e tipagem forte |
| **Banco de Dados** | SQLite (Dev/Testes), DuckDB / PostgreSQL (Prod/Analytics) | Suporte a queries OLAP rápidas e persistência confiável |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Lucide | Dashboard analítico executivo |
| **Integrações** | Jira Cloud REST API, GitHub API, Azure DevOps WIQL, Slack Block Kit | Automação de governança e resposta a incidentes |
| **Infra & Testes** | Docker Compose, Pytest, TestClient | TDD com Golden Dataset (46 testes) e deploy reproduzível |

---

## 🚀 Como Executar

### Opção 1: Execução Rápida com Docker Compose (1 Comando)
```powershell
docker compose up --build
```
- **Dashboard UI:** `http://localhost:3000`
- **API & Swagger Docs:** `http://localhost:8000/docs`

---

### Opção 2: Execução Local para Desenvolvimento

#### 1. Backend (Terminal 1)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Popular o banco com o Golden Dataset
python -m app.seeds.cli

# Rodar a suíte completa de testes (46 testes)
pytest -v

# Iniciar o servidor da API na porta 8000
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend (Terminal 2)
```powershell
cd frontend
npm install
npm run dev
```

Acesse o dashboard em: `http://localhost:3000`

---

## 📄 Licença
Distribuído sob a licença **MIT**. Veja [`LICENSE`](LICENSE) para mais informações.
