# -*- coding: utf-8 -*-
"""第一题 业务操作（不包含初始化，可反复执行）

1. 查询张老师授课且状态 OPEN 的课程，输出课程编号 / 名称 / 章节数量（用 $size 现算）
2. 把本人第 01 门课程的 CH02 章节标题改为 Redis基础与应用-<S>（局部更新）
3. 新增 CH03 章节（hours = 2 + A），连续执行两次仍只保留一个 CH03
4. 核验结果并解释为何用局部更新
"""
import json
import unicodedata

from pymongo import MongoClient

SID = "12408060102"
S, A = 2, 2               # S = 学号末两位 02 -> 2；A = S mod 3 = 2
DB_NAME = "exam_" + SID
MONGO_URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"
COURSE1 = "COURSE-" + SID + "-01"

NEW_CH02_TITLE = "Redis基础与应用-%d" % S
CH03 = {"chapterId": "CH03", "title": "Redis高级操作", "hours": 2 + A}


def dwidth(s):
    """字符串显示宽度：东亚宽字符（中文）按 2 列算"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in str(s))


def pad(s, width):
    s = str(s)
    return s + " " * max(0, width - dwidth(s))


def title(text):
    """单行小标题，输出更紧凑"""
    print()
    head = "== " + text + " "
    print(head + "=" * max(0, 78 - dwidth(head)))


def main():
    client = MongoClient(MONGO_URI)
    courses = client[DB_NAME].courses

    # ---------- 1. 查询 ----------
    title("1. 查询：teacher=张老师 且 status=OPEN 的课程")
    rows = list(courses.aggregate([
        {"$match": {"teacher": "张老师", "status": "OPEN"}},
        {"$project": {
            "_id": 0,
            "课程编号": "$_id",
            "课程名称": "$title",
            "章节数量": {"$size": "$chapters"},     # 由数组现算，不写死
        }},
        {"$sort": {"课程编号": 1}},
    ]))
    print(pad("课程编号", 26) + pad("课程名称", 14) + "章节数量")
    print("-" * 50)
    for r in rows:
        print(pad(r["课程编号"], 26) + pad(r["课程名称"], 14) + str(r["章节数量"]))
    print("命中 %d 门课程" % len(rows))

    # ---------- 2. 局部更新 CH02 标题 ----------
    title("2. 修改 %s 中 CH02 的标题为 %s" % (COURSE1, NEW_CH02_TITLE))
    res = courses.update_one(
        {"_id": COURSE1, "chapters.chapterId": "CH02"},
        {"$set": {"chapters.$.title": NEW_CH02_TITLE}},   # 位置操作符 $：只改命中的那个数组元素
    )
    print("update_one -> acknowledged=%s matchedCount=%d modifiedCount=%d"
          % (res.acknowledged, res.matched_count, res.modified_count))
    doc = courses.find_one({"_id": COURSE1})
    print("更新后的课程文档：")
    print(json.dumps(doc, ensure_ascii=False, indent=2))

    # ---------- 3. 幂等新增 CH03 ----------
    title("3. 新增 CH03（hours = 2 + A = %d），连续执行两次" % CH03["hours"])
    flt = {"_id": COURSE1, "chapters.chapterId": {"$ne": "CH03"}}   # 已存在则条件不成立，不再 push
    for i in (1, 2):
        res = courses.update_one(flt, {"$push": {"chapters": CH03}})
        print("第 %d 次 update_one -> matchedCount=%d modifiedCount=%d"
              % (i, res.matched_count, res.modified_count))

    # ---------- 4. 核验 ----------
    title("4. 核验")
    doc = courses.find_one({"_id": COURSE1})
    chs = doc["chapters"]
    ch02_title = [c["title"] for c in chs if c["chapterId"] == "CH02"][0]
    ch03_num = len([c for c in chs if c["chapterId"] == "CH03"])
    print("(1) 修改后 CH02 的标题      ：%s" % ch02_title)
    print("(2) 两次新增后 CH03 的数量  ：%d" % ch03_num)
    print("(3) 最终章节总数            ：%d（%s）"
          % (len(chs), "、".join(c["chapterId"] for c in chs)))
    keep = doc["teacher"] == "张老师" and doc["status"] == "OPEN"
    print("(4) teacher=%s，status=%s → 是否保持原值：%s"
          % (doc["teacher"], doc["status"], "是" if keep else "否"))
    print()
    print("说明：本题每一步只改动 chapters 数组中命中的那一个元素（$set 配合位置操作符 $），")
    print("      或只追加一个元素（$push 配合 chapterId $ne CH03 的条件），其余字段与其他章节")
    print("      在服务端原样保留。若改为“读整个文档 → 客户端改 → 整文档 replaceOne”，")
    print("      并发时两次读到的都是旧文档，后写者会覆盖前者的修改（丢失更新），")
    print("      而章节数组一旦变长，每次都要整段传输，代价也远高于局部更新。")
    client.close()


if __name__ == "__main__":
    main()
