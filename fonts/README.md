# Figure font

`Merriweather.ttf` is the variable Merriweather source font used to produce
the archived figures. Its name table identifies version 2.100 and:

Copyright 2024 The Merriweather Project Authors
(https://github.com/EbenSorkin/Merriweather4), with Reserved Font Name
"Merriweather".

The accompanying upstream licence is SIL Open Font License 1.1. Its text was
checked at https://raw.githubusercontent.com/google/fonts/main/ofl/merriweather/OFL.txt.
That upstream licence notice uses copyright year 2020; the font binary's
2024 copyright notice is preserved here and in the unmodified font file.

`make_figures.py` creates temporary regular and bold instances at weight
400/700, width 100 and optical size 18. Those local instances are named
"ShadeParadox Text" and are not shipped; renaming does not change the glyph
outlines used in the figures. No system font installation is required.

The font licence applies to the font; it does not assign a licence to the
author's scientific source code or data.
