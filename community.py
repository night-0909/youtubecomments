# -*- encoding: utf-8 -*-

from youtube_community_tab.community_tab import CommunityTab
from youtube_comment_downloader import *
import requests, requests_cache, json, sys
from http.cookiejar import MozillaCookieJar
from datetime import datetime
import dateparser
from zoneinfo import ZoneInfo

class Program():
    def __init__(self, idchannel, urlchannel, youtubeKey, delay_requests, cookies, tz, output_dirs, dateFormats):
        self.idchannel = idchannel
        self.urlchannel = urlchannel
        self.youtubeKey = youtubeKey
        self.tzinfo = ZoneInfo(tz)
        self.delay_requests = delay_requests
        self.cookies = cookies
        self.output_dirs = output_dirs
        self.dateFormats = dateFormats
        self.loggingfile = None
        self.resultfile = None
        
        self.start()
        
    def start(self):
        self.initLoggingFile()
        print("Starting program")
        self.writelog("Starting program")
        
        self.initChannel()
        self.initResultFile()
            
    def initLoggingFile(self):
        loggingfilename = self.output_dirs['log_file'] + "community_" + self.idchannel + ".log"
        try:
            self.loggingfile = open(loggingfilename, "a", encoding="utf-8")
        except Exception as e:
            print(e)
            self.exitProgram()
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = self.output_dirs['result_file'] + "community_" + self.idchannel + "_" + dateNow['dateFileString'] +  ".txt"
        try:
            self.resultfile = open(resultfilename, "w", encoding="utf-8")
        except Exception as e:
            print(e)
            self.exitProgram()
    
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
            channelInfosResponse = response.text
            if response.status_code == 200:
                channel_json = json.loads(channelInfosResponse)       

                if channel_json.get('pageInfo').get('totalResults') == 0:
                    print(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : channel not found")
                    self.writelog(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : channel not found")
                    self.exitProgram()
                
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
        try:
            self.writelog("Execution had errors")
            self.writelog("Ending program")
        except Exception as e:
            print(e)

        self.clean()
        sys.exit(1)
    
    # Used at the end of program without errors/exceptions and when errors/exception occured
    def clean(self):
        try:
            # Close Files
            if self.loggingfile is not None:
                self.loggingfile.close()
            if self.resultfile is not None:    
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
        self.writelog("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")

        # Cache expiration
        EXPIRATION_TIME = 1 * 60 * 60

        # Cookies for youtube_community_tab
        if self.cookies != "":
            cookie_jar = MozillaCookieJar(self.cookies)
            cookie_jar.load(ignore_discard=True)
            requests_cache.cookies = cookie_jar

        try:
            ct = CommunityTab(self.idchannel)
            ct.load_posts(expire_after=EXPIRATION_TIME)

            # Load more posts
            while(ct.posts_continuation_token):
                time.sleep(self.delay_requests)
                ct.load_posts(expire_after=EXPIRATION_TIME)
                #if (len(ct.posts) > 80):
                    #break
        except Exception as e:
            print(f"[×] channel={self.idchannel} Error getting posts from Posts tab : {e}")
            self.writelog(f"[×] channel={self.idchannel} Error getting posts from Posts tab : {e}")
            self.exitProgram()            

        num_posts = len(ct.posts)
        print(f"Posts : {num_posts}")
        self.writelog(f"Posts : {num_posts}")
        self.writeresult(f"Posts : {num_posts}")
        self.writeresult("\n\n")

        num_posts_processed = 0
        for post in ct.posts:
            time.sleep(self.delay_requests)
            url = "https://www.youtube.com/post/" + post.post_id
            print(url)
            self.writeresult(url)
            self.writeresult("\n")
            # We remove (edited) and shared in published_time_text in order to transform published_time_text in date
            datePost = datetime.fromtimestamp(dateparser.parse(post.published_time_text.replace('shared ', '').split('(')[0].strip()).timestamp(), self.tzinfo).strftime(self.dateFormats['dateString'])
            self.writeresult("Date : " + datePost)
            self.writeresult("\n")
            
            self.writeresult("Text :")
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
                        self.writeresult("https://www.youtube.com" + elt["navigationEndpoint"]["commandMetadata"]["webCommandMetadata"]["url"])
                
                # Video link
                if post.backstage_attachment is not None and 'videoRenderer' in post.backstage_attachment:
                    self.writeresult("\n")
                    # url can be None if private video
                    self.writeresult("https://www.youtube.com" + str(post.backstage_attachment['videoRenderer']['watchEndpoint']['url']))

            # Cited post
            if post.original_post is not None:
                # We remove (edited) and shared in published_time_text in order to transform published_time_text in date
                datePostOrigin = datetime.fromtimestamp(dateparser.parse(post.original_post.published_time_text.replace('shared ', '').split('(')[0].strip()).timestamp(), self.tzinfo).strftime(self.dateFormats['dateString'])
                self.writeresult("\nOriginal post :\n")
                self.writeresult("URL : " + "https://www.youtube.com/post/" + post.original_post.post_id)
                self.writeresult("\n")
                self.writeresult("Date original post : " + datePostOrigin)
                self.writeresult("\n")
                self.writeresult("Author : " + post.original_post.author["authorEndpoint"]["url"][1:len(post.original_post.author["authorEndpoint"]["url"])] +
                        " (" + post.original_post.channel_id + ")")
            
            self.writeresult("\n")
            print("Comments :")
            self.writeresult("Comments :")

            # Comments
            lastParentReplies = 0
            idComment = 0
            comments = []
            time.sleep(self.delay_requests)
            
            try:
                downloader = YoutubeCommentDownloader(self.cookies)
                comments = downloader.get_comments_from_url(url, sort_by=SORT_BY_RECENT)
                # comments is a generator so we cast it to list to get its length and don't consume the generator
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
            
            # Add new line for next parentComment // TO VERIFY : is there some cases where we don't want to add new line, eg end of comments ?
            if lastParentReplies != idComment:
                self.writeresult("\n")
            
            # No comment, we add two newlines
            if lastParentReplies == 0 and idComment == 0:
                self.writeresult("\n\n")
                
            num_posts_processed = num_posts_processed + 1

        print(f"Processed : {num_posts_processed}")
        self.writelog(f"Processed : {num_posts_processed}")            

        print("Execution was OK")
        self.writelog("Execution was OK")
        print("Ending program")
        self.writelog("Ending program")
        self.clean()

if __name__ == "__main__":
    # Paths
    output_dirs = {'log_file': "",
                   'result_file': ""
    }    
    # Youtube
    urlchannel = "https://www.youtube.com/@your_channel"
    idchannel = '' # Found channel id on Youtube by clicking "Share channel" then "Copy channel ID"
    youtubeKey = '' # YouTube API Key from Google Cloud, see https://helano.github.io/help.html
    delay_requests = 1 # Delay applied after each loading more posts, each post, each comment download
    cookies = '' # Cookie path or ''
    # Format
    tz = "Europe/Paris"
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}

    # Launch
    program = Program(idchannel, urlchannel, youtubeKey, delay_requests, cookies, tz, output_dirs, dateFormats)
    program.main()

