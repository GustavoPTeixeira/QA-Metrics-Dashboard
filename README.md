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
- [ ] Cálculo de MTTR (Primeira Resolução vs Lead Time Total) e Idade de Defeitos Abertos (P50/P90)
- [ ] Reopen Rate baseado em coortes (`IssueTransition`)
- [ ] Taxa de Passagem (First Attempt vs Final Pass)
- [ ] Flakiness Index e Regra de Quarentena de Testes
- [ ] Defect Risk Score & Densidade de Defeitos por Módulo
- [ ] Escape Rate & Tendência de Backlog
- [ ] 100% de cobertura de testes unitários nas métricas

### Fase 3: API de Ingestão & Segurança
- [ ] Endpoints FastAPI para ingestão de webhooks e relatórios de CI
- [ ] Chaves de Idempotência contra envios duplicados
- [ ] Autenticação e RBAC (Viewer, Squad Lead, Admin)

### Fase 4: Dashboard UI (Frontend)
- [ ] Layout em Next.js (React) + Tailwind CSS + Tremor/Recharts
- [ ] Linha de KPIs Executivos com tamanho de amostra `(n)`
- [ ] Gráficos de Tendência de MTTR (14 dias) e Execução de Testes
- [ ] Heatmap de Risco: Severidade x Módulo
- [ ] "Hall of Shame" de Flakiness (Quarentena com 1 clique)
- [ ] Filtros globais (Período, Módulo, Time, Severidade)

### Fase 5: Integrações Reais & Alertas
- [ ] Conectores para Jira e GitHub Issues
- [ ] Notificações e alertas de SLA para Slack e Email

### Fase 6: Prontidão Open-Source
- [ ] Licenciamento (MIT/Apache 2.0)
- [ ] `CONTRIBUTING.md` e guia de arquitetura
- [ ] `docker-compose.yml` para execução rápida com 1 comando

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Propósito |
| :--- | :--- | :--- |
| **Backend** | Python 3.14+, FastAPI, SQLAlchemy, Pydantic | API de ingestão de alta performance e tipagem forte |
| **Banco de Dados** | SQLite (Dev/Testes), DuckDB / PostgreSQL (Prod/Analytics) | Suporte a queries OLAP rápidas e persistência confiável |
| **Frontend** | Next.js, React, Tailwind CSS, Tremor | Dashboard analítico executivo |
| **Testes** | Pytest | Test-Driven Development (TDD) |

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

# 6. Rodar a suíte de testes (26 testes)
pytest -v
```
