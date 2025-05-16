---                                 
title: 多くのファイルを遅延評価で読み込み、メモリ消費を抑える
date: 2021-09-23
tags:
  - R
  - tidyverse
---

# サンプルデータ作成

- `n`: ファイル数, `nr`:行数, `nc`:列数
- 新しく`data`ディレクトリを直下に掘る
- 1.csv ... n.csvを作成

```
set.seed(2021)
n <- 100
nr <- 100; nc <- 10
f = map_chr(1:n, ~str_c("./data/", .x, ".csv"))
ifelse(!dir.exists(file.path("./data")), dir.create(file.path("./data")), FALSE)

```

```
[1] FALSE
```

```
create_random_df <- function(nr, nc, path) {
  mat <- matrix(rnorm(nr*nc), nr, nc)
  colnames(mat) <- map_chr(1:nc, ~str_c("col_", .x))
  df <- as_tibble(mat)
  write_csv(df, file = path)
}
walk(f, ~create_random_df(nr, nc, .x))

```

```
read_csv("data/1.csv") %>% head() %>% knitr::kable()

```

| col\_1 | col\_2 | col\_3 | col\_4 | col\_5 | col\_6 | col\_7 | col\_8 | col\_9 | col\_10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -0.1224600 | -0.2603365 | 0.2701953 | 1.2060572 | -0.6745562 | 0.2159818 | 0.1492579 | 0.5683032 | 0.5534009 | -0.9598381 |
| 0.5524566 | 0.4503400 | -1.3432502 | 0.9941102 | 0.2381266 | -1.3925378 | -0.3123636 | 0.9520432 | -1.1167970 | 0.8789497 |
| 0.3486495 | -0.1428816 | -0.8488889 | 1.5391577 | 0.5450859 | -0.0743782 | -1.2595894 | 1.2442086 | 0.5740307 | 0.6760329 |
| 0.3596322 | -0.4867215 | -0.4076079 | 0.2918469 | -0.4488515 | -1.1360389 | 0.0519813 | 0.7995387 | 1.2043346 | 1.0426258 |
| 0.8980537 | -1.1957732 | -0.6661505 | 0.5105483 | 0.9712467 | -0.4295111 | 0.2044272 | -0.2429687 | 0.7274956 | 0.8920711 |
| -1.9225695 | 0.0469410 | -0.1032374 | -0.5409150 | -1.5471639 | 0.4795757 | 1.3869823 | -2.1849709 | -0.7023848 | 1.2172707 |

#  csvファイルの名前を1列にしたtribble

```
list_csv <- list.files(path = "data",
                       pattern = ".csv", full.names = TRUE)
df_csv <- tribble(~paths, list_csv) %>%
  unnest(cols = paths)

df_csv %>% head() %>% knitr::kable()

```

| paths |
| --- |
| data/1.csv |
| data/10.csv |
| data/100.csv |
| data/11.csv |
| data/12.csv |
| data/13.csv |

# 遅延評価

まず、dataframes列で`read_csv`をquosureにして評価しない。さらに、各dataframeに行う処理(今回の場合は`nrow()`)をquosureとしている。その後、nrows列を`rlang::eval_tidy`で評価している。

```
df_csv <- df_csv %>%
  mutate(dataframes=map(.x=paths, ~quo(read_csv(.x, col_types = cols())))) %>%
  mutate(nrows=map(.x=dataframes, ~quo(nrow(rlang::eval_tidy(.x)))))

df_csv <- df_csv %>%
  mutate(nrows_eval = map(nrows, rlang::eval_tidy)) %>%
  unnest(nrows_eval)
df_csv %>% head() %>% knitr::kable()

```

| paths | dataframes | nrows | nrows\_eval |
| --- | --- | --- | --- |
| data/1.csv | ~read\_csv(.x, col\_types = cols()) | ~nrow(rlang::eval\_tidy(.x)) | 100 |
| data/10.csv | ~read\_csv(.x, col\_types = cols()) | ~nrow(rlang::eval\_tidy(.x)) | 100 |
| data/100.csv | ~read\_csv(.x, col\_types = cols()) | ~nrow(rlang::eval\_tidy(.x)) | 100 |
| data/11.csv | ~read\_csv(.x, col\_types = cols()) | ~nrow(rlang::eval\_tidy(.x)) | 100 |
| data/12.csv | ~read\_csv(.x, col\_types = cols()) | ~nrow(rlang::eval\_tidy(.x)) | 100 |
| data/13.csv | ~read\_csv(.x, col\_types = cols()) | ~nrow(rlang::eval\_tidy(.x)) | 100 |

## 複数の処理をしたいときは？

実行したい関数をtribbleで返す関数をまとめておく(この場合、`my_func`)。そして新しいtribbleの列を作成する。

```
list_csv <- list.files(path = "data",
                       pattern = ".csv", full.names = TRUE)
df_csv <- tribble(~paths, list_csv) %>%
  unnest(cols = paths)
my_func <- function(x) {
  x <- rlang::eval_tidy(x)
  tribble(~nrows, ~ncols,
          nrow(x), ncol(x))
}

df_csv <- df_csv %>%
  mutate(dataframes = map(.x=paths, ~quo(read_csv(.x, col_types = cols())))) %>%
  mutate(nrows_and_ncols = map(dataframes, my_func))

df_csv %>% head()

```

```
# A tibble: 6 ├Ś 3
  paths        dataframes nrows_and_ncols
  <chr>        <list>     <list>
1 data/1.csv   <quosure>  <tibble [1 × 2]>
2 data/10.csv  <quosure>  <tibble [1 × 2]>
3 data/100.csv <quosure>  <tibble [1 × 2]>
4 data/11.csv  <quosure>  <tibble [1 × 2]>
5 data/12.csv  <quosure>  <tibble [1 × 2]>
6 data/13.csv  <quosure>  <tibble [1 × 2]>
```

最後にtribbleをunnestして分解してあげる。

```
df_csv %>%
  unnest(cols = nrows_and_ncols) %>%
  head() %>% knitr::kable()

```

| paths | dataframes | nrows | ncols |
| --- | --- | --- | --- |
| data/1.csv | ~read\_csv(.x, col\_types = cols()) | 100 | 10 |
| data/10.csv | ~read\_csv(.x, col\_types = cols()) | 100 | 10 |
| data/100.csv | ~read\_csv(.x, col\_types = cols()) | 100 | 10 |
| data/11.csv | ~read\_csv(.x, col\_types = cols()) | 100 | 10 |
| data/12.csv | ~read\_csv(.x, col\_types = cols()) | 100 | 10 |
| data/13.csv | ~read\_csv(.x, col\_types = cols()) | 100 | 10 |

# 参考

- [ブログ記事](https://www.brodrigues.co/blog/2021-03-19-no_loops_tidyeval/)
- [Advanced R](https://adv-r.hadley.nz/evaluation.html)
