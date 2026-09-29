# -*- encoding: utf-8 -*-

from datetime import datetime
import dateutil.parser
from bs4 import BeautifulSoup
import sys
import requests, json
from urllib3.util.retry import Retry
from zoneinfo import ZoneInfo

class Program():
    def __init__(self, idchannel, urlchannel, playlistId, needComments, needDescription, youtubeKey, tz, output_dirs, dateFormats):
        self.idchannel = idchannel
        self.urlchannel = urlchannel
        self.playlistId = playlistId
        self.needComments = needComments
        self.needDescription = needDescription
        self.youtubeKey = youtubeKey        
        self.tzinfo = ZoneInfo(tz)
        self.output_dirs = output_dirs
        self.dateFormats = dateFormats
        self.loggingfile = None
        self.resultfile = None
        self.sessionGoogleApis = None                
        
        self.start()
        
    def start(self):
        self.initLoggingFile()
        print("Starting program")
        self.writelog("Starting program")
        self.initSessionGoogleApis()
        self.initChannel()
        self.initResultFile()
        
    def initLoggingFile(self):
        loggingfilename = self.output_dirs['log_file'] + "playlist_" + self.idchannel + "_" + self.playlistId + ".log"
        try:
            self.loggingfile = open(loggingfilename, "a", encoding="utf-8")
        except Exception as e:
            print(e)
            self.exitProgram()
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = self.output_dirs['result_file'] + "playlist_" + self.idchannel + "_" + self.playlistId + "_" + dateNow['dateFileString'] + ".txt"
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

    def initSessionGoogleApis(self):
        # Youtube Data API V3 can sometimes return HTTP status 400 and 403 whereas request is valid, and sending this same request succeeds.        
        self.sessionGoogleApis = self.create_session(status_forcelist=(400, 403, 408, 425, 429, 500, 502, 503, 504))

    def create_session(
        self,
        retries=3,
        backoff_factor=1,
        backoff_jitter=0.5,
        allowed_methods=frozenset(["GET", "POST", "HEAD", "OPTIONS"]),
        status_forcelist=(408, 425, 429, 500, 502, 503, 504),
    ):
        """Return a requests Session with sensible retry and backoff defaults."""
        session = requests.Session()

        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            backoff_jitter=backoff_jitter,
            allowed_methods=allowed_methods,
            status_forcelist=status_forcelist,
            raise_on_status=False
        )

        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def initChannel(self):
        # Get handle from idchannel
        channelInfosURL = "https://www.googleapis.com/youtube/v3/channels?key=" + self.youtubeKey + "&id=" + self.idchannel + "&part=snippet"
        print(channelInfosURL)
        try:
            response = self.sessionGoogleApis.get(channelInfosURL, timeout=(3.05, 20))
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

    def getComments(self, infosVideo):
        url = "https://www.youtube.com/watch?v=" + infosVideo["videoId"]
        dateNow = self.getDateNow()
        file = self.output_dirs['result_file'] + "comment_" + infosVideo["videoId"] + "_" + dateNow['dateFileString'] + ".txt"
        fcomment = open(file, "a", encoding="utf-8")
        print(url)
        fcomment.write(url + "\n")
        fcomment.write("Title : " + str(infosVideo["title"]) + "\n")
        fcomment.write("Date : " + infosVideo["date"])
  
        # Get liveStreamingDetails infos
        if infosVideo["liveStreamingDetails"] is not None:
            if infosVideo["liveBroadcastContent"] == "none":                    
                actualStartTime_object = dateutil.parser.isoparse(infosVideo.get("liveStreamingDetails").get("actualStartTime", ""))
                actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                actualEndTime_object = dateutil.parser.isoparse(infosVideo.get("liveStreamingDetails").get("actualEndTime", ""))
                actualEndTime_text = actualEndTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])

                fcomment.write(" (start : " + actualStartTime_text)
                fcomment.write(" end : " + actualEndTime_text + ")")
            elif infosVideo["liveBroadcastContent"] == "live":
                actualStartTime_object = dateutil.parser.isoparse(infosVideo.get("liveStreamingDetails").get("actualStartTime", ""))
                actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                actualEndTime_text = "live"
                infosVideo["durationString"] = "None"

                fcomment.write(" (start : " + actualStartTime_text)
                fcomment.write(" end : " + actualEndTime_text + ")")
            elif infosVideo["liveBroadcastContent"] == "upcoming":
                actualscheduledStartTime_object = dateutil.parser.isoparse(infosVideo.get("liveStreamingDetails").get("scheduledStartTime", ""))
                actualscheduledStartTime_text = actualscheduledStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                infosVideo["durationString"] = "None"

                fcomment.write(" (scheduled : " + actualscheduledStartTime_text + ")")
        
        fcomment.write("\n")   
        fcomment.write("Duration : " + str(infosVideo["durationString"]) + "\n")
        fcomment.write("Description : " + str(infosVideo["description"]) + "\n")
        fcomment.write("Comments :")
        
        lastParentReplies = 0
        idComment = 0

        # Get comments
        hasMoreComments = True
        nextPageTokenComments = 0
        nextPageTokenCommentsString = ""
            
        while hasMoreComments is True:
            if nextPageTokenComments != 0 :
                nextPageTokenCommentsString = "&pageToken=" + nextPageTokenComments
                
            commentsURL = "https://www.googleapis.com/youtube/v3/commentThreads?key=" + self.youtubeKey + "&videoId=" + infosVideo['videoId'] + \
                          "&part=id,replies,snippet&maxResults=100" + nextPageTokenCommentsString
            print(commentsURL)
            try:
                response = self.sessionGoogleApis.get(commentsURL, timeout=(3.05, 20))
                commentsResponse = response.text
                if response.status_code == 200:
                    comments_json = json.loads(commentsResponse)
                elif response.status_code == 404:
                    # Video not found
                    comments_json = json.loads(commentsResponse)                           
                    print(f"[×] idVideo={infosVideo['videoId']} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}, error={comments_json['error']['message']}")
                    self.writelog(f"[×] idVideo={infosVideo['videoId']} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}, error={comments_json['error']['message']}")
                    break                    
                elif response.status_code == 403:
                    # Cases where comments are turned off or insufficient permissions, see https://developers.google.com/youtube/v3/docs/errors#commentthreads
                    comments_json = json.loads(commentsResponse)
                    self.writeresult("\n")
                    self.writeresult(f"{comments_json['error']['message']}\n")
                    fcomment.write("\n")
                    fcomment.write(f"{comments_json['error']['message']}\n")
                    break
                else:
                    print(f"[×] idVideo={infosVideo['videoId']} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}")
                    self.writelog(f"[×] idVideo={infosVideo['videoId']} Response of commentsURL {commentsURL} isn't OK : {response.status_code} {response.text}")
                    self.exitProgram()
            except Exception as e:
                print(f"[×] idVideo={infosVideo['videoId']} Error commentsURL {commentsURL} : {e}")
                self.writelog(f"[×] idVideo={infosVideo['videoId']} Error commentsURL {commentsURL} : {e}")
                self.exitProgram()

            items = comments_json.get('items')
            if len(items) > 0:
                fcomment.write("\n")
            
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
                    dateUpdate_object = dateutil.parser.isoparse(dateUpdate)
                    dateUpdate_text = dateUpdate_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                    update_dateString = " (last edited on " + dateUpdate_text + ")"
                
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
                fcomment.write(publish_dateString + update_dateString + " " + author + " (" + channelId + ")" + " : " + textComment)
                fcomment.write("\n")

                # get replies of comment
                # use https://www.googleapis.com/youtube/v3/comments to get all comments
                if snippet.get('totalReplyCount') > 0:
                    print("*** Replies : " + str(snippet.get('totalReplyCount')) + " ***")
                    fcomment.write("*** Replies : " + str(snippet.get('totalReplyCount')) + " ***\n")

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
                            response = self.sessionGoogleApis.get(repliesURL, timeout=(3.05, 20))
                            repliesResponse = response.text
                            if response.status_code == 200:
                                replies_json = json.loads(repliesResponse)
                            elif response.status_code == 404:
                                # Comment parentId not found
                                replies_json = json.loads(repliesResponse)
                                print(f"[×] idVideo={infosVideo['videoId']} Response of repliesURL {repliesURL} isn't OK : {response.status_code} {response.text}, error={replies_json['error']['message']}")
                                self.writelog(f"[×] idVideo={infosVideo['videoId']} Response of repliesURL {repliesURL} isn't OK : {response.status_code} {response.text}, error={replies_json['error']['message']}")
                                break
                            elif response.status_code == 403:
                                # Cases where comments are turned off or insufficient permissions, see https://developers.google.com/youtube/v3/docs/errors#comments_youtube.comments.list
                                replies_json = json.loads(repliesResponse)
                                self.writeresult("\n")
                                self.writeresult(f"{replies_json['error']['message']}")
                                break
                            else:
                                print(f"[×] idVideo={infosVideo['videoId']} Response of repliesURL {repliesURL} isn't OK : {response.status_code} {response.text}")
                                self.writelog(f"[×] idVideo={infosVideo['videoId']} Response of repliesURL {repliesURL} isn't OK : {response.status_code} {response.text}")
                                self.exitProgram()
                        except Exception as e:
                            print(f"[×] idVideo={infosVideo['videoId']} Error repliesURL {repliesURL} : {e}")
                            self.writelog(f"[×] idVideo={infosVideo['videoId']} Error repliesURL {repliesURL} : {e}")
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
                            datePublish_object = dateutil.parser.isoparse(datePublish)
                            datePublish_text = datePublish_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                            publish_dateString = datePublish_text

                            update_dateString = ""
                            if dateUpdate != datePublish:
                                dateUpdate_object = dateutil.parser.isoparse(dateUpdate)
                                dateUpdate_text = dateUpdate_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                                update_dateString = " (last edited on " + dateUpdate_text + ")"
                            
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
                            fcomment.write(publish_dateString + update_dateString + " " + author + " (" + channelId + ")" + " : " + textComment)
                            lastParentReplies = idComment
                            fcomment.write("\n")

                        # Get continue token
                        if "nextPageToken" in replies_json:
                            nextPageTokenReplies = replies_json["nextPageToken"]
                        else:
                            hasMoreReplies = False
                            
                    fcomment.write("\n")                           

            # Get continue token
            if "nextPageToken" in comments_json:
                nextPageTokenComments = comments_json["nextPageToken"]
            else:
                hasMoreComments = False

        # We add new line only if last comment is not a reply of a comment or no comments
        if lastParentReplies != idComment:
            fcomment.write("\n")

        # No comment, we add two newlines
        if lastParentReplies == 0 and idComment == 0:
            fcomment.write("\n\n")

        fcomment.close()
    
    def main(self):
        self.writelog("Channel " + self.urlchannel + " id : " + self.idchannel)        
        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel + " playlist id : " + self.playlistId)
        self.writeresult("\n")

        playlistURL = "https://www.googleapis.com/youtube/v3/playlists?key=" + self.youtubeKey + "&id=" + self.playlistId + \
        "&part=contentDetails,id,localizations,player,snippet,status&maxResults=50"
        print(playlistURL)

        try:
            response = self.sessionGoogleApis.get(playlistURL, timeout=(3.05, 20))
            playlistResponse = response.text
            if response.status_code == 200:
                playlist_json = json.loads(playlistResponse)
                
                if playlist_json.get('pageInfo').get('totalResults') == 0:
                    print(f"[×] playlistId={self.playlistId} Error playlistURL {playlistURL} : playlist not found")
                    self.writelog(f"[×] playlistId={self.playlistId} Error playlistURL {playlistURL} : playlist not found")
                    self.exitProgram()
            else:
                print(f"[×] playlistId={self.playlistId} Response of playlistURL {playlistURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] playlistId={self.playlistId} Response of playlistURL {playlistURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
        except Exception as e:
            print(f"[×] playlistId={self.playlistId} Error playlistURL {playlistURL} : {e}")
            self.writelog(f"[×] playlistId={self.playlistId} Error playlistURL {playlistURL} : {e}")
            self.exitProgram()

        items = playlist_json.get('items')
        snippet = items[0].get('snippet')
        
        title = snippet.get('title')
        description = snippet.get('description')
        itemCount = items[0].get('contentDetails').get('itemCount')
        print(title)
        print(description)
        print(itemCount)
        
        self.writeresult(f"Title : {title}")
        self.writeresult("\n")
        self.writeresult(f"Description : {description}")
        self.writeresult("\n")
        self.writeresult(f"Videos : {itemCount}")
        self.writelog(f"Playlist id : {self.playlistId}")
        self.writelog(f"Videos : {itemCount}")
        self.writeresult("\n\n")
        
        num_videos_processed = 0        

        # max results = 50 and then use nextPageToken value in pageToken for the next request
        nextPageToken = 0
        pageTokenParams = ""
        while nextPageToken is not None:
            if nextPageToken != 0 :
                pageTokenParams = "&pageToken=" + nextPageToken

            playlistItemsURL = "https://www.googleapis.com/youtube/v3/playlistItems?key=" + self.youtubeKey + "&playlistId=" + playlistId + \
            "&part=contentDetails,id,snippet,status" + pageTokenParams + "&maxResults=50"
            print(playlistItemsURL)
            try:
                response = self.sessionGoogleApis.get(playlistItemsURL, timeout=(3.05, 20))
                playlistItemsResponse = response.text
                if response.status_code == 200:
                    playlistItems_json = json.loads(playlistItemsResponse)
                elif response.status_code == 404:
                    # Playlist not found
                    playlistItems_json = json.loads(playlistItemsResponse)                           
                    print(f"[×] playlistId={self.playlistId} Response of playlistItemsURL {playlistItemsURL} isn't OK : {response.status_code} {response.text}, error={playlistItems_json['error']['message']}")
                    self.writelog(f"[×] playlistId={self.playlistId} Response of playlistItemsURL {playlistItemsURL} isn't OK : {response.status_code} {response.text}, error={playlistItems_json['error']['message']}")
                    break                    
                elif response.status_code == 403:
                    # Playlist not accessible, see https://developers.google.com/youtube/v3/docs/errors#playlistItems_youtube.playlistItems.list
                    playlistItems_json = json.loads(playlistItemsResponse)                           
                    print(f"[×] playlistId={self.playlistId} Response of playlistItemsURL {playlistItemsURL} isn't OK : {response.status_code} {response.text}, error={playlistItems_json['error']['message']}")
                    self.writelog(f"[×] playlistId={self.playlistId} Response of playlistItemsURL {playlistItemsURL} isn't OK : {response.status_code} {response.text}, error={playlistItems_json['error']['message']}")
                    break
                else:
                    print(f"[×] playlistId={self.playlistId} Response of playlistItemsURL {playlistItemsURL} isn't OK : {response.status_code} {response.text}")
                    self.writelog(f"[×] playlistId={self.playlistId} Response of playlistItemsURL {playlistItemsURL} isn't OK : {response.status_code} {response.text}")
                    self.exitProgram()
            except Exception as e:
                print(f"[×] playlistId={self.playlistId} Error playlistItemsURL {playlistItemsURL} : {e}")
                self.writelog(f"[×] playlistId={self.playlistId} Error playlistItemsURL {playlistItemsURL} : {e}")
                self.exitProgram()
                
            nextPageToken = playlistItems_json.get('nextPageToken')
            
            itemsPlaylist = playlistItems_json.get('items')
            for itemPlaylist in itemsPlaylist:
                snippetPlaylistItem = itemPlaylist.get('snippet')
                title = snippetPlaylistItem.get('title')
                contentDetailsPlaylistItem = itemPlaylist.get('contentDetails')
                videoId = contentDetailsPlaylistItem.get('videoId')

                print(videoId)
                self.writeresult("videoURL : https://youtube.com/watch?v=" + videoId + "\n")
                print("Title : " + title)
                self.writeresult("Title : " + title + "\n")
                dateAddedToPlaylist = snippetPlaylistItem.get('publishedAt')
                dateAddedToPlaylist_object = dateutil.parser.isoparse(dateAddedToPlaylist)
                dateAddedToPlaylist_text = dateAddedToPlaylist_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                self.writeresult("Add to playlist date : " + dateAddedToPlaylist_text + "\n")
                
                # Get additionnal infos of video
                additionnalInfosURL = "https://www.googleapis.com/youtube/v3/videos?key=" + self.youtubeKey + "&id=" + videoId + "&part=snippet,contentDetails,liveStreamingDetails,statistics"
                print(additionnalInfosURL)
                
                try:
                    response = self.sessionGoogleApis.get(additionnalInfosURL, timeout=(3.05, 20))               
                    additionnalInfosResponse = response.text
                    if response.status_code == 200:
                        video_json = json.loads(additionnalInfosResponse)
                        if video_json.get('pageInfo').get('totalResults') == 0:                        
                            print(f"[×] idVideo={'videoId'} video not found")
                            self.writelog(f"[×] idVideo={videoId} video not found")
                            continue
                    else:
                        print(f"[×] idVideo={videoId} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.writelog(f"[×] idVideo={videoId} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                        self.exitProgram()
                except Exception as e:
                    print(f"[×] idVideo={videoId} Error additionnalInfosURL {additionnalInfosURL} : {e}")
                    self.writelog(f"[×] idVideo={videoId} Error additionnalInfosURL {additionnalInfosURL} : {e}")
                    self.exitProgram()
                    
                if (len(video_json.get('items')) > 0):
                    itemVideo = video_json.get('items')[0]
                    snippetVideo = itemVideo.get('snippet')

                    dateVideo = snippetVideo.get('publishedAt')
                    dateVideo_object = dateutil.parser.isoparse(dateVideo)
                    dateVideo_text = dateVideo_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                    
                    title = snippetVideo.get('title')
                    description = snippetVideo.get('description')

                    contentDetailsVideo = itemVideo.get('contentDetails')
                    duration = contentDetailsVideo.get('duration', '')
                    durationString = duration[2:len(duration)]
                    
                    statsVideo = itemVideo.get('statistics')
                    viewCount = statsVideo.get('viewCount')
                    likeCount = statsVideo.get('likeCount')
                    commentCount = statsVideo.get('commentCount')

                    print("Date : " + dateVideo_text)
                    self.writeresult("Date : " + dateVideo_text)
                        
                    # Get liveStreamingDetails infos
                    if "liveStreamingDetails" in itemVideo:
                        if snippetVideo.get("liveBroadcastContent") == "none":                    
                            actualStartTime_object = dateutil.parser.isoparse(itemVideo.get("liveStreamingDetails").get("actualStartTime", ""))
                            actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                            actualEndTime_object = dateutil.parser.isoparse(itemVideo.get("liveStreamingDetails").get("actualEndTime", ""))
                            actualEndTime_text = actualEndTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])

                            print("start : " + actualStartTime_text)
                            self.writeresult(" (start : " + actualStartTime_text)
                            print("end : " + actualEndTime_text)
                            self.writeresult(" end : " + actualEndTime_text + ")")
                        elif snippetVideo.get("liveBroadcastContent") == "live":
                            actualStartTime_object = dateutil.parser.isoparse(itemVideo.get("liveStreamingDetails").get("actualStartTime", ""))
                            actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                            actualEndTime_text = "live"
                            durationString = "None"

                            print("start : " + actualStartTime_text)
                            self.writeresult(" (start : " + actualStartTime_text)
                            print("end : " + actualEndTime_text)
                            self.writeresult(" end : " + actualEndTime_text + ")")
                        elif snippetVideo.get("liveBroadcastContent") == "upcoming":
                            actualscheduledStartTime_object = dateutil.parser.isoparse(itemVideo.get("liveStreamingDetails").get("scheduledStartTime", ""))
                            actualscheduledStartTime_text = actualscheduledStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats["dateString"])
                            durationString = "None"

                            print("scheduled : " + actualscheduledStartTime_text)
                            self.writeresult(" (scheduled : " + actualscheduledStartTime_text + ")")
                    
                    self.writeresult("\n")

                    print("Duration : " + str(durationString))
                    self.writeresult("Duration : " + str(durationString))
                    self.writeresult("\n")

                    if self.needDescription is True:
                        print("Description : " + str(description))
                        self.writeresult("Description : " + str(description))
                        self.writeresult("\n")
                    
                    print("Views : " + str(viewCount))
                    self.writeresult("Views : " + str(viewCount))
                    self.writeresult("\n")
                    print("Likes : " + str(likeCount))
                    self.writeresult("Likes : " + str(likeCount))
                    self.writeresult("\n")
                    print("Comments : " + str(commentCount))
                    self.writeresult("Comments : " + str(commentCount))
                    self.writeresult("\n")
                                    
                    # Get comments
                    if self.needComments is True:
                        # Just pass useful informations to getComments()
                        print("Get comments video " + str(videoId))
                        infosVideo = {"videoId": videoId, "title": title, "durationString": durationString, "date" : dateVideo_text,
                                      "description": description,
                                      "liveBroadcastContent": snippetVideo.get("liveBroadcastContent", None), 
                                      "liveStreamingDetails": itemVideo.get("liveStreamingDetails", None)}

                        self.getComments(infosVideo)                

                self.writeresult("\n")                
                num_videos_processed = num_videos_processed + 1
        
        print(f"Processed : {num_videos_processed}")
        self.writelog(f"Processed : {num_videos_processed}")
                    
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
    playlistId = "" # What's next to https://www.youtube.com/playlist?list=
    needComments = True
    needDescription = True
    youtubeKey = '' # YouTube API Key from Google Cloud, see https://helano.github.io/help.html

    # Format
    tz = "Europe/Paris"
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}

    # Launch
    program = Program(idchannel, urlchannel, playlistId, needComments, needDescription, youtubeKey, tz, output_dirs, dateFormats)
    program.main()

