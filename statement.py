import camelot
from pypdf import PdfReader
import pandas as pd
import os

def parse_chase_statement(statement_path, first_page_idx=3):
    '''
    Assumptions:
    the first page with transactions is page 4
    last page does not contain transactions
    '''
    reader = PdfReader(statement_path)
    pages = len(reader.pages)
    print(f"{statement_path} has {pages} pages")
    if pages <= first_page_idx:
        raise Exception("Statement does not appear to have transactions pages <= 3.") 
    print(f"processing pages {first_page_idx}-{pages-1}")
    transaction_df = extract_transactions(statement_path, first_page_idx, pages-1)
    save_transactions(statement_path, transaction_df)
    print(f"finished processing {statement_path}")
    print()

def parse_first_chase_statement_page(statement_path, pages=3):
    # 22,840 is x1,y1 in pdf coordinate space (top left)
    # 500,40 is x2,y2 in pdf coordinate space (bottom right)
    # pdf coords start at 0,0 in the bottom left
    table = camelot.read_pdf(statement_path, pages=f"{pages}", flavor="stream", table_areas=["22,840,500,30"], columns=["80,450"], row_tol=12)
    return table

def parse_normal_chase_statement_page(statement_path, pages):
    # 22,920 is x1,y1 in pdf coordinate space (top left)
    # 500,0 is x2,y2 in pdf coordinate space (bottom right)
    # pdf coords start at 0,0 in the bottom left
    table = camelot.read_pdf(statement_path, pages=pages, flavor="stream", table_areas=["22,920,500,30"], columns=["80,450"], row_tol=12)
    return table

def extract_transactions(statement_path, page_start_idx, page_end_idx):
    first_page = parse_first_chase_statement_page(statement_path, pages=page_start_idx)
    # parse remaining pages up until the second to last page since the last statement page has no transactions
    remaining_pages = parse_normal_chase_statement_page(statement_path, pages=f"{page_start_idx+1}-{page_end_idx}")
    remaining_dfs = [remaining_pages[i].df for i in range(0, len(remaining_pages))]
    result = pd.concat([first_page[0].df] + remaining_dfs)
    return result

def save_transactions(old_statement_path, df_result):
    file = os.path.basename(old_statement_path)
    filename, ext = os.path.splitext(file)
    dir_path = os.path.dirname(old_statement_path)
    new_filename = f"{filename}.csv"
    new_path = os.path.join(dir_path, "parsed", new_filename)
    print(f"saving transaction csv to {new_path}")
    df_result.to_csv(new_path, index=False)

