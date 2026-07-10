# Unigram Plus

* Autor: Kostya Gladkiy (Ucrânia)
* [Canal no Telegram](https://t.me/unigramPlus)
* Telegram: @unigramPlus
* Link de donactivos: [https://unigramplus.diaka.ua/donate](https://unigramplus.diaka.ua/donate)

Use o Unigram de uma forma mais confortável e produtiva. Este extra fornece muitas teclas de atalho para o uso rápido e confortável do Unigram e introduz muitas melhorias.
## Algumas das maiores melhorias são:
* Quando o foco está na lista de chat, informações como "chat, separadores, lista selecionada" não são anunciadas e se o cursor estiver na lista de mensagens,  não ouvirá a palavra "Lista".
* Quando o foco está no botão abrir ficheiro ou descarregar ficheiro, o nome e o tamanho do ficheiro serão falados, e se estiver no botão reproduzir de um ficheiro de áudio, ouvirá o seu nome e duração.
* Quando estiver numa mensagem de voz que está a ser reproduzida, ouvirá primeiro o tempo de reprodução e, em seguida, o restante das informações relevantes.
* Quando o foco fica numa mensagem contendo informações sobre uma chamada, a duração dessa chamada é anunciada.
* Quando o foco está numa mensagem seleccionada de Conversas, primeiro ouvirá a informação se ela foi seleccionada e, em seguida, o conteúdo da mensagem.
* Agora, ao rolar por uma lista de mensagens ou Conversas, não ouvirá a palavra "lida", mas "não lida" será falada antes de ler a mensagem em si. atualmente, esse recurso funciona apenas em inglês, russo e ucraniano.
* A função de gravação de mensagem de voz foi significativamente modernizada. gravar, enviar e cancelar mensagens de voz são acompanhados por sons distintos. além disso, quando essas operações são realizadas, o foco permanece na mesma posição e não salta para o botão de gravação ou o campo de edição.
* Adicionada a capacidade de rastrear a actividade de Conversas. Esta função é activada pressionando a combinação "ALT + T" duas vezes.
* Se os ficheiros de mídia anexados a uma mensagem forem abertos pressionando espaço, após fechá-los, o cursor retorna ao local onde estava anteriormente.
* Todos os sons de prompt de função ou apenas os prompts de reprodução de mensagem de voz podem ser desactivados.

## Sons personalizados
Os sons do UnigramPlus ficam na pasta `appModules\media` do complemento. Abra Configurações do NVDA > UnigramPlus e pressione **Abrir pasta de sons do UnigramPlus**. Para personalizar um som, copie para essa pasta o arquivo WAV substituto com o mesmo nome do som que deseja trocar, depois reinicie o NVDA ou recarregue os complementos. Atualizações do complemento podem restaurar os sons incluídos, portanto mantenha uma cópia dos seus arquivos personalizados.

## Informações do desenvolvedor, sobre donativos:
Se realmente gosta deste extra e deseja, e o mais importante, tem a oportunidade de apoiar o desenvolvedor financeiramente e, portanto, motivá-lo a continuar a desenvolver este extra, pode fazer isso transferindo uma pequena quantia usando os seguintes dados bancários: (link de doação ) (https://unigramplus.diaka.ua/donate), o número do cartão é 5169360009004502.
E lembre-se que todos que leram este post pensaram que alguém definitivamente apoiaria o desenvolvedor, mas não serei eu.
(nota dos tradutores: não se entende o que se quer dizer com a frase anterior)

<!-- shortcut-table-start -->
## lista de teclas de atalho:

> In the Category column, `UnigramPlus` identifies shortcuts provided by the add-on and `Unigram` identifies shortcuts built into Unigram.

> [!TIP]
> You can customize UnigramPlus shortcuts from NVDA menu > Preferences > Input gestures.

### Navegação entre conversas

| Atalho | Categoria | Ação |
|---|---|---|
| **Ctrl+Tab / Alt+Arrow Up / Ctrl+Page Up** | Unigram | Next chat |
| **Ctrl+Shift+Tab / Alt+Arrow Down / Ctrl+Page Down** | Unigram | Previous chat |
| **ALT+1** | UnigramPlus | Mover o foco para a lista de conversação |
| **ALT+2** | UnigramPlus | Move focus to the last message in an open chat |
| **ALT+3** | UnigramPlus | Mover o foco para o rótulo de 'mensagens não lidas |
| **ALT+4** | UnigramPlus | Move focus to list of chat folders |
| **ALT+5** | UnigramPlus | Move focus to open profile |
| **ALT+6** | UnigramPlus | Move focus to the list of group threads |
| **ALT+D** | UnigramPlus | Mover o foco para o campo de edição. Se o foco já estiver no campo de edição, depois de premir as teclas de atalho, irá deslocar-se para onde estava anteriormente |
| **ALT+End** | UnigramPlus | Go to the end |

### Pesquisa

| Atalho | Categoria | Ação |
|---|---|---|
| **Ctrl+E** | Unigram | Chat search |
| **Ctrl+F** | Unigram | Messages search per chat |
| **ALT+I** | UnigramPlus | Go to the list with search results |
| **F3** | UnigramPlus | Go to the next search result |
| **Shift+F3** | UnigramPlus | Go to the previous search result |

### Texto selecionado na área de escrita

| Atalho | Categoria | Ação |
|---|---|---|
| **Ctrl+Z** | Unigram | Undo |
| **Ctrl+Y** | Unigram | Redo |
| **Ctrl+X** | Unigram | Cut |
| **Ctrl+C** | Unigram | Copy |
| **Ctrl+V** | Unigram | Paste |
| **Ctrl+A** | Unigram | Select All |
| **Ctrl+B** | Unigram | Bold |
| **Ctrl+I** | Unigram | Italic |
| **Ctrl+K** | Unigram | Create Link |
| **Ctrl+Shift+X** | Unigram | Strikethrough |
| **Ctrl+Shift+M** | Unigram | Monospace |
| **Ctrl+Shift+P** | Unigram | Spoiler |
| **Ctrl+Shift+N** | Unigram | Null / Plain Text |

### Pastas

| Atalho | Categoria | Ação |
|---|---|---|
| **Ctrl+1** | Unigram | First folder (All chats) |
| **Ctrl+2** | Unigram | Second folder |
| **Ctrl+3** | Unigram | Third folder |
| **Ctrl+4** | Unigram | Fourth folder |
| **Ctrl+5** | Unigram | Fifth folder |
| **Ctrl+6** | Unigram | Sixth folder |
| **Ctrl+7** | Unigram | Seventh folder |
| **Ctrl+8** | Unigram | Eighth folder |
| **Ctrl+9** | Unigram | Archive |

### Ações de mensagens

| Atalho | Categoria | Ação |
|---|---|---|
| **Space** | UnigramPlus | Play or stop the focused voice or video message, or open media attached to the message |
| **Ctrl+C** | UnigramPlus | Copy the message if it contains text. If the focus is on a link, the link will be copied |
| **ALT+Q** | UnigramPlus | Pressione o botão "Visão instantânea", se estiver contido na mensagem actual |
| **ALT+Delete** | UnigramPlus | Eliminar uma mensagem ou conversa |
| **Shift+Delete** | UnigramPlus | Eliminar mensagem ou conversa em ambos os lados |
| **Ctrl+ALT+C** | UnigramPlus | Abrir comentários |
| **Enter** | UnigramPlus | Responder à mensagem |
| **ALT+F** | UnigramPlus | Reencaminhar mensagem |
| **Backspace** | UnigramPlus | Editar mensagem |
| **ALT+Shift+R** | UnigramPlus | Marcar conversa como lida |
| **Ctrl+Space** | UnigramPlus | Alternar para o modo de seleção |
| **Unassigned** | UnigramPlus | Guardar ficheiro como... |
| **Unassigned** | UnigramPlus | Pin a message or chat |
| **Left Arrow** | UnigramPlus | Announce the original message, the message that was replied to |
| **Right Arrow** | UnigramPlus | Move to the next media attachment in the focused message |
| **ALT+C** | UnigramPlus | Show message text in popup window |
| **ALT+W** | UnigramPlus | Announces the time a message was sent or received, as well as a list of reactions. Double-clicking toggles the announcement mode for this information. |
| **NVDA+Ctrl+0-9** | UnigramPlus | Review one of the ten most recent messages; 1 is the newest and 0 is the tenth newest |
| **Ctrl+Shift+A** | UnigramPlus | Press "Attach file" button |
| **Ctrl+N** | UnigramPlus | Press "New conversation" button |
| **Arrow Up** | Unigram | Edit last sent message |
| **Ctrl+Arrow Up** | Unigram | Reply to last sent message |
| **Esc / Alt+Arrow Left** | Unigram | Go back |
| **Alt+Arrow Right** | Unigram | Redo go back |

### Mensagens de voz e multimédia

| Atalho | Categoria | Ação |
|---|---|---|
| **ALT+P** | UnigramPlus | Reproduzir/pausar a mensagem de voz que está actualmente a tocar |
| **ALT+S** | UnigramPlus | Aumentar/diminuir a velocidade de reprodução de mensagens de voz |
| **ALT+E** | UnigramPlus | Fechar o leitor de áudio |
| **NVDA+ALT+R** | UnigramPlus | Convert voice message to text |
| **Ctrl+ALT+Right Arrow** | UnigramPlus | Fast forward a voice message |
| **Ctrl+ALT+Left Arrow** | UnigramPlus | Rewind voice message |

### Gravação de mensagens

| Atalho | Categoria | Ação |
|---|---|---|
| **Ctrl+R** | Unigram | Start record |
| **Ctrl+R (again)** | Unigram | Send recorded |
| **Ctrl+D** | Unigram | Stop recording |
| **Space (while recording) / Ctrl+P** | Unigram | Pause recording |
| **Ctrl+R** | UnigramPlus | Start or stop recording a voice message |
| **Ctrl+D** | UnigramPlus | Press once to cancel voice-message recording; press twice to change the recording notification type |

### Chamadas

| Atalho | Categoria | Ação |
|---|---|---|
| **Ctrl+Home** | Unigram | Accept incoming call |
| **Ctrl+End** | Unigram | Reject incoming call |
| **Ctrl+Page Up** | Unigram | Toggle camera |
| **Ctrl+Page Down** | Unigram | Toggle microphone |
| **ALT+Shift+C** | UnigramPlus | Telefonar se for um contacto ou entrar na conversação de voz se for um grupo |
| **ALT+Shift+V** | UnigramPlus | Pressionar o botão de videochamada |
| **ALT+Y** | UnigramPlus | Aceitar chamada |
| **ALT+N** | UnigramPlus | Premir botão "Declinar chamada" se houver uma chamada recebida, botão "Terminar chamada" se uma chamada estiver em curso ou deixar conversa por voz se estiver activa. |
| **ALT+A** | UnigramPlus | Pressionar o botão "Activar/desactivar microfone" |
| **ALT+V** | UnigramPlus | Pressionar o botão "Activar/desactivar câmera |

### Outros atalhos

| Atalho | Categoria | Ação |
|---|---|---|
| **Ctrl+0** | Unigram | Saved messages |
| **Ctrl+W** | Unigram | Close current window |
| **Ctrl+Q** | Unigram | Close Unigram (main window only) |
| **Ctrl+Shift+Y** | Unigram | Change status |
| **ALT+T** | UnigramPlus | Anunciar o nome e o status de uma conversa aberta |
| **ALT+M** | UnigramPlus | Abrir menu de navegação |
| **ALT+Shift+P** | UnigramPlus | Abrir o perfil da conversa atual |
| **ALT+L** | UnigramPlus | Enable automatic reading of new messages in the current chat |
| **ALT+H** | UnigramPlus | Show a list of all UnigramPlus shortcuts |
| **ALT+U** | UnigramPlus | Alternar anúncios da barra de progresso |
| **ALT+Shift+L** | UnigramPlus | Copiar dados de transmissão para a área de transferência |
| **NVDA+ALT+U** | UnigramPlus | Open UnigramPlus settings window |
<!-- shortcut-table-end -->

## Lista de alterações:

### Versão 5.5.8

* Compatibilidade restaurada com o Unigram 12.7, onde vários atalhos e anúncios tinham deixado de funcionar.
* As mensagens de sondagem voltam a anunciar a pergunta e as opções de resposta.
* A lista de tópicos do fórum volta a anunciar a pré-visualização da última mensagem.
* Durante uma chamada individual, os atalhos para silenciar o microfone (ALT+A), ativar ou desativar a câmara (ALT+V) e terminar a chamada (ALT+N) voltam a funcionar.
* ALT+End volta a ir para a mensagem mais recente da conversa.

### Versão 5.5.7

* A secção de atalhos de teclado foi reorganizada em tabelas por categoria e agora combina os atalhos do Unigram e do UnigramPlus.
* Ao gravar uma mensagem de voz ou de vídeo, o NVDA anuncia agora "A gravar uma mensagem de voz" ou "A gravar uma mensagem de vídeo" juntamente com o tempo decorrido, em vez de "Tn voice message".

### Versão 5.5.6

* Corrigido o botão de identidade no perfil de um grupo ou canal que anunciava "Identity root" ao passar pelo nome com a tecla Tab; agora anuncia o nome da conversa e o número de membros.
* O Ctrl+C deixou de ser processado duas vezes: copia a ligação quando o foco está sobre uma ligação e, nos restantes casos, deixa o Unigram copiar a mensagem.

### Versão 5.5.5

* Responder ou editar uma mensagem é agora anunciado no campo de introdução de mensagem, em vez do habitual aviso de mensagem.
* Corrigido o som de escrita que por vezes continuava a tocar após fechar a aplicação, depois de a outra pessoa parar de escrever ou após sair do chat; agora para assim que ninguém está a escrever no chat aberto.
* Atualizada a localização birmanesa.

### Versão 5.5.4

* Corrigidos anúncios indesejados, como contadores de chats não lidos em pastas, por exemplo "Todos 535". O progresso de transferência de arquivos agora fica limitado aos controles de envio e download do Unigram e é ignorado fora das janelas do Unigram.
* Corrigida a convivência com o complemento de NVDA para Telegram Desktop, ativando o UnigramPlus apenas quando o aplicativo em execução é detectado como Unigram.
* Adicionado um botão nas configurações do UnigramPlus para abrir a pasta de sons incluída, facilitando substituir arquivos WAV usando os mesmos nomes.
* Adicionada uma opção para a seta para cima no campo de edição de mensagem que move o foco para a última mensagem focada.
* O chinês tradicional foi recriado como zh_TW e o chinês simplificado foi adicionado como zh_CN.

### Versão 5.5.3

* Adicionado o anúncio automático do progresso de envio e transferência de ficheiros. Foi adicionada uma nova opção "Apenas durante o envio e transferência" à definição de anúncio das barras de progresso e é agora a opção predefinida. O atalho ALT+U alterna agora entre três estados: desativado, apenas durante envio/transferência, e anunciar todas as barras de progresso.
* Atualização do readme e das traduções.

### Versão 5.5.2

* Atualização do readme e das traduções.
* Alterado o som do indicador de escrita.

### Versão 5.5.1

* Corrigido o atalho para navegar pela lista de tópicos do grupo (ALT+6). Agora deteta corretamente a lista de tópicos ao abrir um grupo de fórum a partir da lista de conversas.
* Adicionado som indicador de escrita: é reproduzido um som em ciclo enquanto o outro lado está a escrever na conversa e para quando termina. Esta funcionalidade é inspirada na funcionalidade equivalente do script Unigram para JAWS.

### Versão 5.5.0

* Adicionada compatibilidade com o NVDA 2026.1.

### Versão 5.4.2

* Adicionada compatibilidade com o NVDA 2025.3.3.

### Versão 5.4.1

* Adicionada compatibilidade com o NVDA 2025.1.2.

### Versão 5.4.0

* Corrigido um problema na lista de conversas.

### Versão 1.9.0
* Adicionada uma combinação que alterna o nível de prompts auditivos entre valores como: "anunciar todas as barras de progresso", "anunciar todas as barras de progresso, exceto para reprodução de mensagem de voz" e "não anunciar barras de progresso". Para aqueles utilizadores que têm o carregamento automático de mídia desactivado no Unigram, o valor pode ser definido como "anunciar todas as barras de progresso, exceto aquelas para reprodução de mensagens de voz", e para aqueles que o têm activado, é preferível deixá-lo em "sem anúncio de barras de progresso".
* Adicionadas traduções para espanhol, croata e persa
* Corrigidos pequenos bugs de versões anteriores

### Versão 1.8.0
* Quando o foco é colocado no botão abrir ficheiro ou baixar ficheiro, o nome e o tamanho do ficheiro em questão serão falados, E quando o foco estiver no botão reproduzir em um ficheiro de áudio, ouvirá o seu nome e duração.
* Adicionada função para mover o foco para o campo de edição de mensagem. Se o foco já estiver neste campo, clicar irá mover para o último item em foco.
* Agora a função de seguimento de actividade de chat é activada pressionando ALT + T duas vezes. Ppode simplesmente activá-la, activá-la temporariamente, até a próxima vez que fechar o aplicativo.
* Agora também foi adicionada a capacidade de seleccionar o tipo de notificação para gravar mensagens de voz. Isso é feito pressionando a combinação control + d duas vezes. Aqui pode escolher entre um alerta de áudio, um alerta de texto e retornar ao comportamento padrão de gravação de mensagem de voz.

### Versão 1.7.0
* A função de gravação de mensagem de voz foi significativamente modernizada. gravar, enviar e cancelar são acompanhados por sons distintos. Além disso, enquanto essas operações estão a ser realizadas, o foco permanece na mesma posição e não salta para o botão de gravação ou o campo de edição.
### Versão 1.7.0
* Adicionada capacidade de seguir a actividade de Conversas. Esta opção pode ser activada pressionando ALT + shift + T e permanecerá activa até que o Unigram seja fechado ou até a próxima reinicialização do NVDA.
* As teclas de atalho que activam o botão de mais opções agora funcionam no chat de voz e na janela de chamada.

### Versão 1.6.0
* Se a mídia anexada de uma mensagem for aberta pressionando espaço, após fechá-la, o cursor retornará à sua posição anterior.
* Agora pode retornar ao chat de voz activo, não apenas do grupo actual, mas também de qualquer outro chat.
* Pressionar ALT + shift + C num chat aberto retornará ao chat de voz em vez de ligar para o contacto em questão.
* Se uma mensagem não for enviada, será notificado assim que a mensagem estiver em foco.
* Se uma mensagem em destaque contiver um link, ouvirá apenas o texto do link em si, não a mensagem em sua totalidade.
* Corrigido um problema em que a mudança de estado não era anunciada para botões como ligar / desligar o microfone e ligar / desligar a câmera em chamadas privadas e chats de voz.
* Agora, o recurso de cópia de mensagem permite que copie o conteúdo dos elementos na janela de visualização rápida de uma postagem.

### Versão 1.5.1

Esta actualização corrige um grande número de bugs e melhora o desempenho do extra.

### Versão 1.5.0
Esta actualização adiciona uma combinação que pressiona o botão "visualização rápida" na mensagem, se houver. Por padrão, esta função é activada com a combinação ALT + Q. Após a abertura deste artigo, o foco será automaticamente colocado no primeiro item, e após o fechamento, o foco retornará para a última mensagem vista. Também corrigimos um problema em que todos os itens de um artigo não eram lidos na janela de visualização rápida, mesmo que contivessem texto.
### Versão 1.1.7

Adicionada tradução turca

## Tradução Portuguesa:
Equipa Portuguesa do NVDA: Ângelo Abrantes <ampa4374@gmail.com> e Rui Fontes <Rui Fontes <rui.fontes@tiflotecnia.com>
14-08-2021
