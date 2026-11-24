# Como publicar o Instala Fácil no GitHub como repositório público

Este projeto está preparado para a conta **pizzatto**, repositório **instala-facil**. É necessário que o proprietário faça login no GitHub. O script **não** usa senhas no código.

## Método automático com GitHub CLI

1. Extraia `instala-facil-v2-codigo-fonte.zip` em uma pasta.
2. No Ubuntu, instale Git e a ferramenta oficial do GitHub uma única vez:

```bash
sudo apt update
sudo apt install git gh
```

3. Autentique-se no GitHub:

```bash
gh auth login
```

4. Entre na pasta extraída e publique:

```bash
cd ~/Downloads/instala-facil-v2
bash scripts/publicar_no_github.sh
```

O script irá construir o arquivo `.deb`, inicializar o repositório Git, publicar os arquivos na conta autenticada (exige o usuário `pizzatto`) e criar uma **Release pública v2.0.0** com o `.deb` para qualquer pessoa baixar.

Quando concluído, os endereços serão:

- Repositório: `https://github.com/pizzatto/instala-facil`
- Downloads: `https://github.com/pizzatto/instala-facil/releases`

**Atenção:** esses URLs só funcionarão depois que o usuário executar a publicação com sucesso. A publicação é irreversivelmente pública enquanto o repositório estiver com visibilidade pública.

## Método manual pelo site

1. Acesse `https://github.com/new` logado na conta correta.
2. Nomeie o repositório `instala-facil`, escreva a descrição do README e escolha **Public**.
3. Crie sem README automático, licença ou `.gitignore` (os arquivos já estão incluídos).
4. No terminal, dentro da pasta do código:

```bash
git init -b main
git add .
git commit -m "feat: Instala Fácil 2.0"
git remote add origin https://github.com/pizzatto/instala-facil.git
git push -u origin main
```

5. Na aba Releases, crie a tag `v2.0.0` e envie o pacote da pasta `dist/` criado com `./packaging/build_deb.sh`.

## Revisão antes de publicar

A licença MIT permite uso e contribuição pública. O repositório contém somente código e documentação do projeto, sem chaves de API ou arquivos particulares. Revise as capturas de tela antes de publicar para garantir que nenhum dado pessoal apareça.
