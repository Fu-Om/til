---
title: CmdStanRでGPU(OpenCL)を使う
date: 2021-09-20
tags:
  - R
  - Stan
  - GPU
---

# 動機

DLとか[Rapids](https://rapids.ai/)でどの誤家庭でもあるGPUは高速化のために使えるが、ベイズモデリングで簡単にGPUを利用できるものがなかった。`CmdStan 2.26.1`以降でOpenCL対応したようなので試してみた。`CmdStanR`はターミナルで扱う`CmdStan`をRで使えるようにしたラッパーになる。`rstan`パッケージよりもコンパイルが高速であるらしい。[清水先生の資料](https://www.slideshare.net/simizu706/cmdstanrreducesum)

# 環境確認

```
cat /etc/lsb-release
```

```
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=20.04
DISTRIB_CODENAME=focal
DISTRIB_DESCRIPTION="Ubuntu 20.04.1 LTS"
```

```
clinfo -l
```

```
Platform #0: NVIDIA CUDA
 `-- Device #0: NVIDIA GeForce GTX 1080 Ti
```

Windowsは、GPUサポートのWSL2を使う。あとは、必要に応じて`nvidia-driver`など入れる。

# TL;DR CmdStanでOpenCLを使うため

* [公式ドキュメント](http://mc-stan.org/math/opencl_support.html)と[vignettes](https://mc-stan.org/cmdstanr/articles/opencl.html)
* `CmdStanR`を導入するときに特別なことは必要ない
* `apt install nvidia-opencl-dev`が必要だった
* OpenCLでコンパイルするためには、`make/local`に追記または、コンパイル時に`cpp_options = list(stan_opencl = TRUE)`を渡す

# CmdStanRのインストール

```
install.packages("cmdstanr", repos = c("https://mc-stan.org/r-packages/", getOption("repos")))

```

いつものパッケージと同様にインストールできる。次に`CmdStan`本体をインストールする。

C++コンパイラなどを確認する。

```
check_cmdstan_toolchain()

```

`CmdStan`本体をインストールはこれだけ。

```
install_cmdstan(cores = 2)

```

インストール先は、`~/.cmdstanr/cmdstan-2.27.0/`

```
$tree -L 1  ~/.cmdstanr/cmdstan-2.27.0/
~/.cmdstanr/cmdstan-2.27.0/
├── bin
├── examples
├── install-tbb.bat
├── Jenkinsfile
├── lib
├── LICENSE
├── make
├── makefile
├── README.md
├── runCmdStanTests.py
├── src
├── stan
└── test-all.sh
```

OpenCLでコンパイルする場合は、`make/local`ファイルを編集して、以下を追記する。

```
STAN_OPENCL=true
```

あるいは、モデルコンパイル時に、`cpp_options = list(stan_opencl = TRUE)`を渡す。

# 確認

`examples`があるので実行してみる。

```
cmdstanr::cmdstanr_example(example="schools", chains=2, quiet=FALSE, refresh = 1000)

```

```
Running MCMC with 2 sequential chains...

Chain 1 Iteration:    1 / 2000 [  0%]  (Warmup)
Chain 1 Iteration: 1000 / 2000 [ 50%]  (Warmup)
Chain 1 Iteration: 1001 / 2000 [ 50%]  (Sampling)
Chain 1 Iteration: 2000 / 2000 [100%]  (Sampling)
Chain 1 finished in 0.1 seconds.
Chain 2 Iteration:    1 / 2000 [  0%]  (Warmup)
Chain 2 Iteration: 1000 / 2000 [ 50%]  (Warmup)
Chain 2 Iteration: 1001 / 2000 [ 50%]  (Sampling)
Chain 2 Iteration: 2000 / 2000 [100%]  (Sampling)
Chain 2 finished in 0.1 seconds.

Both chains finished successfully.
Mean chain execution time: 0.1 seconds.
Total execution time: 1.0 seconds.
```

```
 variable   mean median   sd  mad     q5    q95 rhat ess_bulk
 lp__     -56.17 -56.11 6.19 7.66 -65.93 -46.80 1.10       19
 mu         6.90   7.08 3.90 3.76   0.17  13.41 1.09      204
 tau        4.51   3.40 3.72 3.29   0.87  11.85 1.13       14
 theta[1]   9.40   8.28 6.61 4.67   0.37  21.70 1.04      297
 theta[2]   7.17   7.45 5.22 3.99  -1.98  15.70 1.05      400
 theta[3]   6.34   6.91 6.03 4.48  -4.79  15.30 1.05      290
 theta[4]   6.98   7.01 5.48 4.00  -1.94  15.81 1.06      434
 theta[5]   5.47   6.29 5.30 4.23  -4.01  13.41 1.06      229
 theta[6]   5.99   6.39 5.66 4.54  -4.20  14.40 1.06      244
 theta[7]   9.04   8.50 5.52 4.39   0.86  19.35 1.03      282
 ess_tail
       51
      180
       26
      689
      838
      722
      659
      228
      630
      644

 # showing 10 of 11 rows (change via 'max_rows' argument or 'cmdstanr_max_rows' option)
```

`nvidia-smi`などでGPUで実行できているか確認できる。

## 感想

[ここらへんの大きめなSEIRモデル](https://mc-stan.org/users/documentation/case-studies/boarding_school_case_study.html)でどう振る舞うか確認したい。ところで`knitr`って`bash`を組み込めるのですね。
