# Spec: Performance Testing Kit with Locust (P7)

## Goal
Implementar suíte determinística de testes de carga e performance em Python 3.12 usando Locust contra a API REST do Conduit (RealWorld) em Docker local. O kit define perfis de carga reprodutíveis (fumaça, carga sustentada, pico e estresse), estabelece gates de performance baseados em percentis (p95 / p99) e taxa de erro em CI, e inclui mecanismo de injeção de latência sintética para provar que o gate reprova quando o SLO é violado.

---

## System Under Test
- **Alvo:** Conduit API REST (Nitro/Prisma/SQLite em Node/Bun), porta `3000`.
- **Modo de execução:**
  - **Local/E2E:** Docker Compose (`compose.yaml` com imagem Conduit).
  - **Mock / CI rápido:** Servidor local mock em Python (FastAPI/uvicorn ou mock HTTP embutido) com injeção de latência configurável, permitindo rodar em CI em < 30s sem sobrecarregar runners efêmeros.
- **Por que este alvo:** Alvo já padronizado e validado no P1 (`playwright-reference-suite`), seguro, 100% isolado na máquina e sem risco de violação de termos de terceiros.

---

## What Gets Tested

### 1. Perfis de Carga (Workload Profiles)
| Perfil | Finalidade | Usuários | Spawn Rate | Duração | Gate de Aceite |
|---|---|:---:|:---:|:---:|---|
| **Smoke (Fumaça)** | Sanidade em PR/CI | 5 | 2/s | 15s | Error rate = 0%, p95 < 150ms |
| **Load (Carga)** | Carga nominal sustentada | 50 | 5/s | 60s | Error rate ≤ 1%, p95 < 250ms |
| **Spike (Pico)** | Rajada súbita de tráfego | 100 | 25/s | 30s | Error rate ≤ 2%, p95 < 500ms, recuperação pós-pico |
| **Stress (Estresse)** | Ponto de saturação | 200+ | 10/s | até falha | Identificar threshold de saturação e degradação |

### 2. Jornadas de Usuário (User Scenarios)
1. **Anonymous Reader:** navega por tags (`GET /api/tags`), lê feed global (`GET /api/articles?limit=10`), lê artigo individual (`GET /api/articles/{slug}`).
2. **Authenticated Author:** login (`POST /api/users/login`), publica artigo (`POST /api/articles`), favorita artigos (`POST /api/articles/{slug}/favorite`), adiciona comentários (`POST /api/articles/{slug}/comments`).
3. **Weight distribution:** 80% leitura (Anonymous Reader), 20% escrita/interação (Authenticated Author) refletindo uso real de plataforma web.

---

## Metrics & SLO Gates

### Métricas Primárias
- **p95 (Percentil 95):** 95% das requisições devem responder abaixo do limiar (ignora outliers de warmup, foca na experiência típica sob carga).
- **p99 (Percentil 99):** cauda longa de latência sob concorrência.
- **Taxa de Erro (Error Rate):** requisições 5xx ou timeout ÷ total de requisições. Meta ≤ 1% sob carga nominal.
- **RPS / Throughput:** requisições por segundo sustentadas sem degradação de p95.

### Critério de Bloqueio (CI Gate)
O script de execução headless do Locust analisa os resultados pós-teste e retorna exit code não-zero se:
1. `Error Rate > 1.0%`
2. `p95 > 300ms` em rotas de leitura
3. `p95 > 600ms` em rotas de escrita

### Prova do Gate (Failure Injection)
- Suíte inclui flag `--inject-latency` ou fixture de middleware lento.
- Teste de sanidade do próprio gate: injeta 400ms de delay artificial, roda o gate e **prova que o CI fica vermelho**. Sem isso, o gate não é confiável.

---

## Design Rules & Architecture

1. **Modular Tasks & User Classes:** Divisão limpa em `tasks/reader.py`, `tasks/author.py` herdando de `HttpUser`.
2. **Data-Driven & Dynamic Payloads:** Nomes, slugs e títulos gerados dinamicamente para evitar colisões e lock de banco de dados.
3. **Headless & CI Native:** Execução 100% CLI (`locust --headless --csv=... --html=...`).
4. **Resumo Automático de Performance:** Utilitário Python que consome o CSV do Locust e gera Markdown estruturado para o `$GITHUB_STEP_SUMMARY`.
5. **Comparação Histórica (Baseline Drift):** Capacidade de comparar o p95 atual contra um arquivo `baseline.json` e alertar sobre regressão de performance (> 20%).

---

## CI / CD
- Workflow GitHub Actions: `.github/workflows/perf-tests.yml`.
- Roda perfil **Smoke Gate** em todo PR/Push (< 25 segundos).
- Publica tabela de p50, p95, p99 e throughput diretamente no Job Summary.
- Anexa relatórios HTML e CSV como artifacts da build.

---

## Out of Scope
- Testes contra sites ou APIs públicas de terceiros (proibido pela regra de ouro da Parte 1.4).
- Teste de soak de longa duração (> 1 hora) no GitHub Actions gratuito.
- Testes distribuídos multi-worker (cluster Locust com master/workers em Kubernetes). Mantido em nó único para simplicidade e previsibilidade de CI.

---

## Done When
- [ ] Repo inicializado com Python 3.12 + `uv` (`pyproject.toml`, `uv.lock`).
- [ ] Cenários de Leitor e Autor implementados e calibrados (80/20).
- [ ] Execução headless com geração de relatórios HTML, CSV e Summary Markdown.
- [ ] Gate determinístico via script de validação de SLOs (exit 0 se aprovado, exit 1 se violado).
- [ ] Prova do gate: teste automatizado que valida que o gate barra quando latência artificial é injetada.
- [ ] CI GitHub Actions configurado e verde em < 30 segundos no modo smoke.
- [ ] README bilíngue detalhando decisões, SLOs, análise p95 vs média e guia de reprodução.
