import streamlit as st
import pandas as pd
import oracledb
st.set_page_config(layout="wide")
from io import BytesIO

st.markdown("""
<style>
.main .block-container {
    max-width: 100%;
    padding-left: 1rem;
    padding-right: 1rem;
}
            
[data-testid="stDataFrame"] {
    width: 100%;}
            
[data-testid="stDataEditor"] {
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# Database connection parameters
def get_connection():
    """Create and return database connection"""
    try:
        # Get credentials from Streamlit secrets
        EDW_LOGIN = st.secrets["database"]["login"]
        EDW_HOST = st.secrets["database"]["host"]
        EDW_PORT = st.secrets["database"]["port"]
        EDW_PASS = st.secrets["database"]["password"]
        EDW_SERVICE = st.secrets["database"]["service"]
        
        dsn = oracledb.makedsn(EDW_HOST, EDW_PORT, EDW_SERVICE)
        conn = oracledb.connect(user=EDW_LOGIN, password=EDW_PASS, dsn=dsn)
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def search_phones_by_contract(contract_number):
    """Search phone numbers by contract number"""
    conn = get_connection()
    if not conn:
        return None
    
    query = """
    WITH t AS (
        SELECT
             sc.CONTRACT_NUMBER,
             g.IIN_BIN AS IIN,
             g.LONGNAME,
             ccaff_pivot."'MOBILECP1'" AS MOBILECP1,
             ccaff_pivot."'FIOCP1'" AS FIOCP1,
             ccaff_pivot."'RELATIONSHIPCP1'" AS RELATIONSHIPCP1,
             ccaff_pivot."'MOBILECP2'" AS MOBILECP2,
             ccaff_pivot."'FIOCP2'" AS FIOCP2,
             ccaff_pivot."'RELATIONSHIPCP2'" AS RELATIONSHIPCP2,
             ccaff_pivot."'MOBILESPOUSE'" AS MOBILESPOUSE,
             ccaff_pivot."'FIOSPOUSE'" AS FIOSPOUSE
        FROM DDS.RS_CR_CONTRACT_SCD_S sc
        INNER JOIN DDS.RS_GM_PRODUCT_H pr ON sc.rs_gm_product_id = pr.dwh_id AND sc.gm_system_code = pr.gm_system_code
        INNER JOIN DDS.GM_SUBJECT_H g ON sc.GM_SUBJECT_ID = g.DWH_ID AND g.GM_SYSTEM_CODE = sc.Gm_System_Code
        INNER JOIN DDS.RS_CR_CONTRACT_RATE_S cr ON cr.DWH_ID = sc.DWH_ID AND sc.GM_SYSTEM_CODE = cr.GM_SYSTEM_CODE
        INNER JOIN (
            SELECT * FROM (
                SELECT IIN, PROCESS_ID, CODE, VALUE
                FROM DDS.CMD_CCE_APPLICATION_FIELDS_FL
            )
            PIVOT (
                MAX(VALUE)
                FOR CODE IN ('MOBILECP1', 'FIOCP1', 'RELATIONSHIPCP1', 'MOBILECP2', 'FIOCP2', 'RELATIONSHIPCP2', 'MOBILESPOUSE', 'FIOSPOUSE')
            )
        ) ccaff_pivot ON ccaff_pivot.IIN = g.IIN_BIN 
        WHERE sc.gm_system_code = 'RS'
            AND sc.DBZ_NUM IS NOT NULL
            AND sc.IS_ACTUAL = 'A'
            AND cr.IS_ACTUAL = 'A'
            AND sc.STATUS_CODE = 'ACTUAL'
            AND SUBSTR(sc.DBZ_NUM, 1, 2) NOT IN ('ML', 'PL')
            AND sc.CONTRACT_NUMBER = :contract_num
     )
    SELECT DISTINCT CONTRACT_NUMBER, IIN, LONGNAME, tel, fio, otnoshenie
    FROM (
        SELECT CONTRACT_NUMBER, IIN, LONGNAME, MOBILECP1 AS tel, FIOCP1 AS fio, RELATIONSHIPCP1 AS otnoshenie
        FROM t
        WHERE MOBILECP1 IS NOT NULL
        UNION ALL
        SELECT CONTRACT_NUMBER, IIN, LONGNAME, MOBILECP2 AS tel, FIOCP2 AS fio, RELATIONSHIPCP2 AS otnoshenie
        FROM t
        WHERE MOBILECP2 IS NOT NULL
        UNION ALL
        SELECT CONTRACT_NUMBER, IIN, LONGNAME, MOBILESPOUSE AS tel, FIOSPOUSE AS fio, 'SPOUSE' AS otnoshenie
        FROM t
        WHERE MOBILESPOUSE IS NOT NULL
    )
    """
    
    try:
        df = pd.read_sql(query, conn, params={'contract_num': contract_number})
        conn.close()
        
        # Remove duplicates by TEL and FIO
        if not df.empty:
            df = df.drop_duplicates(subset=['TEL', 'FIO']).reset_index(drop=True)
            # Rename columns to uppercase for consistency
            df.columns = df.columns.str.upper()
        
        return df
    except Exception as e:
        st.error(f"Query execution error: {e}")
        conn.close()
        return None

def to_excel(df):
    """Convert DataFrame to Excel bytes"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Phones')
    return output.getvalue()

# Streamlit App
def main():
    st.title("Search phones by contract number")
    
    # Input field for contract number
    contract_number = st.text_input("Enter CONTRACT_NUMBER:", placeholder="e.g., 3177770000104080")
    
    # Search button
    if st.button("Search"):
        if not contract_number:
            st.warning("Please enter a contract number")
        else:
            with st.spinner("Searching..."):
                df_result = search_phones_by_contract(contract_number)
                
                if df_result is not None:
                    if df_result.empty:
                        st.info("No results found for this contract number")
                    else:
                        st.success(f"Found {len(df_result)} phone records")
                        
                        # Display dataframe with configured column widths
                        st.dataframe(
                            df_result, 
                            use_container_width=True,
                            height=400,
                            column_config={
                                "CONTRACT_NUMBER": st.column_config.TextColumn(width=150),
                                "IIN": st.column_config.TextColumn(width=120),
                                "LONGNAME": st.column_config.TextColumn(width=250),
                                "TEL": st.column_config.TextColumn(width=120),
                                "FIO": st.column_config.TextColumn(width=250),
                                "OTNOSHENIE": st.column_config.TextColumn(width=150)
                            }
                        )
                        
                        # Download button
                        excel_data = to_excel(df_result)
                        st.download_button(
                            label="Download as Excel",
                            data=excel_data,
                            file_name=f"contract_{contract_number}_phones.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

if __name__ == "__main__":
    main()
