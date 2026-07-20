# Unigram Plus

* 作者：Kostya Gladkiy（Ukraine）
* [Telegram 頻道](https://t.me/unigramPlus)
* Telegram：@unigramPlus
* 贊助連結：[https://unigramplus.diaka.ua/donate](https://unigramplus.diaka.ua/donate)
* PayPal：gladkiy.kostya@gmail.com

UnigramPlus 讓 Unigram 更容易以 NVDA 操作。它提供許多快速鍵，可快速移到聊天清單、訊息清單、聊天資料夾、個人資料與搜尋結果，也改善訊息、媒體、語音訊息、通話與刪除操作的讀出與焦點行為。

## 主要改善
* 改善投票、連結、附加媒體、語音訊息與通話訊息的讀出。
* 在聊天清單與訊息清單中減少不必要的控制項描述，讓焦點讀出更乾淨。
* 在開啟或下載檔案按鈕上讀出檔案名稱與大小；在音訊播放按鈕上讀出名稱與長度。
* 錄製、傳送與取消語音訊息時可使用文字或音效通知，且焦點會留在原位置。
* 使用空格鍵開啟訊息中的媒體後，關閉檢視器時會盡量回到先前的焦點。
* 進度列讀出可設定為全部、只限檔案上傳與下載，或完全關閉。
* 可在設定中選擇空白訊息編輯欄位按上方向鍵時的動作。

## 將 Unigram 介面切換為正體中文
1. 按下「Open navigation menu」（開啟導覽功能表）按鈕。
2. 進入「Settings」（設定）。
3. 進入「Language」（語言）。
4. 在語言清單中選擇「繁體中文, Chinese (Traditional)」，接著按一次 `Tab`，再按一次空格鍵即可套用。

## 自訂音效
UnigramPlus 的音效檔案位於附加元件的 `appModules\media` 資料夾。請開啟 NVDA 設定 > UnigramPlus，按下 **開啟 UnigramPlus 音效資料夾**。若要自訂音效，請將替換用的 WAV 檔案放入此資料夾，並使用與要取代的音效完全相同的檔名，然後重新啟動 NVDA 或重新載入附加元件。附加元件更新可能會還原內建音效，建議另外保留自訂檔案備份。

<!-- shortcut-table-start -->
## 快速鍵清單

> 「類別」欄位中，「UnigramPlus」表示附加元件提供的快速鍵，「Unigram」表示 Unigram 內建的快速鍵。

> [!TIP]
> 您可以透過「NVDA 功能表 → 偏好 → 輸入手勢」自訂 UnigramPlus 快速鍵。

### 切換聊天

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **Ctrl+Tab / Alt+Arrow Up / Ctrl+Page Up** | Unigram | 下一個聊天 |
| **Ctrl+Shift+Tab / Alt+Arrow Down / Ctrl+Page Down** | Unigram | 上一個聊天 |
| **ALT+1** | UnigramPlus | 將焦點移到聊天清單 |
| **ALT+2** | UnigramPlus | 將焦點移到已開啟聊天中的最後一則訊息 |
| **ALT+3** | UnigramPlus | 將焦點移到「未讀訊息」標籤 |
| **ALT+4** | UnigramPlus | 將焦點移到聊天資料夾清單 |
| **ALT+5** | UnigramPlus | 將焦點移到已開啟的個人資料 |
| **ALT+6** | UnigramPlus | 將焦點移到群組主題清單 |
| **ALT+D** | UnigramPlus | 將焦點移到編輯欄位。若焦點已在編輯欄位中，按下快速鍵後會移回先前所在的位置 |
| **ALT+End** | UnigramPlus | 移至結尾 |

### 搜尋

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **Ctrl+E** | Unigram | 搜尋聊天 |
| **Ctrl+F** | Unigram | 搜尋目前聊天中的訊息 |
| **ALT+I** | UnigramPlus | 移至搜尋結果清單 |
| **F3** | UnigramPlus | 移至下一個搜尋結果 |
| **Shift+F3** | UnigramPlus | 移至上一個搜尋結果 |

### 輸入區中選取的文字

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **Ctrl+Z** | Unigram | 復原 |
| **Ctrl+Y** | Unigram | 取消復原 |
| **Ctrl+X** | Unigram | 剪下 |
| **Ctrl+C** | Unigram | 複製 |
| **Ctrl+V** | Unigram | 貼上 |
| **Ctrl+A** | Unigram | 全選 |
| **Ctrl+B** | Unigram | 粗體 |
| **Ctrl+I** | Unigram | 斜體 |
| **Ctrl+K** | Unigram | 建立連結 |
| **Ctrl+Shift+X** | Unigram | 刪除線 |
| **Ctrl+Shift+M** | Unigram | 等寬 |
| **Ctrl+Shift+P** | Unigram | 防劇透 |
| **Ctrl+Shift+N** | Unigram | 清除格式 |

### 聊天資料夾

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **Ctrl+1** | Unigram | 第一個資料夾（所有聊天） |
| **Ctrl+2** | Unigram | 第二個資料夾 |
| **Ctrl+3** | Unigram | 第三個資料夾 |
| **Ctrl+4** | Unigram | 第四個資料夾 |
| **Ctrl+5** | Unigram | 第五個資料夾 |
| **Ctrl+6** | Unigram | 第六個資料夾 |
| **Ctrl+7** | Unigram | 第七個資料夾 |
| **Ctrl+8** | Unigram | 第八個資料夾 |
| **Ctrl+9** | Unigram | 封存 |

### 訊息操作

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **Space** | UnigramPlus | 播放或停止焦點所在的語音或視訊訊息，或開啟訊息附加的媒體 |
| **Ctrl+C** | UnigramPlus | 若訊息包含文字則複製訊息；若焦點位於連結上，則複製該連結 |
| **ALT+Q** | UnigramPlus | 若目前訊息包含「即時檢視」按鈕，則按下它 |
| **ALT+Delete** | UnigramPlus | 刪除訊息或聊天 |
| **Shift+Delete** | UnigramPlus | 在雙方刪除訊息或聊天 |
| **Ctrl+ALT+C** | UnigramPlus | 開啟留言 |
| **Enter** | UnigramPlus | 回覆訊息 |
| **ALT+F** | UnigramPlus | 轉傳訊息 |
| **Backspace** | UnigramPlus | 編輯訊息 |
| **ALT+Shift+R** | UnigramPlus | 將聊天標示為已讀 |
| **Ctrl+Space** | UnigramPlus | 切換到選取模式 |
| **Unassigned** | UnigramPlus | 另存檔案為... |
| **Unassigned** | UnigramPlus | 置頂訊息或聊天 |
| **Left Arrow** | UnigramPlus | 讀出原始訊息，也就是回覆所針對的訊息 |
| **Right Arrow** | UnigramPlus | 移到焦點訊息中的下一個媒體附件 |
| **ALT+C** | UnigramPlus | 在快顯視窗顯示訊息文字 |
| **ALT+W** | UnigramPlus | 讀出訊息的傳送或接收時間，以及反應清單。連按兩次可切換是否讀出此資訊。 |
| **NVDA+Ctrl+0-9** | UnigramPlus | 讀出最近十則訊息之一；1 是最新訊息，0 是第十則訊息 |
| **Ctrl+Shift+A** | UnigramPlus | 按下「附加檔案」按鈕 |
| **Ctrl+N** | UnigramPlus | 按下「新增對話」按鈕 |
| **Arrow Up** | Unigram | 編輯上一則已傳送訊息 |
| **Ctrl+Arrow Up** | Unigram | 回覆上一則已傳送訊息 |
| **Esc / Alt+Arrow Left** | Unigram | 返回 |
| **Alt+Arrow Right** | Unigram | 前進 |

### 語音訊息與媒體

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **ALT+P** | UnigramPlus | 播放或暫停目前播放中的語音訊息 |
| **ALT+S** | UnigramPlus | 提高或降低語音訊息播放速度 |
| **ALT+E** | UnigramPlus | 關閉音訊播放器 |
| **NVDA+ALT+R** | UnigramPlus | 將語音訊息轉換為文字 |
| **Ctrl+ALT+Right Arrow** | UnigramPlus | 快轉語音訊息 |
| **Ctrl+ALT+Left Arrow** | UnigramPlus | 倒轉語音訊息 |

### 錄製訊息

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **Ctrl+R** | Unigram | 開始錄製 |
| **Ctrl+R (again)** | Unigram | 傳送錄製內容 |
| **Ctrl+D** | Unigram | 停止錄製 |
| **Space (while recording) / Ctrl+P** | Unigram | 暫停錄製 |
| **Ctrl+D** | UnigramPlus | 按一次取消語音訊息錄製；按兩次變更錄製通知方式 |

### 通話

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **Ctrl+Home** | Unigram | 接聽來電 |
| **Ctrl+End** | Unigram | 拒絕來電 |
| **Ctrl+Page Up** | Unigram | 切換相機 |
| **Ctrl+Page Down** | Unigram | 切換麥克風 |
| **ALT+Shift+C** | UnigramPlus | 若為聯絡人則撥打電話，若為群組則進入語音聊天 |
| **ALT+Shift+V** | UnigramPlus | 按下視訊通話按鈕 |
| **ALT+Y** | UnigramPlus | 接聽來電 |
| **ALT+N** | UnigramPlus | 若有來電則按下「拒絕通話」按鈕；若正在通話則按下「結束通話」按鈕；若語音聊天作用中則離開語音聊天。 |
| **ALT+A** | UnigramPlus | 按下「麥克風靜音或取消靜音」按鈕 |
| **ALT+V** | UnigramPlus | 按下「啟用或停用相機」按鈕 |

### 其他快速鍵

| 快速鍵 | 類別 | 操作 |
|---|---|---|
| **Ctrl+0** | Unigram | 我的收藏 |
| **Ctrl+W** | Unigram | 關閉目前視窗 |
| **Ctrl+Q** | Unigram | 關閉 Unigram（僅限主視窗） |
| **Ctrl+Shift+Y** | Unigram | 變更狀態 |
| **ALT+T** | UnigramPlus | 讀出已開啟聊天的名稱與狀態 |
| **ALT+M** | UnigramPlus | 開啟導覽功能表 |
| **ALT+Shift+P** | UnigramPlus | 開啟目前聊天的個人資料 |
| **ALT+L** | UnigramPlus | 啟用目前聊天中新訊息的自動讀出 |
| **ALT+H** | UnigramPlus | 顯示所有 UnigramPlus 快速鍵清單 |
| **ALT+U** | UnigramPlus | 切換進度列讀出 |
| **ALT+Shift+L** | UnigramPlus | 將廣播資料複製到剪貼簿 |
| **NVDA+ALT+U** | UnigramPlus | 開啟 UnigramPlus 設定視窗 |
<!-- shortcut-table-end -->

## 版本變更

### 版本 5.6.0

* 修正 rich message 判斷，貼圖與表情符號訊息不再被錯誤朗讀為 rich message。
* Ctrl+R 現在使用 Unigram 官方的語音訊息錄製與傳送行為，同時保留 UnigramPlus 的錄製開始與結束提示。
* 更新本地化翻譯。

### 版本 5.5.9

* 新增豐富訊息支援。豐富訊息取得焦點時會被朗讀，並可按 Alt+C 在可瀏覽視窗中開啟。
* 豐富訊息中的連結與混合內容會被保留，且可在可瀏覽視窗中啟用連結。

### 版本 5.5.8

* 修正自動更新：現在會從 GitHub 安全取得版本，並在安裝前驗證下載的附加元件。

* 修復與 Unigram 12.7 的相容性，先前有多個快速鍵與語音提示失效。
* 投票訊息會再次朗讀問題與答案選項。
* 論壇主題清單會再次朗讀最後一則訊息的預覽。
* 一對一通話中，靜音麥克風（ALT+A）、開啟或關閉鏡頭（ALT+V）與結束通話（ALT+N）的快速鍵可再次使用。
* ALT+End 會再次移動到聊天中最新的訊息。

### 版本 5.5.7

* 將快速鍵區段重新整理為分類表格，並整合 Unigram 與 UnigramPlus 快速鍵。
* 錄製語音或視訊訊息時，NVDA 現在會朗讀「正在錄製語音訊息」或「正在錄製視訊訊息」並念出經過時間，而不再是「Tn voice message」。

### 版本 5.5.6

* 修正在群組或頻道個人資料中，按 Tab 越過名稱後，身分按鈕被讀成「Identity root」的問題；現在會讀出聊天名稱與成員數。
* control+C 不再被處理兩次：焦點在連結上時複製連結，其他情況則交由 Unigram 複製訊息。

### 版本 5.5.5

* 回覆或編輯訊息時，現在會在訊息輸入欄位中提示「回覆」或「編輯」，而不是平常的訊息輸入提示。
* 修正在關閉應用程式後、對方停止輸入後，或離開聊天後，輸入音效有時仍持續播放的問題；現在只要已開啟的聊天中沒有人在輸入，音效就會立即停止。
* 更新緬甸文本地化。

### 版本 5.5.4

* 修正聊天資料夾未讀數量變化被不必要讀出的問題，例如「全部 535」。檔案傳輸進度現在只會在 Unigram 的上傳與下載控制項中讀出，且會忽略非 Unigram 視窗。
* 修正與 Telegram Desktop NVDA 附加元件的衝突；只有偵測到目前執行的應用程式是 Unigram 時，才會啟用 UnigramPlus。
* 在 UnigramPlus 設定中新增開啟內建音效資料夾的按鈕，方便使用者以相同檔名替換自訂 WAV 音效檔案。
* 在訊息編輯欄位的上方向鍵動作中，新增「移到最後取得焦點的訊息」選項。
* 正體中文重新整理並獨立為 zh_TW，另新增簡體中文 zh_CN。

### 版本 5.5.3

* 新增檔案上傳與下載進度的自動讀出。進度列讀出設定新增「只在上傳與下載時」選項，並設為預設值。ALT+U 現在會在關閉、只限上傳下載、讀出全部進度列三種狀態間切換。
* 更新讀我檔案與翻譯。

### 版本 5.5.2

* 更新讀我檔案與翻譯。
* 變更輸入中提示音效。

### 版本 5.5.1

* 修正移到群組主題清單的快速鍵 ALT+6。
* 新增輸入中提示音：當對方在已開啟聊天中輸入時循環播放，停止輸入後結束播放。
