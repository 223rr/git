"""最简单的内存版 todo CLI，支持 add / list / done / delete。

用法：
    python todo.py add "买牛奶"
    python todo.py list
    python todo.py done 1
    python todo.py delete 1
    python todo.py            # 交互模式，所有命令共用同一份内存数据
"""

import sys

todos: list[dict] = []


def add(text: str) -> None:
    todos.append({"text": text, "done": False})
    print(f"added: {text}")


def show() -> None:
    if not todos:
        print("(empty)")
        return
    for i, item in enumerate(todos, 1):
        mark = "x" if item["done"] else " "
        print(f"{i}. [{mark}] {item['text']}")


def position(rest: list[str]) -> int | None:
    """把命令行里的 1 起始序号转成列表下标，非法时返回 None。"""
    if len(rest) == 1 and rest[0].isdigit() and 1 <= int(rest[0]) <= len(todos):
        return int(rest[0]) - 1
    return None


def done(rest: list[str]) -> None:
    i = position(rest)
    if i is None:
        print("usage: done <number>")
        return
    todos[i]["done"] = True
    print(f"done: {todos[i]['text']}")


def delete(rest: list[str]) -> None:
    i = position(rest)
    if i is None:
        print("usage: delete <number>")
        return
    print(f"deleted: {todos.pop(i)['text']}")


def run(command: str, rest: list[str]) -> None:
    if command == "add":
        text = " ".join(rest).strip()
        if text:
            add(text)
        else:
            print("usage: add <text>")
    elif command == "list":
        show()
    elif command == "done":
        done(rest)
    elif command == "delete":
        delete(rest)
    else:
        print(f"unknown command: {command!r} (supported: add, list, done, delete)")


def main() -> None:
    if len(sys.argv) == 1:
        print("命令: add <文本> / list / done <编号> / delete <编号>，输入 quit 退出")
    args = sys.argv[1:]
    if args:
        run(args[0], args[1:])
        return

    while True:
        try:
            line = input("todo> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        command, _, rest = line.strip().partition(" ")
        if command in ("quit", "exit"):
            break
        if command:
            run(command, rest.split())


if __name__ == "__main__":
    main()
