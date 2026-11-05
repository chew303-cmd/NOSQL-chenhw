# -*- coding: utf-8 -*-
"""第二题 业务操作：原子扣减 + 事务 + 场景测试（不含初始化，可反复执行）

个人参数：S = 2，A = 2，C = 2 → Stock = 5 + C = 7，Buy = 1 + A = 3
"""
import unicodedata

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

SID = "12408060102"
S, A, C = 2, 2, 2
STOCK = 5 + C               # 7
BUY = 1 + A                 # 3
BOOK_ID = "BOOK-" + SID
DB_NAME = "exam_" + SID
MONGO_URI = "mongodb://127.0.0.1:27017/?replicaSet=rs0"


class StockNotEnough(Exception):
    """库存不足或教材不存在"""


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


def decrement(client, buy=BUY, session=None, break_update=False):
    """把“库存条件检查 + 扣减”合并成一次单文档原子更新。

    返回 (状态码, 说明, 扣减后的文档)。三种状态完全由数据库的返回结果决定：
      OK        —— 返回了更新后的文档（扣减成功）
      NO_STOCK  —— 返回 None（不满足 _id 与 stock>=buy 条件，未发生扣减）
      DB_ERROR  —— 抛出 PyMongoError（数据库执行异常）
    """
    db = client[DB_NAME]
    flt = {"_id": BOOK_ID, "stock": {"$gte": buy}}          # 同时筛选教材编号和库存条件
    upd = {"$inc": {"stock": "NaN"}} if break_update else {"$inc": {"stock": -buy}}
    try:
        doc = db.inventory.find_one_and_update(flt, upd, session=session,
                                              return_document=ReturnDocument.AFTER)
    except PyMongoError as exc:
        brief = str(exc).split(", full error")[0][:62]      # 只保留关键信息，便于阅读
        return "DB_ERROR", "%s: %s" % (type(exc).__name__, brief), None
    if doc is None:
        return "NO_STOCK", "库存不足或教材不存在，未执行扣减", None
    return "OK", "扣减成功，扣减后库存 = %d" % doc["stock"], doc


def order(client, request_id, force_error=False):
    """订购：库存扣减与订单插入使用同一 session、同一事务。

    只有事务提交成功才返回 True；扣减失败或中途异常一律回滚并返回 False。
    """
    db = client[DB_NAME]
    session = client.start_session()
    try:
        session.start_transaction()
        status, msg, _doc = decrement(client, session=session)
        if status != "OK":
            raise StockNotEnough(msg)                      # 扣减失败 → 不生成订单
        if force_error:
            raise RuntimeError("模拟故障：库存已扣减、订单插入前主动抛出异常")
        db.orders.insert_one({
            "_id": request_id,
            "bookId": BOOK_ID,
            "studentId": SID,
            "quantity": BUY,
        }, session=session)                                 # 同一事务
        session.commit_transaction()                        # 提交成功才算订购成功
        return True, "事务提交成功"
    except Exception as exc:                                # noqa: BLE001
        if session.in_transaction:
            session.abort_transaction()                     # 异常 → 回滚
        return False, "%s: %s" % (type(exc).__name__, exc)
    finally:
        session.end_session()


def reset(client, stock=STOCK):
    """每个场景开始前单独重置 inventory 与 orders"""
    db = client[DB_NAME]
    db.inventory.replace_one({"_id": BOOK_ID},
                             {"_id": BOOK_ID, "title": "NoSQL数据库教材", "stock": stock},
                             upsert=True)
    db.orders.delete_many({})


def snapshot(client):
    db = client[DB_NAME]
    doc = db.inventory.find_one({"_id": BOOK_ID}) or {}
    return doc.get("stock"), db.orders.count_documents({})


def run_scenario(client, name, init_stock, attempts, force_error=False,
                 expect_ok=None):
    reset(client, init_stock)
    ok = fail = 0
    for i in range(attempts):
        good, _msg = order(client, "REQ-%s-%s-%02d" % (SID, name, i + 1), force_error)
        ok += 1 if good else 0
        fail += 0 if good else 1
    stock, orders = snapshot(client)
    passed = (ok == expect_ok) and (stock == init_stock - ok * BUY) and (orders == ok)
    return {"name": name, "init": init_stock, "buy": BUY, "ok": ok, "fail": fail,
            "stock": stock, "orders": orders, "pass": passed}


def main():
    client = MongoClient(MONGO_URI)
    print("第二题 MongoDB 原子扣减与事务验证")
    print("参数：S=%d A=%d C=%d  Stock=5+C=%d  Buy=1+A=%d  bookId=%s"
          % (S, A, C, STOCK, BUY, BOOK_ID))

    # ---------- 1. 原子扣减 ----------
    title("1. 原子扣减：find_one_and_update 一次完成“条件检查 + 扣减”")
    reset(client)
    print("filter = {\"_id\": \"%s\", \"stock\": {\"$gte\": %d}}   update = {\"$inc\": {\"stock\": -%d}}"
          % (BOOK_ID, BUY, BUY))
    status, msg, doc = decrement(client)
    print("数据库返回：%s（%s）" % (msg, status))
    print("当前库存：%s，订单数：%s" % snapshot(client))

    # ---------- 2. 根据返回结果判断 ----------
    title("2. 判断操作结果（三种分支都由数据库返回值决定）")
    reset(client)
    head2 = pad("场景", 12) + pad("状态码", 11) + "说明"
    print(head2)
    print("-" * dwidth(head2))
    cases = [
        ("库存充足", BUY, False),
        ("库存不足", BUY - 1, False),
        ("执行异常", BUY, True),
    ]
    for label, stock, broken in cases:
        reset(client, stock)
        st, m, _ = decrement(client, break_update=broken)
        print("%s %s %s" % (pad(label, 12), pad(st, 10), m))
    print("判定依据：返回文档=成功；返回 None=库存不足/教材不存在；抛 PyMongoError=执行异常。")
    print("（不看程序执行到哪一行，只看数据库这一次操作的返回结果。）")

    # ---------- 3. 事务 ----------
    title("3. 事务：库存扣减 + 订单插入，同一 session、同一事务")
    reset(client)
    ok, msg = order(client, "REQ-%s-T1-demo" % SID)
    print("正常订购 order(forceError=False) -> %s（%s），库存=%s，订单=%s"
          % (ok, msg, snapshot(client)[0], snapshot(client)[1]))
    reset(client)
    ok, msg = order(client, "REQ-%s-ERR-demo" % SID, force_error=True)
    print("故障订购 order(forceError=True)  -> %s（%s）" % (ok, msg))
    print("回滚后库存=%s（应仍为 %d），订单=%s（应为 0）"
          % (snapshot(client)[0], STOCK, snapshot(client)[1]))

    # ---------- 4. 系统测试 ----------
    title("4. 系统测试：每场景独立重置，实际结果与程序计算的预期值比较")
    scenarios = [
        run_scenario(client, "T1", STOCK, 1, expect_ok=1),
        run_scenario(client, "T2", BUY - 1, 1, expect_ok=0),
        run_scenario(client, "T3", STOCK, 1, force_error=True, expect_ok=0),
        run_scenario(client, "T4", STOCK, STOCK // BUY + 1, expect_ok=STOCK // BUY),
    ]
    head = "%-14s %-9s %-7s %-5s %-5s %-9s %-7s %s" % (
        "场景", "初始库存", "购买量", "成功", "失败", "最终库存", "订单数", "核验")
    print(head)
    print("-" * dwidth(head))
    labels = {"T1": "T1 正常订购", "T2": "T2 库存不足", "T3": "T3 中途异常", "T4": "T4 连续购买"}
    for r in scenarios:
        print("%s %s %s %s %s %s %s %s" % (
            pad(labels[r["name"]], 14), pad(r["init"], 9), pad(r["buy"], 7),
            pad(r["ok"], 5), pad(r["fail"], 5), pad(r["stock"], 9),
            pad(r["orders"], 7), "PASS" if r["pass"] else "FAIL"))
    print("说明：T4 共发起 ⌊%d/%d⌋+1 = %d 次订购，预期成功 %d 次、剩余 %d 本。"
          % (STOCK, BUY, STOCK // BUY + 1, STOCK // BUY, STOCK % BUY))

    # ---------- 5. 结果解释 ----------
    title("5. 结果解释")
    print("(1) 为什么单次扣减具有原子性，仍然需要事务？")
    print("    单文档扣减只能保证“库存”这一个文档不被并发改坏；而订购业务要同时改两个文档")
    print("    （inventory 与 orders）。如果扣减成功、插入订单时进程崩溃或抛异常，库存少了却")
    print("    没有订单，账就对不上。事务把两次写入绑成一个整体：要么都提交，要么都回滚。")
    print("(2) forceError 测试验证了什么？")
    print("    T3 在库存扣减之后、订单插入之前主动抛异常。回滚后库存仍是 %d、订单数为 0，"
          % STOCK)
    print("    证明事务确实撤销了已经执行的扣减，说明“扣减成功但订单没落库”这种半成品状态")
    print("    不会留在数据库里；同时也说明结论必须以“提交成功”为准，而不是以扣减返回成功为准。")
    client.close()


if __name__ == "__main__":
    main()
