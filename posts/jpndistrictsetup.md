---                                                                                                       
title: jpndistrictのDocker環境設定
date: 2021-12-08
tags:
  - R
  - Docker
---

# jpndistrictのinstallに失敗する

ただの備忘録。[jpndistrict](https://github.com/uribo/jpndistrict)を用いて、[この記事](%5Bhttps%3A//yoshi-nishikawa.hatenablog.com/entry/2020/06/02/004647%5D)に従って地図を作成しようとしたところ、installで失敗する。Windows, WSL2で実行した。

`.docker-compose.yml`がrepo内にあるため、`docker compose up`で実行したものの、パラメータが足りずに実行できない。結局、`Dockerfile`から実行することにした。

実行環境: WSL2

```
> cat /etc/lsb-releases
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=20.04
DISTRIB_CODENAME=focal
DISTRIB_DESCRIPTION="Ubuntu 20.04.3 LTS"
```

まずは、repoをclone。

```
> git clone https://github.com/uribo/jpndistrict
```

docker imageを作成。rstudio server実行。

```
> cd jpndistrict
> docker build . -t uribo/jpndistrict:latest
> docker run -e PASSWORD=password -p 8787:8787 -v $(pwd):/home/rstudio -d --name jpndistrict uribo/jpndistrict:latest
```

`localhost:87887`にアクセス。必要パッケージをインストール。

```{ r }
install.packages("fastmap")
install.packages("Rcpp")
remotes::install_github("uribo/jpndistrict")

```

以上で環境構築完了。
