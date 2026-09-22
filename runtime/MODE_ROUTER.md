# Mode Router｜双运行时总控

系统只有两种业务模式：

```text
LEARN
WRITE
```

不得同时激活。

## 状态机

```text
IDLE
 ├─> LEARN ──publish──> IDLE
 └─> WRITE ───────────> IDLE
```

禁止：

```text
LEARN + WRITE
WRITE -> 偷偷学习 -> WRITE
LEARN -> 顺手续写正文
```

## 中间件
Middleware 不属于第三种业务模式。
它是常驻桥接层：

- LEARN 发布知识给 Middleware
- WRITE 把当前状态变化交给 Middleware
- Middleware 只从 published snapshot 检索
- Middleware 不创造新学习成果
