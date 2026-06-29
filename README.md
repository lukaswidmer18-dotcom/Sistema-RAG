# Plataforma de RAG Avançado para Auditoria de Contratos

Dashboard executivo que permite enviar um contrato em PDF e auditá-lo via RAG local: o texto é
extraído, dividido em blocos e indexado em um ChromaDB persistente no disco; as perguntas são
respondidas pelo Groq (Llama 3 70B) usando exclusivamente os trechos recuperados do documento.

## Como instalar e rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
# edite o .env e cole sua GROQ_API_KEY

streamlit run app.py
```

Na primeira indexação, o `fastembed` baixa o modelo de embedding local
(`intfloat/multilingual-e5-large`, ~1.1GB, via onnxruntime) — é necessária conexão à internet
apenas nesse primeiro uso. O download é maior que um embedding genérico em inglês porque é o
que entrega recall aceitável em português (ver "Decisões de arquitetura" abaixo).

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `GROQ_API_KEY` | Sim | Chave da API Groq (console.groq.com), usada pelo `llm.py`. |

Veja `.env.example`.

## Como usar

1. Na barra lateral, envie o contrato em PDF. O app extrai, divide em blocos (~1000
   caracteres, 200 de sobreposição) e indexa no ChromaDB local (`./chroma_db`).
2. Clique em **Executar Auditoria Expressa** para disparar as 4 perguntas críticas padrão
   (multas/rescisão, vigência/renovação, confidencialidade/não-concorrência,
   pagamento/reajuste) e ver as respostas em cards.
3. Use o chat na parte inferior para perguntas livres sobre o mesmo contrato.
4. Cada resposta tem um expander **"Fontes utilizadas pela IA"** com o texto exato dos
   trechos recuperados do ChromaDB — útil para auditar a própria resposta da IA.

## Como rodar os testes

Este escopo inicial não inclui suíte de testes automatizados. Para validar manualmente:
`streamlit run app.py`, subir um PDF de teste e conferir indexação, Auditoria Expressa e chat.

## Decisões de arquitetura

- **Chunking sem LangChain**: em vez de `langchain-community` só para o text splitter,
  `pipeline.py` implementa uma janela deslizante (1000/200) que ajusta o corte para o
  parágrafo/frase/espaço mais próximo. Evita uma dependência pesada para uma função de
  ~25 linhas.
- **`llm.py` separado de `app.py`**: chamada ao Groq e o prompt anti-alucinação ficam isolados
  da camada de UI, facilitando troca de modelo/provedor sem tocar no Streamlit.
- **ChromaDB `PersistentClient`**: vetores salvos em `./chroma_db` (git-ignored). A cada novo
  upload, a coleção é recriada (`pipeline.reset()`) para a auditoria refletir só o documento
  atual, evitando contaminação cruzada entre contratos.
- **Modelo Groq**: `llama3-70b-8192` (pedido original) foi descontinuado pela Groq. Trocado para
  `llama-3.3-70b-versatile`, validado contra `client.models.list()` na conta do projeto. Se a
  Groq descontinuar esse id também, troque a constante `MODEL_NAME` em `llm.py`.
- **Chunking por cláusula antes da janela deslizante** (`pipeline.py`): testes manuais mostraram
  que cortar só por tamanho fixo (1000/200) misturava 2-3 cláusulas diferentes no mesmo chunk
  (ex: objeto + regime de execução + vigência), diluindo o embedding e fazendo a cláusula certa
  cair fora do top-15 em buscas de data ("quando o contrato vai acabar/iniciar"). `chunk_text`
  agora separa primeiro por `CLÁUSULA N` / `ARTIGO N` / `SEÇÃO N` (regex), e só então aplica a
  janela deslizante dentro de cada cláusula — assim uma cláusula nunca se mistura com a vizinha.
- **Embedding multilíngue (`intfloat/multilingual-e5-large` via `fastembed`/onnxruntime), não o
  default do ChromaDB**: o default (`all-MiniLM-L6-v2`, treinado majoritariamente em inglês)
  rankeava a cláusula certa fora do top-15 de 28 chunks para perguntas em português coloquial.
  `sentence-transformers` (torch) foi tentado primeiro e descartado: travou nesta máquina Windows
  por política de App Control bloqueando `torch/lib/shm.dll` — `fastembed` evita totalmente o
  torch. O e5-large exige prefixar `"query: "` nas perguntas e `"passage: "` nos chunks (convenção
  do modelo para retrieval assimétrico); por isso os embeddings são calculados manualmente em
  `_embed_query`/`_embed_documents` e passados via `query_embeddings=`/`embeddings=`, em vez de
  registrar um `embedding_function` no ChromaDB (que usaria o mesmo texto para os dois casos).
  Com essa combinação, as duas perguntas que falhavam subiram para rank 1 de 28 (similaridade
  ~0.85, contra <0.55 antes).
- **`TOP_K_DEFAULT = 5`** (`pipeline.py`): mantido em 5 (subido de 3) como margem extra de recall;
  não foi a causa raiz do problema acima, mas ajuda em casos de ambiguidade lexical (ex:
  "prestação" = serviço vs. parcela de pagamento).
