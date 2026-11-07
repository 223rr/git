# 属性与生活2 存档修改器

通过 MIUI 本地备份改存档，**不改 APK、不需要 root、保留进度**。

## 原理

```
手机导出备份 zip
  └─ <游戏>.bak  =  MIUI 头 + "ANDROID BACKUP\n5\n0\nnone\n" + tar
        tar 里 apps/<包名>/sp/<包名>.v2.playerprefs.xml  ← 明文存档
```

工具原地改写这个 PlayerPrefs XML（保持字节长度不变），重新打包后推回手机，
再用系统「备份与恢复 → 恢复」写回应用数据。

## 首次准备

1. 手机开启 USB 调试并连接电脑
2. 下载 adb（只需一次）：

```powershell
py cheat.py setup-adb
```

3. 在手机上手动做一次本地备份：设置 → 备份与恢复 → 本地备份 → 只勾选「属性与生活2」，
   **不要设置密码**。备份文件位于 `/sdcard/MIUI/backup/AllBackup/`，拷到电脑。

## 用法

```powershell
# 1. 查看当前数值
py cheat.py inspect backup.zip

# 2. 生成修改后的备份（默认全满：金钱 999999999、属性 9999）
py cheat.py patch backup.zip -o patched.zip

# 自定义
py cheat.py patch backup.zip -o patched.zip --money 99999999 --attrs 5000
py cheat.py patch backup.zip -o patched.zip --set "Year=1" --set "Cham=5000"
py cheat.py patch backup.zip -o patched.zip --no-defaults --set "Money=100000"

# 3. 推送到手机并打开恢复页面
py cheat.py push patched.zip --open

# 或者一条龙（patch + push + 打开页面）
py cheat.py apply backup.zip --money 999999999
```

手机端：备份与恢复 → 恢复 → 选择最新备份 → 勾选「属性与生活2」→ 恢复。

## 支持的字段

默认会改：`Money` `MyBalance` `Coding` `Art` `Music` `Action` `Cham` `BasicCham`
`Healthy` `Plan` `Fans` `MaxCoding` `MaxArt` `MaxMusic` `MaxAction` `MaxPlan`

`--attrs N` 同时设置 `Coding/Art/Music/Action/Cham/BasicCham/Healthy/Plan/Fans`。

## 注意

- 备份文件**不能加密**，否则无法解析
- 改写后 XML 与原文件等长（压缩空白 + 尾部空格填充），保证 tar 结构不变
- 游戏版本不同字段可能变化，先 `inspect` 确认
- 还原：用原始备份再恢复一次即可
- 修改前建议保留原始备份 zip

## 目录

- `cheat.py` —— 主程序，仅依赖 Python 标准库
- `backups/` —— 原始与修改后的备份留底（已在 .gitignore 中，不会提交）
- `tools/` —— `setup-adb` 下载的 platform-tools（不提交）
