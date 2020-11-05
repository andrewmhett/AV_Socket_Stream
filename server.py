import socket
import threading
import os
import datetime
import atexit
import sys
import time
import cv2

command_s = socket.socket()
video_s = socket.socket()
command_port=12345
video_port=12346
audio_port=12347
command_s.bind(('',command_port))
video_s.bind(('',video_port))
command_s.listen(5)
video_s.listen(5)
const_byte_len=0

atexit.register(command_s.close)
atexit.register(video_s.close)

def format_length(length):
    out_str=""
    for i in range(10-len(str(length))):
        out_str+="0"
    out_str+=str(length)
    return out_str

class TargetConnection():
    def __init__(self,command_c,video_c):
        self.command_c=command_c
        self.video_c=video_c
        self.command_data_length=0
        self.video_data_length=0
        self.previous_time=None
        self.current_frame=0
        self.framerate=0
        self.metadata={}
        self.cap=None
        self.stream_thread=None
        self.streaming=False
        self.width=0
        self.height=0
        threading.Thread(target=self.receive_command).start()
    def stream_video_data(self):
        while self.streaming:
            self.current_frame+=1
            try:
                self.send_data(self.video_c,cv2.cvtColor(cv2.resize(self.cap.read(self.current_frame)[1], (self.width,self.height)),cv2.COLOR_BGR2RGB).tobytes())
            except cv2.error:
                self.video_c.send(("VE"+("\n"*15)).encode("utf-8"))
                self.streaming=False
    def receive_command(self):
        global const_byte_len
        while True:
            if self.command_data_length>0:
                data=self.command_c.recv(self.command_data_length-const_byte_len).decode()
                if data == "VQ":
                    self.streaming=False
                    self.send_data(self.command_c,"M:Successfully connected to AV server.\nPlease select a video to play.")
                    self.cap=None
                    self.filename=""
                    self.current_frame=0
                if data.startswith("VN:"):
                    video_name=data.split("VN:")[1]
                    for directory in os.walk('videos'):
                        for video in directory[2]:
                            if video.startswith(video_name):
                                self.filename=video
                    self.send_data(self.command_c,"M:Loading {0}...".format(video_name))
                    self.cap=cv2.VideoCapture("videos/"+self.filename)
                    while not self.cap.isOpened():
                        pass
                    self.framerate=self.cap.get(5)
                    print("----LOADING VIDEO----")
                    print(self.filename)
                    self.width=int(400*self.cap.get(3)/self.cap.get(4))
                    self.height=int(self.width*self.cap.get(4)/self.cap.get(3))
                    print(str(int(self.cap.get(3)))+"x"+str(int(self.cap.get(4))))
                    print("FRAMERATE: {0}".format(self.framerate))
                    print("---------------------")
                    self.send_data(self.command_c,"VI:{0},{1},{2}".format(self.width,self.height,int(self.framerate)))
                    self.stream_thread=threading.Thread(target=self.stream_video_data)
                    self.streaming=True
                    self.stream_thread.start()
                if data.startswith("C:"):
                    command=data.split("C:")[1]
                    if command == "TOGGLE_PAUSE":
                        pass
                    if command == "FAST_FORWARD":
                        pass
                    if command == "REWIND":
                        pass
                if data.startswith("E:"):
                    error=data.split("E:")[1]
                    if error=="BUFFERING":
                       #self.height=int(self.height/1.1)
                       #self.width=int(self.width/1.1)
                       pass
                self.command_data_length=0
            else:
                data=self.command_c.recv(17)
                if data.startswith(b"LENGTH"):
                    data=data.decode()
                    self.command_data_length=int(data.split("LENGTH:")[1])
                elif len(data)==3:
                    const_byte_len=int(data.decode()[0:2])
    def send_data(self,connection,data):
        if type(data) != bytes:
            connection.send("LENGTH:{0}".format(format_length(sys.getsizeof(data))).encode("utf-8"))
        else:
            connection.send("LENGTH:{0}".format(format_length(self.width*self.height*3)).encode("utf-8"))
        if type(data)==str:
            connection.send(data.encode("utf-8"))
        elif connection == self.video_c and type(data)==bytes:
            last_count=0
            size=0
            for i in range(int((self.width*self.height*3)/10000)):
                connection.sendall(data[i*10000:(i+1)*10000])
                size+=10000
            connection.sendall(data[size:self.width*self.height*3])

def catch_incoming_connections():
    global const_byte_len
    while True:
        command_c, addr = command_s.accept()
        video_c, addr = video_s.accept()
        counter=0
        videos=[]
        for directory in os.walk('videos'):
            videos=directory[2]
        counter=0
        for video in videos:
            videos[counter]=".".join(video.split(".")[:-1])
            counter+=1
        command_c.send("{0}/".format(sys.getsizeof("")).encode("utf-8"))
        target_connection=TargetConnection(command_c,video_c)
        if len(videos)>0:
            target_connection.send_data(command_c,"M:Successfully connected to AV server.\nPlease select a video to play.")
            target_connection.send_data(command_c,"VL:{0}".format(",".join(videos)))
            target_connection.send_data(command_c,"RB:Play")
        else:
            target_connection.send_data(command_c,"M:Successfully connected to AV server.\nThere are currently no videos on this server. Reload the client in order to refresh.")
        time.sleep(1)

threading.Thread(target=catch_incoming_connections).start()
print("AV server running on {0}".format(socket.gethostbyname(socket.gethostname())))
