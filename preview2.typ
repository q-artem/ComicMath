#set page(width: 18cm, height: auto, margin: 1.2cm, fill: white)
#set text(font: "Comic Neue", size: 11pt)

#let demo(name, mathfont) = block(width: 100%, inset: 9pt, stroke: 0.5pt + gray, radius: 4pt)[
  #text(weight: "bold", size: 13pt)[#name]
  #v(3pt)
  #show math.equation: set text(font: mathfont)
  $ f(x) = sum_(i=1)^n (x_i^2 + alpha_i)/(sqrt(beta - gamma_i)) $
  #v(2pt)
  $ integral_0^oo e^(-x^2) dif x = sqrt(pi)/2 quad mat(a, b; c, d) quad RR -> CC $
  #v(2pt)
  $ E = m c^2 quad a^2 + b^2 = c^2 quad lim_(n->oo) (1 + 1/n)^n = e $
]

#align(center)[#text(size: 20pt, weight: "bold")[ComicMath — прототип B (Comic Neue × Fira Math)]]
#v(8pt)
#demo("Fira Math (база)", "Fira Math")
#v(8pt)
#demo("Comic Math (буквы Comic Neue)", "Comic Math")
