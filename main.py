# main.py

from flask import Flask, request, render_template, url_for, redirect
from requests.models import parse_header_links
from config import DevConfig
import pandas as pd
import os
from goodinfo_crawler import *
import draw 

# 初始化 Flask 類別成為 instance
app = Flask(__name__)
app.config.from_object(DevConfig)

# 路由和處理函式配對
@app.route('/')
@app.route('/index')
def hello():
    lst = draw.go()   
    return render_template('mainpage.html', name = 'ccClub'
    ,lst=lst)

@app.route('/stock/')
def stock_query():
    stock_id = request.args.get('stock_id')
    stock_name = type(stock_id)
    table = pd.read_csv('./database/stock_id.csv')
    if stock_id.isdigit():

        if int(stock_id) in table['股票代號'].values:
            stock_name = table[table['股票代號'] == int(stock_id)]['名稱'].values[0]
        else:
            return render_template('search.html') # 此股票不存在

    elif stock_id.isalpha():

        if stock_id in table['名稱'].values:
            stock_name = stock_id
            stock_id = str(table[table['名稱'] == stock_id]['股票代號'].values[0])
        else:
            return render_template('search.html') # 此股票不存在

    else:
        return render_template('search.html') # 此股票不存在
        
    df = pd.read_csv('.\\database\\' + stock_id + '_year.csv')
    column_names = df.columns.tolist()
    df = df.astype({'年度':'object'})
    df = df.values.tolist()

    return render_template('search.html', stock_name = stock_name, stock_id = stock_id, 
                            column_names = column_names, df = df)



if __name__=='__main__':
    
    app.run(debug=True)
    


