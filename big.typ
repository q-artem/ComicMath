#set page(width: 22cm, height: auto, margin: 1cm, fill: white)
#set text(font: "Comic Neue", size: 13pt, weight: "bold")
#set par(leading: 18pt)
#let row(t, mf) = { text(t); v(2pt); show math.equation: set text(font: mf, size: 46pt); $ a g e x  alpha beta theta pi  =  3 8 $ ; v(10pt) }
#row("Чистый", "Comic Math")
#row("Wobble ×1 (умеренно)", "Comic Math Wobble")
#row("Wobble ×2 (сильно)", "Comic Math Wobble2")
