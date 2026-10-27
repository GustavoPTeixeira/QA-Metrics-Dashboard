# QA Metrics Dashboard

> **Strategic Engineering Quality Governance Platform for Historical Defect Tracking & Test Telemetry**  
> *Specification Ref: QA-GOV-2026-v1.0*

## 🎯 Visão Geral
O **QA Metrics Dashboard** é uma plataforma de governança de qualidade open-source projetada para transformar dados brutos de bug trackers (Jira, GitHub Issues) e de execuções de testes em CI/CD (JUnit, Allure, Playwright) em insights acionáveis para liderança técnica (VPs, Diretores, Quality Leads).

A plataforma responde a 5 perguntas críticas:
1. **MTTR & Idade de Defeitos:** Com que rapidez triamos e corrigimos bugs por severidade?
2. **Taxa de Reabertura (Cohort-Based):** Nossas correções estão gerando regressões?
3. **Pass Rate Final vs. Flakiness Index:** Os desenvolvedores podem confiar nos sinais dos testes automatizados?
4. **Densidade de Defeitos por Módulo:** Quais subsistemas da aplicação concentram o maior risco?
5. **Escape Rate:** Quais defeitos escaparam para produção?

---

## 🗺️ Roadmap de Entrega e Progresso

### Fase 0: Estrutura Base & Tooling
- [x] Criação da estrutura do repositório (`backend/`, `docs/`)
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
- [x] Endpoints de Ingestão de Telemetria com Idempotência Estrita:
  - [x] `POST /api/ingest/test-run` (Ingestão de relatórios de testes de CI/CD, detecção automática de flakiness e retries)
  - [x] `POST /api/ingest/issue` (Ingestão de bugs e tracking de transições de status)
- [x] Segurança de Ingestão via token no header `X-API-Key`
- [x] Tratamento de concorrência com `StaticPool` e supressão de warnings no pytest
- [x] 100% de cobertura em testes de API e integração

### Fase 4: Dashboard UI (Frontend)
- [ ] Setup da aplicação Next.js (App Router, Tailwind CSS, Lucide Icons, Recharts/Tremor)
- [ ] Linha de KPIs Executivos com tamanho de amostra `(n)`
- [ ] Heatmap de Risco: Severidade x Módulo
- [ ] Tabela interativa de Quarentena ("Hall of Shame") com ação de quarentena
- [ ] Filtro temporal dinâmico (Janela de 30, 60, 90, 120 dias)

### Fase 5: Integrações Reais & Alertas
- [ ] Conectores para Jira e GitHub Issues
- [ ] Notificações e alertas de SLA para Slack e Email

### Fase 6: Prontidão Open-Source
- [ ] Licenciamento (MIT/Apache 2.0)
- [ ] `CONTRIBUTING.md` e guia de arquitetura
- [ ] `docker-compose.yml` para execução rápida com 1 comando

---

## 🔌 Especificação da API REST

A API do backend fornece contratos tipados e documentados automaticamente pelo Swagger / OpenAPI:

| Método | Endpoint | Descrição | Autenticação |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Health check da API | Pública |
| `GET` | `/api/metrics/kpis` | Métricas executivas com janela configurável (`?window_days=60`) | Pública |
| `GET` | `/api/metrics/heatmap` | Matriz de densidade de defeitos (Módulo x Severidade) | Pública |
| `GET` | `/api/metrics/quarantine` | Testes instáveis recomendados para quarentena (Hall of Shame) | Pública |
| `POST` | `/api/ingest/test-run` | Ingestão idempotente de relatórios de testes de CI/CD | `X-API-Key` |
| `POST` | `/api/ingest/issue` | Ingestão ou atualização de defeitos (webhooks de bug trackers) | `X-API-Key` |

Documentação interativa disponível localmente em: `http://localhost:8000/docs`

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Propósito |
| :--- | :--- | :--- |
| **Backend** | Python 3.14+, FastAPI, SQLAlchemy 2.0, Pydantic v2 | API de ingestão de alta performance e tipagem forte |
| **Banco de Dados** | SQLite (Dev/Testes), DuckDB / PostgreSQL (Prod/Analytics) | Suporte a queries OLAP rápidas e persistência confiável |
| **Frontend** | Next.js, React, Tailwind CSS, Lucide | Dashboard analítico executivo |
| **Testes** | Pytest, TestClient | Test-Driven Development (TDD) com Golden Dataset |

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.11+ instalado
- Git

### Configuração do Backend
```powershell
# 1. Clonar o repositório
git clone <url-do-repo>
cd QA-Metrics-Dashboard/backend

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Instalar dependências em modo editável
pip install -e ".[dev]"

# 4. Executar as migrações do banco de dados (Alembic)
alembic upgrade head

# 5. Popular o banco com dados do Golden Dataset
python -m app.seeds.cli

# 6. Rodar a suíte completa de testes
pytest -v

# 7. Iniciar o servidor da API
uvicorn app.main:app --reload --port 8000
```
