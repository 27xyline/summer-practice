#let arguments(..args, year: auto) = {
  let values = args.named()
  values.insert("year", year)
  values
}

#let template(
  ministry: none,
  organization: (full: none, short: none),
  faculty: none,
  department: none,
  report-type: "Отчёт",
  about: none,
  subject: none,
  manager: (position: none, name: none),
  performer: (position: none, name: none),
  city: "Москва",
  year: auto,
  ..rest,
) = {
  align(center)[
    #ministry
    #linebreak()
    #organization.full
    #linebreak()
    #organization.short

    #v(20mm)

    Институт № 3 — «#faculty»
    #v(5mm)
    Кафедра 307 — «#department»
  ]

  v(1fr)

  align(center)[
    #text(size: 17pt, weight: "bold")[#upper(report-type)]
    #v(4mm)
    #upper(about)
    #v(12mm)
    по теме:
    #v(5mm)
    #text(size: 16pt)[#upper(subject)]
  ]

  v(1fr)

  table(
    columns: (1.35fr, 1.6fr, 1.35fr),
    rows: (auto, 8mm, auto, 8mm),
    inset: (x: 4pt, y: 3pt),
    stroke: none,
    align(left + horizon)[
      Выполнил: #performer.position
    ],
    [],
    align(left + horizon)[#performer.name],
    [],
    align(center + horizon)[
      #line(length: 100%, stroke: 0.5pt)
      #text(size: 8pt)[подпись, дата]
    ],
    [],
    align(left + horizon)[
      Принял: #manager.position
    ],
    [],
    align(left + horizon)[#manager.name],
    [],
    align(center + horizon)[
      #line(length: 100%, stroke: 0.5pt)
      #text(size: 8pt)[подпись, дата]
    ],
    [],
  )

  v(1fr)
}
