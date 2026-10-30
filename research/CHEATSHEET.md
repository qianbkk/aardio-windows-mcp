# aardio 速查表

## 0. Hello World
```aardio
import console;
console.log("Hello World");
console.pause();
```

## 1. 基础语法

### 1.1 变量
```aardio
var a = 1;          // 动态类型
var s = "中文";      // 默认 UTF-8
var t = {1, 2, 3};  // 数组/表
var m = {x=1; y=2}; // map
var n = null;       // 空值
```

### 1.2 控制流
```aardio
if (a > 0) {
    // ...
} elseif (a < 0) {
    // ...
} else {
    // ...
}

for (i=1; 10; 1) {  // 起始; 终止; 步长
    io.print(i);
}

for (k, v in m) {  // 遍历表
    io.print(k, v);
}

while (cond) { }

do { } while (cond);
```

### 1.3 函数
```aardio
var add = function(a, b) {
    return a + b;
}
```

### 1.4 字符串操作
```aardio
var s = "Hello World"
#s                    // 长度
string.upper(s)
string.lower(s)
string.find(s, "World")
string.trim(s)
string.split(s, " ")
string.format("%d %s", 1, "x")
string.startWith(s, "Hello")
```

### 1.5 表 (map + array 二合一)
```aardio
var t = {1, 2, 3}            // 数组
var m = {a=1; b=2}           // map
var t2 = table.array(1,2,3)  // 纯数组
table.push(t, 4)              // 追加
#t                            // 长度
```

## 2. 窗口程序

### 2.1 模板
```aardio
import win.ui;
/*DSG{{*/
var winform = win.form(text="标题";right=600;bottom=400)
winform.add(
btn={cls="button";text="按钮";left=10;top=10;right=100;bottom=40}
)
/*}}*/

winform.btn.oncommand = function(id, event) {
    winform.msgbox("点了!");
}

winform.show();
win.loopMessage();
```

### 2.2 常用控件
| 控件 | cls | 说明 |
|---|---|---|
| 按钮 | button | 按钮 |
| 文本 | static | 显示文字 |
| 输入框 | edit | 单/多行编辑 |
| 列表 | listbox | 简单列表 |
| 表格 | listview | 多列列表 |
| 树 | treeview | 树形 |
| 下拉 | combobox | 下拉 |
| 标签 | tab | 标签页 |
| 工具条 | toolbar | |
| 状态栏 | statusbar | |
| 菜单 | menu | |
| 托盘 | trayicon | 任务栏图标 |
| 复选 | checkbox | |
| 单选 | radiobutton | |
| 自定义 | custom | 自绘 |

### 2.3 常用事件
```aardio
winform.button.oncommand = function(id, event) { }
winform.edit.onOk = function() { }  // 回车
winform.edit.onChange = function() { }
winform.onClose = function(hwnd, message, wParam, lParam) { }
winform.onMouseDown = function() { }
```

### 2.4 弹窗
```aardio
winform.msgbox("内容", "标题", 0x40/*MB_ICONINFORMATION*/);
```

## 3. 控件位置 (DSG 格式)
```
left, top, right, bottom (像素)
dl, dr, dt, db = 1      // 锚定 (左/右/上/下)
align = "center"        // 对齐
transparent = 1          // 透明
edge = 1                 // 边框
multiline = 1            // 多行
z = N                    // Z 序
```

## 4. 文件操作

### 4.1 文件读写
```aardio
import fsys.file;
var f = fsys.file("/path/to/file", "w");
f.write("内容");
f.close();

var f = fsys.file("/path/to/file", "r");
var content = f.read();
f.close();
```

### 4.2 路径
```aardio
io.localpath("C:/Users/")    // 反斜杠处理
io.fullpath("relative")      // 转绝对
io.exist(path)               // 存在?
io.isdir(path)               // 是目录?
io.size(path)                // 字节数
```

### 4.3 目录
```aardio
import fsys.dir;
for (filename in fsys.dir("/path")) {
    io.print(filename);
}
```

### 4.4 INI 配置
```aardio
import fsys.ini;
var ini = fsys.ini("/config.ini")
ini.set("section", "key", "value")
var v = ini.get("section", "key")
ini.save()
```

## 5. 网络

### 5.1 HTTP
```aardio
import inet.http;
var http = inet.http();
var resp, err = http.get("https://example.com");
io.print(resp);
```

### 5.2 REST 链式
```aardio
import web.rest;
var api = web.rest("https://api.github.com")
var resp, err = api.users.aardio.get()
```

### 5.3 下载文件
```aardio
import inet.down;
var down = inet.down({
    url = "https://...";
    savePath = "/local/file";
    onError = function(err) { io.print(err); };
    onEnd = function() { io.print("done"); };
})
```

## 6. 进程/系统

### 6.1 进程
```aardio
import process;
process.execute("notepad.exe", "C:/file.txt", 0/*隐藏*/);
var pid = process.run("cmd.exe /c echo hello");
```

### 6.2 全局热键
```aardio
var hkId = winform.reghotkey(
    function() { /* 触发 */ },
    0x0002/*_MOD_CONTROL*/, 'S'#
);
winform.unreghotkey(hkId);
```

### 6.3 剪贴板
```aardio
import win.clipboard;
win.clipboard.write("hello");
var s = win.clipboard.read();
```

### 6.4 键盘模拟
```aardio
import key;
key.press("Ctrl+C");
key.sendString("hello");  // 模拟输入
```

## 7. 多线程

### 7.1 后台执行
```aardio
import thread;
thread.invoke(
    function(winform) {
        // 后台干的事
        sleep(5000);
        winform.msgbox("done");
    },
    winform
);
```

### 7.2 真线程
```aardio
var t = thread(function() {
    while(true) {
        sleep(1000);
        io.print("tick");
    }
})
t.resume();
```

## 8. 数据库

### 8.1 SQLite
```aardio
import sqlite;
var db = sqlite("/data.db")
db.exec("CREATE TABLE t (id INTEGER, name TEXT);")
db.exec("INSERT INTO t VALUES (1, 'x');")
for (row in db.query("SELECT * FROM t")) {
    io.print(row.id, row.name);
}
```

## 9. 编码/序列化

### 9.1 JSON
```aardio
import JSON;
var j = JSON.stringify({a=1; b=[1,2,3]})
var o = JSON.parse(j)
```

### 9.2 时间
```aardio
import time;
var t = time.now();          // 当前时间戳 (ms)
var d = time(t, "%Y-%m-%d %H:%M:%S");
```

## 10. 工具速记

| 想做什么 | 用什么 |
|---|---|
| 窗口程序 | `import win.ui;` |
| 网页界面 | `import web.view;` |
| HTTP | `import inet.http;` 或 `import web.rest;` |
| 多线程 | `import thread;` |
| 文件 | `import fsys.file;` |
| 配置 | `import fsys.ini;` |
| 数据库 | `import sqlite;` |
| 加密 | `import crypt;` |
| 压缩 | `import sevenZip;` |
| AI | `import web.rest.aiChat;` |
| 键盘 | `import key;` |
| 鼠标 | `import mouse;` |
| 剪贴板 | `import win.clipboard;` |
| 取色 | `import mouse.cursor;` |
| 截图 | `import win.clip;` |
| 串口 | `import serialport;` |
| JSON | `import JSON;` |
| 时间 | `import time;` |
| 进程 | `import process;` |
| 7Z | `import sevenZip;` |
| COM | `import com;` |
| DLL | `raw.loadDll("xxx.dll")` |
| WebSocket | `import web.socket;` |

## 11. 发布
- IDE 内按 F7
- 选"发布 → EXE 文件"
- 选项:
  - "EXE + 文件夹" (含源码,可调试)
  - "字节码 EXE" (不可还原,**推荐商用**)
  - "单文件 EXE" (资源内嵌,极致便携)
