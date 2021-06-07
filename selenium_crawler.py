from time import sleep
import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

options = webdriver.ChromeOptions()
options.add_argument('--headless') # 可以不讓瀏覽器執行在前景，而是在背景執行（不讓我們肉眼看得見）

# error: (Timed out receiving message from renderer exception)
# happened randomly at the start of the test after calling for driver.get(url) without throwing any exception, it just freezes
# "Timed out receiving message from renderer" means that chromedriver can't receive a response from chrome in time, it's a miscommunication between chromedriver and chrome.
options.add_argument('--disable-gpu') # google document 提到需要加上這個屬性來規避 bug 
# 主要問題可能是Selenium加載頁面時間過長
options.add_argument('start-maximized')
options.add_argument('enable-automation')
options.add_argument('--no-sandbox')
options.add_argument('--disable-infobars')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-browser-side-navigation')

# error: (USB: usb_device_handle_win.cc:1056 Failed to read descriptor from node connection)
options.add_experimental_option('excludeSwitches', ['enable-logging']) # 取消log

# error: (selenium.common.exceptions.WebDriverException: Message: unknown error : net::ERR_CONNECTION_TIMED_OUT)
# 連線失敗，請檢察連線
'''
wrong →→→   driver = webdrive.Chrome(options=options)
error: AttributeError: ResultSet object has no attribute 'to_capabilities'.
讀了selenium對應的webriver初始化py檔(source code)，在實例化webdriver時出錯
如果實例化webdriver沒有傳參的話，那麼給他一個默認值
        if options is None:
            # desired_capabilities stays as passed in
            if desired_capabilities is None:
                desired_capabilities = self.create_options().to_capabilities()
        else:
            if desired_capabilities is None:
wrong →→→       desired_capabilities = options.to_capabilities()
            else:
                desired_capabilities.update(options.to_capabilities())
解決辦法，把options拿掉，變成driver = webdriver.Chrome()
解決辦法，使用global options，一樣寫driver = webdriver.Chrome() →→→偶爾可以動，但偶爾又會出錯
'''

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
        # mystock['股票代號'].str.zfill(4) 沒有inplace = True但能覆蓋原本的mystock資料
        mystock = mystock[mystock['股票代號'].apply(lambda x: len(x) == 4)] # 篩選4位數的股票代碼
        stock_list.append(mystock)

    TWstock_list = pd.concat([stock_list[0], stock_list[1]])
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
    driver.find_element(By.XPATH, '//*[@id="frmStockSearch"]/input[2]').click()
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
            RE_year = parse_Goodinfo_RE_year(dfs)

            try:
                #切換年度至2013年
                driver.find_element(By.ID, "RPT_CAT").click()
                driver.find_element(By.ID, "QRY_TIME").click()
                dropdown = driver.find_element(By.ID, "QRY_TIME")
                dropdown.find_element(By.XPATH, '//*[@id="QRY_TIME"]/option[8]').click()
                driver.find_element(By.ID, "QRY_TIME").click()
                sleep(7)
            except Exception as e:
                print(stockNo + "沒有2013年以前的資產負債表")
            else:
                #取得2013~2007年的資料
                html = driver.page_source # 取得html文字
                soup = BeautifulSoup(html, 'lxml')
                table = soup.select_one('#txtFinBody')

                #資料整理
                dfs = pd.read_html(table.prettify())
                data_y = parse_Goodinfo_RE_year(dfs)
                RE_year = pd.concat([RE_year, data_y], axis = 0, ignore_index = True).dropna()
            finally:
                driver.close() # 關閉分頁視窗
                # driver.quit() # 關閉視窗+關閉driver.exe，釋放記憶體

            return RE_year

def parse_Goodinfo_RE_year(dfs):
    df = dfs[1]
    row = df.iloc[:,0].values.tolist().index('保留盈餘合計')
    year = df.iloc[0,1:14:2].replace('-', np.nan).values
    data_y = df.iloc[row, 1:14:2].replace('-', np.nan).astype('float').values
    RE_year = pd.DataFrame({'年度':year, '保留盈餘合計': data_y})

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

def fetch_retained_earnings_quarter(stockNo): # 保留盈餘合計
    # 進入Goodinfo首頁
    driver = webdriver.Chrome()   
    driver.get('https://goodinfo.tw/StockInfo/index.asp')
    driver.implicitly_wait(1)

    #找到最上方查詢框輸入股票代碼並送出
    driver.find_element(By.ID, "txtStockCode").click()
    driver.find_element(By.ID, "txtStockCode").send_keys(stockNo)
    driver.find_element(By.XPATH, '//*[@id="frmStockSearch"]/input[2]').click()
    driver.implicitly_wait(3)
    try:
        #切換到資產負債表的頁面
        driver.find_element(By.LINK_TEXT, "資產負債表").click()
        driver.implicitly_wait(3)
    except:
        RE_quarter = None
    else:
        #取得2021Q1~2019Q3年的資料
        html = driver.page_source # 取得html文字
        soup = BeautifulSoup(html, 'lxml')
        table = soup.select_one('#txtFinBody')
        
        #資料整理
        dfs = pd.read_html(table.prettify())
        if len(dfs) == 1: # 代表抓不到資料
            RE_quarter = None
        else:
            RE_quarter = parse_Goodinfo_RE_quarter(dfs)

            QRY_TIME = soup.select_one('#QRY_TIME')
            options = QRY_TIME.find_all('option')
            values = [item.string for item in options]
            if len(values) > 7:
                COUNT = 1
                for j in range(7, len(values), 7):
                    try:
                        #QRY_TIME > option:nth-child(8)
                        #切換季度
                        driver.find_element(By.ID, "QRY_TIME").click()
                        dropdown = driver.find_element(By.ID, "QRY_TIME")
                        dropdown.find_element(By.CSS_SELECTOR, '#QRY_TIME > option:nth-child(' + str(j+1) + ')').click()
                        sleep(7)
                    except Exception as e:
                        print(stockNo + "沒有" + values(j) + "以前的資產負債表")
                    else:
                        #取得季度資料
                        html = driver.page_source # 取得html文字
                        soup = BeautifulSoup(html, 'lxml')
                        table = soup.select_one('#txtFinBody')

                        #資料整理
                        data_q = parse_Goodinfo_RE_quarter(dfs)
                        
                        RE_quarter = pd.concat([RE_quarter, data_q], axis = 0, ignore_index = True)

                    COUNT += 1
                    if COUNT == 4:
                        break

    finally:
        driver.close() # 關閉分頁視窗
        # driver.quit() # 關閉視窗+關閉driver.exe，釋放記憶體
        
    return RE_quarter

def parse_Goodinfo_RE_quarter(dfs):
    df = dfs[1]
    row = df.iloc[:,0].values.tolist().index('保留盈餘合計')
    quarter = df.iloc[0,1:14:2].values
    data_q = df.iloc[row, 1:14:2].replace('-', np.nan).astype('float').values
    RE_quarter = pd.DataFrame({'季度':quarter, '保留盈餘合計': data_q})

    return RE_quarter

def fetch_EPS_ROE_ROA_quarter(stockNo):
    # 進入Goodinfo首頁
    driver = webdriver.Chrome()   
    driver.get('https://goodinfo.tw/StockInfo/index.asp')
    driver.implicitly_wait(1)

    #找到最上方查詢框輸入股票代碼並送出
    driver.find_element(By.ID, "txtStockCode").click()
    driver.find_element(By.ID, "txtStockCode").send_keys(stockNo)
    driver.find_element(By.XPATH, '//*[@id="frmStockSearch"]/input[2]').click()
    driver.implicitly_wait(3)
    try:
        #切換到財務比率表的頁面
        driver.find_element(By.LINK_TEXT, "財務比率表").click()
        driver.implicitly_wait(3)
    except:
        EPS_q, ROE_q, ROA_q = None, None, None
    else:
        #切換為單季
        driver.find_element(By.ID, "RPT_CAT").click()
        dropdown = driver.find_element(By.ID, "RPT_CAT")
        dropdown.find_element(By.XPATH, '//*[@id="RPT_CAT"]/option[1]').click()
        sleep(5)

        #取得2021Q1~2018Q2年的資料
        html = driver.page_source # 取得html文字
        soup = BeautifulSoup(html, 'lxml')
        table = soup.select_one('#txtFinBody')
        
        #資料整理
        dfs = pd.read_html(table.prettify())
        if len(dfs) == 1: # 代表抓不到資料
            EPS_q, ROE_q, ROA_q = None, None, None
        else:
            EPS_q, ROE_q, ROA_q = parse_Goodinfo_EPS_ROE_ROA_quarter(dfs)

            QRY_TIME = soup.select_one('#QRY_TIME')
            options = QRY_TIME.find_all('option')
            values = [item.get('value') for item in options]
            if len(values) > 10:
                COUNT = 1
                for j in range(10, len(values), 10):
                    try:
                        #QRY_TIME > option:nth-child(8)
                        #切換季度
                        driver.find_element(By.ID, "QRY_TIME").click()
                        dropdown = driver.find_element(By.ID, "QRY_TIME")
                        dropdown.find_element(By.CSS_SELECTOR, '#QRY_TIME > option:nth-child(' + str(j+1) + ')').click()
                        sleep(5)
                    except Exception as e:
                        print(stockNo + "沒有" + values(j) + "以前的財務比率表")
                    else:
                        #取得季度資料
                        html = driver.page_source # 取得html文字
                        soup = BeautifulSoup(html, 'lxml')
                        table = soup.select_one('#txtFinBody')
                        try:
                            #資料整理
                            dfs = pd.read_html(table.prettify())
                            df_eps, df_roe, df_roa = parse_Goodinfo_EPS_ROE_ROA_quarter(dfs)
                            
                            EPS_q = pd.concat([EPS_q, df_eps], axis = 0, ignore_index = True)
                            ROE_q = pd.concat([ROE_q, df_roe], axis = 0, ignore_index = True)
                            ROA_q = pd.concat([ROA_q, df_roa], axis = 0, ignore_index = True)
                        except Exception as e:
                            print('發生錯誤：', e)

                    COUNT += 1
                    if COUNT == 3:
                        break

    finally:
        driver.close() # 關閉分頁視窗
        # driver.quit() # 關閉視窗+關閉driver.exe，釋放記憶體
        
    return EPS_q, ROE_q, ROA_q

def parse_Goodinfo_EPS_ROE_ROA_quarter(dfs):
    df = dfs[1]
    quarter = df.iloc[0,1:].values
    row1 = df.iloc[:,0].values.tolist().index(u'每股稅後盈餘\xa0(元)')
    row2 = df.iloc[:,0].values.tolist().index('股東權益報酬率  (當季)')
    row3 = df.iloc[:,0].values.tolist().index('資產報酬率  (當季)')
    eps = df.iloc[row1,1:].replace('-', np.nan).astype('float').values
    roe = df.iloc[row2,1:].replace('-', np.nan).astype('float').values
    roa = df.iloc[row3,1:].replace('-', np.nan).astype('float').values
    
    EPS_q = pd.DataFrame({'季度':quarter, '每股稅後盈餘(EPS)':eps})
    ROE_q = pd.DataFrame({'季度':quarter, '股東權益報酬率(ROE)':roe})
    ROA_q = pd.DataFrame({'季度':quarter, '資產報酬率(ROA)':roa})

    return EPS_q, ROE_q, ROA_q

def parse_PChome_quarter(html):
    bts = BeautifulSoup(html, 'lxml')
    quarter = bts.select('#bttb > table > tbody > tr:nth-child(4) > th')
    eps = bts.select('#bttb > table > tbody > tr:nth-child(15) > td')
    roe = bts.select('#bttb > table > tbody > tr:nth-child(17) > td')
    roa = bts.select('#bttb > table > tbody > tr:nth-child(18) > td')
    # 季度名稱要跟Goodinfo統一
    Quarter = [quarter[i].text.replace('年第', 'Q')[:6] for i in range(1, len(quarter))]
    EPS = [eps[i].text for i in range(1, len(eps))]
    ROE = [roe[i].text for i in range(1, len(roe))]
    ROA = [roa[i].text for i in range(1, len(roa))]

    EPS_q = pd.DataFrame({'季度':Quarter, '每股稅後盈餘(EPS)':EPS}).replace('-', np.nan).astype({'每股稅後盈餘(EPS)':float})
    ROE_q = pd.DataFrame({'季度':Quarter, '股東權益報酬率(ROE)':ROE}).replace('-', np.nan).astype({'股東權益報酬率(ROE)':float})
    ROA_q = pd.DataFrame({'季度':Quarter, '資產報酬率(ROA)':ROA}).replace('-', np.nan).astype({'資產報酬率(ROA)':float})

    return EPS_q, ROE_q, ROA_q

def fetch_PChome_EPS_ROE_ROA_quarter(stockNo):
    # 進入PChome財務比率表
    driver = webdriver.Chrome()
    driver.get("https://pchome.megatime.com.tw/stock/sto2/ock2/sid" + stockNo + ".html") 
    sleep(5) # 等待javascript渲染出來

    html = driver.page_source # 取得html文字
    bts = BeautifulSoup(html, 'lxml')
    EPS_q, ROE_q, ROA_q = parse_PChome_quarter(html)

    # 搜尋dropdown，計算季度數量
    quarter_options = bts.select('#bttb > table > tbody > tr:nth-child(1) > td > div:nth-child(2) > select > option')
    values = [item.string for item in quarter_options]
    if len(values) > 8:
        COUNT = 1
        for j in range(8, len(values), 8):
            try:
                #切換季度
                dropdown = driver.find_element(By.TAG_NAME,"select")
                dropdown.find_element(By.CSS_SELECTOR, '#bttb > table > tbody > tr:nth-child(1) > td > div:nth-child(2) > select > option:nth-child(' + str(j+1) + ')').click()
                sleep(7)
            except Exception as e:
                print(stockNo + "沒有" + values(j+1) + "以前的財務比率表")
            else:
                #取得季度資料
                html = driver.page_source # 取得html文字
                df_eps, df_roe, df_roa = parse_PChome_quarter(html)

                EPS_q = pd.concat([EPS_q, df_eps], axis = 0, ignore_index = True)
                ROE_q = pd.concat([ROE_q, df_roe], axis = 0, ignore_index = True)
                ROA_q = pd.concat([ROA_q, df_roa], axis = 0, ignore_index = True)

            COUNT += 1
            if COUNT == 4:
                break

    driver.close() # 關閉分頁視窗
    # driver.quit() # 關閉視窗+關閉driver.exe，釋放記憶體

    return EPS_q, ROE_q, ROA_q

def fetch_stock_quarter_data():
    table = pd.read_csv('./database/stock_id.csv', encoding = 'utf-8')
    stock_list = table['股票代號'].astype(str).values.tolist()
    for stockNo in stock_list:
        print(stockNo)
        file1 = 'database/' + stockNo + '_quarter.csv'
        if os.path.exists(file1): 
            continue
        else:
            RE_q = fetch_retained_earnings_quarter(stockNo) # 抓Goodinfo

            if isinstance(RE_q, pd.DataFrame) == False: # 如果RE_q不是DataFrame物件代表沒抓到資料
                print(stockNo + '查無資料！')
                sleep(3)
                continue # 跳過抓不到資料的股票代碼
            else:
                EPS_q, ROE_q, ROA_q = fetch_EPS_ROE_ROA_quarter(stockNo) # 抓PChome
                
                # 合併數據並輸出csv檔
                data_quarter = pd.concat([RE_q, EPS_q, ROE_q, ROA_q], axis = 1, join = 'inner')
                data_quarter = data_quarter.loc[:,~data_quarter.columns.duplicated()] 
                data_quarter.to_csv('database\\' + stockNo + '_quarter.csv', encoding = 'utf-8', index = False)
                sleep(3)


if __name__=='__main__':
    update_stock_list()

    update_finished = False
    while not update_finished:
        try:
            fetch_stock_quarter_data()
            fetch_stock_year_data()
            update_finished = True
        except Exception as e:
            print("發生錯誤：", e)
        finally:
            sleep(3)
    if update_finished:
        print('所有股票爬蟲執行完畢')
        



