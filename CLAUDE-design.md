# CLAUDE.md — Padrões de Design de Software/UI

Este arquivo define como você (Claude Code) deve tomar decisões de design visual e de interface em qualquer projeto, independente de stack (React, Vue, HTML puro, ou outro). É agnóstico de framework e de cliente: não carrega identidade de marca específica. Quando um projeto tiver marca própria (cores, tipografia, logo de um cliente), essas regras vivem em arquivo separado e têm prioridade sobre as decisões genéricas daqui, mas a lógica estrutural abaixo (como compor, como nomear, como tratar estado) continua valendo.

## 1. Princípios de design

Estes princípios governam toda decisão abaixo. Quando uma situação nova não estiver coberta por uma regra específica, volte a eles.

- **Hierarquia visual existe para guiar o olho, não para decorar.** Toda escolha de tamanho, peso ou cor deve responder à pergunta: o que o usuário deve notar primeiro, segundo, terceiro?
- **Consistência vale mais que originalidade pontual.** Um botão novo "criativo" que não segue o padrão dos outros botões do sistema cria atrito de aprendizado para o usuário. Resolva o problema dentro do sistema antes de inventar exceção.
- **Densidade de informação tem limite.** Tela cheia de elementos competindo por atenção não é "completa", é confusa. Espaço vazio é decisão de design, não espaço desperdiçado.
- **Estado é parte do design, não detalhe de implementação depois.** Todo componente interativo tem estados (default, hover, focus, active, disabled, loading, erro, vazio) definidos desde o início, não adicionados quando o bug aparecer.
- **Genérico, "parece template", e "parece IA" são o mesmo problema.** Antes de aceitar um layout, pergunte-se se ele tem alguma decisão de design intencional ou se é só o default da biblioteca sem ajuste nenhum.

## 2. Tokens e fundamentos

- Defina espaçamento como escala, não como valor arbitrário por componente. Use uma progressão fixa (ex.: 4, 8, 12, 16, 24, 32, 48, 64) e nunca um valor fora dela sem justificativa explícita.
- Cor é sistema, não paleta solta. Defina papéis (primária, secundária, texto, fundo, borda, erro, sucesso, aviso) em vez de aplicar hexadecimais direto nos componentes. Quando o projeto tiver marca própria, os papéis recebem os valores da marca; quando não tiver, use uma paleta neutra coerente.
- Tipografia segue escala modular, não tamanho aleatório por tela. Defina no máximo 5 a 6 níveis (display, título, subtítulo, corpo, legenda) e reutilize; criar um tamanho novo por tela quebra a hierarquia do sistema inteiro.
- Raio de borda, sombra e elevação seguem a mesma lógica de escala fixa que o espaçamento. Decisão ad-hoc em qualquer um desses cria inconsistência visual cumulativa que fica cara de corrigir depois.
- Nomeie tokens pela função (`color-text-primary`, `space-md`), nunca pelo valor (`color-blue-500` como nome de uso, ainda que o valor por trás seja azul). Nome por função sobrevive a redesign; nome por valor não.

## 3. Componentes

- Todo componente novo declara, antes da implementação: quais estados ele tem, quais props/variações são realmente necessárias agora (não especulativas), e onde ele se encaixa na hierarquia visual (primário, secundário, terciário).
- Componentes são compostos a partir de primitivos menores, não duplicados com pequena variação. Se você está copiando 90% de um componente existente para criar outro, o primitivo certo é extrair a parte comum, não duplicar.
- Nomenclatura de componente descreve o papel, não a aparência (`PrimaryButton`, não `BlueButton`; a cor pode mudar com o tema, o papel não).
- Todo componente interativo (botão, input, link, card clicável) precisa de feedback visual claro de hover e focus antes de ser considerado pronto. Ausência de estado de foco é falha de design, não detalhe menor.
- Estado vazio (lista sem itens, busca sem resultado) e estado de erro são parte do design do componente, definidos junto com o estado de sucesso, não como reflexão tardia.

## 4. Layout e responsividade

- Projete mobile-first quando o produto tiver uso real em tela pequena; quando não tiver (ferramenta interna de desktop, por exemplo), declare isso explicitamente em vez de aplicar responsividade que ninguém vai usar.
- Grid e alinhamento seguem a mesma escala de espaçamento da seção 2. Coluna, gutter e margem não são valores improvisados por tela.
- Breakpoints são poucos e consistentes em todo o projeto (tipicamente 3 a 4: mobile, tablet, desktop, wide), não um valor novo cada vez que um layout específico "quase encaixa".
- Texto e elementos interativos nunca dependem de uma largura de tela exata para funcionar; teste mentalmente o intervalo entre breakpoints, não só os pontos exatos.

## 5. Acessibilidade

- Contraste de texto contra fundo respeita no mínimo WCAG AA. Isso não é flexível por preferência estética.
- Todo elemento interativo é navegável por teclado e tem estado de foco visível. Se o componente só funciona com mouse, ele está incompleto.
- Imagens e ícones funcionais (não puramente decorativos) têm texto alternativo. Ícone sem label, sem `aria-label` ou equivalente, é falha, não estilo minimalista.
- Tamanho mínimo de área clicável em elementos tocáveis (mobile) segue referência de mercado (~44x44px), não o tamanho visual do ícone sozinho.
- Acessibilidade é parte do design entregue, não etapa de auditoria posterior. Se um componente não passaria um teste básico de leitor de tela, ele não está pronto, está pela metade.

## 6. Quando marca de cliente ou pedido específico conflita com este arquivo

Quando um cliente trouxer identidade própria (cor de marca com contraste insuficiente, tipografia sem boa legibilidade em corpo de texto, ou pedido de remover estado de foco "porque é mais bonito sem"), a prioridade é:

1. Resolver dentro da identidade da marca quando possível (ex.: usar a cor de marca só em elementos grandes onde o contraste funciona, e uma variação mais escura/clara dela em texto).
2. Quando não for possível resolver sem violar acessibilidade ou um princípio estrutural da seção 1, sinalizar o conflito explicitamente e propor a alternativa, em vez de aplicar o pedido literal e deixar o problema para descoberta tardia.

Estética de marca não anula usabilidade. As duas coisas raramente competem de verdade; quando parecem competir, normalmente existe uma solução que atende as duas e ainda não foi procurada.
