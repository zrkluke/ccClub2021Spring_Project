# main.py

from flask import Flask, request, render_template, url_for, redirect
from config import DevConfig
import pandas as pd
import os
import time
import draw

# 初始化 Flask 類別成為 instance
app = Flask(__name__)
app.config.from_object(DevConfig)

# 路由和處理函式配對
@app.route('/')
@app.route('/index')
def hello():
    lst = draw.go()   
    return render_template('mainpage.html', name = 'ccClub',lst=lst)

@app.route('/stock/')
def stock_query():
    stock_id = request.args.get('stock_id')
    table = pd.read_csv('./database/stock_id.csv')
    if stock_id.isdigit():
        if int(stock_id) in table['股票代號'].values:
            stock_name = table[table['股票代號'] == int(stock_id)]['名稱'].values[0]
        else:
            return render_template('search.html', stock_name = '您查詢的公司不存在', result = '請確認輸入的股票名稱或代號是否正確，再重新查詢看看', Growth = 0) # 此股票不存在

    else:
        if stock_id in table['名稱'].values:
            stock_name = stock_id
            stock_id = str(table[table['名稱'] == stock_id]['股票代號'].values[0])
        else:
            return render_template('search.html', stock_name = '您查詢的公司不存在', result = '請確認輸入的股票名稱或代號是否正確，再重新查詢看看', Growth = 0) # 此股票不存在


    year_data_time = time.strftime("%Y/%m/%d",time.localtime(os.path.getmtime('.\\database\\' + stock_id + '_year.csv')))      
    df_year = pd.read_csv('.\\database\\' + stock_id + '_year.csv')
    column_year = df_year.columns.tolist()
    df_year = df_year.astype({'年度':'object'})
    year_data = df_year.values.tolist()

    quarter_data_time = time.strftime("%Y/%m/%d",time.localtime(os.path.getmtime('.\\database\\' + stock_id + '_quarter.csv'))) 
    df_quarter = pd.read_csv('.\\database\\' + stock_id + '_quarter.csv')
    column_quarter = df_quarter.columns.tolist()
    quarter_data = df_quarter.values.tolist()

    df_year['RR'] = df_year['現金股利'] / df_year['每股稅後盈餘(EPS)']
    ROA = df_year['資產報酬率(ROA)'].head(5).mean() / 100
    RR = df_year['RR'].head().mean()
    Growth = ROA * RR
    EPS = df_year['每股稅後盈餘(EPS)'].head(5).mean()
    D = EPS * (1 - RR)
    

    return render_template('search.html', stock_name = stock_name, stock_id = '(' + stock_id + ')', 
                            column_year = column_year, year_data = year_data, year_data_time = year_data_time,
                            column_quarter = column_quarter, quarter_data = quarter_data, quarter_data_time = quarter_data_time,
                            Growth = Growth, EPS = EPS, D = D
                            )






if __name__=='__main__':
    
    app.run(debug=True)
    


        

