import aiohttp
from aiohttp import web
import mariadb
import datetime
import logging
logging.basicConfig(level=logging.DEBUG)

class MessageDB:
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

        self.cur.execute("SELECT * FROM information_schema.tables WHERE TABLE_NAME = 'messages'")
        if len(self.cur.fetchall()) == 0:
            self.cur.execute("""CREATE TABLE miac.messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        snils INT NOT NULL,
        text TEXT NOT NULL,
        delivered BOOLEAN NOT NULL
        ) ENGINE=InnoDB;""")
            self.db.commit()

    def new_message(self, patient_id, text):
        self.cur.execute("INSERT INTO miac.messages(snils,text,delivered) VALUES (?,?,?);",(patient_id,text,False))
        self.db.commit()
    
    def get_messages(self,patient_id=None,unread=False):
        query = "SELECT * FROM miac.messages"
        if patient_id is not None or unread is True:
            query += " WHERE"
        if patient_id is not None:
            query += f" snils = '{patient_id}'"
        if unread:
            self.cur.execute(query + " delivered = '?';",(not unread,))
        else:
            self.cur.execute(query +';')
        return self.cur.fetchall()
class MeasuresDB:
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

    def patient_means(self,patient_id,ts_start=None,ts_end=None):
        data = self.get_patient_data(patient_id,ts_start=ts_start,ts_end=ts_end)
        sum_upper = 0
        sum_lower = 0
        sum_pulse = 0
        for line in data:
            sum_upper += line['up_press']
            sum_lower += line['down_press']
            sum_pulse += line['pulse']
        return {'upper':f"{sum_upper/len(data):.1f}",'lower':f"{sum_lower/len(data):.1f}",'pulse':f"{sum_pulse/len(data):.1f}"}

# def format_in_series(tag,name,color,values):
#     data = []
#     for row in values:
#         data.append(row[tag])
#     return f'{{show: true, spanGaps: true, label: "{name}",stroke:"rgb({color})", width: 1, fill: "rgba({", ".join([str(chn) for chn in color])}, 0.25)",dash: [10, 5]}}',data

def format_in_series(tag,name,color,values,not_lower=None,not_higher=None,parsed=False):
    data = []
    if parsed:
        for row in values:
            data.append({'x':row['ts']*1000,'y':row[tag]})
    else:
        for row in values:
            data.append(row[tag])
    definition = f'{{label: "{name}",data: {data}, borderColor: "rgb({", ".join([str(chn) for chn in color])})"'
    if not_lower is not None:
        definition += f", segment: {{borderColor: ctx => lower(ctx, 'rgb(200,15,15)', {not_lower}),}}"
    if not_higher is not None:
        definition += f", segment: {{borderColor: ctx => higher(ctx, 'rgb(200,15,15)', {not_higher}),}}"
    definition += '}'
    return definition,data

def format_static_line(value,name,color,values):
    data = []
    for row in range(len(values)):
        data.append(value)
    return f'{{show: true, spanGaps: true, label: "{name}",stroke:"{color}",width: 3}}',data

val_db = MeasuresDB()    
msg_db = MessageDB()
routes = web.RouteTableDef()
routes.static('/dist', 'html/dist')
routes.static('/static', 'html/static')

@routes.get('/')
async def root(req):
    text = """<html>
    <head></head>
    <body>
        <div style="position:fixed;width:100%;height:100%;background:black;left:0;top:0;z-index:9000"><div style="text-align:center;width:100%;height:100%;padding-top:40%;color:black">Here be dragons.</div></div>
    </body>
</html>"""
    return web.Response(text=text,content_type='text/html')

@routes.get('/favicon.ico')
async def meow(req):
    pass

@routes.get('/ws')
async def ws_handler(req):
    ws = web.WebSocketResponse()
    await ws.prepare(req)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            patient_id,text = msg.data.split(':::')
            msg_db.new_message(patient_id,text) 
    return ws

@routes.get('/{patient_id}')
async def patient_page(req):
    print(msg_db.get_messages())
    #print(db.patient_states(req.match_info['patient_id']))
    patient_id = req.match_info['patient_id']
    data = val_db.get_patient_data(patient_id)
    if len(data) != 0:
        name = 'Пупкин Василий Иванович'
        birth = datetime.datetime.fromtimestamp(185938914)
        means = val_db.patient_means(patient_id)
        fmt_data = {'ts':None,'upper':None,'lower':None,'pulse':None,'oxymetr':None,'mid_upper':None,'mid_lower':None,'mid_pulse':None}
        fmt_data['ts'] = format_in_series("ts","Время",(0,0,0),data)
        fmt_data['upper'] = format_in_series("up_press","Верхее А/Д",(0,200,200),data,not_higher=140)
        fmt_data['lower'] = format_in_series("down_press","Нижнее А/Д",(200,200,0),data)
        fmt_data['pulse'] = format_in_series("pulse","Пульс",(0,200,0),data)
        timestamps = [val*1000 for val in fmt_data['ts'][1]]
        datasets = fmt_data['upper'][0] + ',' + fmt_data['lower'][0] + ',' + fmt_data['pulse'][0]
        # fmt_data['mid_upper'] = format_static_line(means['upper'], "Верхнее А/Д (ср.)", "lightblue",data)
        # fmt_data['mid_lower'] = format_static_line(means['lower'], "Нижнее А/Д (ср.)", "yellow",data)
        # fmt_data['mid_pulse'] = format_static_line(means['pulse'], "Пульс (ср.)", "green",data)
        # series = f'{{label: "Время"}},{fmt_data["upper"][0]},{fmt_data["lower"][0]},{fmt_data["pulse"][0]},{fmt_data["mid_upper"][0]},{fmt_data["mid_lower"][0]},{fmt_data["mid_pulse"][0]}'
        # values = [fmt_data['ts'][1],fmt_data['upper'][1],fmt_data['lower'][1],fmt_data['pulse'][1],fmt_data['mid_upper'][1],fmt_data['mid_lower'][1],fmt_data['mid_pulse'][1]]
    else:
        name = 'Пациент не определен'
        birth = datetime.datetime.fromtimestamp(0)
        means = {'upper':0,'lower':0,'pulse':0}
        values = []
        series = '{}'
    userdata = f'<p><strong>ФИО: </strong>{name}</p>\n<p><strong>Дата рождения: </strong>{birth.strftime("%d.%m.%Y")} ({int((datetime.datetime.now()-birth).days/365)} лет)</p>\n<p><strong>Средние показатели: </strong>{means["upper"]}/{means["lower"]}/{means["pulse"]}</p>'
    with open('html\\index.html','r',encoding='utf-8') as f:
        html = f.read()
        html = html.replace("===TIMESTAMPS===",str([val for val in timestamps]))
        html = html.replace("===DATASETS===",datasets)
        html = html.replace("===USERDATA===",userdata)
        return web.Response(text=html,content_type='text/html')

@routes.get('/{patient_id}/data')
async def get_data(req):
    values = val_db.get_patient_data(req.match_info['patient_id'],req.query.get('ts_start',None),req.query.get('ts_end',None))
    #print(values)
    return web.json_response(values)

@routes.post('/{patient_id}/data')
async def set_data(req):
    data = await req.post()
    print(data)
    val_db.add_measurement(req.match_info['patient_id'],data['upper'],data['lower'],data['pulse'],oxymetr=data.get('oxymetr',None),state=data.get('state',None))
    return web.HTTPOk()

app = web.Application()
app.add_routes(routes)
web.run_app(app)