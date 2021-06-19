from enum import EnumMeta
from aiohttp import web
import mariadb
import datetime
import logging
logging.basicConfig(level=logging.DEBUG)
class DB:
    def __init__(self):
        self.db = mariadb.connect(
            user="root",
            password="Meow",
            host="localhost",
            port=3306)
        self.cur = self.db.cursor()
        self.cur.execute("SELECT * FROM information_schema.partitions WHERE TABLE_SCHEMA = 'miac'")
        if len(self.cur.fetchall()) == 0:
            self.cur.execute("CREATE DATABASE IF NOT EXISTS miac;")
            self.db.commit()

        self.cur.execute("SELECT * FROM information_schema.tables WHERE TABLE_NAME = 'pressure'")
        if len(self.cur.fetchall()) == 0:
            self.cur.execute("""CREATE TABLE miac.pressure (
        id INT AUTO_INCREMENT PRIMARY KEY,
        snils INT NOT NULL,
        up_press INT NOT NULL,
        down_press INT NOT NULL,
        pulse INT NOT NULL,
        oxymetr INT,
        state TEXT,
        ts INT NOT NULL
        ) ENGINE=InnoDB;""")
            self.db.commit()

    def get_patient_data(self,patient_id,ts_start=None,ts_end=None):
        if ts_start is not None:
            start_secs = ts_start
            start_query = f" AND ts >= '{start_secs}'"
        else:
            start_query = ""
        if ts_end is not None:
            end_secs = ts_end
            end_query = f" AND ts <= '{end_secs}'"
        else:
            end_query = ""
        self.cur.execute(f"SELECT * FROM miac.pressure WHERE snils = '{patient_id}'{start_query}{end_query};")
        print(f"SELECT * FROM miac.pressure WHERE snils = '{patient_id}'{start_query}{end_query};")
        data = self.cur.fetchall()
        ret_arr = []
        for line in data:
            ret_arr.append({'ts':line[7],'up_press':line[2],'down_press':line[3],'pulse':line[4],'oxymetr':line[5],'state':line[6]})
        return ret_arr

    def add_measurement(self,patient_id,up_press,down_press,pulse,oxymetr=None,state=None):
        self.cur.execute(f"INSERT INTO miac.pressure (snils,up_press,down_press,pulse,oxymetr,state,ts) VALUES (?,?,?,?,?,?,?);",(patient_id,up_press,down_press,pulse,oxymetr,state,datetime.datetime.now().timestamp()))
        self.db.commit()

    def patient_states(self,patient_id):
        counts = {}
        self.cur.execute(f"SELECT state FROM miac.pressure WHERE snils = '{patient_id}';")
        for row in self.cur.fetchall():
            if row[0] is not None:
                if counts.get(row[0],None) is None:
                    counts[row[0]] = 1
                else:
                    counts[row[0]] += 1
        return dict(sorted(counts.items(), key=lambda item: item[1],reverse=True))

def format_in_series(tag,name,color,values):
    data = []
    for row in values:
        data.append(row[tag])
    return f'{{show: true, spanGaps: true, label: "{name}",stroke:"rgb({color})", width: 1, fill: "rgba({", ".join([str(chn) for chn in color])}, 0.25)",dash: [10, 5]}}',data

db = DB()    
routes = web.RouteTableDef()
routes.static('/dist', 'html/dist')

@routes.get('/')
async def root(req):
    text = """<html>
    <head></head>
    <body>
        <div style="position:fixed;width:100%;height:100%;background:black;left:0;top:0;z-index:9000"><div style="text-align:center;width:100%;height:100%;padding-top:40%;color:black">Here be dragons.</div></div>
    </body>
</html>"""
    return web.Response(text=text,content_type='text/html')

@routes.get('/{patient_id}')
async def patient_page(req):
    #print(db.patient_states(req.match_info['patient_id']))
    data = db.get_patient_data(req.match_info['patient_id'])
    fmt_data = {'ts':None,'upper':None,'lower':None,'pulse':None,'oxymetr':None}
    fmt_data['ts'] = format_in_series("ts","Время",(0,0,0),data)
    fmt_data['upper'] = format_in_series("up_press","Верхее А/Д",(200,0,0),data)
    fmt_data['lower'] = format_in_series("down_press","Нижнее А/Д",(200,200,0),data)
    fmt_data['pulse'] = format_in_series("pulse","Пульс",(0,200,0),data)
    series = f'{{label: "Время"}},{fmt_data["upper"][0]},{fmt_data["lower"][0]},{fmt_data["pulse"][0]}'
    values = [fmt_data['ts'][1],fmt_data['upper'][1],fmt_data['lower'][1],fmt_data['pulse'][1]]
    with open('html\\index.html','r',encoding='utf-8') as f:
        html = f.read()
        html = html.replace("===DATA===",str(values))
        html = html.replace("===SERIES===",series)
        return web.Response(text=html,content_type='text/html')

@routes.get('/{patient_id}/data')
async def get_data(req):
    values = db.get_patient_data(req.match_info['patient_id'],req.query.get('ts_start',None),req.query.get('ts_end',None))
    #print(values)
    return web.json_response(values)

@routes.post('/{patient_id}/data')
async def set_data(req):
    data = await req.post()
    print(data)
    db.add_measurement(req.match_info['patient_id'],data['upper'],data['lower'],data['pulse'],oxymetr=data.get('oxymetr',None),state=data.get('state',None))
    return web.HTTPOk()

app = web.Application()
app.add_routes(routes)
web.run_app(app)