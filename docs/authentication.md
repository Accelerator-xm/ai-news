# 密码与身份认证

身份认证回答“请求者是谁”，授权回答“这个身份能操作什么”。密码用于建立身份，Token 或会话用于让后续请求延续登录状态。两者承担不同职责，不能把一个接口返回了 Token 就等同于权限已经处理完整。

## 密码哈希与验证

密码通常保存为专门的密码哈希，不保存明文，也不依靠能够解密的密文恢复原密码。验证时，将输入密码按存储值记录的参数进行验证，结果只需要表示匹配或不匹配。

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

stored = get_hash_password("example-password")
print(verify_password("example-password", stored))
print(verify_password("wrong-password", stored))
```

同一个密码两次 hash 通常得到不同字符串，因为每次自动生成随机盐。盐让相同密码不产生相同存储值，并降低预计算表的复用效果。盐本身不需要保密，bcrypt 会将算法版本、计算成本、盐和结果编码在同一个字符串中。

verify 从旧哈希读取原来的算法参数和盐，所以可以验证用户输入。直接执行 `hash(输入) == 旧哈希` 不正确，因为新的 hash 通常采用新的盐。bcrypt 中的 cost 是对数成本参数，提高一级通常约增加一倍计算工作，不是把密码加密某个固定次数。[bcrypt](https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html)

普通 SHA-256 计算快，适合许多完整性用途，但不适合单独用来存密码。专门的密码哈希会增加批量猜测的成本；新系统可以优先考虑 Argon2id，并根据服务资源调整成本参数。具体算法选择应考虑现有数据兼容和库支持，而不是认为任意“加盐 SHA”都等价于密码哈希。[密码存储](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

bcrypt 的输入边界通常是 72 字节，而不是 72 个字符。中文的 UTF-8 编码可能占多个字节；不同版本的库可能拒绝或截断超长输入，因此应明确字节长度策略，不能依赖默默截断。密码哈希本身是计算操作，在 async 路由中直接调用仍会占用事件循环线程，必要时放入工作线程。

## 哈希策略与更新

哈希字符串包含算法与成本信息，因此旧数据可以在用户下一次成功登录时逐步升级。普通 verify 只验证，不会自动修改数据库；`deprecated="auto"` 也不意味着自动持久化新哈希。

```python
valid, replacement = pwd_context.verify_and_update(plain_password, stored_hash)
if valid and replacement is not None:
    user.password_hash = replacement
```

是否返回 replacement 取决于配置中的算法弃用与参数策略。收到新哈希后，仍需要由业务事务保存。密码原文只应在必要的校验过程中短暂使用，日志和响应都不应包含它或数据库中的密码哈希。[CryptContext](https://passlib.readthedocs.io/en/stable/lib/passlib.context.html#hash-migration)

## Token 与会话

HTTP 请求本身不保存“上一次已经登录”的记忆。常见做法是登录成功后生成难以猜测的随机 Token，服务端保存它对应的用户与过期时间，客户端在后续请求中携带 Token。

```python
import secrets
from datetime import datetime, timedelta, timezone

token = secrets.token_urlsafe(32)
expires_at = datetime.now(timezone.utc) + timedelta(days=7)
```

Token 不必包含用户信息，随机字符串加服务端查询已经可以构成会话机制。客户端通常通过请求头发送：

```http
Authorization: Bearer <token>
```

服务端需要确认 Token 是否存在、是否过期、是否已撤销，再找到当前用户。Token 代表持有者的能力，不能因为内容看不出用户 ID 就认为泄露无影响。HTTPS 保护传输，过期和撤销处理生命周期，它们不是同一层机制。

一个用户只保存一行 Token 时，再次登录替换旧值，会使之前的 Token 失效。多设备独立会话则需要多条会话记录及各自的撤销方式；只清除浏览器中的 Token 不会让服务端现存 Token 自动失效。

JWT 是另一种携带声明的 Token 格式，常见签名形式保证完整性，并不加密载荷。验证时还需要检查签名、算法、有效期及实际采用的签发方和受众规则。随机会话令牌与 JWT 各有状态管理方式，不能仅因 JWT 能解码就把它当成不安全，也不能仅因有签名就不检查其他声明。

## 在接口中使用当前身份

认证逻辑适合封装为依赖，让需要登录的路由接收当前用户。下面的字典仅说明查找流程，实际身份数据可以来自数据库或其他会话存储。

```python
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI()
sessions = {"example-token": {"id": 1, "username": "alice"}}

def current_user(
    authorization: Annotated[str | None, Header()] = None,
):
    scheme, _, token = (authorization or "").partition(" ")
    user = sessions.get(token) if scheme.lower() == "bearer" else None
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="登录凭据无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.get("/me")
async def me(user: Annotated[dict, Depends(current_user)]):
    return user
```

将缺失请求头声明为可选，再主动返回 401，可以与“凭据无效”统一处理；声明为必填 Header 时，完全缺失通常先进入请求校验，得到 422。

认证完成后，还要在查询和修改中限定数据归属。例如删除收藏，应同时按当前 user.id 和收藏对应的资源 ID 过滤，不能让前端通过任意 user_id 决定操作谁的数据。已登录但无权访问通常使用 403，是否对外隐藏资源存在性还需要接口有一致约定。
