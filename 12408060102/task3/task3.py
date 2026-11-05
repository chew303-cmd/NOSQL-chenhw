# -*- coding: utf-8 -*-
"""第三题 Redis 学习信息与排行榜

个人参数：S = 2，A = 2，C = 2 → 本人成绩 = 70 + C = 72
所有键统一使用前缀 exam:<SID>:
"""
import time
import unicodedata

from redis.cluster import RedisCluster

SID = "12408060102"
S, A, C = 2, 2, 2
PREFIX = "exam:%s:" % SID
K_STU = PREFIX + "student"
K_CHAPTERS = PREFIX + "chapters"
K_RANK = PREFIX + "rank"
K_SESSION = PREFIX + "session"

CLASS_NAME = "大数据管理与应用2024级"
COURSE_ID = "COURSE-%s-01" % SID
ME = "Student:" + SID
SCORE = 70 + C                      # 72

SEED = {"host": "127.0.0.1", "port": 50102}     # 任一节点即可，客户端会自动发现整个集群


def dwidth(s):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in str(s))


def pad(s, width):
    s = str(s)
    return s + " " * max(0, width - dwidth(s))


def title(text):
    """单行小标题，输出更紧凑"""
    print()
    head = "== " + text + " "
    print(head + "=" * max(0, 80 - dwidth(head)))


def main():
    # protocol=2：本实验的 Redis 5.0 不支持 RESP3 的 HELLO 命令
    rc = RedisCluster(host=SEED["host"], port=SEED["port"], decode_responses=True, protocol=2)
    print("第三题 Redis 学习信息与排行榜   键前缀：%s" % PREFIX)

    # ---------- 1. 学生信息（Hash） ----------
    title("1. 学生信息维护（Hash：%s）" % K_STU)
    rc.delete(K_STU)
    rc.hset(K_STU, mapping={
        "studentId": SID,
        "name": "张三",
        "className": CLASS_NAME,
        "courseId": COURSE_ID,
        "status": "learning",
    })
    print("创建后 HGETALL：", rc.hgetall(K_STU))

    rc.hset(K_STU, "status", "completed")
    print("修改后 HGET name    ：", rc.hget(K_STU, "name"))
    print("修改后 HGET status  ：", rc.hget(K_STU, "status"))
    full = rc.hgetall(K_STU)
    print("修改后 HGETALL      ：", full)
    print("其他字段是否保留    ：%s（studentId=%s，className=%s，courseId=%s）"
          % ("是" if full.get("studentId") == SID and full.get("className") == CLASS_NAME
             else "否", full.get("studentId"), full.get("className"), full.get("courseId")))

    # ---------- 2. 已完成章节（Set） ----------
    title("2. 已完成章节记录（Set：%s）" % K_CHAPTERS)
    rc.delete(K_CHAPTERS)
    for ch in ("CH01", "CH02", "CH02", "CH03"):
        rc.sadd(K_CHAPTERS, ch)
        print("提交 %s 后 → 已完成章节数量 = %d" % (ch, rc.scard(K_CHAPTERS)))
    print("最终全部章节：", sorted(rc.smembers(K_CHAPTERS)))
    print("CH02 是否已完成：%d；CH04 是否已完成：%d"
          % (rc.sismember(K_CHAPTERS, "CH02"), rc.sismember(K_CHAPTERS, "CH04")))
    before = rc.scard(K_CHAPTERS)
    rc.sadd(K_CHAPTERS, "CH02")
    after = rc.scard(K_CHAPTERS)
    print("再次提交 CH02：数量 %d → %d，%s"
          % (before, after, "未增加，重复提交被去重" if before == after else "增加了（异常）"))

    # ---------- 3. 成绩排行榜（Sorted Set） ----------
    title("3. 成绩排行榜（Sorted Set：%s）" % K_RANK)
    rc.delete(K_RANK)
    rc.zadd(K_RANK, {ME: SCORE, "demo:01": 85, "demo:02": 90, "demo:03": 60, "demo:04": 80})
    print("初始成绩：", rc.zrevrange(K_RANK, 0, -1, withscores=True))
    top3 = rc.zrevrange(K_RANK, 0, 2, withscores=True)
    print("按分数从高到低前 3 名：")
    for i, (m, sc) in enumerate(top3, start=1):
        print("    第%d名  %-18s %.0f 分" % (i, m, sc))

    rc.zincrby(K_RANK, 20, ME)
    print("本人成绩 +20 后：%.0f 分" % rc.zscore(K_RANK, ME))
    top3 = rc.zrevrange(K_RANK, 0, 2, withscores=True)
    print("再次输出前 3 名：")
    for i, (m, sc) in enumerate(top3, start=1):
        print("    第%d名  %-18s %.0f 分" % (i, m, sc))

    my_score = rc.zscore(K_RANK, ME)
    my_rank = rc.zrevrank(K_RANK, ME)          # 降序位置，从 0 开始
    print("本人更新后：分数 = %.0f，名次 = 第%d名（降序位置 %d）"
          % (my_score, my_rank + 1, my_rank))

    # ---------- 4. 会话生命周期（String + TTL） ----------
    title("4. 会话生命周期（String：%s，有效期 5 秒）" % K_SESSION)
    rc.delete(K_SESSION)
    rc.set(K_SESSION, "sess-%s-%d" % (SID, int(time.time())), ex=5)
    sess_type = rc.type(K_SESSION)             # 过期前先记录类型（第 5 小题要用）
    print("创建后 GET  ：", rc.get(K_SESSION))
    print("创建后 TTL  ：%d 秒" % rc.ttl(K_SESSION))
    print("等待 6 秒 ……")
    time.sleep(6)
    print("6 秒后 EXISTS：%d" % rc.exists(K_SESSION))
    print("6 秒后 TTL   ：%d（-2 表示键已不存在）" % rc.ttl(K_SESSION))
    print("过期验证    ：%s" % ("通过（键在 5 秒后自动消失）" if rc.exists(K_SESSION) == 0 else "未通过"))

    # ---------- 5. 数据类型核验 ----------
    title("5. 数据类型核验")
    rows = [
        (K_STU, "Hash", "学生信息是多字段对象，Hash 可以按字段读写、保留其他字段"),
        (K_CHAPTERS, "Set", "已完成章节需要去重且要判断成员是否存在，Set 天然唯一并支持集合运算"),
        (K_RANK, "Sorted Set", "成绩需要按分数排序取前 N 名，Sorted Set 按 score 自动排序"),
        (K_SESSION, "String", "会话标识是一个整体值，只需整体读写并配合过期时间"),
    ]
    print(pad("键", 30) + pad("实际类型", 14) + "选择理由")
    print("-" * 96)
    for key, expect, why in rows:
        actual = sess_type if key == K_SESSION else rc.type(key)
        print(pad(key, 30) + pad(actual, 14) + why)
    print("（会话键在过期前已检查过类型：TYPE = %s；过期后再查会返回 none）" % sess_type)
    rc.close()


if __name__ == "__main__":
    main()
