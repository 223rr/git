# todo

一个只用 Python 标准库的极简命令行 todo 程序：添加、查看、完成、删除任务，数据保存在 `todos.json`，**退出后重新运行数据仍然存在**。

## 环境要求

- Python 3.10+（用到了 `list[dict]`、`int | None` 这些写法）

## 快速开始

无需安装依赖，直接运行：

```bash
py todo.py add "买牛奶"
py todo.py list
py todo.py done 1
py todo.py delete 2
```

Windows 上 `python` 通常是应用商店别名，建议用 `py`；其他平台用 `python3`。

## 命令

| 命令 | 作用 |
| --- | --- |
| `add <文本>` | 添加任务，文本可以用空格分隔多个词 |
| `list` | 查看全部任务，`[x]` 表示已完成 |
| `done <编号>` | 把第 N 条标记为已完成 |
| `delete <编号>` | 删除第 N 条任务 |
| `quit` / `exit` | 退出交互模式（仅交互模式可用） |

编号从 1 开始；编号越界或不是数字时只打印 `usage`，不会改动数据。

## 交互模式

不带参数运行会进入交互模式，所有命令共用同一份数据，适合连续操作：

```text
$ py todo.py
命令: add <文本> / list / done <编号> / delete <编号>，输入 quit 退出
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

## 数据保存

- 数据文件是脚本同目录下的 `todos.json`，每次增删改后立即写入。
- 写入采用“临时文件 + 原子替换”，中途中断不会留下半个文件。
- 文件不存在、为空或内容损坏时，程序按空列表处理，不会崩溃。
- `todos.json` 和 `todos.json.tmp` 已加入 `.gitignore`，不会被误提交。

数据结构很简单：

```json
[
  { "text": "买牛奶", "done": false },
  { "text": "写代码", "done": true }
]
```

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `todo.py` | 全部实现，约 130 行 |
| `todos.json` | 运行时生成的数据文件 |
| `.gitignore` | 忽略运行产物与 `node_modules` |

## 版本

当前版本 **v1.0.0**。
