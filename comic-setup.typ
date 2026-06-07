// Подключение ComicMath в любой Typst-документ:
//   #import "comic-setup.typ": comic
//   #show: comic
// собирать с:  typst compile --font-path <папка-со-шрифтами> doc.typ
#let comic(body) = {
  set text(font: ("Comic Relief", "DejaVu Sans"))      // текст: лат+кириллица, комикс
  show math.equation: set text(font: "Comic Math Relief", size: 1.2em)  // формулы +20%
  // скруглённые концы дробной черты (Typst по умолчанию рисует прямоугольник)
  show math.frac: it => context {
    let w = calc.max(measure(it.num).width, measure(it.denom).width) + 0.22em
    box(baseline: 0.34em, stack(dir: ttb, spacing: 0.16em,
      align(center, it.num),
      line(length: w, stroke: (thickness: 0.06em, cap: "round")),
      align(center, it.denom)))
  }
  body
}
