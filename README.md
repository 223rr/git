# todo

一个最简单的内存版命令行 todo 程序，只用 Python 标准库，无第三方依赖。

## 用法

```bash
py todo.py add "买牛奶"
py todo.py list
py todo.py done 1
py todo.py delete 1
```

不带参数运行会进入交互模式，所有命令共用同一份内存数据：

```text
$ py todo.py
todo> add 买牛奶
added: 买牛奶
todo> add 写代码
added: 写代码
todo> done 2
done: 写代码
todo> list
1. [ ] 买牛奶
2. [x] 写代码
todo> quit
```

## 命令

| 命令 | 说明 |
| --- | --- |
| `add <文本>` | 新增一条待办 |
| `list` | 列出全部待办，`[x]` 表示已完成 |
| `done <编号>` | 把第 N 条标记为已完成 |
| `delete <编号>` | 删除第 N 条 |
| `quit` / `exit` | 退出交互模式（仅交互模式可用） |

编号从 1 开始，越界或非数字会提示 `usage`。

## 说明

- 数据只存在内存中，进程退出即清空。所以单独执行 `add` 后再执行 `list` 只会看到 `(empty)`；要在同一次运行里查看结果，请用交互模式。
- 需要 Python 3.10+（注解中使用了 `int | None` 写法）。
