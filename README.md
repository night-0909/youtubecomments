# youtubecomments
Extract comments and chat messages of a Youtube channel (videos, shorts, streams and posts)

chat.py : extract chat messages of all ended streams of a Youtube channel.<br />
chat-one.py : extract chat messages from one ended stream (modify source if you want chat from an ongoing live, see line 134)<br />
comment_APIV3.py : extract comments of videos (type:videos/shorts/streams) of a Youtube channel.<br />
comment-one_APIV3.py : extract comments of one video.<br />
community.py : extract Posts tab (posts + comments) of a Youtube channel.<br />

Modules used and some edits to do :<br />
I use youtube-comment-downloader version 0.1.76 (https://github.com/egbertbouman/youtube-comment-downloader/) without edit I think.<br />
I use chat_downloader version 0.2.8 (https://github.com/xenova/chat-downloader) and youtube-community-tab (https://github.com/HoloArchivists/youtube-community-tab) and made edits.<br />
I modified some things in chat_downloader and youtube-community-tab modules, read at the top of my scripts.<br />

I didn't track every changes I made, so if you want the same thing I have in my computer take my youtube-comment-downloader, chat_downloader and youtube-community-tab folders.<br />

Tested with Python 3.9
