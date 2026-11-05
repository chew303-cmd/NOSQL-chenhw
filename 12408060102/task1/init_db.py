# -*- coding: utf-8 -*-
"""第一题 初始化代码（与业务操作 task1.py 分开执行）

重建 exam_<SID>.courses 三个课程文档。重复执行本脚本会先清空再重建，
业务操作脚本 task1.py 不包含任何初始化逻辑，因此可以反复运行验证重复执行效果。
"""
from pymongo import MongoClient

SID = "12408060102"
DB_NAME = "exam_" + SID
MONGO_URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"

COURSES = [
    {
        "_id": "COURSE-" + SID + "-01",
        "title": "NoSQL数据库",
        "teacher": "张老师",
        "status": "OPEN",
        "chapters": [
            {"chapterId": "CH01", "title": "MongoDB基础", "hours": 2},
            {"chapterId": "CH02", "title": "Redis基础", "hours": 2},
        ],
    },
    {
        "_id": "COURSE-" + SID + "-02",
        "title": "数据库原理",
        "teacher": "张老师",
        "status": "CLOSED",
        "chapters": [
            {"chapterId": "CH01", "title": "关系模型", "hours": 2},
        ],
    },
    {
        "_id": "COURSE-" + SID + "-03",
        "title": "机器学习",
        "teacher": "李老师",
        "status": "OPEN",
        "chapters": [
            {"chapterId": "CH01", "title": "分类", "hours": 2},
            {"chapterId": "CH02", "title": "聚类", "hours": 2},
        ],
    },
]


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    db.courses.delete_many({})
    db.courses.insert_many(COURSES)
    print("[init] 数据库：%s  集合：courses" % DB_NAME)
    print("[init] 已写入 %d 门课程：" % db.courses.count_documents({}))
    for d in db.courses.find({}, {"title": 1, "teacher": 1, "status": 1, "chapters": 1}).sort("_id", 1):
        print("       %-28s %-8s %-12s %-6s 章节数=%d"
              % (d["_id"], d["title"], d["teacher"], d["status"], len(d["chapters"])))
    client.close()


if __name__ == "__main__":
    main()
