# Keep the existing imports, credentials, browser setup,
# Google Sheets connection, and choose_dropdown() function.

REPORTS = [
    ("ALL", "Ongoing"),
    ("2026-2027", "Approve"),
    ("2025-2026", "Approve"),
    ("2024-2025", "Approve"),
    ("2026-2027", "Completed"),
    ("2025-2026", "Completed"),
    ("2024-2025", "Completed"),
]

all_rows = []
failed_reports = []

for fin_year, work_status in REPORTS:
    print(f"Running report: year={fin_year}, status={work_status}")

    try:
        # Set the filters for each report.
        choose_dropdown(page, "District", "DANTEWADA")
        choose_dropdown(page, "Block", "ALL")
        choose_dropdown(page, "Work Start Fin Yr", fin_year)
        choose_dropdown(page, "Work Status", work_status)

        # Find and click the report submission button.
        submit = page.get_by_role(
            "button",
            name=re.compile(r"view|submit|show|search", re.I)
        )

        if submit.count() == 0:
            submit = page.locator(
                'input[type="submit"], input[type="button"]'
            )

        if submit.count() == 0:
            raise RuntimeError("Report submission button not found")

        submit.first.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)

        # Extract non-empty tables from the result page.
        tables = page.locator("table")
        candidates = []

        for i in range(tables.count()):
            table = tables.nth(i)
            rows = table.locator("tr")
            extracted = []

            for r in range(rows.count()):
                cells = rows.nth(r).locator("th, td")
                row = [
                    cells.nth(c).inner_text().strip()
                    for c in range(cells.count())
                ]
                if row and any(row):
                    extracted.append(row)

            if len(extracted) >= 2:
                candidates.append(extracted)

        if not candidates:
            raise RuntimeError("No report table found")

        # IMPORTANT: verify this selects the actual report table,
        # not a navigation or layout table, before production use.
        report = max(candidates, key=len)

        # Do not treat an empty result as a successful report.
        if not any(
            cell.strip()
            for row in report[1:]
            for cell in row
        ):
            raise RuntimeError("Report contains no data rows")

        # Add filter information to every row for identification.
        all_rows.append([
            f"Financial Year: {fin_year}",
            f"Work Status: {work_status}",
        ])
        all_rows.extend(report)
        all_rows.append([])

        print(f"Successfully extracted {fin_year} / {work_status}")

    except Exception as exc:
        failed_reports.append(
            f"{fin_year} / {work_status}: {exc}"
        )
        print(f"FAILED: {fin_year} / {work_status}: {exc}")

# Never replace the sheet with incomplete data.
if failed_reports:
    raise RuntimeError(
        "Some reports failed. Existing Google Sheet was not changed:\n"
        + "\n".join(failed_reports)
    )

if not all_rows:
    raise RuntimeError("No report data collected; sheet not changed")

# Replace the worksheet only after all seven reports succeed.
timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
all_rows.insert(0, ["Last refreshed", timestamp])

worksheet.clear()
worksheet.update(
    range_name="A1",
    values=all_rows,
    value_input_option="USER_ENTERED",
)

print(f"Updated Google Sheet with all {len(REPORTS)} reports.")
