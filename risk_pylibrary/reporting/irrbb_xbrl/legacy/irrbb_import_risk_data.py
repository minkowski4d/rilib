import logging
import os

import pandas as pd

from tools.snowflake_db import db_connection as db
from tools import python2s3 as ps3

logger = logging.getLogger(__name__)

DEFAULT_TMP_PATH = os.getenv('TEMP_PATH', '/tmp')
DEFAULT_S3_PATH = os.getenv('S3_PATH', 'risk_write/mr/banking_book/irrbb/positions')


def get_irrbb_risk_data() -> pd.DataFrame:

    query = """
        SELECT 'J_01_00' AS REPORT, REPORT_DATE, IDX::VARCHAR AS IDX, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J01_00
        UNION ALL
        SELECT 'J_02_00', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J02_00
        UNION ALL
        SELECT 'J_03_00', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J03_00
        UNION ALL
        SELECT 'J_04_00', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J04_00
        UNION ALL
        SELECT 'J_05_00_A', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J05_00_A
        UNION ALL
        SELECT 'J_05_00_B', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J05_00_B
        UNION ALL
        SELECT 'J_06_00_A', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J06_00_A
        UNION ALL
        SELECT 'J_06_00_B', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J06_00_B
        UNION ALL
        SELECT 'J_07_00_A', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J07_00_A
        UNION ALL
        SELECT 'J_07_00_B', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J07_00_B
        UNION ALL
        SELECT 'J_08_00_A', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J08_00_A
        UNION ALL
        SELECT 'J_08_00_B', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J08_00_B
        UNION ALL
        SELECT 'J_09_00_A', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J09_00_A
        UNION ALL
        SELECT 'J_09_00_B', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J09_00_B
        UNION ALL
        SELECT 'J_10_01', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J10_01
        WHERE REPORT_DATE <> '2024-09-30'
        UNION ALL
        SELECT 'J_10_02', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J10_02
        WHERE REPORT_DATE <> '2024-09-30'
        UNION ALL
        SELECT 'J_11_01', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, NULL AS VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J11_01
        UNION ALL
        SELECT 'J_11_02', REPORT_DATE, IDX::VARCHAR, GROUP_0, GROUP_1, FMT, NULL AS VALUE
        FROM TEAMS_PRD.RISK_DATA.MR_IRRBB_EBA_J11_02
    """
    
    
    return db.run_query(query)


def export_irrbb_positions_to_s3(
    tmp_path: str = DEFAULT_TMP_PATH,
    s3_path: str = DEFAULT_S3_PATH,
) -> dict:
    logger.info("Fetching IRRBB positions from Snowflake")
    df = get_irrbb_risk_data()
    logger.info(f"Retrieved {len(df)} rows")

    os.makedirs(tmp_path, exist_ok=True)
    file_name = "irrbb_positions.parquet"
    local_path = os.path.join(tmp_path, file_name)

    df.to_parquet(local_path, index=False)
    logger.info(f"Saved parquet to {local_path}")

    ps3.save_in_s3(
        local_path=local_path,
        path_s3=s3_path,
        file_name=file_name,
        file_type='parquet',
    )
    logger.info(f"Uploaded to s3://tr-risk-data-prd/{s3_path}/{file_name}")

    return {'success': True, 'message': f"Uploaded {len(df)} rows to s3://tr-risk-data-prd/{s3_path}/{file_name}"}
