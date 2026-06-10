#!/usr/bin/env bash
# Собирает папку release/ и zip-архив
# Использование:  ./make-release.sh [версия]
set -euo pipefail
cd "$(dirname "$0")"

VER="${1:-1.0.0}"
OUT="release"
ZIP="ComicMath-${VER}.zip"

copy() {  # copy <src> <dst-name>
  if [[ ! -f "$1" ]]; then
    echo "  ОШИБКА: нет файла $1" >&2
    echo "  (собери шрифт: .venv/bin/python build.py 0 relief; превью: typst compile --font-path fonts font-preview.typ font-preview.pdf)" >&2
    exit 1
  fi
  cp "$1" "$OUT/$2"
  echo "  + $2"
}

rm -rf "$OUT" "$ZIP"
mkdir -p "$OUT"
echo "Собираю release/ (версия $VER):"

copy fonts/ComicMathRelief.otf        ComicMathRelief.otf          # формулы
copy fonts/donor-ComicRelief.ttf      ComicRelief-Regular.ttf      # обычный текст
copy fonts/ComicRelief-Bold-fixed.ttf ComicRelief-Bold.ttf         # жирный текст (с починенной ю)
copy OFL.txt                          OFL.txt                      # лицензия
copy font-preview.pdf                 font-preview.pdf             # превью

# короткая инструкция для пользователя
cat > "$OUT/README.txt" <<EOF
Comic Math ${VER} — комиксовый математический шрифт для Typst.

Установка (рядом с документом):
  ComicMathRelief.otf       — формулы (семейство "Comic Math Relief")
  ComicRelief-Regular.ttf   — обычный текст (семейство "Comic Relief")
  ComicRelief-Bold.ttf      — жирный текст

  typst compile --font-path . doc.typ

В документе:
  #show math.equation: set text(font: "Comic Math Relief")
  #set text(font: ("Comic Relief", "DejaVu Sans"))

В онлайн-редакторе typst.app просто загрузить .otf/.ttf в проект, папка fonts/.

Лицензия: SIL Open Font License 1.1 — см. OFL.txt.
Доноры: Fira Math, Comic Relief, Courgette, UnifrakturCook.
EOF
echo "  + README.txt"

PY="$(command -v python3 || echo .venv/bin/python)"
"$PY" - "$ZIP" "$OUT" <<'PYEOF'
import sys, os, zipfile
zipname, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(zipname, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(out)):
        z.write(os.path.join(out, f), f)      # без префикса release/
PYEOF
echo "Готово: $OUT/  и  $ZIP ($(du -h "$ZIP" | cut -f1))"
