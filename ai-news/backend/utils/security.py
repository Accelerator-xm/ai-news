"""
passlib + bcrypt 实现的密码哈希（加密）工具，不是对称加密、不能解密

核心思想：不存明文密码，只存哈希摘要；登录时对比摘要，而不是反向解密
"""

# passlib 密码哈希管理库，封装了 bcrypt、argon2、sha256_crypt 等多种密码哈希，自动加盐、版本、算法迁移
from passlib.context import CryptContext

# 创建密码上下文
# - schemes=["bcrypt"]：指定使用 crypt 哈希算法
# - deprecated="auto"：自动处理旧版本、过时的哈希方案，有兼容旧哈希的能力
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt 算法特点：
# 1. 自带盐（salt）：盐编码在哈希字符串中，随机生成salt，同一明文每次调用生成的哈希都不一样
# 2. 自适应算力（cost 代价因子）：
#   - 默认 cost=12，代表计算哈希要循环 2¹² 次；cost 越大，计算越慢、暴力破解越难
#   - 可以在 CryptContext 里配置 `bcrypt__rounds=12`
# 3. 专门为密码设计，慢哈希：极大增加黑客暴力破解成本
# 4. 密码长度上限：bcrypt 原始最多接受 72 字节的密码，超过部分会被截断

# 其他算法
# - bcrypt：简单、兼容性好，适合大多数项目
# - argon2id：目前密码哈希竞赛冠军，安全性更高
# - sha256 + 自己加盐：不推荐，容易写 bug，而且是快哈希



def get_hash_password(password: str):
    """密码加密：明文 → bcrypt哈希串"""
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """密码验证: verify 返回值是布尔型"""
    return pwd_context.verify(plain_password, hashed_password)



