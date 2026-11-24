# Instala Fácil

Instalador gráfico de aplicativos para Linux, gratuito e de código aberto.

**Versão 2.0.0 · Python 3 · MIT**

O Instala Fácil permite selecionar instaladores baixados de fontes confiáveis, confirmar a instalação e acompanhar os resultados sem precisar abrir o terminal a cada vez.

## Instalação pelo código-fonte

```bash
git clone https://github.com/pizzatto/instala-facil.git
cd instala-facil
sudo apt install python3 python3-tk pkexec
python3 src/main.py
```

## Formatos previstos

DEB (APT), RPM (DNF/Zypper), AppImage e Flatpak. A compatibilidade depende das ferramentas instaladas na distribuição. Utilize apenas arquivos de fontes confiáveis; o aplicativo não verifica assinaturas criptográficas nem oferece isolamento adicional.

## Licença

MIT.
