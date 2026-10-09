# 技能说明书（Skill.md）
# 每个技能 = 一段"什么时候用什么命令"的说明。需要用到时，用下面给定的命令去执行。

## 1. 获取新闻（视频中的例子）
如果需要获取新闻，使用如下命令，XXX 为用户希望搜索的关键词：
curl -L -A "Mozilla/5.0" "https://news.google.com/rss/search?q=XXX&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"

## 2. 查看当前目录文件
如果需要查看当前目录下有什么文件：
ls

## 3. 读取文件内容
如果需要查看某个文件的内容，例如查看 hello.txt：
cat hello.txt

## 4. 创建文件
如果需要在当前目录创建一个文件，例如创建内容为 hello world 的 hello.txt：
printf 'hello world' > hello.txt

## 5. 下载 B 站视频（视频中的例子）
如果需要下载 B 站视频，使用如下命令，XXX 为视频链接：
yt-dlp "XXX"
