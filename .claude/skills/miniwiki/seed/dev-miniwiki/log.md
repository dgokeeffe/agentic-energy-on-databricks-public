# Log

Append-only timeline, newest at the bottom. A GFM table — one row per
capture, pipe-delimited so it stays greppable (`tail`, `awk -F'|'`). The
`---` separator row is what makes GitHub render it as a table; new `save`
rows append below it.

utc | mode | topic | kind | branch @ host | summary | path
--- | --- | --- | --- | --- | --- | ---
