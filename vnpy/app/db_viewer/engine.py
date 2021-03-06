import datetime
import pymongo
from vnpy.event import EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.setting import SETTINGS

APP_NAME = "DbViewer"


class DbViewEngine(BaseEngine):
    """数据库浏览引擎"""
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """初始化"""
        super().__init__(main_engine, event_engine, APP_NAME)
        self.app_engine = self.main_engine.get_engine(APP_NAME)
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.username = SETTINGS["database.user"]
        self.password = SETTINGS["database.password"]
        self.host = SETTINGS["database.host"]
        self.port = SETTINGS["database.port"]
        self.authentication_source = SETTINGS["database.authentication_source"]
        self.col_names = []
        try:
            self.db_client = pymongo.MongoClient(self.host, int(self.port))
            self.avtive = True
            self.update_db_info()
        except Exception as e:
            self.write_log("打开数据库失败{self.host}{self.port}")
            self.avtive = False

    def update_db_info(self):
        """ 更新数据库连接信息 """
        self.db_info = {
            "连接地址": self.db_client.HOST,
            "连接端口": str(self.db_client.PORT),
            "占用空间": str(self.db_client.server_info()['maxBsonObjectSize']),
            "连接状态": "连接中" if self.avtive else "断开连接"
        }
        self.dbs = self.db_client.list_database_names()

        for db in self.dbs:
            self.collections = {db: self.db_client[db].list_collection_names}

    def write_log(self, msg):
        """ 写日志记录 """
        print(msg)

    def get_db_names(self):
        """ 获得所有的数据库名称列表 """
        return self.dbs

    def get_collections_by_dbname(self, db_name):
        """ 根据数据库名称获得集合名称列表 """
        return self.db_client[db_name].list_collection_names()

    def get_column_names(self):
        """ 获得列名称的列表 """
        return self.col_names

    def find_sample(self, db_name, collection_name):
        """ 找到一个样本 """
        try:
            return self.db_client[db_name][collection_name].find_one()
        except Exception as e:
            self.write_log("无法获取sample")
            return []

    def get_collection_info(self, db_name, collection_name):
        """ 获得集合的信息 """
        sample = self.find_sample(db_name, collection_name)
        if sample:
            res = {
                "集合名称":
                collection_name,
                "所属数据库":
                db_name,
                "占用空间":
                f'{self.db_client[db_name].validate_collection(collection_name)["datasize"] / 1024 / 1024:.2f}M',
                "数据总量":
                str(self.db_client[db_name]
                    [collection_name].estimated_document_count())
            }
            keys = list(sample) if sample else []
            res["列名集合"] = str(keys)
            self.col_names = keys
            self.collection_info = res
            return res
        else:
            return []

    def strftime_by_modestr(self, datetime_, mode_str):
        """按照指定字符串模式进行日期识别"""
        modes = [
            '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y%m%d%H%M%S',
            '%Y-%m-%d', '%Y%m%d'
        ]

        for mode in modes:
            try:
                datetime.datetime.strptime(mode_str, mode)
                return datetime.datetime.strftime(datetime_, mode)
            except ValueError:
                pass

    def get_data(self, db_name, collection_name, flt={}, limit=100):
        """ 从数据库获取数据 """
        try:
            if limit:
                d = list(self.db_client[db_name][collection_name].find(
                    flt, {"_id": 0}, limit=limit))
            else:
                d = list(self.db_client[db_name][collection_name].find(
                    flt, {"_id": 0}))
            return d
        except Exception as e:
            self.write_log(f"查询失败{db_name}.{collection_name}:{flt}")
            return []


if __name__ == '__main__':
    ee = EventEngine()
    me = MainEngine(ee)
    engine = DbViewEngine(me, ee)
    engine.update_db_info()
    print(engine.get_db_names())
    print(engine.db_info["连接地址"])
    print(engine.db_info["连接端口"])
    print(engine.db_info["连接状态"])
    print(engine.db_info["占用空间"])
    for db in engine.get_db_names():
        for coll in engine.get_collections_by_dbname(db):
            print(f"{db}:{coll}")
    print(engine.get_data("quantaxis", "stock_min"))
    print(engine.get_collection_info("quantaxis", "stock_day"))

    info = [
        f"{k}:{v}" for k, v in engine.get_collection_info(
            "quantaxis", "stock_day").items()
    ]
    print(info)
    now = datetime.date.today()
    print(engine.strftime_by_modestr(now, "2019-10-10 12:00:00"))
    d = engine.find_sample("quantaxis", "index_day")
    print(engine.strftime_by_modestr(now, d["date"]))
    ee.stop()
