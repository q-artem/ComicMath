// Витрина шрифта Comic Math Relief.
// Сборка:  typst compile --font-path fonts font-preview.typ font-preview.png
#set page(width: 20cm, height: auto, margin: 1.4cm, fill: white)
#set text(font: ("Comic Relief", "Libertinus Serif"), size: 11pt, lang: "ru")
#set par(leading: 0.7em)
#show math.equation: set text(font: "Comic Math Relief")

#let accent = rgb("#e8543f")
#let sec(t) = block(above: 1.1em, below: 0.5em, text(fill: accent, weight: "bold", size: 12pt, t))
#let row(label, body) = grid(
  columns: (3.6cm, 1fr), column-gutter: 8pt, row-gutter: 4pt,
  text(fill: luma(90), size: 10pt, label), body,
)

// ─── шапка ────────────────────────────────────────────────────────────────
#align(center)[
  #text(size: 30pt, weight: "bold")[Comic Math Relief]
  #v(-6pt)
  #text(fill: luma(110), size: 12pt)[математический шрифт в стиле Comic Sans для Typst]
]
#line(length: 100%, stroke: 0.6pt + luma(200))

// ─── алфавиты ───────────────────────────────────────────────────────────────
#sec[Алфавиты]
#row("курсив (переменные)", $a b c d e f g h i j k l m n o p q r s t u v w x y z$)
#row("заглавные", $A B C D E F G H I J K L M N O P Q R S T U V W X Y Z$)
#row("греческий", $alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi pi rho sigma tau phi chi psi omega$)
#row("Греческий", $Gamma Delta Theta Lambda Xi Pi Sigma Phi Psi Omega$)
#row("кириллица", $а б в г д е ж з и к л м н о п р с т у ф х ц ч ш щ э ю я$)
#row("цифры", $0 1 2 3 4 5 6 7 8 9$)

// ─── начертания ──────────────────────────────────────────────────────────────
#sec[Начертания]
#row("blackboard", $NN quad ZZ quad QQ quad RR quad CC quad PP quad HH$)
#row("каллиграфия", $cal(A) cal(B) cal(C) cal(D) cal(E) cal(F) cal(G) cal(L) cal(N) cal(R)$)
#row("фрактура", $frak(A) frak(B) frak(C) frak(M) frak(R) frak(S) frak(Z)$)
#row("жирный", $bold(A) bold(b) bold(C) bold(1) bold(2) bold(alpha) bold(omega)$)
#row("моно / sans", $sans(A B C) quad mono(x y z)$)

// ─── операторы и отношения ────────────────────────────────────────────────────
#sec[Операторы и отношения]
#row("арифметика", $a + b - c times d div e plus.minus f$)
#row("отношения", $a = b quad a != b quad x <= y quad x >= y quad a approx b quad a equiv b quad a tilde b quad a prop b$)
#row("множества/логика", $x in A quad x in.not B quad A subset B quad A subset.eq B quad A union B quad A sect B quad p and q quad p or q quad not p$)
#row("стрелки", $a -> b quad a <- b quad a <-> b quad p => q quad p <== q quad p <=> q quad a |-> b quad arrow.t arrow.b$)
#row("операции", $f compose g quad a dot b quad a star b quad nabla f quad diff f quad a plus.o b quad a times.o b$)

// ─── крупные операторы ────────────────────────────────────────────────────────
#sec[Крупные операторы]
$ sum_(k=1)^n k = n(n+1)/2 quad product_(i=1)^n i = n! quad integral_a^b f(x) dif x quad integral.double_D f quad integral.triple_V g quad integral.cont_gamma f dif z $

// ─── корни и дроби ─────────────────────────────────────────────────────────────
#sec[Корни и дроби]
$ sqrt(2) quad sqrt(x^2 + y^2) quad root(3, x) quad root(n, a + b) quad a/b quad (x + 1)/(x - 1) quad 1/(1 + 1/(1 + x)) $

// ─── акценты ───────────────────────────────────────────────────────────────────
#sec[Акценты]
$ hat(x) quad tilde(a) quad overline(z) quad arrow(v) quad dot(y) quad dot.double(y) quad macron(A B) quad underline(x + y) quad overbrace(a + b + c, "сумма") $

// ─── скобки разной высоты ──────────────────────────────────────────────────────
#sec[Скобки (растягиваются)]
$ (a) [b] {c} bar.v d bar.v quad
  ( x/y ) [ x/y ] lr({ vec(a, b, c) }) lr(( mat(1, 0; 0, 1) )) quad
  cases(x &"если " x > 0, -x &"иначе") $

// ─── формулы ───────────────────────────────────────────────────────────────────
#sec[Формулы]
$ x_(1,2) = (-b plus.minus sqrt(b^2 - 4 a c))/(2 a) $
$ e^(i pi) + 1 = 0 quad quad integral_(-oo)^(oo) e^(-x^2) dif x = sqrt(pi) $
$ f(z) = 1/(2 pi i) integral.cont_gamma (f(zeta))/(zeta - z) dif zeta quad quad sum_(n=0)^oo x^n/n! = e^x $
$ nabla times bold(E) = -(diff bold(B))/(diff t) quad quad mat(a, b; c, d)^(-1) = 1/(a d - b c) mat(d, -b; -c, a) $

#v(0.6em)
#align(center, text(fill: luma(150), size: 9pt)[
  Comic Math Relief · база Fira Math · очертания Comic Relief / Courgette / UnifrakturCook · OFL 1.1
])
