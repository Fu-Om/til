---                                                                                                       
title: dplyrを使った関数
date: 2021-09-18
tags:
  - R
  - tidyverse
  - dplyr
---
# dplyrを使った関数

探索的に使うdplyr.

```
mtcars %>%
  filter(cyl == 6) %>%
  rmarkdown::paged_table()
```

特に問題ない.

```
my_filter <- function(filter_var, condition, df=mtcars) {
  df %>%
    filter(filter_var == condition)
}
my_filter(cyl, 6, mtcars) %>% rmarkdown::paged_table()
```

```
Problem with `filter()` input `..1`.
x object 'cyl' not found
ℹ Input `..1` is `filter_var == condition`.
```

どうやら、`filter_var`を参照している。`cyl`を参照してもらいたい。

# `enquo()`を使う方法

```
my_filter <- function(filter_var, condition, df=mtcars) {
  filter_var <- enquo(filter_var)
  df %>%
    filter(!!filter_var == condition)
}
my_filter(cyl, 6, mtcars) %>% rmarkdown::paged_table()
```

[Non Standard Evaluationの詳しい説明](https://adv-r.hadley.nz/evaluation.html)

# 簡単な方法`{{}}`

```
my_filter2 <- function(filter_var, condition, df=mtcars) {
  df %>%
    filter({{filter_var}} == condition)
}
my_filter2(cyl, 6, mtcars) %>% rmarkdown::paged_table()
```

# 複数の引数のとき

```
my_select <- function(df=mtcars, ...) {
  vars <- enquos(...)
  df %>%
    select(!!!vars)
}
my_select(mtcars, mpg, cyl) %>% rmarkdown::paged_table()
```
