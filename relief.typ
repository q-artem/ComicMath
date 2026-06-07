#set page(width: 21cm, height: auto, margin: 1cm, fill: white)
#set text(font: "Comic Neue", size: 12pt)
#set par(leading: 12pt)
#let demo(title, mf) = block(width: 100%, inset: 9pt, stroke: 0.5pt + gray, radius: 4pt)[
  #text(font: "Comic Neue", weight: "bold", size: 13pt)[#title]
  #v(3pt)
  #show math.equation: set text(font: mf, size: 24pt)
  $ a b c d e f g x y z  alpha beta gamma pi omega  0123456789 $
  #v(2pt)
  #show math.equation: set text(font: mf)
  $ f(x) = sum_(i=1)^n (x_i^2 + alpha_i)/(sqrt(beta - gamma_i)) quad integral_0^oo e^(-x^2) dif x = sqrt(pi)/2 $
]
#align(center)[#text(size: 18pt, weight: "bold")[Донор латиницы: Comic Neue vs Comic Relief]]
#v(8pt)
#demo("Comic Neue (текущий, гладкий/причёсанный)", "Comic Math")
#v(8pt)
#demo("Comic Relief (прямой клон Comic Sans)", "Comic Math Relief")
