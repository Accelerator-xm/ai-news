import json
from typing import Any

import redis.asyncio as redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0


# 创建 Redis 的连接对象
redis_client = redis.Redis(
    host=REDIS_HOST,  # Redis 服务器的主机地址
    port=REDIS_PORT,  # Redis 端口号
    db=REDIS_DB,  # Redis 数据库编号，0~15
    decode_responses=True  # 是否将字节数据解码为字符串
)


# 原数据可能是字符串、列表、字典
# 在redis里存储的都是字符串："{}"、"[]"
# 封装两个读取方法

async def get_cache(key: str):
    """读取：字符串"""
    try:
        return await redis_client.get(key)
    except Exception as e:
        print(f"获取缓存失败：{e}")
        return None


async def get_json_cache(key: str):
    """读取：列表或字典"""
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)  # 反序列化
        return None
    except Exception as e:
        print(f"获取 JSON 缓存失败：{e}")
        return None

 
async def set_cache(key: str, value: Any, expire: int = 3600):
    """设置缓存 setex(key, expire, value)"""

    try:
        if isinstance(value, (dict, list)):
            # 转字符串再存
            value = json.dumps(value, ensure_ascii=False)  # 序列化
        await redis_client.setex(key, expire, value)
        return True
    except Exception as e:
        print(f"设置缓存失败：{e}")
        return False
