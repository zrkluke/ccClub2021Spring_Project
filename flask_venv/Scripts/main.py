# main.py

from flask import Flask, request, render_template, url_for, redirect
from config import DevConfig
import pandas as pd

# 初始化 Flask 類別成為 instance
app = Flask(__name__)
app.config.from_object(DevConfig)

# 路由和處理函式配對
@app.route('/')
@app.route('/home')
@app.route('/index')
def hello():
    return render_template('index.html', name = 'ccClub')

@app.route('/stock/')
def stock_query():
    stock_id = request.args.get('stock_id')
    df = pd.read_csv('.\\database\\' + stock_id + '.csv')
    if stock_id == '1101':
        stock_name = '台泥'
    elif stock_id == '1234':
        stock_name = '黑松'
    elif stock_id == '2345':
        stock_name = '智邦'
    elif stock_id == '2330':
        stock_name = '台積電'
    elif stock_id == '8464':
        stock_name = '億豐'
    column_names = df.columns.tolist()
    df = df.astype({'年度':'object'})
    df = df.values.tolist()
    return render_template('stock.html', stock_name = stock_name, stock_id = stock_id, 
                            column_names = column_names, df = df)

@app.route('/stock/213')
def stock_page2():
    stock_id = request.args.get('stock_id')
    return '<h1>Hello, World! %s</h1>' % stock_id


