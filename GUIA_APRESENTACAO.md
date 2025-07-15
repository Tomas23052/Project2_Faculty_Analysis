# 🎯 Guia de Preparação para Apresentação
## IPT Faculty Performance Assessment System

### 📋 CHECKLIST PRÉ-APRESENTAÇÃO

#### ✅ Verificação Técnica:
- [ ] Sistema funciona: `python verify_system.py`
- [ ] Dashboard carrega: `streamlit run src/advanced_dashboard.py`
- [ ] Dados disponíveis: verificar pasta `data/`
- [ ] Notebook demo ready: `notebooks/apresentacao_demo.ipynb`

#### ✅ Materiais Preparados:
- [ ] **APRESENTACAO.md** - Slides estruturados
- [ ] **RELATORIO_TECNICO.md** - Documentação completa  
- [ ] **Notebook Demo** - Demonstração interativa
- [ ] **Dashboard Live** - Para mostrar em tempo real

---

## 🎤 ESTRUTURA DA APRESENTAÇÃO (15-20 min)

### 1️⃣ O PROBLEMA (3-4 min)
**Pergunta chave**: "Qual era o problema? Porque é que isto é um problema?"

**Pontos a cobrir:**
- Dados dispersos por múltiplas fontes
- Avaliação manual e subjetiva
- Sem visibilidade de métricas de investigação
- Decisões baseadas em intuição

**Material**: Slide 1 da APRESENTACAO.md

### 2️⃣ A SOLUÇÃO (8-10 min)
**Pergunta chave**: "Qual foi a solução que desenvolvi e como?"

**Pontos técnicos:**
- **Arquitetura ETL**: Extract → Transform → Load
- **Tecnologias**: Python, pandas, Streamlit, APIs
- **Fontes integradas**: HR PDFs, IPT profiles, ORCID, Scopus
- **Challenges resolvidos**: Rate limiting, name matching, data quality

**Material**: 
- Slides 2-3 da APRESENTACAO.md
- Notebook cells 3-4 para código
- Mostrar ficheiros em `src/`

### 3️⃣ OS BENEFÍCIOS (4-5 min)
**Pergunta chave**: "Qual o benefício disto?"

**Demonstração prática:**
- **Dashboard live**: `streamlit run src/advanced_dashboard.py`
- **Métricas concretas**: 100+ docentes, 5 fontes, 17 métricas
- **Insights acionáveis**: Top performers, compliance gaps
- **Impacto**: Decisões data-driven vs intuição

**Material**:
- Dashboard em tempo real
- Notebook cells 5-7 para visualizações
- Slides 4-5 da APRESENTACAO.md

---

## 🗣️ PONTOS DE DISCUSSÃO ESPERADOS

### Perguntas Técnicas Prováveis:

**Q: "Como garantem a qualidade dos dados scraped?"**
A: Sistema de validation com alertas automáticos, rate limiting respeitoso, multiple PDF libraries para robustez, retry logic para falhas temporárias.

**Q: "Que challenges enfrentaram com APIs?"**
A: ORCID tem rate limits (12 requests/segundo), Google Scholar não tem API oficial (usamos scholarly), Scopus requer acesso institucional.

**Q: "Como escalaria para outras instituições?"**
A: Arquitetura modular permite configuração de diferentes fontes, parametrização de URLs, templates customizáveis para diferentes formatos de dados.

**Q: "Qual foi a parte mais difícil?"**
A: Name matching entre fontes (variações, acentos, abreviações), data quality assurance, design de UX do dashboard.

### Demonstrar Conhecimento Técnico:

**Mostrar código específico:**
```python
# Exemplo de rate limiting implementado
def respectful_scraping(url, delay=2):
    time.sleep(delay)
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    return requests.get(url, headers=headers)
```

**Explicar decisões arquiteturais:**
- Porque pandas em vez de databases? → Simplicidade e performance para este volume
- Porque Streamlit? → Rapid prototyping e interactive dashboards
- Porque multiple PDF libraries? → Robustez para diferentes formatos

---

## 💻 SETUP PARA DEMONSTRAÇÃO

### Terminal Commands Preparados:
```bash
# 1. Verificação rápida
python verify_system.py

# 2. Dashboard (manter running em background)
streamlit run src/advanced_dashboard.py

# 3. Data overview (se perguntarem)
head -5 data/faculty_research_metrics.csv

# 4. Code walkthrough (se perguntarem)
cat src/collect_all_data.py
```

### Browser Tabs Preparados:
1. **Dashboard**: http://localhost:8501
2. **Notebook**: Jupyter com apresentacao_demo.ipynb
3. **Code**: VS Code com projeto aberto
4. **Documentation**: README.md aberto

---

## 🎯 MENSAGENS-CHAVE A TRANSMITIR

### 1. **Compreensão do Problema**
"Identifiquei que o IPT tinha dados valiosos dispersos e sem aproveitamento para insights estratégicos"

### 2. **Competência Técnica**  
"Implementei um pipeline robusto que integra 5 fontes diferentes com tratamento de qualidade de dados"

### 3. **Pensamento Crítico**
"Enfrentei challenges reais como rate limiting e name matching, desenvolvendo soluções técnicas apropriadas"

### 4. **Value Creation**
"O sistema transforma dados scattered num dashboard acionável que melhora decision-making"

### 5. **Production Mindset**
"Não é apenas um protótipo - tem documentação, testing, e está pronto para deployment"

---

## ⚠️ COISAS A EVITAR

- ❌ "O Copilot fez tudo" → ✅ "Usei ferramentas modernas para aumentar produtividade"
- ❌ Mostrar código sem explicar → ✅ Explicar lógica e decisões
- ❌ Saltar entre ficheiros aleatórios → ✅ Seguir estrutura lógica
- ❌ Focar só em features → ✅ Explicar business value

---

## 🏆 OBJETIVO FINAL

**Demonstrar que:**
1. **Compreendo** o problema de negócio
2. **Domino** as tecnologias usadas  
3. **Penso criticamente** sobre soluções
4. **Entrego valor** concreto e mensurável

**Meta**: Professor sair convencido de que desenvolvi um sistema profissional que resolve um problema real com competência técnica demonstrada.

---

## 📞 BACKUP PLANS

**Se dashboard não funcionar:**
- Notebook com visualizações estáticas
- Screenshots preparados
- Walkthrough do código

**Se perguntarem sobre partes específicas:**
- RELATORIO_TECNICO.md tem detalhes completos
- Código bem comentado em src/
- CLEANUP_SUMMARY.md mostra processo de otimização

**✅ PRONTO PARA APRESENTAÇÃO DE EXCELÊNCIA!**
