import camelot
from pypdf import PdfReader
import pandas as pd
import os
import fitz

RESOURCE_COORDS = {
    "account_summary": {
        "table": [16,588,258,408],
        "columns": [170]
    },
    "first_transaction_page": {
        "table": [22,840,500,30],
        "columns": [80,450],
    },
    "normal_transaction_page": {
        "table": [22,920,500,30],
        "columns": [80,450],
    },
}

PAGE_DIMENSIONS = {
    "width": 522,
    "height": 1008
}

SUMMARY_KEYWORDS = ["Total", "Totals", "Balance", "Payment", "Year-to-Date", "fees charged", "interest charged"]

def save_debug_pdf(path: str, table_coords: list[int], column_coords: list[int], pages: str):
    h = PAGE_DIMENSIONS["height"]
    x1, y1, x2, y2 = table_coords
    fitz_rect = fitz.Rect(x1, h - y1, x2, h - y2)
    page_indices = []
    for part in pages.split(","):
        if "-" in part:
            start, end = part.split("-")
            page_indices.extend(range(int(start) - 1, int(end)))
        else:
            page_indices.append(int(part) - 1)
    pdf = fitz.open(path)
    for idx in page_indices:
        page = pdf[idx]
        page.draw_rect(fitz_rect, color=(1, 0, 0), width=1)
        for col_x in column_coords:
            page.draw_line((col_x, fitz_rect.y0), (col_x, fitz_rect.y1), color=(0, 0, 1), width=0.5)
    debug_path = os.path.splitext(path)[0] + "_debug.pdf"
    pdf.save(debug_path)
    return debug_path


def parse_chase_statement(statement_path, first_page_idx=3):
    '''
    Assumptions:
    the first page with transactions is page 4
    '''
    reader = PdfReader(statement_path)
    pages = len(reader.pages)
    print(f"{statement_path} has {pages} pages")
    if pages <= first_page_idx:
        raise Exception("Statement does not appear to have transactions pages <= 3.") 
    print(f"processing pages {first_page_idx}-{pages-1}")
    transaction_df = extract_transactions(statement_path, first_page_idx, pages)
    transaction_df = cleanup_transactions(transaction_df)
    account_summary_df = account_summary(statement_path)
    # compare account summary total with sum of transactions as a sanity check
    save_transactions(statement_path, transaction_df)
    print(f"finished processing {statement_path}")
    print()


def account_summary(path: str):
    # found coordinates using fitz and trial and error to find the right bounding box that captures the account summary table without extra text
    # but fitz uses top-left origin (y increases downward), but camelot uses bottom-left origin (y increases upward, PDF standard).
    # fitz.Rect(16, 420, 258, 600) height is 1008 so we subtract
    table = RESOURCE_COORDS["account_summary"]["table"]
    columns = RESOURCE_COORDS["account_summary"]["columns"]
    pages = "1"
    table = camelot.read_pdf(path, pages=pages, flavor="stream", table_areas=[",".join(map(str, table))], columns=[",".join(map(str, columns))], row_tol=10)
    if len(table) == 0:
        coords = RESOURCE_COORDS["account_summary"]
        debug_path = save_debug_pdf(path, coords["table"], coords["columns"], pages=pages)
        raise Exception(f"No tables found in account summary area. Debug PDF saved to {debug_path}")

    df = table[0].df
    
    return df

def parse_first_chase_statement_page(statement_path, pages=3):
    # 22,840 is x1,y1 in pdf coordinate space (top left)
    # 500,40 is x2,y2 in pdf coordinate space (bottom right)
    # pdf coords start at 0,0 in the bottom left
    table = camelot.read_pdf(statement_path, pages=f"{pages}", flavor="stream", table_areas=["22,840,500,30"], columns=["80,450"], row_tol=12)
    if len(table) == 0:
        coords = RESOURCE_COORDS["first_transaction_page"]
        debug_path = save_debug_pdf(statement_path, coords["table"], coords["columns"], pages=f"{pages}")
        raise Exception(f"No tables found in first chase transaction page. Debug PDF saved to {debug_path}")
    
    df = table[0].df

    # skip leading header rows (e.g. AutoPay text, "ACCOUNT ACTIVITY") before the first real transaction
    DATE_PATTERN = r"^\d\d/\d\d$"  # MM/DD
    first_date_pos = df.iloc[:, 0].str.match(DATE_PATTERN).argmax()
    df = df.iloc[first_date_pos:].reset_index(drop=True)

    return df

def parse_normal_chase_statement_page(statement_path, pages):
    # 22,920 is x1,y1 in pdf coordinate space (top left)
    # 500,0 is x2,y2 in pdf coordinate space (bottom right)
    # pdf coords start at 0,0 in the bottom left
    table = camelot.read_pdf(statement_path, pages=pages, flavor="stream", table_areas=["22,920,500,30"], columns=["80,450"], row_tol=12)
    if len(table) == 0:
        coords = RESOURCE_COORDS["normal_transaction_page"]
        debug_path = save_debug_pdf(statement_path, coords["table"], coords["columns"], pages=pages)
        raise Exception(f"No tables found in chase transaction page. Debug PDF saved to {debug_path}")

    df = pd.concat([table[i].df for i in range(len(table))]).reset_index(drop=True)

    for i, row in df.iterrows():
        row_text = " ".join(str(val) for val in row)
        if any(keyword in row_text for keyword in SUMMARY_KEYWORDS):
            return df.loc[:i-1].reset_index(drop=True)

    return df

def extract_transactions(statement_path, page_start_idx, page_end_idx):
    first_page = parse_first_chase_statement_page(statement_path, pages=page_start_idx)
    # parse remaining pages up until the second to last page since the last statement page has no transactions
    remaining_pages = parse_normal_chase_statement_page(statement_path, pages=f"{page_start_idx+1}-{page_end_idx}")
    result = pd.concat([first_page, remaining_pages])
    return result

def cleanup_transactions(result):
    result = merge_international_transactions(result)
    # after merging, remove section header rows (e.g. "PURCHASE") — valid rows all have a MM/DD date at this point
    DATE_PATTERN = r"^\d\d/\d\d$"  # MM/DD
    result = result[result.iloc[:, 0].str.match(DATE_PATTERN)].reset_index(drop=True)
    result.columns = ["DATE", "TRANSACTION_NAME", "AMOUNT"]
    return result

def merge_international_transactions(df):
    '''
    Merges international transaction rows where exchange rate information is on a separate line.
    Rows with empty date columns are continuation rows and are merged with the previous row.
    '''
    merged_rows = []

    for _, row in df.iterrows():
        date_val = str(row.iloc[0]).strip()
        if date_val == "" or date_val == "nan":
            if merged_rows:
                merged_rows[-1].iloc[1] += "\n" + row.iloc[1]
        else:
            merged_rows.append(row.copy())

    result_df = pd.DataFrame(merged_rows)
    result_df.columns = df.columns
    return result_df.reset_index(drop=True)

def save_transactions(old_statement_path, df_result):
    file = os.path.basename(old_statement_path)
    filename, ext = os.path.splitext(file)
    dir_path = os.path.dirname(old_statement_path)
    new_filename = f"{filename}.csv"
    new_path = os.path.join(os.path.dirname(dir_path), "parsed", new_filename)
    print(f"saving transaction csv to {new_path}")
    df_result.to_csv(new_path, index=False)

