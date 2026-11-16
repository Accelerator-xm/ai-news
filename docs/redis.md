# Redis 与缓存

缓存保存可以重建的数据副本，用于减少重复查询或计算。数据库通常保留事实数据，缓存可以过期、淘汰或暂时不可用；是否允许读到短暂旧值，应由业务需要决定。

## 存储结构与序列化

Redis 支持 String、Hash、List、Set、Sorted Set 等结构。把 Python 字典写入 Redis String 时，需要先编码成字符串或字节；这个选择不代表 Redis 只能存字符串。

```python
import json
from typing import Any
import redis.asyncio as redis

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

async def get_json_cache(key: str):
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"获取 JSON 缓存失败：{e}")
        return None

async def set_cache(key: str, value: Any, expire: int = 3600):
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        await redis_client.setex(key, expire, value)
        return True
    except Exception as e:
        print(f"设置缓存失败：{e}")
        return False
```

`decode_responses=True` 只把返回字节解码为字符串，不负责把 JSON 解析成字典。写入时 json.dumps，读取时 json.loads，得到的是通用 Python 数据，不是数据库映射对象。[异步 redis-py](https://redis.io/docs/latest/develop/clients/redis-py/async/)

这两个缓存工具方法将读取错误降级为 None、写入错误降级为 False，调用方可以继续从数据库获取数据。setex 同时写值和设置过期秒数；传入字典或列表前，其中的时间等值仍需要转换为 JSON 兼容类型。

数据库返回 datetime，JSON 通常保存 ISO 字符串，因此缓存命中后类型可能不同。新闻输出模型可以复用于这个转换边界：写缓存时使用内部字段名，生成 API 响应时启用别名。

```python
from schemas.news import NewsItemBase

data = NewsItemBase(
    id=1,
    title="理解缓存",
    category_id=2,
    views=0,
    publish_time="2026-01-01T12:00:00",
)
cached = data.model_dump(mode="json", by_alias=False)
restored = NewsItemBase.model_validate(cached)
payload = restored.model_dump(mode="json", by_alias=True)
```

cached 中是 `publish_time` 字符串，restored 的对应属性恢复为 datetime，payload 中则是 `publishTime` 字符串。`model_validate()` 完成类型解析，`model_dump(mode="json")` 完成 JSON 兼容转换，两者职责不同。

`News(**cached)` 只是构造新的 ORM 实例，不会查询数据库、恢复 Session 跟踪状态，也不会按 Pydantic 规则把时间字符串解析成 datetime。接口可以接收数据模型或字典，关键是两条读取路径遵守同一个输出契约。

## 旁路缓存与键设计

旁路缓存由应用主动管理：先查缓存，未命中再查数据库，将结果放入缓存后返回。缓存不是自动监听数据库变化的副本，写入和失效逻辑都需要应用明确处理。组合前面的工具方法时，数据库加载函数应返回 JSON 兼容的字典或列表：

```python
async def read_with_cache(key, load_from_database, expire=300):
    cached = await get_json_cache(key)
    if cached is not None:
        return cached

    data = await load_from_database()
    await set_cache(key, data, expire)
    return data
```

这里使用 `cached is not None`，所以已缓存的 `[]` 可以被正常读取。get_json_cache 检查的是解析前的非空字符串 `"[]"`，而业务层的 `if cached:` 检查的是解析后的空列表，两者判断结果不同。把空列表、空字典和不存在混在一起，会导致空结果反复回源。是否缓存空结果可以按数据特点决定，通常也需要明确过期时间。

键应覆盖所有影响查询结果的参数。例如新闻列表使用 `news_list:{category_id}:{page}:{size}`，新闻详情使用 `news:detail:{news_id}`；如果增加排序、搜索词或用户权限过滤，键也需要反映这些差异，否则不同查询可能错误共享同一份结果。

TTL 限制一份缓存最多保留多久，不保证这段时间数据一直最新。过期时间长可以减少回源，但会增加旧数据停留时间；给不同数据设置不同 TTL 或适当随机抖动，可以减少集中失效的概率，但不能解决全部可用性问题。

## 更新与一致性

常见写入顺序是先完成数据库事务，再删除受影响的缓存，让下次读取重建。先删缓存再更新数据库，可能让中间的读取重新缓存旧值；但先更新再删也不构成数据库与 Redis 之间的原子事务。

如果写库成功而删缓存失败，旧缓存可能继续被使用，直到被补偿删除或过期。简单展示数据通常允许短暂延迟；必须满足更强保证时，需要额外的一致性设计，不能只把“用了事务”当成跨系统强一致。

浏览量等统计值可以在数据库中原子增加，而详情缓存仍保留旧快照。这表示写入正确但展示有延迟。可以接受统计快照、单独读取计数或在响应中处理当前增量，选择取决于页面需要的准确程度。

缓存穿透通常指持续查询不存在的数据，缓存击穿指热点键失效后大量请求同时回源，缓存雪崩指大量键或缓存服务集中失效。它们触发条件不同，空结果缓存、热点回源互斥、TTL 抖动和请求控制也分别解决不同问题，不需要为所有场景一次性加入全部机制。

## 连接、原子操作与故障

Redis 客户端通常复用连接池，使用异步命令时需要 await，应用退出时还要关闭客户端和相关资源。连接池可以共享，不代表持有中间状态的 pipeline 或事务对象适合随意在并发任务间共享。

单条 INCR 之类的命令可以原子修改一个值；先 GET，在 Python 中加一，再 SET 则是多步操作，可能丢失并发更新。pipeline 主要用于减少网络往返，是否具有事务语义取决于客户端配置和实际命令，不能只因为批量发送就认为全部动作不可分割。

缓存异常时可以按业务选择回退数据库，但应区分未命中、数据解析失败和服务连接失败，避免完全失去错误信号。高流量下全部回源还会增加数据库压力，缓存可选不等于它失效时系统一定仍能承受原有流量。

缓存的输出形状和序列化边界见 [FastAPI](fastapi.md)，数据库对象状态见 [SQLAlchemy](sqlalchemy.md)。
