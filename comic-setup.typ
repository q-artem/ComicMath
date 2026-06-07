// Подключение ComicMath в любой Typst-документ:
//   #import "comic-setup.typ": comic
//   #show: comic
// собирать с:  typst compile --font-path <папка-со-шрифтами> doc.typ
#let comic(body) = {
  set text(font: ("Comic Relief", "DejaVu Sans"))      // текст: лат+кириллица, комикс
  show math.equation: set text(font: "Comic Math Relief", size: 1.2em)  // формулы +20%
  body
}
