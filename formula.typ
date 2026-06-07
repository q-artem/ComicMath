#set page(width: 26cm, height: auto, margin: 1.4cm, fill: white)
#set text(font: "Comic Neue", size: 13pt)
#show math.equation: set text(font: "Comic Math Relief")

Наконец, пусть $x in op("Im") cal(N)^m inter op("Im") q(cal(N))$.

#v(10pt)
#set math.equation(numbering: none)
$
underbrace(
  underbrace(u(cal(N)) cal(N)^m x, cal(N)^m x = 0 arrow.l.double cases(in op("Im") cal(N)^m, op("Im") q(cal(N)) subset.eq op("ker") cal(N)^m))
  + underbrace(v(cal(N)) q(cal(N)) x, q(cal(N)) x = 0 arrow.l.double cases(in op("Im") q(cal(N)), in op("Im") cal(N)^m subset.eq q(cal(N)))),
  0 + 0
) = x ==> op("Im") cal(N)^m inter op("Im") q(cal(N)) = {0}, wide (66)
$
