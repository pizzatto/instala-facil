# Instala Fácil 2.0.0

Segunda versão com interface redesenhada e foco em facilitar a instalação de programas baixados dos sites oficiais.

## Novidades

- Visual em preto e branco com barra lateral e cartões de status.
- Novo fluxo de instalação: arquivos ficam "Pronto para instalar" e passam para "Preparando…" e "Instalando…" após confirmação.
- Indicadores de instalados, pendentes e falhas.
- Relatórios detalhados de erro, que podem ser copiados.
- Opção de tentar novamente somente itens que falharam.
- Suporte a `.deb`, `.rpm`, `.AppImage`, `.flatpakref`, `.flatpak`/`.flatpakbundle`.
- Documentação de uso, contribuição e segurança, CI e 17 testes automatizados.

## Instalação

Baixe o arquivo `.deb` anexo e abra com o instalador gráfico do Ubuntu/Mint/Debian ou use:

```bash
sudo apt install ./instala-facil_2.0.0_all.deb
```

## Observações

A aplicação foi validada por testes unitários, abertura gráfica em ambiente de testes e simulação APT. Ainda é importante validar instalações reais nas distribuições dos usuários. Para instalar arquivos DEB/RPM, é necessário `pkexec` e um agente de autenticação gráfica. Use apenas arquivos de fontes confiáveis.
