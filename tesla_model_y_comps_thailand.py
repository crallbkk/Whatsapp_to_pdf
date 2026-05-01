from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "Model Y 2023 LR Comps TH"

headers = [
    "Source / URL",
    "Model Year",
    "Trim (Long Range?)",
    "Enhanced Autopilot (EAP)",
    "FSD",
    "Mileage (km)",
    "Price (THB)",
    "Notes",
]

rows = [
    # Sorted by price, high to low. Unknown prices at the bottom.
    [
        "https://www.one2car.com/en/used-cars-for-sale/tesla/model-y/year-2023/thailand_bangkok-metropolitan_bangkok",
        2023, "Long Range AWD", "Unknown", "Unknown", 28000, 1499000,
        "One2car snippet: '2023 Model Y Long Range, ~28,000 km, ~1,499,000 THB'. Closest mileage comp to your car.",
    ],
    [
        "https://www.one2car.com/en/used-cars-for-sale/tesla/model-y/year-2023/thailand_bangkok-metropolitan_bangkok",
        2023, "Long Range AWD", "Unknown", "Unknown", 28000, 1469000,
        "One2car snippet: same/similar 28k km LR car at 1,469,000 THB. Confirm if duplicate of row above.",
    ],
    [
        "https://www.one2car.com/en/used-cars-for-sale/tesla/model-y/year-2023",
        2023, "Long Range AWD", "Unknown", "Unknown", 30000, 1350000,
        "One2car snippet: 2023 LR 30,000 km @ 1,350,000 THB.",
    ],
    [
        "https://www.one2car.com/en/used-cars-for-sale/tesla/model-y/year-2023",
        2023, "Long Range AWD", "Unknown", "Unknown", 30000, 1290000,
        "One2car snippet: 2023 LR 30-35k km @ 1,290,000 THB.",
    ],
    [
        "https://www.one2car.com/en/cars-for-sale/tesla/model-y/all/long-range-4wd?page_size=26",
        2023, "Long Range '507 AT'", "Unknown", "Unknown", None, 1260000,
        "One2car snippet: 2023 LR 507 AT, 0-baht down. Mileage not surfaced in snippet.",
    ],
    [
        "https://www.one2car.com/en/cars-for-sale/tesla/model-y/all/long-range-4wd?page_size=26",
        2023, "Long Range AWD", "Yes", "Unknown", 64000, 1188000,
        "Single owner, '+EAP +Profender'. Mileage well above your 25k target.",
    ],
    [
        "https://www.taladrod.com/w40/icar/cardet.aspx?cid=2872040",
        2023, "Long Range", "Unknown", "Unknown", 30000, None,
        "TaladROD listing - direct URL. Price not in snippet; open page to confirm.",
    ],
    [
        "https://www.taladrod.com/w40/icar/cardet.aspx?cid=2877904",
        2023, "Long Range", "Unknown", "Unknown", None, None,
        "TaladROD listing - direct URL. Mileage and price need page visit.",
    ],
    [
        "https://chobrod.com/car-tesla-model-y-long-range-awd-bangkok/2023-%E0%B8%A3%E0%B8%96%E0%B8%A2%E0%B8%99%E0%B8%95%E0%B9%8C%E0%B9%84%E0%B8%9F%E0%B8%9F%E0%B9%89%E0%B8%B2%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B8%AB%E0%B8%A2%E0%B8%B1%E0%B8%94%E0%B8%9E%E0%B8%A5%E0%B8%B1%E0%B8%87%E0%B8%87%E0%B8%B2%E0%B8%99-aid25371772",
        2023, "Long Range AWD", "Unknown", "Unknown", None, None,
        "Chobrod individual listing, Bangkok. Open page for details.",
    ],
    [
        "https://chobrod.com/car-tesla-model-y-long-range-awd-bangkok/%E0%B8%82%E0%B8%B2%E0%B8%A2%E0%B8%A3%E0%B8%96%E0%B8%AA%E0%B8%A7%E0%B8%A2-long-range-dual-motor-all-wheel-drive-aid22865762",
        2023, "Long Range AWD (Dual Motor)", "Unknown", "Unknown", None, None,
        "Chobrod individual listing, Bangkok.",
    ],
    [
        "https://www.one2car.com/en/used-cars-for-sale/tesla/model-y/year-2023",
        2023, "Long Range AWD", "Unknown", "Unknown", 39000, None,
        "Listed by Tesla Thailand certified-used channel - usually a price premium.",
    ],
    [
        "https://chobrod.com/car-tesla-model-y-long-range-awd-bangkok",
        2023, "Long Range AWD (multiple)", "Varies", "Varies", None, None,
        "Chobrod aggregator page with multiple 2023 LR cars.",
    ],
    [
        "https://rod.kaidee.com/c11a779-auto-car-tesla",
        2023, "Various (filter for LR)", "Varies", "Varies", None, None,
        "Kaidee owner-direct platform - filter for LR 2023.",
    ],
    [
        "https://tesla-info.com/for-sale/Thailand/MY/",
        2023, "Various", "Varies", "Varies", None, None,
        "VIN-level aggregator for cross-checking original options (EAP/FSD/HW3).",
    ],
    [
        "https://www.facebook.com/marketplace/bangkok/tesla/",
        2023, "Various", "Varies", "Varies", None, None,
        "Private owners often spell out EAP/FSD here.",
    ],
]

ws.append(headers)

for r in rows:
    ws.append(r)

# Styling
header_font = Font(bold=True, color="FFFFFF")
header_fill = PatternFill("solid", fgColor="1F4E78")
for col_idx, _ in enumerate(headers, start=1):
    cell = ws.cell(row=1, column=col_idx)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    for cell in row:
        cell.alignment = Alignment(vertical="top", wrap_text=True)

price_col = headers.index("Price (THB)") + 1
for r in range(2, ws.max_row + 1):
    cell = ws.cell(row=r, column=price_col)
    if isinstance(cell.value, (int, float)):
        cell.number_format = '#,##0'

mileage_col = headers.index("Mileage (km)") + 1
for r in range(2, ws.max_row + 1):
    cell = ws.cell(row=r, column=mileage_col)
    if isinstance(cell.value, (int, float)):
        cell.number_format = '#,##0'

widths = [55, 11, 24, 18, 10, 14, 14, 60]
for i, w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w

ws.row_dimensions[1].height = 32
ws.freeze_panes = "A2"

# Reference / pricing notes sheet
ws2 = wb.create_sheet("Reference & Pricing Notes")
notes = [
    ["Reference data point", "Value (THB)", "Source"],
    ["New 2023 Model Y Long Range AWD launch price (Tesla Thailand)", 2259000, "https://autolifethailand.tv/official-price-tesla-model-y-thailand/"],
    ["2023 Model Y LR price after Dec 2023 cut", 2019000, "https://autolifethailand.tv/tesla-modely-up-price-official-12dec2023/"],
    ["Enhanced Autopilot (EAP) option (when ordered new)", 122000, "Tesla Thailand configurator"],
    ["", "", ""],
    ["Comp band (2023 LR, 25-40k km)", "1,290,000 - 1,500,000", "Synthesised from One2car snippets"],
    ["EAP-equipped twin should price at small premium (~30-60k) over non-EAP", "", "EAP retail = 122k, depreciates"],
    ["Tesla Thailand certified-used cars typically command a premium vs gray-market", "", ""],
    ["", "", ""],
    ["Caveat", "", ""],
    ["Many 2023 Model Ys in TH are gray-market imports - not eligible for Tesla Thailand service / 8-yr battery warranty.", "", ""],
    ["Always verify VIN against Tesla Thailand records when comparing.", "", ""],
    ["", "", ""],
    ["Data limitation", "", ""],
    ["Direct fetches to one2car / chobrod / taladrod / kaidee returned 403; rows above are pieced together from search snippets. Confirm each row by opening the URL.", "", ""],
]
for row in notes:
    ws2.append(row)

for col_idx, _ in enumerate(notes[0], start=1):
    cell = ws2.cell(row=1, column=col_idx)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal="center", vertical="center")

for r in range(2, ws2.max_row + 1):
    cell = ws2.cell(row=r, column=2)
    if isinstance(cell.value, (int, float)):
        cell.number_format = '#,##0'

for i, w in enumerate([60, 22, 70], start=1):
    ws2.column_dimensions[get_column_letter(i)].width = w

for row in ws2.iter_rows(min_row=2, max_row=ws2.max_row):
    for cell in row:
        cell.alignment = Alignment(vertical="top", wrap_text=True)

out = "/home/user/Whatsapp_to_pdf/tesla_model_y_2023_LR_comps_thailand.xlsx"
wb.save(out)
print(f"Wrote {out}")
