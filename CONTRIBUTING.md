# Contribuindo com o Instala Fácil

Obrigado por ajudar o projeto!

1. Abra uma Issue descrevendo o bug ou a melhoria e informando sua distribuição Linux, versão do sistema, versão do Instala Fácil e o comportamento esperado.
2. Faça um fork do repositório e crie um branch claro: `fix/corrigir-login` ou `feat/atalho-appimage`.
3. Mantenha a interface em português brasileiro, acessível e sem dependências desnecessárias.
4. Adicione testes para mudanças em `src/core.py`.
5. Rode `python3 -m unittest discover -s tests -v` e `xvfb-run -a python3 src/main.py --smoke-test` antes de abrir um Pull Request.
6. Abra o PR com descrição, como testar e capturas quando houver alterações visuais.

Não inclua tokens, chaves, senhas ou arquivos pessoais. Evite que comandos construídos com dados de arquivos executem `shell=True`. Não use elevação de privilégios onde não for estritamente necessária.

As contribuições serão disponibilizadas sob a licença MIT do repositório.
