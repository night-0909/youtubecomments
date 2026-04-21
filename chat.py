# -*- encoding: utf-8 -*-

# I made some changes in chat_downloader module :
# formatting\format.py I added tz : value = microseconds_to_timestamp(value, formatting, tz)
# utils\core.py I added tz info : see function def microseconds_to_timestamp(microseconds, format='%Y-%m-%d %H:%M:%S'):
# formatting\custom_formats.json I added author id : "template": "{time_text|timestamp}{author.badges}{money.text}{author.display_name|author.name} ({author.id}){message}",

from chat_downloader import ChatDownloader
from chat_downloader.errors import (
    ChatDisabled,
    NoChatReplay,
    LoginRequired,
    VideoUnplayable,
    ChatDownloaderError
)

import scrapetube
import sys, re
import requests, json
from datetime import datetime
import dateutil.parser
from zoneinfo import ZoneInfo

class Program():
    def __init__(self, idchannel, urlchannel, youtubeKey, tz, dateFormats):
        self.idchannel = idchannel
        self.urlchannel = urlchannel
        self.youtubeKey = youtubeKey
        self.tzinfo = ZoneInfo(tz)
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
        loggingfilename = "chat_" + self.idchannel
        self.loggingfile = open(loggingfilename + ".log", "a", encoding="utf-8")
    
    def initResultFile(self):
        dateNow = self.getDateNow()
        resultfilename = "chat_" + self.idchannel + "_" + dateNow['dateFileString'] +  ".txt"
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

    def safely_get_value_from_key(self, *args, default=None):
        obj = args[0]
        keys = args[1:]

        for key in keys:
            try:
                obj = obj[key]
            except Exception:
                return default

        return obj        

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
            if self.loggingfile is not None:
                self.loggingfile.close()
            if self.resultfile is not None:    
                self.resultfile.close()
        except Exception as e:
            print("Error cleaning up : " + str(e))
    
    def main(self):
        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")

        # Get all url streams and Premiere videos
        videostypes = ["streams", "videos"]
        for videotype in videostypes :
            print("Type : " + videotype)
            self.writeresult("Type : " + videotype)
            self.writeresult("\n\n")
            
            videos = scrapetube.get_channel(channel_id=self.idchannel, content_type=videotype, sort_by="newest")
            for video in videos:
                url = "https://www.youtube.com/watch?v="+str(video['videoId'])

                if videotype == "videos":
                    # Impossible to determine with scrapetube.get_channel() if a video is a Premiere
                    # and I don't want to hit YTB API V3 /videos for each video and consume a lot of quota.
                    # So I can determine wether a video has/had a chat by hitting Youtube video page source checking in var ytInitialPlayerResponse = {}
                    try:
                        response = requests.get(url)
                        if response.status_code == 200:
                            youtubeVideoResponse = response.text
                            ytIniatialPlayerResponse = re.findall('ytInitialPlayerResponse\\s*=\\s*({.+?})\\s*;', response.text)[0]
                            data = json.loads(ytIniatialPlayerResponse)

                            # Ditch videos with no chat or videos with chat that are still on air
                            liveBroadcastDetails = self.safely_get_value_from_key(data, "microformat", "playerMicroformatRenderer", "liveBroadcastDetails")
                            if liveBroadcastDetails is None or liveBroadcastDetails.get("isLiveNow") is True:
                                continue
                        else:
                            print(f"[×] idVideo={video['videoId']} Response of url {url} isn't OK : {response.status_code} {response.text}")
                            self.writelog(f"[×] idVideo={video['videoId']} Response of url {url} isn't OK : {response.status_code} {response.text}")
                            self.exitProgram()
                    except Exception as e:
                        print(f"[×] idVideo={video['videoId']} Error url {url} : {e}")
                        self.writelog(f"[×] idVideo={video['videoId']} Error url {url} : {e}")
                        self.exitProgram()
                        
                # Here, we only have streams and videos that have/had a chat
                # If you don't want to use YTB API V3, use data and search for title, dates, description, duration, liveBroadcastDetails
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
                dateVideo_text = dateVideo_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])
                title = snippet.get('title')
                description = snippet.get('description')

                contentDetails = item.get('contentDetails')
                duration = contentDetails.get('duration')
                durationString = duration[2:len(duration)]

                # Check if video is ended. Because some videos can be scheduled and chat is on with messages, for this case video don't have start and endtime.
                # liveBroadcastContent is "upcoming" if scheduled and will be "live" when on and none I guess when done. So we check "none"
                if "liveStreamingDetails" in item and snippet.get("liveBroadcastContent") == "none":
                    print(url)
                    self.writeresult(url)
                    self.writeresult("\n")
                    print(title)
                    self.writeresult(title)
                    self.writeresult("\n")
                    print("Date : " + dateVideo_text)
                    self.writeresult("Date : " + dateVideo_text)
                    
                    actualStartTime_object = dateutil.parser.isoparse(item.get("liveStreamingDetails").get("actualStartTime", ""))
                    actualStartTime_text = actualStartTime_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])
                    actualEndTime_object = dateutil.parser.isoparse(item.get("liveStreamingDetails").get("actualEndTime", ""))
                    actualEndTime_text = actualEndTime_object.astimezone(self.tzinfo).strftime(self.dateFormats['dateString'])                                  
                    print("start : " + actualStartTime_text)
                    self.writeresult(" (start : " + actualStartTime_text)
                    print("end : " + actualEndTime_text)
                    self.writeresult(" end : " + actualEndTime_text + ")")
                    
                    self.writeresult("\n")
                    print(durationString)
                    self.writeresult(durationString)
                    self.writeresult("\n")
                    #print(str(description))
                    #self.writeresult(str(description))
                    #self.writeresult("\n")

                    try:
                        chat = ChatDownloader().get_chat(url)       # create a generator
                        for message in chat:                        # iterate over messages
                            print(chat.format(message))
                            self.writeresult(chat.format(message))
                            self.writeresult("\n")
                    # List of exceptions : https://deepwiki.com/xenova/chat-downloader/6-error-handling
                    # These exceptions are not really errors (LoginRequired isn't to me as I don't want to use authentication, VideoUnplayable for members-only content)
                    # If you prefer not display any error in result file, comment this except block
                    except (NoChatReplay, ChatDisabled, LoginRequired, VideoUnplayable) as ex:
                        print(f"{ex}")
                        self.writeresult(f"{ex}")
                        self.writeresult("\n")
                    # These are errors
                    except Exception as ex:
                        print(f"[×] idVideo={video['videoId']} Error writing chat : {ex}")
                        self.writelog(f"[×] idVideo={video['videoId']} Error writing chat : {ex}")
                        self.exitProgram()

                    self.writeresult("\n")
            
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
    tz = "Europe/Paris" # Set tz also in chat_downloader/formatting/custom_formats.json to apply tz to chat messages date
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}

    # Launch
    program = Program(idchannel, urlchannel, youtubeKey, tz, dateFormats)
    program.main()
    
