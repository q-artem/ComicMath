# Comic Math

Математический шрифт в стиле Comic Sans для Typst.

Typst для формул требует шрифт с OpenType-таблицей `MATH` — иначе он откатывается
на New Computer Modern. Готового «комиксового» матшрифта нет, поэтому здесь берётся
таблица `MATH`, метрики, делимитеры и редкие символы у **Fira Math**, а очертания
букв, греческого, цифр, операторов и скобок пересаживаются из рукописных/комиксовых
шрифтов. Часть символов (`= ≠ ≤ ≥`, радикал, скобки, стрелки, акценты, штрих) рисуется
процедурно в `build.py`.

Готовый шрифт: **`fonts/ComicMathRelief.otf`** (семейство «Comic Math Relief»).

## Что внутри

Комиксовые: латиница, греческий, кириллица (для подписей в формулах), цифры,
`∑ ∏ ∫ ∬ ∭ ∮`, `√`, дроби, отношения (`= ≠ ≤ ≥ ≈ ≡ ∼ …`), стрелки, скобки
`( ) [ ] { } | ⌊⌋ ⌈⌉ ⟨⟩` и их растягивающиеся варианты, акценты, blackboard
(`ℕ ℤ ℝ …`, рисованные от руки), каллиграфика (`cal`), фрактура (`frak`),
bold и bold-italic.

`≤ ≥` — в российском начертании (нижняя черта параллельна галочке). Дробная черта
остаётся нативной (её рисует движок Typst, а не шрифт). Очень высокие скобки и
радикалы за пределами самого крупного размера собираются из кусочков Fira Math.

## Использование в Typst

```typ
#show math.equation: set text(font: "Comic Math Relief")
#set text(font: ("Comic Relief", "DejaVu Sans"))   // обычный текст: лат + кириллица
```

Собирать с указанием папки шрифтов:

```sh
typst compile --font-path fonts doc.typ
```

Готовый помощник для подключения — `comic-setup.typ`.

## Сборка шрифта

Нужны Python с `fonttools` и `skia-pathops` (см. `.venv`).

```sh
.venv/bin/python build.py 0 relief
```

Аргументы: `argv[1]` — сила «дрожания» очертаний (0 = чисто), `argv[2]` — донор
латиницы: `relief` (Comic Relief, по умолчанию) или `neue` (Comic Neue).
Результат пишется в `fonts/`.

Рукописные blackboard-буквы рисуются в [Rnote](https://rnote.flxzt.net)
(`sources/letters.rnote`), экспортируются в SVG и нарезаются по одной:

```sh
ROW_COUNTS="13,13" .venv/bin/python import_rnote.py sources/letters.svg "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
```

(`ROW_COUNTS` режет каждый ряд по N−1 самым большим зазорам — иначе двойные
обводки букв путают разбивку.)

## Структура

| | |
|---|---|
| `build.py` | сборка шрифта |
| `import_rnote.py` | нарезка рукописных букв из Rnote-SVG в `svg/bb/` |
| `fonts/` | база (Fira Math), доноры, готовые шрифты |
| `svg/bb/` | рукописные blackboard-буквы, по одной на файл |
| `sources/` | исходник Rnote |
| `comic-setup.typ` | подключение шрифта в документ |

## Лицензии

Готовые шрифты — и все шрифты-доноры — под **SIL Open Font License 1.1**
(полный текст: [`OFL.txt`](OFL.txt)). Шрифт является производной работой и
распространяется тоже под OFL 1.1.

Скрипты (`build.py`, `import_rnote.py`) — **MIT**.

Шрифты-источники:

| Шрифт | Авторы | Источник |
|---|---|---|
| Fira Math | © 2018–2020 Xiangdong Zeng | https://github.com/firamath/firamath |
| Comic Relief | © 2013 The Comic Relief Project Authors | https://github.com/loudifier/Comic-Relief |
| Comic Neue | © 2014 The Comic Neue Project Authors | https://github.com/crozynski/comicneue |
| Courgette | © 2012 Sorkin Type Co | https://fonts.google.com/specimen/Courgette |
| UnifrakturCook | © 2010 j. „mach“ wust, © 2009 Peter Wiegel | https://fonts.google.com/specimen/UnifrakturCook |

Рукописные blackboard-буквы (`sources/`, `svg/bb/`) — авторские, под OFL 1.1
вместе со шрифтом.
