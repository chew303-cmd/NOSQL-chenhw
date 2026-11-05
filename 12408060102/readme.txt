《NoSQL数据库》上机测验  提交说明
=====================================

一、个人信息
    学号：12408060102
    姓名：张三（按测验要求，源码中涉及姓名处统一使用“张三”）
    个人参数：S = 2（学号末两位 02）
              A = S mod 3 = 2
              B = S mod 4 = 2
              C = S mod 5 = 2
    个人数据库：exam_12408060102
    Redis 键前缀：exam:12408060102:

二、运行环境
    操作系统：Windows 10（10.0.19045，64 位）
    Python：3.14.3
    依赖：redis==8.1.0、pymongo==4.19.0       安装：pip install redis pymongo

    MongoDB：8.x，单节点副本集 rs0，地址 mongodb://127.0.0.1:27017/?replicaSet=rs0
             （第二题的事务依赖副本集，standalone 模式下 startTransaction 会报错）
    Redis：Redis 5.0.14.1（Windows 兼容版），3 主 3 从集群，端口 50102—50107
           客户端连接 127.0.0.1:50102 后自动发现整个集群；因 Redis 5.0 不支持 RESP3，
           代码中显式指定 protocol=2。

三、各题执行方法
    task1   MongoDB 课程信息查询与维护
            cd task1
            python init_db.py     # 初始化（重建 courses 集合）
            python task1.py       # 业务操作（可重复执行，不重新初始化）

    task2   MongoDB 原子扣减与事务验证
            cd task2
            python init_db.py     # 初始化（库存 Stock=7，清空 orders）
            python task2.py       # 原子扣减 / 结果判断 / 事务 / 四场景测试

    task3   Redis 学习信息与排行榜
            cd task3
            python task3.py       # Hash、Set、Sorted Set、会话过期、类型核验

    task4   Redis Pipeline 与性能比较（选做）
            cd task4
            python task4.py       # N=1202、Q=100，逐条写入 vs 普通 Pipeline

    运行结果：各目录下 result.txt（task1/task2 的初始化输出在 out_init.txt），
             与提交的实验报告中的截图一一对应。

四、目录结构
    12408060102/
    ├─ readme.txt
    ├─ task1/   init_db.py  task1.py  result.txt  out_init.txt  说明.md
    ├─ task2/   init_db.py  task2.py  result.txt  out_init.txt  说明.md
    ├─ task3/   task3.py    result.txt  说明.md
    └─ task4/   task4.py    result.txt  说明.md
