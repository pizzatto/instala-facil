# Guia de uso — Instala Fácil 2.0

## Instalação

Abra `instala-facil_2.0.0_all.deb` com um instalador gráfico. Alternativamente, no Ubuntu/Debian:

```bash
cd ~/Downloads
sudo apt install ./instala-facil_2.0.0_all.deb
```

Caso a pasta se chame `Baixados`, use `cd ~/Baixados`.

## Fluxo de instalação

1. Selecione arquivos compatíveis.
2. Quando aparecer a caixa de confirmação, escolha **Sim**.
3. Veja a situação de cada arquivo: `Pronto para instalar` → `Preparando…` → `Instalando…` → `Concluído` ou `Falhou`.
4. Se o sistema pedir senha, confirme apenas se você confia no arquivo selecionado.
5. Clique em **Ver detalhes** para inspecionar mensagens e **Copiar relatório** para compartilhar problemas.

Quando uma instalação falha, o botão **Instalar agora** tenta novamente apenas os arquivos ainda não concluídos.

## Diagnóstico

```bash
instala-facil --version
instala-facil --diagnostico
```

### O aplicativo não abre

Verifique `python3-tk` e sua sessão gráfica (variáveis `DISPLAY` ou `WAYLAND_DISPLAY`). Se necessário, abra a partir de um terminal para ler a mensagem de erro. Exceções de inicialização também são registradas em `~/.local/state/instala-facil/erros.log` (ou em `XDG_STATE_HOME`).

### Autorização de administrador não aparece

Para DEB/RPM, o sistema precisa de `pkexec` e de um agente PolicyKit gráfico em execução. Algumas sessões minimalistas não possuem esse agente. O aplicativo informa essa falha no relatório. Consulte a documentação da sua distribuição antes de instalar componentes.

### O arquivo não é aceito

Formatos são verificados antes da instalação. Um arquivo com extensão `.deb` cujo cabeçalho está inválido será rejeitado. Um arquivo `.exe` é destinado ao Windows e não é instalado aqui.

### A instalação começa mas falha

Os detalhes vêm de APT, DNF/Zypper ou Flatpak, conforme o arquivo. Verifique se o arquivo é compatível com sua distribuição e arquitetura, se a rede funciona (dependências) e se há espaço em disco.

### Como remover programas

O Instala Fácil **não** possui desinstalador nesta versão. Use o gerenciador de aplicativos da sua distribuição. Para AppImages, o arquivo está em `~/.local/share/instala-facil/appimages/`, e o atalho em `~/.local/share/applications/`.

## Segurança e privacidade

O aplicativo é executado localmente. Ele não verifica a assinatura do pacote nem garante que o software baixado seja seguro; prefira sempre os sites oficiais e lojas da distribuição. Não inclua senhas nos relatórios compartilhados.
