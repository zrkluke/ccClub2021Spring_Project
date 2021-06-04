import random
from time import sleep
import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options

# chrome_options = Options()
# chrome_options.add_argument('--disable-gpu')

options = webdriver.ChromeOptions()
# options.add_argument('--headless') # 可以不讓瀏覽器執行在前景，而是在背景執行（不讓我們肉眼看得見）
# error: (Timed out receiving message from renderer exception)
options.add_argument('--disable-gpu') # google document 提到需要加上這個屬性來規避 bug 
options.add_experimental_option('excludeSwitches', ['enable-logging'])
delay_choice = [random.randint(10,20) for i in range(10)]

def update_stock_list():
    TWSE_url = 'http://isin.twse.com.tw/isin/C_public.jsp?strMode=2' # 上市
    TPEX_url = 'http://isin.twse.com.tw/isin/C_public.jsp?strMode=4' # 上櫃
    stock_list = []
    for url in [TWSE_url, TPEX_url]:
        response = requests.get(url)
        # 資料整理
        df = pd.read_html(response.text)[0]
        df.columns = df.iloc[0]
        df = df.iloc[2:]
        id_name = df['有價證券代號及名稱'].str.split(u"\u3000", expand = True)
        id_name.columns = ['股票代號','名稱']
        info = df.loc[:,'上市日':'產業別']
        mystock = pd.concat([id_name, info], axis = 1).dropna(subset = ['名稱'])
        mystock = mystock[mystock['股票代號'].apply(lambda x: len(x) < 5)] # 篩選小於4位數的股票代碼
        stock_list.append(mystock)

    TWstock_list = pd.concat([stock_list[0], stock_list[1]], )
    TWstock_list.to_csv('database\\stock_id.csv', encoding = 'utf-8', index = False)

def fetch_retained_earnings_year(stockNo): # 保留盈餘合計
    # 進入Goodinfo首頁
    driver = webdriver.Chrome(options=options)
    driver.get('https://goodinfo.tw/StockInfo/index.asp')
    driver.implicitly_wait(1)
    driver.set_window_size(1242, 706)

    #找到最上方查詢框輸入股票代碼並送出
    driver.find_element(By.ID, "txtStockCode").click()
    driver.find_element(By.ID, "txtStockCode").send_keys(stockNo)
    driver.find_element(By.CSS_SELECTOR, "input:nth-child(2)").click()
    driver.implicitly_wait(3)
    try:
        #切換到資產負債表的頁面
        driver.find_element(By.LINK_TEXT, "資產負債表").click()
        driver.implicitly_wait(3)
    except:
        driver.close()
        return None
    else:
        #切換為年度
        driver.find_element(By.ID, "RPT_CAT").click()
        dropdown = driver.find_element(By.ID, "RPT_CAT")
        dropdown.find_element(By.XPATH, '//*[@id="RPT_CAT"]/option[2]').click()
        sleep(7)

        #取得2020~2014年的資料
        html = driver.page_source # 取得html文字
        soup = BeautifulSoup(html, 'lxml')
        table = soup.select_one('#txtFinBody')
        
        #資料整理
        dfs = pd.read_html(table.prettify())
        if len(dfs) == 1: # 代表抓不到資料
            driver.close()
            return None
        else:
            df = dfs[1]
            row = df.iloc[:,0].values.tolist().index('保留盈餘合計')
            year = df.iloc[0,1:14:2].replace('-', np.nan).values
            data_y = df.iloc[row, 1:14:2].replace('-', np.nan).astype('float').values
            RE_year = pd.DataFrame({'年度':year, '保留盈餘合計': data_y})  

            try:
                #切換年度至2013年
                driver.find_element(By.ID, "RPT_CAT").click()
                driver.find_element(By.ID, "QRY_TIME").click()
                dropdown = driver.find_element(By.ID, "QRY_TIME")
                dropdown.find_element(By.XPATH, '//*[@id="QRY_TIME"]/option[8]').click()
                driver.find_element(By.ID, "QRY_TIME").click()
                sleep(7)
            except Exception as e:
                print("沒有2013年以前的資產負債表", e)
            else:
                #取得2013~2007年的資料
                html = driver.page_source # 取得html文字
                soup = BeautifulSoup(html, 'lxml')
                table = soup.select_one('#txtFinBody')

                #資料整理
                dfs = pd.read_html(table.prettify())
                df = dfs[1]
                row = df.iloc[:,0].values.tolist().index('保留盈餘合計')
                year = df.iloc[0,1:14:2].replace('-', np.nan).values
                data_y = df.iloc[row, 1:14:2].replace('-', np.nan).astype('float').values
                df = pd.DataFrame({'年度':year, '保留盈餘合計': data_y})
                RE_year = pd.concat([RE_year, df], axis = 0, ignore_index = True).dropna()
            finally:
                driver.close()

            return RE_year

def fetch_EPS_ROE_ROA_year(stockNo):
    # 進入PChome財務比率表
    driver = webdriver.Chrome(options=options)
    driver.get("https://pchome.megatime.com.tw/stock/sto2/ock6/sid" + stockNo + ".html") 
    sleep(5) # 等待javascript渲染出來
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
    # 進入CMoney股利政策
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.cmoney.tw/finance/f00027.aspx?s=" + stockNo) 
    sleep(5) # 等待AJAX渲染出來
    html = driver.page_source # 取得html文字
    driver.close()  # 關掉Driver打開的瀏覽器

    bts = BeautifulSoup(html, 'lxml')
    table = bts.select_one('#MainContent > ul > li > article > div > div > div.tb-out > table')
    
    if table == None:
        return None
    else:
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
            RE_y = fetch_retained_earnings_year(stockNo) # 抓Goodinfo

            if isinstance(RE_y, pd.DataFrame) == False: # 如果RE_y不是DataFrame物件代表沒抓到資料
                print(stockNo + '查無資料！')
                sleep(3)
                continue # 跳過抓不到資料的股票代碼
            else:
                EPS_y, ROE_y, ROA_y = fetch_EPS_ROE_ROA_year(stockNo) # 抓PChome

                CashDividend_y = fetch_cash_dividend_year(stockNo) # 抓CMoney
                
                # 合併數據並輸出csv檔
                data_year = pd.concat([RE_y, EPS_y, ROE_y, ROA_y, CashDividend_y], axis = 1, join = 'inner')
                data_year = data_year.loc[:,~data_year.columns.duplicated()] 
                data_year = data_year.astype({'年度':str})
                data_year.to_csv('database\\' + stockNo + '_year.csv', encoding = 'utf-8', index = False)
                sleep(3)


if __name__=='__main__':

    fetch_stock_year_data()

