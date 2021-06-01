import random
from time import sleep
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import numpy as np
import pandas as pd
import os

user_agent = UserAgent()
headers = {'User-Agent': user_agent.random}
delay_choice = [random.randint(15,30) for i in range(10)]
DELAY = random.choice(delay_choice)

def update_stock_list():
    TWSE_url = 'http://isin.twse.com.tw/isin/C_public.jsp?strMode=2' # 上市
    TPEX_url = 'http://isin.twse.com.tw/isin/C_public.jsp?strMode=4' # 上櫃
    stock_list = []
    for url in [TWSE_url, TPEX_url]:
        response = requests.get(url)

        df = pd.read_html(response.text)[0]
        df.columns = df.iloc[0]
        df = df.iloc[2:]
        id_name = df['有價證券代號及名稱'].str.split(u"\u3000", expand = True)
        id_name.columns = ['股票代號','名稱']
        info = df.loc[:,'上市日':'產業別']
        mystock = pd.concat([id_name, info], axis = 1).dropna(subset = ['名稱'])
        mystock = mystock[mystock['股票代號'].apply(lambda x: len(x) < 5)]
        stock_list.append(mystock)

    TWstock_list = pd.concat([stock_list[0], stock_list[1]], )
    TWstock_list.to_csv('database\\stock_id.csv', encoding = 'utf-8', index = False)

def get_retained_earnings_year(stockNo): # 保留盈餘合計
    url = 'https://goodinfo.tw/StockInfo/StockFinDetail.asp' # 資產負債表
    my_params = {'RPT_CAT':'BS_M_YEAR', 'STOCK_ID':stockNo}
    response = requests.get(url, params = my_params, timeout = 5, headers = headers)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    table = soup.select_one('#txtFinBody')
    
    dfs = pd.read_html(table.prettify())
    df = dfs[1]
    row = df.iloc[:,0].values.tolist().index('保留盈餘合計')
    year = df.iloc[0,1:14:2].replace('-', np.nan).values
    data_y = df.iloc[row, 1:14:2].replace('-', np.nan).astype('float').values
    RE_year = pd.DataFrame({'年度':year, '保留盈餘合計': data_y})   
    
    QRY_TIME = soup.select_one('#QRY_TIME')
    options = QRY_TIME.find_all('option')
    values = [item.get('value') for item in options]
    
    if len(values) > 7:
        sleep(DELAY)
        for j in range(7, len(values), 7):
            my_params = {'RPT_CAT':'BS_M_YEAR', 'QRY_TIME':values[j], 'STOCK_ID':stockNo}
            response = requests.get(url, params = my_params, timeout = 5, headers = headers)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.select_one('#txtFinBody')
            
            dfs = pd.read_html(table.prettify())
            df = dfs[1]
            row = df.iloc[:,0].values.tolist().index('保留盈餘合計')
            year = df.iloc[0,1:14:2].replace('-', np.nan).values
            data_y = df.iloc[row, 1:14:2].replace('-', np.nan).astype('float').values
            
            df = pd.DataFrame({'年度':year, '保留盈餘合計': data_y})
            RE_year = pd.concat([RE_year, df], axis = 0, ignore_index = True).dropna()
            
            sleep(DELAY)

    return RE_year

def get_EPS_ROE_ROA_year(stockNo):
    url = 'https://goodinfo.tw/StockInfo/StockFinDetail.asp' # 財務比率表
    my_params = {'RPT_CAT':'XX_M_YEAR', 'STOCK_ID':stockNo}
    response = requests.get(url, params = my_params, timeout = 5, headers = headers)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    table = soup.select_one('#txtFinBody')
    
    dfs = pd.read_html(table.prettify())
    df = dfs[1]
    year = df.iloc[0,1:].replace('-', np.nan).values
    eps = df.iloc[7,1:].replace('-', np.nan).astype('float').values
    roe = df.iloc[9,1:].replace('-', np.nan).astype('float').values
    roa = df.iloc[10,1:].replace('-', np.nan).astype('float').values
    
    EPS_y = pd.DataFrame({'年度':year, '每股稅後盈餘(EPS)':eps})
    ROE_y = pd.DataFrame({'年度':year, '股東權益報酬率(ROE)':roe})
    ROA_y = pd.DataFrame({'年度':year, '資產報酬率(ROA)':roa})
    
    QRY_TIME = soup.select_one('#QRY_TIME')
    options = QRY_TIME.find_all('option')
    values = [item.get('value') for item in options]
    
    if len(values) > 12:
        sleep(DELAY)
        for i in range(12, len(values), 12):
            my_params = {'RPT_CAT':'XX_M_YEAR', 'QRY_TIME':values[i], 'STOCK_ID':stockNo}
            response = requests.get(url, params = my_params, timeout = 5, headers = headers)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.select_one('#txtFinBody')
            
            dfs = pd.read_html(table.prettify())
            df = dfs[1]
            year = df.iloc[0,1:].replace('-', np.nan).values
            eps = df.iloc[7,1:].replace('-', np.nan).astype('float').values
            roe = df.iloc[9,1:].replace('-', np.nan).astype('float').values
            roa = df.iloc[10,1:].replace('-', np.nan).astype('float').values
            
            df_eps = pd.DataFrame({'年度':year, '每股稅後盈餘(EPS)':eps})
            df_roe = pd.DataFrame({'年度':year, '股東權益報酬率(ROE)':roe})
            df_roa = pd.DataFrame({'年度':year, '資產報酬率(ROA)':roa})
            
            EPS_y = pd.concat([EPS_y, df_eps], axis = 0, ignore_index = True).dropna()
            ROE_y = pd.concat([ROE_y, df_roe], axis = 0, ignore_index = True).dropna()
            ROA_y = pd.concat([ROA_y, df_roa], axis = 0, ignore_index = True).dropna()
            
            sleep(DELAY)
    
    return EPS_y, ROE_y, ROA_y

def get_cash_dividend_year(stockNo):
    url = 'https://goodinfo.tw/StockInfo/StockDividendPolicy.asp' # 股利政策
    my_params = {'STOCK_ID':stockNo}
    response = requests.get(url, params = my_params, timeout = 5, headers = headers)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    table = soup.select_one('#divDetail')
    
    dfs = pd.read_html(table.prettify())
    df = dfs[0]
    year = df.iloc[:,19].replace('-', np.nan).values.tolist()
    cash = df.iloc[:,3].replace('-', np.nan).astype('float').values.tolist()
    
    year_new = []
    cash_new = []
    YEAR = ''
    TOTAL = 0
    i = 0
    while  i < len(year)-1:
        if 'Q' in year[i] and 'Q' in year[i+1]:
            if '~' in year[i]:
                Y1, Y2 = year[i].split('~')
                
                if YEAR == '':
                    YEAR = '20' + Y1.strip()[:2]
                    
                if YEAR == '20' + Y1.strip()[:2]:
                    if Y1.strip()[:2] == Y2.strip()[:2]:
                        TOTAL += cash[i]
                        
                        if Y2.strip() in year:
                            index = year.index(Y2.strip())
                            i = index
                            
                elif YEAR != '20' + Y1.strip()[:2]:
                    year_new.append(YEAR)
                    cash_new.append(TOTAL)
                    YEAR = '20' + Y1.strip()[:2]
                    TOTAL = cash[i]
                    
            elif YEAR == '':
                YEAR = '20' + year[i][:2]
                TOTAL += cash[i]
                
            elif YEAR == '20' + year[i][:2]:
                TOTAL += cash[i]
                
            elif YEAR != '20' + year[i][:2]:
                year_new.append(YEAR)
                cash_new.append(TOTAL)
                YEAR = '20' + year[i][:2]
                TOTAL = cash[i]
                
        elif 'Q' in year[i] and year[i+1].isdigit():
            YEAR = '20' + year[i][:2]
            TOTAL += cash[i]
            year_new.append(YEAR)
            cash_new.append(TOTAL)
            
        elif year[i].isdigit():
            year_new.append(year[i])
            cash_new.append(cash[i])
            
        i += 1
        
    CashDividend_y = pd.DataFrame({'年度':year_new, '現金股利':cash_new}).drop_duplicates().dropna()
    
    return CashDividend_y

def update_stock_year_data():
    table = pd.read_csv('./database/stock_id.csv', encoding = 'utf-8')
    stock_list = table['股票代號'].astype(str).values.tolist()
    for stockNo in stock_list:
        print(stockNo)
        file1 = 'database/' + stockNo + '_year.csv'
        if os.path.exists(file1):
            continue
        else:
            RE_y = get_retained_earnings_year(stockNo)
            sleep(DELAY)

            if isinstance(RE_y, pd.DataFrame) == False: # 跳過抓不到資料的股票代碼
                continue
            else:
                EPS_y, ROE_y, ROA_y = get_EPS_ROE_ROA_year(stockNo)
                sleep(DELAY)

                CashDividend_y = get_cash_dividend_year(stockNo)
                sleep(DELAY)

                data_year = pd.concat([RE_y, EPS_y, ROE_y, ROA_y, CashDividend_y], axis = 1, join = 'inner')
                data_year = data_year.loc[:,~data_year.columns.duplicated()] 
                data_year = data_year.astype({'年度':'object'})
                data_year.to_csv('database\\' + stockNo + '_year.csv', encoding = 'utf-8', index = False)

def get_retained_earnings_quarter(stockNo):
    url = 'https://goodinfo.tw/StockInfo/StockFinDetail.asp' # 資產負債表
    my_params = {'RPT_CAT':'BS_M_QUAR', 'STOCK_ID':stockNo}
    response = requests.get(url, params = my_params, timeout = 5, headers = headers)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    table = soup.select_one('#txtFinBody')
    
    dfs = pd.read_html(table.prettify())
    df = dfs[1]
    row = df.iloc[:,0].values.tolist().index('保留盈餘合計')
    quarter = df.iloc[0,1:14:2].values
    data_q = df.iloc[row, 1:14:2].astype('float').values
    RE_quarter = pd.DataFrame({'季度':quarter, '保留盈餘合計': data_q})
    
    QRY_TIME = soup.select_one('#QRY_TIME')
    options = QRY_TIME.find_all('option')
    values = [item.get('value') for item in options]
    
    if len(values) > 7:
        sleep(DELAY)
        for j in range(7, len(values), 7):
            my_params = {'RPT_CAT':'BS_M_QUAR', 'QRY_TIME':values[j], 'STOCK_ID':stockNo}
            response = requests.get(url, params = my_params, timeout = 5, headers = headers)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.select_one('#txtFinBody')
            
            dfs = pd.read_html(table.prettify())
            df = dfs[1]
            row = df.iloc[:,0].values.tolist().index('保留盈餘合計')
            quarter = df.iloc[0,1:14:2].values
            data_q = df.iloc[row, 1:14:2].astype('float').values
            
            df = pd.DataFrame({'季度':quarter,'保留盈餘合計': data_q})
            RE_quarter = pd.concat([RE_quarter, df], axis = 0, ignore_index = True)
                
    return RE_quarter

def get_EPS_ROE_ROA_quarter(stockNo):
    url = 'https://goodinfo.tw/StockInfo/StockFinDetail.asp' # 財務比率表
    my_params = {'RPT_CAT':'XX_M_QUAR', 'STOCK_ID':stockNo}
    response = requests.get(url, params = my_params, timeout = 5, headers = headers)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    table = soup.select_one('#txtFinBody')
    
    dfs = pd.read_html(table.prettify())
    df = dfs[1]
    quarter = df.iloc[0,1:].values
    eps = df.iloc[7,1:].astype('float').values
    roe = df.iloc[9,1:].astype('float').values
    roa = df.iloc[11,1:].astype('float').values
    
    EPS_q = pd.DataFrame({'季度':quarter, '每股稅後盈餘(EPS)':eps})
    ROE_q = pd.DataFrame({'季度':quarter, '股東權益報酬率(ROE)':roe})
    ROA_q = pd.DataFrame({'季度':quarter, '資產報酬率(ROA)':roa})
    
    QRY_TIME = soup.select_one('#QRY_TIME')
    options = QRY_TIME.find_all('option')
    values = [item.get('value') for item in options]
    
    if len(values) > 10:
        sleep(DELAY)
        for i in range(10, len(values), 10):
            my_params = {'RPT_CAT':'XX_M_QUAR', 'QRY_TIME':values[i], 'STOCK_ID':stockNo}
            response = requests.get(url, params = my_params, timeout = 5, headers = headers)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.select_one('#txtFinBody')
            
            dfs = pd.read_html(table.prettify())
            df = dfs[1]
            quarter = df.iloc[0,1:].values
            eps = df.iloc[7,1:].astype('float').values
            roe = df.iloc[9,1:].astype('float').values
            roa = df.iloc[11,1:].astype('float').values
            
            df_eps = pd.DataFrame({'季度':quarter, '每股稅後盈餘(EPS)':eps})
            df_roe = pd.DataFrame({'季度':quarter, '股東權益報酬率(ROE)':roe})
            df_roa = pd.DataFrame({'季度':quarter, '資產報酬率(ROA)':roa})
            
            EPS_q = pd.concat([EPS_q, df_eps], axis = 0, ignore_index = True)
            ROE_q = pd.concat([ROE_q, df_roe], axis = 0, ignore_index = True)
            ROA_q = pd.concat([ROA_q, df_roa], axis = 0, ignore_index = True)
            
    return EPS_q, ROE_q, ROA_q

def update_stock_quarter_data():
    table = pd.read_csv('./database/stock_id.csv', encoding = 'utf-8')
    stock_list = table['股票代號'].astype(str).values.tolist()
    for stockNo in stock_list:
        print(stockNo)
        file2 = 'database/' + stockNo + '_quarter.csv'
        if os.path.exists(file2):
            continue
        else:
            RE_q = get_retained_earnings_quarter(stockNo)
            sleep(DELAY)
            
            if isinstance(RE_q, pd.DataFrame) == False: # 跳過抓不到資料的股票代碼
                continue
            else:
                EPS_q, ROE_q, ROA_q = get_EPS_ROE_ROA_quarter(stockNo)
                sleep(DELAY)

                data_quarter = pd.concat([RE_q, EPS_q, ROE_q, ROA_q], axis = 1, join = 'inner')
                data_quarter = data_quarter.loc[:,~data_quarter.columns.duplicated()]
                data_quarter.to_csv('database\\' + stockNo + '_quarter.csv', encoding = 'utf-8', index = False)


if __name__=='__main__':
    
    update_stock_list()
    update_stock_year_data()
    update_stock_quarter_data()
        