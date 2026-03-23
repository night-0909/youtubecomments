# -*- encoding: utf-8 -*-

# Community Posts : https://github.com/HoloArchivists/youtube-community-tab
# I made some changes in :
# helpers\clean_items.py : see function def clean_backstage_attachment(attachment) :
# post.py : see function def from_data(post_data):

# Comments https://github.com/egbertbouman/youtube-comment-downloader/

from youtube_community_tab.community_tab import CommunityTab
from youtube_comment_downloader import *
import requests, json, sys
from datetime import datetime
import dateparser
from zoneinfo import ZoneInfo

class Program():
    def __init__(self, idchannel, urlchannel, youtubeKey, tz, dateFormats):
        self.idchannel = idchannel
        self.urlchannel = urlchannel
        self.youtubeKey = youtubeKey
        self.tzinfo = ZoneInfo(tz)
        self.dateFormats = dateFormats
        
        self.initLoggingFile()
        self.initResultFile()
            
    def initLoggingFile(self):
        loggingfilename = "community_" + self.idchannel
        self.loggingfile = open(loggingfilename + ".log", "a", encoding="utf-8")
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = "community_" + self.idchannel + "_" + dateNow['dateFileString'] + ".txt"
        self.resultfile = open(resultfilename, "w", encoding="utf-8")
    
    def getDateNow(self):
        timestamp_now = datetime.now().timestamp()
        date = datetime.fromtimestamp(timestamp_now, self.tzinfo)
        dateString = date.strftime(self.dateFormats['dateString'])
        dateDBString = date.strftime(self.dateFormats['dateDBString'])
        dateFileString = date.strftime(self.dateFormats['dateFileString'])
        
        dateNow = {"dateString": dateString, "dateDBString": dateDBString, "dateFileString": dateFileString}
        
        return dateNow

    def writelog(self, message):
        dateNow = self.getDateNow()
        self.loggingfile.write(dateNow["dateString"] + " : " + message + "\n")
        # Write in real time
        self.loggingfile.flush()
            
    def writeresult(self, message):
        self.resultfile.write(message)
        # Write in real time
        #self.resultfile.flush()

    def initChannel(self):
        # Get handle from idchannel
        channelInfosURL = "https://www.googleapis.com/youtube/v3/channels?key=" + self.youtubeKey + "&id=" + self.idchannel + "&part=snippet"
        print(channelInfosURL)
        try:
            response = requests.get(channelInfosURL)
            if response.status_code == 200:
                channelInfosResponse = response.text
                channel_json = json.loads(channelInfosResponse)       
                
                item = channel_json.get('items')[0]
                snippet = item.get('snippet')
                handle = snippet.get('customUrl')[1:len(snippet.get('customUrl'))]
                self.urlchannel = "https://www.youtube.com/@" + handle
            else:
                print(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
        except Exception as e:
            print(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.writelog(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.exitProgram()

    # Used when errors/exceptions occured and when we want to exit right now
    def exitProgram(self):
        self.writelog("Execution had errors")
        self.writelog("Ending program")
        self.clean()
        sys.exit(1)
    
    # Used at the end of program without errors/exceptions and when errors/exception occured
    def clean(self):
        try:
            # Close Files
            self.loggingfile.close()
            self.resultfile.close()
        except Exception as e:
            print("Error cleaning up : " + str(e))

    def searchInListcomments(self, listcomments, attribute, value):
        element = None

        for comment in listcomments:
            if comment[attribute] == value:
                element = comment
                break

        return element

    def arrangeComments(self, listcomments):
        # Sorting of comments : Parent comments are first then children, so we need to rearrange listcomments
        # Make comment/reply hierarchy see https://github.com/egbertbouman/youtube-comment-downloader/issues/148
        # There's a reply boolean in the comment output:  will be True/False depending on whether or not it's a reply to another comment.
        # If you want the comment ID of the parent, you can just do something like comment['cid'].split('.')[0].
        # comment['replies'] will be "" or a string with number eg "1"
        
        newlistcomments = []
        
        for comment in listcomments:
            if comment['replies'] != "":
                comment['repliesList'] = []

            if comment['reply'] is False:
                newlistcomments.append(comment)    
            else:
                parentCommentCid = comment['cid'].split('.')[0]
                parentComment = self.searchInListcomments(newlistcomments, 'cid', parentCommentCid)
                parentComment['repliesList'].append(comment)
        
        return newlistcomments
     
    def main(self):
        print("Starting program")
        self.writelog("Starting program")
        self.initChannel()

        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")

        # Cache expiration
        EXPIRATION_TIME = 1 * 60 * 60

        ct = CommunityTab(self.idchannel)
        ct.load_posts(expire_after=EXPIRATION_TIME)

        # Load more posts
        while(ct.posts_continuation_token):
            ct.load_posts(expire_after=EXPIRATION_TIME)
            #if (len(ct.posts) > 80):
                #break

        print(str(len(ct.posts))+ " posts")

        for post in ct.posts:
            url = "https://youtube.com/post/" + post.post_id
            print(url)
            self.writeresult(url)
            self.writeresult("\n")
            datePost = datetime.fromtimestamp(dateparser.parse(post.published_time_text.replace('shared ', '').split('(')[0].strip()).timestamp(), self.tzinfo).strftime(self.dateFormats['dateString'])
            self.writeresult("Date : " + datePost)
            self.writeresult("\n")
            
            if "runs" in post.content_text:
                print(post.content_text["runs"])
                for elt in post.content_text["runs"]:
                    self.writeresult(elt["text"])
                    if "urlEndpoint" in elt:
                        self.writeresult("\n")
                        self.writeresult(elt["urlEndpoint"]["url"])

                    if "navigationEndpoint" in elt and "commandMetadata" in elt["navigationEndpoint"] and "webCommandMetadata" in elt["navigationEndpoint"]["commandMetadata"]:
                        self.writeresult("\n")
                        self.writeresult("https://youtube.com" + elt["navigationEndpoint"]["commandMetadata"]["webCommandMetadata"]["url"])
                
                # Video link
                if post.backstage_attachment is not None and 'videoRenderer' in post.backstage_attachment:
                    self.writeresult("\n")
                    # url can be None if private video
                    self.writeresult("https://youtube.com" + str(post.backstage_attachment['videoRenderer']['watchEndpoint']['url']))

            # Cited post
            if post.original_post is not None:
                datePostOrigin = datetime.fromtimestamp(dateparser.parse(post.original_post.published_time_text.replace('shared ', '').split('(')[0].strip()).timestamp(), self.tzinfo).strftime(self.dateFormats['dateString'])
                self.writeresult("\n\Original post :\n")
                self.writeresult("URL : " + "https://youtube.com/post/" + post.original_post.post_id)
                self.writeresult("\n")
                self.writeresult("Date original post : " + datePostOrigin)
                self.writeresult("\n")
                self.writeresult("Author : " + post.original_post.author["authorEndpoint"]["url"][1:len(post.original_post.author["authorEndpoint"]["url"])] +
                        " (" + post.original_post.channel_id + ")")
                self.writeresult("\n")

            # Comments
            lastParentReplies = 0
            idComment = 0
            comments = []
            try:
                downloader = YoutubeCommentDownloader()
                comments = downloader.get_comments_from_url(url, sort_by=SORT_BY_RECENT)
                # comments is a generator so we cast it to list to get length and don't consume the generator
                listcomments = list(comments)
            except Exception as e:
                print(f"[×] {url} Error YoutubeCommentDownloader : {e}")
                self.writelog(f"[×] {url} Error YoutubeCommentDownloader : {e}")
                self.exitProgram()
                
            if len(listcomments) > 0:
                # Sorting of comments : Parent comments are first then replies, so we need to rearrange listcomments
                listcomments = self.arrangeComments(listcomments)
                self.writeresult("\n")
                for comment in listcomments:
                    idComment = comment['cid']
                    date = datetime.fromtimestamp(comment['time_parsed'])
                    date = date.astimezone(self.tzinfo)
                    print(date.strftime(self.dateFormats['dateString']))
                    print(comment['text'])
                    self.writeresult(date.strftime(self.dateFormats['dateString']) + " " + comment['author'] + " (" + comment['channel'] + ")" + ": " + comment['text'])
                    self.writeresult("\n")

                    if comment['replies'] != "":
                        print("*** Replies : " + comment['replies'] + " ***\n")
                        self.writeresult("*** Replies : " + comment['replies'] + " ***\n")
                        lastParentReplies = idComment
                        for reply in comment['repliesList']:
                            date = datetime.fromtimestamp(reply['time_parsed'])
                            date = date.astimezone(self.tzinfo)
                            print(date.strftime(self.dateFormats['dateString']))
                            print(reply['text'] + "\n")
                            self.writeresult(date.strftime(self.dateFormats['dateString']) + " " + reply['author'] + " (" + reply['channel'] + ")" + ": " + reply['text'])
                            self.writeresult("\n")

                        self.writeresult("\n")
            
            # Add new line for next parentComment
            if lastParentReplies != idComment:
                self.writeresult("\n")
            
            # No comment, we add two newlines
            if lastParentReplies == 0 and idComment == 0:
                self.writeresult("\n\n")

        print("Execution was OK")
        self.writelog("Execution was OK")
        print("Ending program")
        self.writelog("Ending program")
        self.clean()

if __name__ == "__main__":
    # Youtube
    urlchannel = "https://www.youtube.com/@your_channel"
    idchannel = '' # Found channel id on Youtube by clicking "Share channel" then "Copy channel ID"
    youtubeKey = '' # YouTube API Key from Google Cloud, see https://helano.github.io/help.html
    # Format
    tz = "Europe/Paris"
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}

    # Launch
    program = Program(idchannel, urlchannel, youtubeKey, tz, dateFormats)
    program.main()
