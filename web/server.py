from aiohttp import web
import mariadb
import datetime

class DB:
    def __init__(self):
        self.db = mariadb.connect(
            user="root",
            password="Meow",
            host="localhost",
            port=3306)
        self.cur = self.db.cursor()
        self.cur.execute("SELECT * FROM information_schema.tables WHERE TABLE_NAME = 'pressure'")
        if len(self.cur.fetchall()) == 0:
            self.cur.execute("CREATE DATABASE IF NOT EXISTS miac;")
            self.db.commit()
            self.cur.execute("""CREATE TABLE miac.pressure (
        id INT AUTO_INCREMENT PRIMARY KEY,
        snils INT NOT NULL,
        up_press INT NOT NULL,
        down_press INT NOT NULL,
        pulse INT NOT NULL,
        oxymetr INT,
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
            ret_arr.append({'up_press':line[2],'down_press':line[3],'pulse':line[4],'oxymetr':line[5],'ts':line[6]})
        return ret_arr

    def add_measurement(self,patient_id,up_press,down_press,pulse,oxymetr=None):
        self.cur.execute(f"INSERT INTO miac.pressure (snils,up_press,down_press,pulse,oxymetr,ts) VALUES (?,?,?,?,?,?);",(patient_id,up_press,down_press,pulse,oxymetr,datetime.datetime.now().timestamp()))
        self.db.commit()


db = DB()    
routes = web.RouteTableDef()

@routes.get('/')
async def root(req):
    text = """<html>
    <head></head>
    <body>
        <div style="position:fixed;width:100%;height:100%;background:black;left:0;top:0;z-index:9000"><div style="text-align:center;width:100%;height:100%;padding-top:40%;color:black">Here be dragons.</div></div>
    </body>
</html>"""
    return web.Response(text=text,content_type='text/html')

@routes.get('/{patient_id}/data')
async def get_data(req):
    values = db.get_patient_data(req.match_info['patient_id'],req.query.get('ts_start',None),req.query.get('ts_end',None))
    #print(values)
    return web.json_response(values)

@routes.post('/{patient_id}/data')
async def set_data(req):
    data = await req.post()
    print(data)
    db.add_measurement(req.match_info['patient_id'],data['upper'],data['lower'],data['pulse'])
    return web.HTTPOk()

app = web.Application()
app.add_routes(routes)
web.run_app(app)