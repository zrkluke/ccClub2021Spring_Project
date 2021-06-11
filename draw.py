import requests
import json

import datetime

def stay(lst,today):
    
    try :
        nu=int(lst[3])
        gotime = str(int(lst[1][0:3])+1911)+lst[1][3:]
        strtime= str(int(lst[5][0:3])+1911)+lst[5][3:]
        endtime= str(int(lst[6][0:3])+1911)+lst[6][3:]
        givtime= str(int(lst[11][0:3])+1911)+lst[11][3:]
        x= (datetime.datetime.strptime(endtime,'%Y/%m/%d')).strftime('%Y/%m/%d')
        
        if x >= today :
            newl = []
            newl.append(gotime)
            newl.append(lst[2])
            newl.append(lst[3])
            newl.append(strtime)
            newl.append(endtime)
            newl.append(lst[7])
            newl.append(lst[9])
            newl.append(givtime)
            return newl
        else :
            return 0 
    except:
        return 0

def go():
    url = 'https://www.twse.com.tw/announcement/publicForm'
    r = requests.get(url)
    today=datetime.datetime.now().strftime("%Y/%m/%d")
    ##y= (datetime.datetime.strptime('2021/05/01','%Y/%m/%d')).strftime('%Y/%m/%d') 測試日期

    x = json.loads(r.text)

    tot = []

    for each in x['data'] :

        new = stay(each,today)
        if new != 0 :
            tot.append(new)
    return tot
        


    