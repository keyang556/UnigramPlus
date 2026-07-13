# Unigram Plus

* 作者：Kostya Gladkiy（Ukraine）
* [Telegram 频道](https://t.me/unigramPlus)
* Telegram：@unigramPlus
* 赞助链接：[https://unigramplus.diaka.ua/donate](https://unigramplus.diaka.ua/donate)
* PayPal：gladkiy.kostya@gmail.com

UnigramPlus 让 Unigram 更容易通过 NVDA 操作。它提供许多快捷键，可快速移到聊天列表、消息列表、聊天文件夹、个人资料和搜索结果，也改善消息、媒体、语音消息、通话和删除操作的读出与焦点行为。

## 主要改进
* 改善投票、链接、附加媒体、语音消息和通话消息的读出。
* 在聊天列表和消息列表中减少不必要的控件描述，让焦点读出更简洁。
* 在打开或下载文件按钮上读出文件名称和大小；在音频播放按钮上读出名称和时长。
* 录制、发送和取消语音消息时可使用文本或声音通知，且焦点会保留在原位置。
* 使用空格键打开消息中的媒体后，关闭查看器时会尽量回到先前的焦点。
* 进度条读出可设置为全部、仅限文件上传和下载，或完全关闭。
* 可在设置中选择空白消息编辑字段按上方向键时的操作。

## 将 Unigram 界面切换为简体中文
1. 按下「Open navigation menu」（打开导航菜单）按钮。
2. 进入「Settings」（设置）。
3. 进入「Language」（语言）。
4. 在语言列表中选择「简体中文, Chinese (Simplified)」，接着按一次 `Tab`，再按一次空格键即可应用。

## 自定义声音
UnigramPlus 的声音文件位于插件的 `appModules\media` 文件夹。请打开 NVDA 设置 > UnigramPlus，按下 **打开 UnigramPlus 声音文件夹**。若要自定义声音，请将替换用的 WAV 文件放入此文件夹，并使用与要取代的声音完全相同的文件名，然后重启 NVDA 或重新加载插件。插件更新可能会还原内置声音，建议另外保留自定义文件备份。

<!-- shortcut-table-start -->
## 快捷键清單

> “类别”栏中，“UnigramPlus”表示插件提供的快捷键，“Unigram”表示 Unigram 内置的快捷键。

> [!TIP]
> 您可以通过“NVDA 菜单 → 选项 → 输入手势”自定义 UnigramPlus 快捷键。

### 切换聊天

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **Ctrl+Tab / Alt+Arrow Up / Ctrl+Page Up** | Unigram | 下一个聊天 |
| **Ctrl+Shift+Tab / Alt+Arrow Down / Ctrl+Page Down** | Unigram | 上一个聊天 |
| **ALT+1** | UnigramPlus | 将焦点移到聊天列表 |
| **ALT+2** | UnigramPlus | 将焦点移到已打开聊天中的最后一条消息 |
| **ALT+3** | UnigramPlus | 将焦点移到“未读消息”标签 |
| **ALT+4** | UnigramPlus | 将焦点移到聊天文件夹列表 |
| **ALT+5** | UnigramPlus | 将焦点移到已打开的个人资料 |
| **ALT+6** | UnigramPlus | 将焦点移到群组话题列表 |
| **ALT+D** | UnigramPlus | 将焦点移到编辑字段。如果焦点已在编辑字段中，按下快捷键后会移回先前所在的位置 |
| **ALT+End** | UnigramPlus | 转到末尾 |

### 搜索

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **Ctrl+E** | Unigram | 搜索聊天 |
| **Ctrl+F** | Unigram | 搜索当前聊天中的消息 |
| **ALT+I** | UnigramPlus | 转到搜索结果列表 |
| **F3** | UnigramPlus | 转到下一个搜索结果 |
| **Shift+F3** | UnigramPlus | 转到上一个搜索结果 |

### 输入区中选中的文本

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **Ctrl+Z** | Unigram | 撤消 |
| **Ctrl+Y** | Unigram | 重做 |
| **Ctrl+X** | Unigram | 剪切 |
| **Ctrl+C** | Unigram | 复制 |
| **Ctrl+V** | Unigram | 粘贴 |
| **Ctrl+A** | Unigram | 全选 |
| **Ctrl+B** | Unigram | 粗体 |
| **Ctrl+I** | Unigram | 斜体 |
| **Ctrl+K** | Unigram | 创建链接 |
| **Ctrl+Shift+X** | Unigram | 删除线 |
| **Ctrl+Shift+M** | Unigram | 等宽 |
| **Ctrl+Shift+P** | Unigram | 遮罩 |
| **Ctrl+Shift+N** | Unigram | 清除格式 |

### 聊天文件夹

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **Ctrl+1** | Unigram | 第一个文件夹（所有聊天） |
| **Ctrl+2** | Unigram | 第二个文件夹 |
| **Ctrl+3** | Unigram | 第三个文件夹 |
| **Ctrl+4** | Unigram | 第四个文件夹 |
| **Ctrl+5** | Unigram | 第五个文件夹 |
| **Ctrl+6** | Unigram | 第六个文件夹 |
| **Ctrl+7** | Unigram | 第七个文件夹 |
| **Ctrl+8** | Unigram | 第八个文件夹 |
| **Ctrl+9** | Unigram | 归档 |

### 消息操作

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **Space** | UnigramPlus | 播放或停止焦点所在的语音或视频消息，或打开消息附加的媒体 |
| **Ctrl+C** | UnigramPlus | 如果消息包含文本则复制消息；如果焦点位于链接上，则复制该链接 |
| **ALT+Q** | UnigramPlus | 如果当前消息中包含“即时预览”按钮，则按下它 |
| **ALT+Delete** | UnigramPlus | 删除消息或聊天 |
| **Shift+Delete** | UnigramPlus | 为双方删除消息或聊天 |
| **Ctrl+ALT+C** | UnigramPlus | 打开评论 |
| **Enter** | UnigramPlus | 回复消息 |
| **ALT+F** | UnigramPlus | 转发消息 |
| **Backspace** | UnigramPlus | 编辑消息 |
| **ALT+Shift+R** | UnigramPlus | 将聊天标记为已读 |
| **Ctrl+Space** | UnigramPlus | 切换到选择模式 |
| **Unassigned** | UnigramPlus | 文件另存为... |
| **Unassigned** | UnigramPlus | 置顶消息或聊天 |
| **Left Arrow** | UnigramPlus | 读出原始消息，也就是所回复的消息 |
| **Right Arrow** | UnigramPlus | 移到焦点消息中的下一个媒体附件 |
| **ALT+C** | UnigramPlus | 在弹出窗口中显示消息文本 |
| **ALT+W** | UnigramPlus | 读出消息的发送或接收时间，以及回应列表。连按两次可切换是否读出此信息。 |
| **NVDA+Ctrl+0-9** | UnigramPlus | 读出最近十条消息之一；1 是最新消息，0 是第十条消息 |
| **Ctrl+Shift+A** | UnigramPlus | 按下“附加文件”按钮 |
| **Ctrl+N** | UnigramPlus | 按下“新建对话”按钮 |
| **Arrow Up** | Unigram | 编辑上一条已发送消息 |
| **Ctrl+Arrow Up** | Unigram | 回复上一条已发送消息 |
| **Esc / Alt+Arrow Left** | Unigram | 返回 |
| **Alt+Arrow Right** | Unigram | 前进 |

### 语音消息与媒体

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **ALT+P** | UnigramPlus | 播放或暂停当前正在播放的语音消息 |
| **ALT+S** | UnigramPlus | 提高或降低语音消息播放速度 |
| **ALT+E** | UnigramPlus | 关闭音频播放器 |
| **NVDA+ALT+R** | UnigramPlus | 将语音消息转换为文本 |
| **Ctrl+ALT+Right Arrow** | UnigramPlus | 快进语音消息 |
| **Ctrl+ALT+Left Arrow** | UnigramPlus | 倒回语音消息 |

### 录制消息

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **Ctrl+R** | Unigram | 开始录制 |
| **Ctrl+R (again)** | Unigram | 发送录制内容 |
| **Ctrl+D** | Unigram | 停止录制 |
| **Space (while recording) / Ctrl+P** | Unigram | 暂停录制 |
| **Ctrl+R** | UnigramPlus | 开始或停止录制语音消息 |
| **Ctrl+D** | UnigramPlus | 按一次取消语音消息录制；按两次更改录制通知方式 |

### 通话

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **Ctrl+Home** | Unigram | 接听来电 |
| **Ctrl+End** | Unigram | 拒绝来电 |
| **Ctrl+Page Up** | Unigram | 切换相机 |
| **Ctrl+Page Down** | Unigram | 切换麦克风 |
| **ALT+Shift+C** | UnigramPlus | 如果是联系人则拨打电话，如果是群组则进入语音聊天 |
| **ALT+Shift+V** | UnigramPlus | 按下视频通话按钮 |
| **ALT+Y** | UnigramPlus | 接听来电 |
| **ALT+N** | UnigramPlus | 如果有来电则按下“拒绝通话”按钮；如果正在通话则按下“结束通话”按钮；如果语音聊天处于活动状态则离开语音聊天。 |
| **ALT+A** | UnigramPlus | 按下“麦克风静音或取消静音”按钮 |
| **ALT+V** | UnigramPlus | 按下“启用或禁用摄像头”按钮 |

### 其他快捷键

| 快捷键 | 类别 | 操作 |
|---|---|---|
| **Ctrl+0** | Unigram | 我的收藏 |
| **Ctrl+W** | Unigram | 关闭当前窗口 |
| **Ctrl+Q** | Unigram | 关闭 Unigram（仅限主窗口） |
| **Ctrl+Shift+Y** | Unigram | 更改状态 |
| **ALT+T** | UnigramPlus | 读出已打开聊天的名称和状态 |
| **ALT+M** | UnigramPlus | 打开导航菜单 |
| **ALT+Shift+P** | UnigramPlus | 打开当前聊天的个人资料 |
| **ALT+L** | UnigramPlus | 启用当前聊天中新消息的自动读出 |
| **ALT+H** | UnigramPlus | 显示所有 UnigramPlus 快捷键列表 |
| **ALT+U** | UnigramPlus | 切换进度条读出 |
| **ALT+Shift+L** | UnigramPlus | 将广播数据复制到剪贴板 |
| **NVDA+ALT+U** | UnigramPlus | 打开 UnigramPlus 设置窗口 |
<!-- shortcut-table-end -->

## 版本变更

### 版本 5.5.9

* 新增富文本消息支持。富文本消息获得焦点时会被朗读，并可按 Alt+C 在浏览窗口中打开。
* 富文本消息中的链接和混合内容会被保留，且可在浏览窗口中激活链接。

### 版本 5.5.8

* 修复自动更新：现在会从 GitHub 安全获取版本，并在安装前验证下载的插件。

* 修复与 Unigram 12.7 的兼容性，此前有多个快捷键和语音提示失效。
* 投票消息会再次朗读问题和答案选项。
* 论坛话题列表会再次朗读最后一条消息的预览。
* 一对一通话中，静音麦克风（ALT+A）、开启或关闭摄像头（ALT+V）和结束通话（ALT+N）的快捷键可再次使用。
* ALT+End 会再次移动到聊天中最新的消息。

### 版本 5.5.7

* 将快捷键区段重新整理为分类表格，并整合 Unigram 与 UnigramPlus 快捷键。
* 录制语音或视频消息时，NVDA 现在会朗读「正在录制语音消息」或「正在录制视频消息」并念出经过时间，而不再是「Tn voice message」。

### 版本 5.5.6

* 修复在群组或频道个人资料中，按 Tab 越过名称后，身份按钮被读成“Identity root”的问题；现在会读出聊天名称与成员数。
* control+C 不再被处理两次：焦点在链接上时复制链接，其他情况则交由 Unigram 复制消息。

### 版本 5.5.5

* 回复或编辑消息时，现在会在消息输入字段中提示“回复”或“编辑”，而不是平常的消息输入提示。
* 修复在关闭应用程序后、对方停止输入后，或离开聊天后，输入声音有时仍持续播放的问题；现在只要已打开的聊天中没有人在输入，声音就会立即停止。
* 更新缅甸语本地化。

### 版本 5.5.4

* 修复聊天文件夹未读数量变化被不必要读出的问题，例如“所有聊天 535”。文件传输进度现在只会在 Unigram 的上传和下载控件中读出，且会忽略非 Unigram 窗口。
* 修复与 Telegram Desktop NVDA 插件的冲突；只有检测到当前运行的应用程序是 Unigram 时，才会启用 UnigramPlus。
* 在 UnigramPlus 设置中新增打开内置声音文件夹的按钮，方便用户以相同文件名替换自定义 WAV 声音文件。
* 在消息编辑字段的上方向键操作中，新增“移到最后获得焦点的消息”选项。
* 繁体中文重新整理并独立为 zh_TW，另新增简体中文 zh_CN。

### 版本 5.5.3

* 新增文件上传和下载进度的自动读出。进度条读出设置新增“仅在上传和下载时”选项，并设为默认值。ALT+U 现在会在关闭、仅限上传下载、读出全部进度条三种状态间切换。
* 更新自述文件和翻译。

### 版本 5.5.2

* 更新自述文件和翻译。
* 更改输入中提示声音。

### 版本 5.5.1

* 修复移到群组话题列表的快捷键 ALT+6。
* 新增输入中提示音：当对方在已打开聊天中输入时循环播放，停止输入后结束播放。
