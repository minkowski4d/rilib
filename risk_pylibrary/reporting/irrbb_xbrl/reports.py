
import os
import sys
import ast
import json
import zipfile

from lxml import etree
import pandas as pd
from typing import List, Tuple, Dict
import datetime

# Add this file's directory to sys.path so 'utils' package is resolvable
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from utils.snowflake import run_query
from utils.irrbb import base_context, context, fIndicators, metric, schema_ref, unit, get_decimal, get_unit_ref, get_mapping
from utils.general import compress_file, save_in_s3, combine_report_flags
from utils.irrbb_cell_mapping import DIMENSION_MAPPING


C_NO = "5299009IFX1XTKDY4568.IND"
PERIOD = "2026-03-31"
USERNAME = 'fabio.balloni@traderepublic.com'

NS = "http://www.xbrl.org/2003/instance" # namespace declaration

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REPORTS = [
    "J_01.00",
    "J_02.00",
    "J_03.00",
    "J_04.00",
    "J_05.00",
    "J_06.00",
    "J_07.00",
    "J_08.00",
    "J_09.00",
    "J_10.01",
    "J_10.02",
    "J_11.01",
    "J_11.02",
]

DEFAULT_REPORTS_TO_RUN = [
    # Quarterly reports
    'J_01.00',
    'J_01.00_EUR',  # EUR version as sep sheet. ToDo: Added real loop for all currencies
    'J_03.00',
    #'J_03.00_EUR',
    'J_06.00.a',
    'J_09.00.a',
    'J_09.00.b',

    # Annual reports
    'J_11.01',
    'J_11.02',
]

# Framework 4.2 xBRL-CSV entry point (valid from 2026-03-31).
# Derived from Bundesbank entry points Excel ("4.2/mod/irrbb.json") and the DORA 4.0
# URL pattern. Verify inside the EBA Framework 4.2 taxonomy package before submitting.
SCHEMA_JSON_URL_42 = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/irrbb/4.2/mod/irrbb.json"

# Canonical dimension type ordering for xBRL-CSV column layout
_IRRBB_DIM_ORDER = [
    "BAS", "MCY", "TIU", "CPS", "PFS", "LIQ", "PUR", "CAL", "APS",
    "APL", "CIC", "RCO", "TRI", "PRP", "OFS", "PIN", "CSC", "RES", "RPE", "SCI",
]

# EBA domain-code → namespace prefix mapping (mirrors the nsmap in build_xml)
_DOMAIN_NS_PREFIX = {
    "BA": "eba_BA", "MC": "eba_MC", "CS": "eba_CS", "CT": "eba_CT",
    "TI": "eba_TI", "PL": "eba_PL", "TR": "eba_TR", "AP": "eba_AP",
    "PI": "eba_PI", "IM": "eba_IM", "OF": "eba_OF", "RF": "eba_RF",
    "LQ": "eba_LQ", "PU": "eba_PU", "CU": "eba_CU", "ZZ": "eba_ZZ",
}


def _xbrl_csv_table_name(report_nms: str) -> str:
    """Map a variant report name to the canonical xBRL-CSV template filename.

    Examples:
        J_01.00_EUR  → j_01.00.csv
        J_06.00.a    → j_06.00.csv
        J_09.00.b    → j_09.00.csv
        J_11.01      → j_11.01.csv
    """
    name = report_nms.replace("_EUR", "")
    parts = name.split(".")
    if len(parts) == 3 and parts[2].lower() in ("a", "b", "c"):
        name = ".".join(parts[:2])
    return name.lower() + ".csv"


def _to_eba_qname(dim_value: str) -> str:
    """Convert a bare domain value like 'BA:x6' to the EBA QName 'eba_BA:x6'."""
    if not dim_value:
        return ""
    parts = dim_value.split(":")
    if len(parts) == 2:
        prefix = _DOMAIN_NS_PREFIX.get(parts[0], f"eba_{parts[0]}")
        return f"{prefix}:{parts[1]}"
    return dim_value


def _csv_escape(value: str) -> str:
    """RFC 4180 CSV quoting: wrap in double-quotes if the value contains special chars."""
    if "," in value or '"' in value or "\n" in value or "\r" in value:
        return '"' + value.replace('"', '""') + '"'
    return value


def load_raw_data(report: str, report_nms: str, period: str = PERIOD, username: str = USERNAME) -> pd.DataFrame:

    # Modified report name to match Compliance and Risk team's table name
    modified_report_name = (report[:1] + report[2:]).replace(".", "_").upper()

    # query the data
    query = f"""
        SELECT * FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_{modified_report_name}
        WHERE REPORT_DATE = '{period}'
    """

    raw_data = run_query(
        query,
        username=username
    )

    # Apply the function to create a new column with the mapping values
    raw_data['mapped_values'] = raw_data.apply(get_mapping, axis=1, report=report)

    # Drop rows where 'value' is null
    raw_data = raw_data.dropna(subset=['value'])

    # Save CSV to output/{period_dir}/csv/
    period_dir = period.replace("-", "")
    csv_dir = os.path.join(BASE_DIR, "output", period_dir, "csv")
    os.makedirs(csv_dir, exist_ok=True)
    csv_name = report_nms if report != report_nms else report
    csv_path = os.path.join(csv_dir, f"{period.replace('-', '_')}_{csv_name.replace('.', '_')}.csv")
    raw_data.to_csv(csv_path, index=False)

    return raw_data


def build_data_filings(raw_data: pd.DataFrame, report: str, report_nms: str) -> list:
    data_filings = []

    # Iterate over the rows of the DataFrame using itertuples()
    for row in raw_data.itertuples(index=False):
        # Extract the dimensions list
        dimension_list = ast.literal_eval(str(row[6]))

        # Remove NaN values from the dimension_list
        dimension_list = [DIMENSION_MAPPING.get(value) for value in dimension_list if (pd.notna(value) and value != "")]

        # Check which report it is, then adjust the currency
        if report in ["J_01.00"]:
            if report_nms == "J_01.00_EUR":
                # If the report is J_01.00_EUR, we need to add the EUR currency
                dimension_list.append(("SCI", "CU:EUR"))
            else:
                # Add the currency "All currencies"
                dimension_list.append(("SCI", "CU:x1"))

        elif report not in ["J_11.01"]:
            # Add the currency to all the dimensions
            dimension_list.append(("SCI", "CU:EUR"))

        # Get unit based on the metric type (mi, ri, pi, etc)
        unit_ref = get_unit_ref(dimension_list)

        # RTS on SOT Art. 4(1) + Art. 3(8): NII gains (IDX=130, value > 0) are capped at 50%
        # when aggregating into the X1 (all currencies) sheet. Losses are unaffected.
        amount = row[5]
        if report == "J_01.00" and report_nms != "J_01.00_EUR" and row[1] == 130 and amount > 0:
            amount = amount * 0.5

        data_filings.append(
            [
                dimension_list[1:],     # the list of dimensions
                dimension_list[0],      # the metric
                unit_ref,               # the type of the amount
                amount,                 # the amount
                get_decimal(unit_ref)   # the decimal part
            ]
        )

    return data_filings


def build_metadata(report: str) -> Tuple[List[List[str]], List[List[str]]]:

    # Dynamically create the list showing true for ONLY the report going to be saved in this xml
    #     ["J_01.00", "true"],
    #     ["J_02.00", "false"],
    #     ["J_03.00", "false"],
    #     ...
    data_reports = [[r, "true" if r[:4] == report[:4] else "false"] for r in REPORTS]

    data_units = [
        ["uPURE", "xbrli:pure"],
        ["uEUR", "iso4217:EUR"],
    ]

    return data_reports, data_units


def build_xml(data_filings: list, data_reports: List, data_units: List, period: str = PERIOD) -> str:

    xbrl = etree.Element(
        etree.QName(NS, "xbrl"),
        nsmap={
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xbrli": "http://www.xbrl.org/2003/instance",
            "xbrldi": "http://xbrl.org/2006/xbrldi",
            "eba_model": "http://www.eba.europa.eu/xbrl/ext/model",
            "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
            "find": "http://www.eurofiling.info/xbrl/ext/filing-indicators",
            "xlink": "http://www.w3.org/1999/xlink",
            "link": "http://www.xbrl.org/2003/linkbase",
            # For the data filings
            "eba_BA": "http://www.eba.europa.eu/xbrl/crr/dict/dom/BA",
            "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
            "eba_TR": "http://www.eba.europa.eu/xbrl/crr/dict/dom/TR",
            "eba_PL": "http://www.eba.europa.eu/xbrl/crr/dict/dom/PL",
            "eba_AP": "http://www.eba.europa.eu/xbrl/crr/dict/dom/AP",
            "eba_ZZ": "http://www.eba.europa.eu/xbrl/crr/dict/dom/ZZ",
            "eba_IM": "http://www.eba.europa.eu/xbrl/crr/dict/dom/IM",
            "eba_MC": "http://www.eba.europa.eu/xbrl/crr/dict/dom/MC",
            "eba_CS": "http://www.eba.europa.eu/xbrl/crr/dict/dom/CS",
            "eba_CU": "http://www.eba.europa.eu/xbrl/crr/dict/dom/CU",
            "eba_CT": "http://www.eba.europa.eu/xbrl/crr/dict/dom/CT",
            "eba_PU": "http://www.eba.europa.eu/xbrl/crr/dict/dom/PU",
            "eba_LQ": "http://www.eba.europa.eu/xbrl/crr/dict/dom/LQ",
            "eba_RF": "http://www.eba.europa.eu/xbrl/crr/dict/dom/RF",
            "eba_TI": "http://www.eba.europa.eu/xbrl/crr/dict/dom/TI",
            "eba_OF": "http://www.eba.europa.eu/xbrl/crr/dict/dom/OF",
            "eba_PI": "http://www.eba.europa.eu/xbrl/crr/dict/dom/PI",
            "iso4217": "http://www.xbrl.org/2003/iso4217",
        },
    )

    # Depending on the period, the schema reference will be different
    if period >= "2024-09-30":
        schema_ref_value = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/irrbb/its-2023-03/2024-02-29/mod/irrbb.xsd"
    else:
        schema_ref_value = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/irrbb/its-2023-03/2023-10-15/mod/irrbb.xsd"

    # Schema Reference
    xbrl.append(schema_ref(schema_ref_value))

    # Units
    for report_unit in data_units:
        xbrl.append(unit(report_unit[0], report_unit[1]))

    # Base Context
    xbrl.append(base_context("c1", C_NO, period))

    # Filing Indicators
    xbrl.append(fIndicators("c1", data_reports))

    # Contexts and Measures
    c_next = 2
    for filing in data_filings:
        cid = "c" + str(c_next)
        xbrl.append(context(cid, C_NO, period, filing[0]))
        xbrl.append(metric(filing[1], cid, str(filing[4]), filing[2], filing[3]))
        c_next += 1

    # Convert to string and save to file
    xml = etree.tostring(
        xbrl, pretty_print=True, encoding="utf-8", xml_declaration=True
    ).decode("utf-8")

    return xml


def save_the_report(xml: str, report: str, report_nms: str, period: str = PERIOD, to_s3: bool = False, compress: bool = False) -> None:

    filename    = f"{period.replace('-', '_')}_{(report_nms if report != report_nms else report).replace('.', '_')}"
    period_dir  = period.replace("-", "")

    xbrl_dir = os.path.join(BASE_DIR, "output", period_dir, "xbrl")
    os.makedirs(xbrl_dir, exist_ok=True)

    output_xbrl = os.path.join(xbrl_dir, f"{filename}.xbrl")

    with open(output_xbrl, "w") as f:
        f.write(xml)

    if compress:
        output_zip = os.path.join(BASE_DIR, "output", period_dir, f"{filename}.xbrl.zip")
        compress_file(output_xbrl, output_zip)

    if to_s3:
        save_in_s3(output_xbrl, f"reports/{filename}.xbrl", file_type='xml')
        if compress:
            save_in_s3(output_zip, f"reports/{filename}.xbrl.zip", file_type='zip')


def save_stacked_reports(
    all_data_filings: list,
    all_data_reports: list,
    reports_to_run: list,
    data_units: list,
    period: str = PERIOD,
) -> None:

    period_dir = period.replace("-", "")
    csv_dir = os.path.join(BASE_DIR, "output", period_dir, "csv")

    # Read all individual CSVs and stack them
    stacked_raw_data = pd.concat(
        (
            pd.read_csv(
                os.path.join(csv_dir, f"{period.replace('-', '_')}_{r.replace('.', '_')}.csv"),
                dtype=str,
            )
            for r in reports_to_run
        ),
        ignore_index=True,
    )
    stacked_raw_data.to_csv(os.path.join(csv_dir, f"{period.replace('-', '_')}_STACKED_REPORTS.csv"), index=False)

    # Building the XML file
    xml = build_xml(
        all_data_filings,
        combine_report_flags(all_data_reports),
        data_units,
        period=period,
    )

    save_the_report(xml, "STACKED_REPORTS", "STACKED_REPORTS", period=period, compress=True)


def build_xbrl_csv_package(
    data_filings_by_report: Dict[str, list],
    data_reports: List[List[str]],
    period: str = PERIOD,
    output_dir: str = None,
    entity_id: str = C_NO,
    to_s3: bool = False,
) -> str:
    """Build an EBA xBRL-CSV report package ZIP for IRRBB Framework 4.2.

    Generates the XBRL Report Package 1.0 structure required by Bundesbank
    PRISMA for periods >= 2026-03-31:

        {root}/META-INF/reportPackage.json
        {root}/reports/report.json
        {root}/reports/parameters.csv
        {root}/reports/FilingIndicators.csv
        {root}/reports/{template}.csv   (one per reported table)

    The entry point URL in SCHEMA_JSON_URL_42 must be verified against the
    official EBA Framework 4.2 taxonomy package before submitting to PRISMA.

    Args:
        data_filings_by_report: {report_nms: [[dims, metric, unit_ref, amount, decimal], ...]}
        data_reports: combined [report_code, "true"/"false"] list (from combine_report_flags)
        period: reference date "YYYY-MM-DD"
        output_dir: directory for the output ZIP (defaults to output/{period_dir}/xbrl_csv/)
        entity_id: LEI + suffix, e.g. "5299009IFX1XTKDY4568.IND"
        to_s3: whether to upload the ZIP to S3

    Returns:
        Absolute path to the generated ZIP file.
    """
    period_dir = period.replace("-", "")
    if output_dir is None:
        output_dir = os.path.join(BASE_DIR, "output", period_dir, "xbrl_csv")

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S000")
    root_folder = f"{entity_id}_DE_IRRBB040000_IRRBB_{period}_{timestamp}"
    zip_path = os.path.join(output_dir, f"{root_folder}.zip")

    os.makedirs(output_dir, exist_ok=True)

    # Merge variants (J_01.00_EUR, J_09.00.a/b, etc.) into per-template CSV tables first,
    # so we can derive filing indicators from actual data presence.
    tables: Dict[str, list] = {}
    for report_nms, filings in data_filings_by_report.items():
        table_file = _xbrl_csv_table_name(report_nms)
        tables.setdefault(table_file, []).extend(filings)

    # A template is "reported=true" only when its table CSV has at least one data row.
    # This avoids a mismatch between FilingIndicators and missing/empty CSVs.
    tables_with_data = {tf for tf, filings in tables.items() if filings}
    fi_map = {r: ("true" if r.lower() + ".csv" in tables_with_data else "false") for r in REPORTS}

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:

        # META-INF/reportPackage.json — fixed per XBRL Report Package 1.0 spec
        zf.writestr(
            f"{root_folder}/META-INF/reportPackage.json",
            json.dumps({"documentInfo": {"documentType": "https://xbrl.org/report-package/2023"}}, indent=2),
        )

        # reports/report.json — references the EBA taxonomy entry point
        zf.writestr(
            f"{root_folder}/reports/report.json",
            json.dumps(
                {"documentInfo": {"documentType": "https://xbrl.org/2021/xbrl-csv", "extends": [SCHEMA_JSON_URL_42]}},
                indent=2,
            ),
        )

        # reports/parameters.csv — entity, period, currency, decimal precision
        entity_uri = f"https://eurofiling.info/eu/rs#{entity_id}"
        params = (
            "name,value\n"
            f"entityID,{entity_uri}\n"
            f"refPeriod,{period}\n"
            "baseCurrency,EUR\n"
            "decimals_monetary,-3\n"
            "decimals_percentage,4\n"
        )
        zf.writestr(f"{root_folder}/reports/parameters.csv", params)

        # reports/FilingIndicators.csv — true/false for every template in the module
        fi_lines = ["templateID,reported"]
        for r in REPORTS:
            fi_lines.append(f"{r},{fi_map[r]}")
        zf.writestr(f"{root_folder}/reports/FilingIndicators.csv", "\n".join(fi_lines) + "\n")

        for table_file, filings in tables.items():
            if not filings:
                continue

            # Determine which dimension types appear (preserve canonical order)
            dim_types_present: set = set()
            for filing in filings:
                for dim_type, _ in filing[0]:
                    dim_types_present.add(dim_type)
            dim_cols = [d for d in _IRRBB_DIM_ORDER if d in dim_types_present]

            header = ["datapoint", "factValue"] + [f"eba_dim:{d}" for d in dim_cols]
            rows = [",".join(header)]

            for filing in filings:
                dims_dict = {d[0]: d[1] for d in filing[0]}
                metric_code: str = filing[1]
                unit_ref = filing[2]
                amount = filing[3]

                if unit_ref == "uEUR":
                    fact_val = f"{float(amount):.2f}"
                elif unit_ref == "uPURE":
                    fact_val = f"{float(amount):.6f}"
                else:
                    fact_val = _csv_escape(str(amount)) if amount is not None else ""

                dim_values = [_to_eba_qname(dims_dict.get(d, "")) for d in dim_cols]
                row_cols = [metric_code, fact_val] + dim_values
                rows.append(",".join(_csv_escape(v) for v in row_cols))

            zf.writestr(f"{root_folder}/reports/{table_file}", "\n".join(rows) + "\n")

    print(f"xBRL-CSV package: {zip_path}")

    if to_s3:
        save_in_s3(zip_path, f"reports/{root_folder}.zip", file_type="zip")

    return zip_path


def run(
    reports_to_run: list = None,
    period: str = PERIOD,
    username: str = USERNAME,
    to_s3: bool = False
) -> None:
    """Generate IRRBB XBRL reports and upload them to S3.

    Can be called from a terminal script or a Jupyter notebook:

        from reporting.irrbb_xbrl.reports import run
        run(period="2025-12-31")

    Args:
        reports_to_run: List of report codes to process. Defaults to DEFAULT_REPORTS_TO_RUN.
        period:         Reporting reference date as "YYYY-MM-DD". Defaults to module-level PERIOD.
        username:       Snowflake username. Defaults to module-level USERNAME.
    """
    
    
    print("============================================================")
    print("\n Initialising IRRBB XBRL Report: %s\n\n"%datetime.datetime.now())

    if reports_to_run is None:
        reports_to_run = DEFAULT_REPORTS_TO_RUN

    # Annual reports (J_11.xx) are only submitted at year-end
    if not period.endswith("12-31"):
        reports_to_run = [r for r in reports_to_run if not r.startswith("J_11.")]

    # Framework 4.2 (xBRL-CSV) is required for periods >= 2026-03-31
    use_xbrl_csv = period >= "2026-03-31"

    all_data_filings = []
    all_data_reports = []
    data_filings_by_report: Dict[str, list] = {}
    data_units = None  # will be set on first iteration

    for report in reports_to_run:
        print(f"==============================")
        print(f"Building report: {report}")

        # Resolve report / report_nms aliases
        if report == "J_01.00_EUR":
            report_key = "J_01.00"
            report_nms = "J_01.00_EUR"
        # elif report == "J_03.00_EUR":
        #     report_key = "J_03.00"
        #     report_nms = "J_03.00_EUR"
        else:
            report_key = report
            report_nms = report

        raw_data = load_raw_data(report_key, report_nms, period=period, username=username)

        # Adjusting the data format
        data_filings = build_data_filings(raw_data, report_key, report_nms)
        all_data_filings.extend(data_filings)
        data_filings_by_report.setdefault(report_nms, []).extend(data_filings)

        # Getting the metadata for the report
        data_reports, data_units = build_metadata(report_key)
        all_data_reports.extend(data_reports)

        # Building the individual XML file (saved locally for all periods; not uploaded for 2026+)
        xml = build_xml(data_filings, data_reports, data_units, period=period)
        save_the_report(xml, report_key, report_nms, period=period, to_s3=(to_s3 and not use_xbrl_csv))

        out_name = f"{period.replace('-', '_')}_{report_key.replace('.', '_')}.xbrl"
        print(f"Report output/{out_name} created successfully!")
        print(f"==============================")

    if use_xbrl_csv:
        # Framework 4.2: produce the xBRL-CSV report package (the Bundesbank submission format)
        period_dir = period.replace("-", "")
        xbrl_csv_dir = os.path.join(BASE_DIR, "output", period_dir, "xbrl_csv")
        combined_reports = combine_report_flags(all_data_reports)
        pkg_path = build_xbrl_csv_package(
            data_filings_by_report,
            combined_reports,
            period=period,
            output_dir=xbrl_csv_dir,
            to_s3=to_s3,
        )
        print(f"xBRL-CSV package ready for submission: {pkg_path}")
    else:
        # Framework 3.4: stacked XBRL — required by Bundesbank for the production submission
        save_stacked_reports(all_data_filings, all_data_reports, reports_to_run, data_units, period=period)



if __name__ == "__main__":
    run()
