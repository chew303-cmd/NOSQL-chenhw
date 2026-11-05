# -*- coding: utf-8 -*-
"""第四题（选做）Redis Pipeline 与性能比较

个人参数：S = 2，C = 2 → N = 1000 + 100*C + S = 1202，每批最多 Q = 100
"""
import math
import time
import unicodedata

from redis.cluster import RedisCluster

SID = "12408060102"
S, C = 2, 2
PREFIX = "exam:%s:" % SID
N = 1000 + 100 * C + S          # 1202
Q = 100                         # 每批最多 100 条

SEED = {"host": "127.0.0.1", "port": 50102}     # 任一节点即可，客户端会自动发现整个集群


def dwidth(s):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in str(s))


def pad(s, width):
    s = str(s)
    return s + " " * max(0, width - dwidth(s))


def key_seq(i):
    return PREFIX + "seq:%d" % i


def key_pipe(i):
    return PREFIX + "pipe:%d" % i


def value(i):
    return "value-%s-%d" % (SID, i)


def run_sequential(rc):
    """方案甲：逐条写入，每条收到返回后再发下一条（不使用 Pipeline / 多线程 / 异步）"""
    t0 = time.perf_counter()
    for i in range(1, N + 1):
        rc.set(key_seq(i), value(i))
    return time.perf_counter() - t0


def run_pipeline(rc):
    """方案乙：普通 Pipeline，每批最多 Q 条，一批执行并取回全部结果后再提交下一批"""
    batches = math.ceil(N / Q)
    last = 0
    t0 = time.perf_counter()
    for b in range(batches):
        lo = b * Q + 1
        hi = min((b + 1) * Q, N)
        pipe = rc.pipeline(transaction=False)       # 普通（非事务）Pipeline
        for i in range(lo, hi + 1):
            pipe.set(key_pipe(i), value(i))
        pipe.execute()                              # 一批全部返回后才进入下一批
        last = hi - lo + 1
    return time.perf_counter() - t0, batches, last


def verify(rc, keyfn):
    """完整性核验：分批 GET 全部 N 个键，检查存在且值正确"""
    ok = 0
    for base in range(1, N + 1, 200):
        rng = list(range(base, min(base + 200, N + 1)))
        pipe = rc.pipeline(transaction=False)
        for i in rng:
            pipe.get(keyfn(i))
        for i, v in zip(rng, pipe.execute()):
            if v == value(i):
                ok += 1
    return ok


def main():
    # protocol=2：本实验的 Redis 5.0 不支持 RESP3 的 HELLO 命令
    rc = RedisCluster(host=SEED["host"], port=SEED["port"], decode_responses=True, protocol=2)
    print("第四题（选做）Redis Pipeline 与性能比较")
    print("参数：S=%d C=%d → N = 1000+100*C+S = %d，每批 Q = %d" % (S, C, N, Q))
    print("键前缀：%s（方案甲 seq:<i>，方案乙 pipe:<i>，i 从 1 到 %d）" % (PREFIX, N))

    rc.delete(*[key_seq(i) for i in range(1, N + 1)])
    rc.delete(*[key_pipe(i) for i in range(1, N + 1)])

    print()
    print("方案甲：逐条写入（每条等返回）……")
    t_a = run_sequential(rc)
    a_ok = verify(rc, key_seq)
    print("        完成，核验 %d/%d 个键存在且值正确" % (a_ok, N))

    print("方案乙：普通 Pipeline，每批最多 %d 条……" % Q)
    t_b, batches, last = run_pipeline(rc)
    b_ok = verify(rc, key_pipe)
    print("        完成，核验 %d/%d 个键存在且值正确" % (b_ok, N))

    print()
    rows = [
        ("命令总数", str(N)),
        ("Pipeline批次数", str(batches)),
        ("最后一批数量", str(last)),
        ("方案甲耗时(ms)", "%.2f" % (t_a * 1000)),
        ("方案乙耗时(ms)", "%.2f" % (t_b * 1000)),
    ]
    print(pad("指标", 22) + "程序输出值")
    print("-" * 40)
    for k, v in rows:
        print(pad(k, 22) + v)

    print()
    print("结论：方案乙（Pipeline）明显更快，约 %.1f 倍（%.2f ms vs %.2f ms）。"
          % (t_a / t_b, t_b * 1000, t_a * 1000))
    print("原因：方案甲每条命令都要等一次网络往返（RTT），%d 条就是 %d 次往返；" % (N, N))
    print("      方案乙把 %d 条命令压成 %d 批，往返次数降到 %d 次，"
          % (N, batches, batches))
    print("      命令本身的执行时间被摊平，剩下的主要是服务端处理与网络带宽。")
    print("      如果两者差异不明显，可能是因为：数据量太小或 RTT 本来就极低（本机回环）、")
    print("      批大小设置过小、客户端每条命令后仍做了额外同步、或服务端成为瓶颈（单线程处理已饱和）。")
    rc.close()


if __name__ == "__main__":
    main()
