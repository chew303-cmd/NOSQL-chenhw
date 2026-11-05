# -*- coding: utf-8 -*-
"""第二题 初始化代码（与业务操作 task2.py 分开执行）

重建 inventory（库存 = Stock = 5 + C）并清空 orders。
task2.py 在每个测试场景开始前也会单独重置这两个集合，因此本脚本只需执行一次。
"""
from pymongo import MongoClient

SID = "12408060102"
C = 2                       # C = S mod 5，S = 2
STOCK = 5 + C               # 7
BOOK_ID = "BOOK-" + SID
DB_NAME = "exam_" + SID
MONGO_URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    db.inventory.replace_one(
        {"_id": BOOK_ID},
        {"_id": BOOK_ID, "title": "NoSQL数据库教材", "stock": STOCK},
        upsert=True,
    )
    db.orders.delete_many({})
    print("[init] 数据库：%s" % DB_NAME)
    print("[init] inventory：%s" % db.inventory.find_one({"_id": BOOK_ID}))
    print("[init] orders   ：%d 条" % db.orders.count_documents({}))
    client.close()


if __name__ == "__main__":
    main()
