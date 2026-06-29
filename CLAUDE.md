# CLAUDE.md — Padrões de Desenvolvimento (TypeScript/JS + Python)

Este arquivo define como você (Claude Code) deve se comportar ao trabalhar em qualquer projeto TypeScript/JavaScript ou Python sob minha supervisão. Não é um conjunto de sugestões: é o padrão mínimo aceitável. Quando um pedido meu conflitar com este arquivo, sinalize o conflito antes de executar, em vez de obedecer silenciosamente.

## 1. Princípios gerais

Estes princípios governam todas as decisões técnicas abaixo. Quando uma regra específica não cobrir uma situação nova, volte a estes princípios em vez de improvisar.

- **Correto antes de elegante.** Código que funciona de forma óbvia e um pouco verboso vale mais que uma abstração elegante que esconde um bug.
- **Legibilidade para humano, não só para máquina.** Otimização prematura é desperdício de tempo; clareza de leitura não é.
- **Menor mudança possível para resolver o problema.** Não refatore código não relacionado ao pedido a menos que eu peça explicitamente.
- **Sem mágica.** Evite metaprogramação, decorators customizados ou padrões "inteligentes" quando uma solução direta resolve. Mágica economiza linhas hoje e custa horas de debug depois.
- **Dependência é dívida.** Antes de adicionar uma biblioteca, pergunte-se se a necessidade justifica o custo de manutenção, superfície de ataque e peso que ela traz.

## 2. Arquitetura

- Defina a estrutura de pastas antes de escrever o primeiro arquivo de código. Separe por responsabilidade (camada de dados, lógica de negócio, apresentação), não por tipo de arquivo.
- Funções e módulos têm uma responsabilidade clara. Se a descrição de uma função precisa da palavra "e" ("busca o usuário e formata a resposta e loga o evento"), ela provavelmente deveria ser três funções.
- Evite estado global mutável. Quando inevitável, isole-o e documente quem pode alterá-lo.
- Em TypeScript: prefira composição sobre herança. Interfaces e types para contratos, classes apenas quando há estado e comportamento genuinamente acoplados.
- Em Python: siga a mesma lógica. Dataclasses ou Pydantic para dados, funções puras para lógica, classes reservadas para quando há estado real a encapsular.
- Antes de criar uma abstração nova (classe base, factory, plugin system), confirme que existem pelo menos dois casos de uso concretos que a justificam. Abstração para um caso hipotético futuro é complexidade paga adiantada sem garantia de retorno.

## 3. Qualidade de código

### TypeScript/JavaScript
- `strict: true` no tsconfig, sem exceção. `any` é proibido salvo comentário explicando por que é inevitável.
- ESLint + Prettier configurados desde o primeiro commit do projeto, não retrofitados depois.
- Nomes de variáveis e funções em inglês, completos e sem abreviação críptica (`userCount`, não `usrCnt`).
- Funções pequenas: se passar de ~40 linhas, considere dividir, e diga por que decidiu não dividir caso mantenha o tamanho.
- Async/await sempre, nunca misturar com `.then()` no mesmo bloco lógico.

### Python
- Type hints em toda função pública (parâmetros e retorno). Sem isso, o código não está completo.
- Siga PEP 8. Use `black` para formatação e `ruff` ou `flake8` para lint, configurados no projeto.
- f-strings para formatação, nunca `%` ou `.format()` em código novo.
- Evite `*args, **kwargs` sem necessidade real; eles escondem o contrato da função.
- Context managers (`with`) para qualquer recurso que precise ser liberado (arquivos, conexões, locks).

### Ambas linguagens
- Comentários explicam **por quê**, não **o quê**. Código que precisa de comentário explicando o que faz é candidato a ser reescrito de forma mais clara.
- Nada de código morto, comentado, ou `TODO` sem ticket ou data associada.

## 4. Testes

- Toda lógica de negócio não trivial tem teste. "Não trivial" significa: tem ramificação condicional, manipula dado externo, ou já causou bug uma vez.
- Teste o comportamento, não a implementação. Se um teste quebra porque você renomeou uma variável interna sem mudar o resultado, o teste está malfeito.
- Pirâmide de testes: a maioria unitária e rápida, alguns de integração nos pontos de junção real (banco, API externa), poucos end-to-end nos fluxos críticos.
- Antes de corrigir um bug, escreva o teste que reproduz a falha. Só depois corrija. Isso prova que o fix funciona e evita regressão.
- Cobertura mínima de 70% em lógica de negócio não é meta em si; é sinal de alerta quando está abaixo disso.

## 5. Segurança

- Nenhum secret, chave de API, token ou senha em código versionado, nunca, mesmo em branch temporário ou commit que será revertido depois. Use variáveis de ambiente e `.env` no `.gitignore` desde o primeiro commit.
- Valide e sanitize todo input externo (formulário, query param, payload de API, upload de arquivo) antes de usar. Nunca confie em dado vindo de fora do seu controle direto.
- Em SQL, sempre query parametrizada. Concatenação de string em query é proibida sem exceção.
- Atualize dependências com vulnerabilidade conhecida (`npm audit`, `pip-audit`) antes de considerar o projeto pronto para produção.
- Logs nunca contêm dado sensível (senha, token, CPF, dado de cartão) mesmo em ambiente de desenvolvimento.

## 6. Disciplina de desenvolvimento incremental

- Trabalhe em incrementos pequenos e revisáveis. Um commit (ou uma resposta sua) deve representar uma unidade de mudança que eu consigo revisar de uma vez, não um despejo de várias features misturadas.
- Antes de avançar para a próxima etapa de uma tarefa maior, confirme que a etapa atual está funcional e foi validada (rodou, testou, ou pelo menos foi revisada por mim), em vez de empilhar mudanças não verificadas.
- Quando uma tarefa for grande, declare o plano em etapas antes de começar a codar, para eu poder interromper ou redirecionar antes do trabalho estar feito.
- Nunca refatore arquitetura em paralelo com a implementação de uma feature nova. São duas mudanças diferentes; misturadas, ficam impossíveis de revisar ou reverter isoladamente.

## 7. Documentação e README

Um projeto não está pronto sem README cobrindo, no mínimo:
- O que o projeto faz, em uma ou duas frases.
- Como instalar e rodar localmente (comandos exatos, não descrição vaga).
- Variáveis de ambiente necessárias, com exemplo de `.env.example`.
- Como rodar os testes.
- Decisões de arquitetura não óbvias, se houver (por que essa estrutura, por que essa biblioteca em vez da alternativa comum).

Documentação que descreve o que o código já deixa óbvio é ruído. Documentação que explica a decisão por trás do código que não é óbvia é o que importa.

## 8. Quando este arquivo e meu pedido entrarem em conflito

Se eu pedir algo que viole uma regra acima (por exemplo, pedir para você colar uma chave de API direto no código "só para testar rápido"), sinalize o conflito e proponha a alternativa que respeita a regra, em vez de obedecer e assumir que eu sei o que estou fazendo. Regra existe justamente para os momentos de pressa em que eu mesmo esqueceria dela.
