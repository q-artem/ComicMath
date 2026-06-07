#set page(width: 20cm, height: auto, margin: 1.2cm, fill: white)
#set text(font: "Comic Neue", size: 11pt)

#let sample(name, mathfont) = {
  block(width: 100%, inset: 8pt, stroke: 0.5pt + gray, radius: 4pt, breakable: false)[
    #text(weight: "bold", size: 13pt)[#name]
    #v(2pt)
    #show math.equation: set text(font: mathfont)
    $ f(x) = sum_(i=1)^n (x_i^2 + alpha_i)/(sqrt(beta - gamma_i)) $
    #h(1fr)
    $ integral_0^oo e^(-x^2) dif x = sqrt(pi)/2 $
    #v(4pt)
    $ mat(a, b; c, d) quad RR -> CC quad lim_(n->oo) (1 + 1/n)^n = e $
  ]
}

#align(center)[#text(size: 20pt, weight: "bold")[ComicMath — сравнение математических шрифтов]]
#v(4pt)
#align(center)[#text(size: 10pt)[Текст-подписи набраны Comic Neue (цель стиля). Формулы — кандидаты в math-базу.]]
#v(8pt)

#text(size: 13pt, weight: "bold")[SANS-SERIF (ближе к Comic Sans)]
#v(4pt)
#sample("Fira Math", "Fira Math")
#v(6pt)
#sample("Lete Sans Math", "Lete Sans Math")
#v(6pt)
#sample("Noto Sans Math", "Noto Sans Math")

#v(10pt)
#text(size: 13pt, weight: "bold")[SERIF (для контраста)]
#v(4pt)
#sample("New Computer Modern Math (дефолт Typst)", "New Computer Modern Math")
#v(6pt)
#sample("DejaVu Math TeX Gyre", "DejaVu Math TeX Gyre")
