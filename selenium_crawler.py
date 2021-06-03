import random
from time import sleep
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import numpy as np
import pandas as pd
import os
from selenium import webdriver

user_agent = UserAgent()
headers = {'User-Agent': user_agent.random}
delay_choice = [random.randint(20,40) for i in range(30)]

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
    url = 'https://goodinfo.tw/StockInfo/StockFinDetail.asp' # goodinfo資產負債表
    my_params = {'RPT_CAT':'BS_M_YEAR', 'STOCK_ID':stockNo}
    response = requests.get(url, params = my_params, timeout = 10, headers = headers)
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
        sleep(random.choice(delay_choice))
        COUNT = 1
        for j in range(7, len(values), 7):
            my_params = {'RPT_CAT':'BS_M_YEAR', 'QRY_TIME':values[j], 'STOCK_ID':stockNo}
            response = requests.get(url, params = my_params, timeout = 10, headers = headers)
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
            
            sleep(random.choice(delay_choice))

            COUNT += 1
            if COUNT == 2:
                break

    return RE_year

def fetch_EPS_ROE_ROA_year(stockNo):
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options)
    driver.get("https://pchome.megatime.com.tw/stock/sto2/ock6/sid" + stockNo + ".html") # PChome財務比率表
    sleep(3) # 等待javascript渲染出來
    html = driver.page_source # 取得html文字
    driver.close()  # 關掉Driver打開的瀏覽器

    bts = BeautifulSoup(html, 'lxml')
    year = bts.select('#bttb > table > tbody > tr:nth-child(4) > th')
    eps = bts.select('#bttb > table > tbody > tr:nth-child(15) > td')
    roe = bts.select('#bttb > table > tbody > tr:nth-child(17) > td')
    roa = bts.select('#bttb > table > tbody > tr:nth-child(18) > td')

    Year = [year[i].text[:4] for i in range(1, len(year))]
    EPS = [eps[i].text for i in range(1, len(eps))]
    ROE = [roe[i].text for i in range(1, len(roe))]
    ROA = [roa[i].text for i in range(1, len(roa))]

    EPS_y = pd.DataFrame({'年度':Year, '每股稅後盈餘(EPS)':EPS}).replace('-', np.nan).astype({'每股稅後盈餘(EPS)':float})
    ROE_y = pd.DataFrame({'年度':Year, '股東權益報酬率(ROE)':ROE}).replace('-', np.nan).astype({'股東權益報酬率(ROE)':float})
    ROA_y = pd.DataFrame({'年度':Year, '資產報酬率(ROA)':ROA}).replace('-', np.nan).astype({'資產報酬率(ROA)':float})

    return EPS_y, ROE_y, ROA_y

def fetch_cash_dividend_year(stockNo):
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.cmoney.tw/finance/f00027.aspx?s=" + stockNo) # cmoney股利政策
    sleep(3) # 等待javascript渲染出來
    html = driver.page_source # 取得html文字
    driver.close()  # 關掉Driver打開的瀏覽器

    bts = BeautifulSoup(html, 'lxml')
    table = bts.select_one('#MainContent > ul > li > article > div > div > div.tb-out > table')
    df = pd.read_html(table.prettify())[0]
    df = df.astype({'年度':str})
    CashDividend_y = df.loc[:,'年度':'現金股利']
    
    return CashDividend_y

def fetch_stock_year_data():
    table = pd.read_csv('./database/stock_id.csv', encoding = 'utf-8')
    stock_list = table['股票代號'].astype(str).values.tolist()
    for stockNo in stock_list:
        print(stockNo)
        file1 = 'database/' + stockNo + '_year.csv'
        if os.path.exists(file1):
            continue
        else:
            RE_y = get_retained_earnings_year(stockNo) # 抓Goodinfo
            sleep(random.choice(delay_choice))

            if isinstance(RE_y, pd.DataFrame) == False: # 跳過抓不到資料的股票代碼
                continue
            else:
                EPS_y, ROE_y, ROA_y = fetch_EPS_ROE_ROA_year(stockNo) # 抓PChome

                CashDividend_y = fetch_cash_dividend_year(stockNo) # 抓CMoney
                

                data_year = pd.concat([RE_y, EPS_y, ROE_y, ROA_y, CashDividend_y], axis = 1, join = 'inner')
                data_year = data_year.loc[:,~data_year.columns.duplicated()] 
                data_year = data_year.astype({'年度':str})
                data_year.to_csv('database\\' + stockNo + '_year.csv', encoding = 'utf-8', index = False)
                sleep(random.choice(delay_choice))


if __name__=='__main__':

    fetch_stock_year_data()

