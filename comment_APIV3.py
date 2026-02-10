# -*- encoding: utf-8 -*-

import scrapetube
from datetime import datetime
import dateutil.parser
from bs4 import BeautifulSoup
import sys
import requests, json
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
        loggingfilename = "comment_" + self.idchannel
        self.loggingfile = open(loggingfilename + ".log", "a", encoding="utf-8")
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = "comment_" + self.idchannel + "_" + dateNow['dateFileString'] + ".txt"
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
    
    def main(self):
        print("Starting program")
        self.writelog("Starting program")
        self.initChannel()

        self.writeresult("Chaine " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")
        
        # Get all comments on videos
        videostypes = ["streams", "videos", "shorts"]
        for videotype in videostypes :
            print("Type : " + videotype)
            self.writeresult("Type : " + videotype)
            self.writeresult("\n\n")
            
            videos = scrapetube.get_channel(channel_id=self.idchannel, content_type=videotype, limit=20, sort_by="newest")
            videosList = list(videos)
            for video in videosList:
                url = "https://www.youtube.com/watch?v="+str(video['videoId'])
                print(url)
                self.writeresult(url)

                lastParentReplies = 0
                idComment = 0

                # Get additional infos of video
                additionnalInfosURL = "https://www.googleapis.com/youtube/v3/videos?key=" + self.youtubeKey + "&id=" + video['videoId'] + "&part=snippet,contentDetails,liveStreamingDetails,statistics"
                print(additionnalInfosURL)
                try:
                    response = requests.get(additionnalInfosURL)
                    if response.status_code == 200:
                        additionnalInfosResponse = response.text
                        video_json = json.loads(additionnalInfosResponse)
                    else:
                        print(f"[×] idVideo={video['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.writelog(f"[×] idVideo={video['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.exitProgram()
                except Exception as e:
                    print(f"[×] idVideo={video['videoId']} Error additionnalInfosURL {additionnalInfosURL} : {e}")
                    self.writelog(f"[×] idVideo={video['videoId']} Error additionnalInfosURL {additionnalInfosURL} : {e}")
                    self.exitProgram()
                    
                item = video_json.get('items')[0]
                snippet = item.get('snippet')
                dateVideo = snippet.get('publishedAt')
                dateVideo_object = dateutil.parser.isoparse(dateVideo)
                dateVideo_text = dateVideo_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                
                title = snippet.get('title')
                description = snippet.get('description')

                contentDetails = item.get('contentDetails')
                duration = contentDetails.get('duration')
                durationString = duration[2:len(duration)]

                self.writeresult("\n")
                print(title)
                self.writeresult(title)
                self.writeresult("\n")
                print("Date : " + dateVideo_text)
                self.writeresult("Date : " + dateVideo_text)

                # Warning : somes lives are scheduled but still have chat messages and comments, so no start and end time for them
                if "liveStreamingDetails" in item:
                    actualStartTime_object = dateutil.parser.isoparse(item.get("liveStreamingDetails").get("actualStartTime", ""))
                    actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])                   
                    actualEndTime_object = dateutil.parser.isoparse(item.get("liveStreamingDetails").get("actualEndTime", ""))
                    actualEndTime_text = actualEndTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])                   
                    
                    print("début : " + actualStartTime_text)
                    self.writeresult(" (début : " + actualStartTime_text)
                    print("fin : " + actualEndTime_text)
                    self.writeresult(" fin : " + actualEndTime_text + ")")
                    
                #self.writeresult("\n")
                #print(str(description))
                #self.writeresult(str(description))                
                self.writeresult("\n")
                print(durationString)
                self.writeresult(durationString)
                  
                # Get comments
                hasMoreComments = True
                nextPageTokenComments = 0
                nextPageTokenCommentsString = ""
                    
                while hasMoreComments is True:
                    if nextPageTokenComments != 0 :
                        nextPageTokenCommentsString = "&pageToken=" + nextPageTokenComments
                        
                    commentsURL = "https://www.googleapis.com/youtube/v3/commentThreads?key=" + self.youtubeKey + "&videoId=" + video['videoId'] + \
                                  "&part=id,replies,snippet&maxResults=100" + nextPageTokenCommentsString
                    print(commentsURL)
                    try:
                        response = requests.get(commentsURL)
                        if response.status_code == 200:
                            commentsResponse = response.text
                            comments_json = json.loads(commentsResponse)
                        elif response.status_code == 403:
                            # Cases where comments are turned off or insufficient permissions, see https://developers.google.com/youtube/v3/docs/errors#commentthreads
                            commentsResponse = response.text
                            comments_json = json.loads(commentsResponse)
                            self.writeresult("\n")
                            self.writeresult(f"{comments_json['error']['message']}")
                            break
                        else:
                            print(f"[×] idVideo={video['videoId']} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}")
                            self.writelog(f"[×] idVideo={video['videoId']} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}")
                            self.exitProgram()
                    except Exception as e:
                        print(f"[×] idVideo={video['videoId']} Error commentsURL {commentsURL} : {e}")
                        self.writelog(f"[×] idVideo={video['videoId']} Error commentsURL {commentsURL} : {e}")
                        self.exitProgram()
                
                    items = comments_json.get('items')
                    if len(items) > 0:
                        self.writeresult("\n")
                    
                    for item in items:
                        idComment = item.get('id')
                        snippet = item.get('snippet')
                        realsnippet = snippet.get('topLevelComment').get('snippet')
                        author = realsnippet.get('authorDisplayName')
                        channelId = realsnippet.get('authorChannelId').get('value')
                        text = realsnippet.get('textDisplay')
                        datePublish = realsnippet.get('publishedAt')
                        dateUpdate = realsnippet.get('updatedAt')

                        # Transform 2025-02-04T18:03:53Z to self.dateFormats["dateString"]
                        datePublish_object = dateutil.parser.isoparse(datePublish)
                        datePublish_text = datePublish_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                        publish_dateString = datePublish_text

                        update_dateString = ""
                        if dateUpdate != datePublish:
                            #dateUpdate_object = datetime.fromisoformat(dateUpdate)
                            dateUpdate_object = dateutil.parser.isoparse(dateUpdate)
                            dateUpdate_text = dateUpdate_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                            update_dateString = " (maj le " + dateUpdate_text + ")"
                        
                        # Clean HTML :
                        # replace unicode characters by utf-8
                        # first replace <br> by new lines
                        # then delete all HTML tags
                        # https://www.geeksforgeeks.org/python/how-to-remove-html-tags-from-string-in-python/
                        text = text.replace("\r\n", "<br>")
                        text = text.replace("\r", "<br>")
                        text = text.replace("<br>", "\n")
                        soup = BeautifulSoup(text, "html.parser")
                        textComment = soup.get_text()

                        print(publish_dateString + update_dateString + " " + author + " (" + channelId + ")" + " : " + textComment)
                        self.writeresult(publish_dateString + update_dateString + " " + author + " (" + channelId + ")" + " : " + textComment)
                        self.writeresult("\n")

                        # Get replies of comment
                        # Use https://www.googleapis.com/youtube/v3/comments to get all comments
                        if snippet.get('totalReplyCount') > 0:
                            print("*** Réponses : " + str(snippet.get('totalReplyCount')) + " ***")
                            self.writeresult("*** Réponses : " + str(snippet.get('totalReplyCount')) + " ***\n")

                            hasMoreReplies = True
                            nextPageTokenReplies = 0
                            nextPageTokenRepliesString = ""
                            while hasMoreReplies is True:
                                if nextPageTokenReplies != 0 :
                                    nextPageTokenRepliesString = "&pageToken=" + nextPageTokenReplies
                                    
                                repliesURL = "https://www.googleapis.com/youtube/v3/comments?key=" + self.youtubeKey + "&parentId=" + idComment + \
                                "&part=id,snippet&maxResults=100" + nextPageTokenRepliesString
                                print(repliesURL)

                                try:
                                    response = requests.get(repliesURL)
                                    if response.status_code == 200:
                                        repliesResponse = response.text
                                        replies_json = json.loads(repliesResponse)
                                    else:
                                        print(f"[×] idVideo={video['videoId']} Response of repliesURL {repliesURL} isn't OK : {response.status_code} {response.text}")
                                        self.writelog(f"[×] idVideo={video['videoId']} Response of repliesURL {repliesURL} isn't OK : {response.status_code} {response.text}")
                                        self.exitProgram()
                                except Exception as e:
                                    print(f"[×] idVideo={video['videoId']} Error repliesURL {repliesURL} : {e}")
                                    self.writelog(f"[×] idVideo={video['videoId']} Error repliesURL {repliesURL} : {e}")
                                    self.exitProgram()

                                items = replies_json.get('items')
                                for item in items:
                                    realsnippet = item.get('snippet')
                                    author = realsnippet.get('authorDisplayName')
                                    channelId = realsnippet.get('authorChannelId').get('value')
                                    text = realsnippet.get('textDisplay')
                                    datePublish = realsnippet.get('publishedAt')
                                    dateUpdate = realsnippet.get('updatedAt')

                                    # Transform 2025-02-04T18:03:53Z to self.dateFormats["dateString"]
                                    #datePublish_object = datetime.fromisoformat(datePublish)
                                    datePublish_object = dateutil.parser.isoparse(datePublish)
                                    datePublish_text = datePublish_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                                    publish_dateString = datePublish_text

                                    update_dateString = ""
                                    if dateUpdate != datePublish:
                                        #dateUpdate_object = datetime.fromisoformat(dateUpdate)
                                        dateUpdate_object = dateutil.parser.isoparse(dateUpdate)
                                        dateUpdate_text = dateUpdate_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                                        update_dateString = " (maj le " + dateUpdate_text + ")"
                                    
                                    # Clean HTML :
                                    # first replace <br> by new lines
                                    # then delete all HTML tags
                                    # https://www.geeksforgeeks.org/python/how-to-remove-html-tags-from-string-in-python/
                                    text = text.replace("\r\n", "<br>")
                                    text = text.replace("\r", "<br>")
                                    text = text.replace("<br>", "\n")
                                    soup = BeautifulSoup(text, "html.parser")
                                    textComment = soup.get_text()

                                    print(publish_dateString + update_dateString + " " + author + " (" + channelId + ")" + " : " + textComment)
                                    self.writeresult(publish_dateString + update_dateString + " " + author + " (" + channelId + ")" + " : " + textComment)
                                    lastParentReplies = idComment
                                    self.writeresult("\n")

                                # Get continue token
                                if "nextPageToken" in replies_json:
                                    nextPageTokenReplies = replies_json["nextPageToken"]
                                else:
                                    hasMoreReplies = False
                                    
                            self.writeresult("\n")                           

                    # Get continue token
                    if "nextPageToken" in comments_json:
                        nextPageTokenComments = comments_json["nextPageToken"]
                    else:
                        hasMoreComments = False
                    
                # We add new line only if last comment is not a reply of a comment or no comments
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
    
