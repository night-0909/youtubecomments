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
    ChatDownloaderError
)
import scrapetube
import sys, requests, json
from datetime import datetime
from zoneinfo import ZoneInfo

class Program():
    def __init__(self, idchannel, urlchannel, videoId, youtubeKey, tz, dateFormats):
        self.idchannel = idchannel
        self.urlchannel = urlchannel
        self.videoId = videoId
        self.youtubeKey = youtubeKey
        self.tzinfo = ZoneInfo(tz)
        self.dateFormats = dateFormats
        
        self.initLoggingFile()
        self.initResultFile()
            
    def initLoggingFile(self):
        loggingfilename = "chat-one_" + self.idchannel
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
                
                item = channel_json.get('items')[0]
                snippet = item.get('snippet')
                handle = snippet.get('customUrl')[1:len(snippet.get('customUrl'))]
                self.urlchannel = "https://www.youtube.com/@" + handle
            else:
                print(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.writeresult(f"[×] channel={self.idchannel} Response of channelInfosURL {channelInfosURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
        except Exception as e:
            print(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
            self.writeresult(f"[×] channel={self.idchannel} Error channelInfosURL {channelInfosURL} : {e}")
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

        self.writeresult("Channel " + self.urlchannel + " id : " + self.idchannel)
        self.writeresult("\n\n")

        url = "https://www.youtube.com/watch?v=" + videoId

        # Get video information
        additionnalInfosURL = "https://www.googleapis.com/youtube/v3/videos?key=" + self.youtubeKey + "&id=" + videoId + "&part=snippet,contentDetails,liveStreamingDetails,statistics"
        print(additionnalInfosURL)
        try:
            response = requests.get(additionnalInfosURL)
            if response.status_code == 200:
                additionnalInfosResponse = response.text
                video_json = json.loads(additionnalInfosResponse)
            else:
                print(f"[×] idVideo={stream['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                self.writelog(f"[×] idVideo={stream['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
                self.exitProgram()
        except Exception as e:
            print(f"[×] idVideo={stream['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
            self.writelog(f"[×] idVideo={stream['videoId']} Response of additionnalInfosURL {additionnalInfosURL} isn't OK : {response.status_code} {response.text}")
            self.exitProgram()

        item = video_json.get('items')[0]
        snippet = item.get('snippet')
        date = snippet.get('publishedAt')
        title = snippet.get('title')
        description = snippet.get('description')

        contentDetails = item.get('contentDetails')
        duration = contentDetails.get('duration')
        durationString = duration[2:len(duration)]

        # Check if live is ended. Because some lives can be scheduled and chat is on with messages, for this case live don't have start and endtime.
        # liveBroadcastContent is "upcoming" if scheduled and will be "live" when on and none I guess when done. So we check "none"
        if "liveStreamingDetails" in item and snippet.get("liveBroadcastContent") == "none":
            print(url)
            self.writeresult(url)
            self.writeresult("\n")
            print(title)
            self.writeresult(title)
            self.writeresult("\n")
            print("Date : " + date)
            self.writeresult("Date : " + date)
            
            print("start : " + item.get("liveStreamingDetails").get("actualStartTime"))
            self.writeresult(" (start : " + item.get("liveStreamingDetails").get("actualStartTime"))
            print("end : " + item.get("liveStreamingDetails").get("actualEndTime"))
            self.writeresult(" end : " + item.get("liveStreamingDetails").get("actualEndTime") + ")")
            
            self.writeresult("\n")
            print(durationString)
            self.writeresult(durationString)
            self.writeresult("\n")

            try:
                chat = ChatDownloader().get_chat(url)       # create a generator
                for message in chat:                        # iterate over messages
                    print(chat.format(message))
                    self.writeresult(chat.format(message))
                    self.writeresult("\n")
            # List of exceptions : https://deepwiki.com/xenova/chat-downloader/6-error-handling
            # These exceptions are not really errors (LoginRequired isn't to me as I don't want to use authentication)
            # If you prefer not display any error in result file, comment this block
            except (NoChatReplay, ChatDisabled, LoginRequired) as ex:
                print(f"{ex}")
                self.writeresult(f"{ex}")
                self.writeresult("\n")
            # These are errors
            except Exception as ex:
                print(f"[×] idVideo={stream['videoId']} Error writing chat : {ex}")
                self.writelog(f"[×] idVideo={stream['videoId']} Error writing chat : {ex}")
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
    idchannel = '' # Found channel id on Youtube by clicking "Share channel" then Copy channel ID
    videoId = "" # What's next to https://www.youtube.com/watch?v=
    youtubeKey = '' # YouTube API Key from Google Cloud, see https://helano.github.io/help.html

    # Format
    tz = "Europe/Paris" # Set tz also in chat_downloader/formatting/custom_formats.json to apply tz to chat messages date
    dateFormats = {"dateString": "%d/%m/%Y %H:%M:%S", "dateDBString": "%Y-%m-%d %H:%M:%S", "dateFileString": "%d%m%Y%H%M%S"}

    # Launch
    program = Program(idchannel, urlchannel, videoId, youtubeKey, tz, dateFormats)
    program.main()
