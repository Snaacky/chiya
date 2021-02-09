# Chiya
Our private bot for the /r/animepiracy [Discord server](https://discord.gg/piracy).

# Getting started
The easiest way is to use docker via:

```
docker run -d docker.pkg.github.com/ranimepiracy/chiya/chiya-bot
```

## Building from source
To build the [docker image](https://docs.docker.com/engine/reference/commandline/build/) you will need to run:
```
docker build . -t chiya-bot
```
Afterwards you will just need to run
```
docker run -d index-web
```
