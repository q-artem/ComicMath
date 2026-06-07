#set page(width: 22cm, height: auto, margin: 1.2cm, fill: white)
#set text(font: "Comic Neue", size: 12pt)
#show math.equation: set text(font: "Comic Math Relief")
#align(center)[#text(size:20pt, weight:"bold")[ComicMath — полное покрытие]]
#v(8pt)
#set text(size: 14pt)
#let lbl(s) = text(font:"Comic Neue", size:10pt, fill: gray)[#s]
#lbl("стили алфавита") \
$ A bold(A) italic(A) bold(italic(A)) sans(A) cal(A) cal(a) frak(A) frak(a) bb(A) bb(R) bb(N) $
#v(5pt) #lbl("bold + греческий + цифры") \
$ bold(F) = m bold(a) quad bold(alpha) + bold(Omega) quad bold(2) pi quad nabla bold(v) $
#v(5pt) #lbl("акценты, скобы") \
$ hat(x) tilde(a) arrow(v) dot(y) macron(z) quad underbrace(a+b+c, n) quad overbrace(x_1 + dots + x_n) $
#v(5pt) #lbl("числа, операторы, корни") \
$ NN subset ZZ subset QQ subset RR subset CC quad sum_(k=1)^oo 1/k^2 = pi^2/6 quad integral.cont_C bold(F) dif bold(r) quad sqrt((a+b)/c) $
#v(5pt) #lbl("логика, множества, стрелки") \
$ forall x exists y: p and q ==> r quad A union B subset.eq C quad f: cal(X) -> cal(Y) quad a arrow.tr b quad x equiv y $
