import socket
import tkinter
import threading
import atexit
import sys
import pygame
import time
import datetime

main=tkinter.Tk()
main.title("AV Stream Client")
command_s = socket.socket()
video_s = socket.socket()
command_port=12345
video_port=12346

pygame.display.init()

main.protocol('WM_DELETE_WINDOW',lambda: (sys.exit(0),main.destroy()))

atexit.register(command_s.close)
atexit.register(video_s.close)

server_ip=""
video_menu=None

def connect(ip):
    global server_ip
    global command_s
    global video_s
    global const_byte_len
    try:
        command_s.connect((ip,command_port))
        video_s.connect((ip,video_port))
        recv_byte=b""
        init_str=""
        while recv_byte != b"/":
            init_str+=recv_byte.decode()
            recv_byte=command_s.recv(1)
        const_byte_len=int(init_str)
        command_s.send("{0}/".format(sys.getsizeof("")).encode("utf-8"))
        server_ip=ip
        ipinf.destroy()
        ipent.destroy()
        ipbut.destroy()
        receiveText.pack()
        sendText.pack()
        b1.pack()
        threading.Thread(target=receive_video).start()
        threading.Thread(target=receive_command).start()
        threading.Thread(target=update_screen).start()
    except Exception as e:
        print(e)
        ipinf.configure(text="Failed to connect to server")

command_data_length=0
video_data_length=0
main_button_text="Send"
aspect_ratio=[0,0]
width=0
height=0
display=None
video_list=[]
aspect_ratio=0
orig_width=0
orig_height=0
framerate=0
start_time=None
frame_buffer=[]
all_frames_buffered=False
previous_frames=[]
paused=False
frame_updated=False

def read_video_frame_from_buffer(length):
    data=b""
    counter=0
    while counter<(length-length%2048):
        counter+=2048
        data+=video_s.recv(2048)
    data+=video_s.recv(length-sys.getsizeof(data))
    return data

def track_pygame_events():
    global display
    global video_list
    global video_menu
    global b1
    global media_control_frame
    global aspect_ratio
    global width
    global height
    global framerate
    global frame_buffer
    global all_frames_buffered
    global previous_frames
    while display != None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                display=None
                send_data(command_s,"VQ")
                toggle_pause_button.destroy()
                ff_button.destroy()
                media_control_frame.destroy()
                framerate=0
                frame_buffer=[]
                video_menu=tkinter.OptionMenu(main, selected_video_name, *(video_list))
                video_menu.pack()
                all_frames_buffered=False
                b1=tkinter.Button(main,text=main_button_text,command=send_button_callback)
                b1.pack()
                previous_frames=[]
            if event.type == pygame.VIDEORESIZE:
                width=int(event.w)
                height=int(event.w/aspect_ratio)
                pygame.display.set_mode((width,height),pygame.RESIZABLE)
        time.sleep(.2)

def receive_command():
    global b1
    global command_data_length
    global main_button_text
    global video_menu
    global display
    global width
    global height
    global video_list
    global media_control_frame
    global aspect_ratio
    global orig_width
    global orig_height
    global start_time
    global framerate
    global all_frames_buffered
    global const_byte_len
    while True:
        if command_data_length>0:
            data=command_s.recv(command_data_length-const_byte_len).decode()
            if data.startswith("M:"):
                serverTextVar.set(data.split("M:")[1])
            if data.startswith("VL:"):
                video_list=data.split("VL:")[1].split(",")
                video_menu=tkinter.OptionMenu(main, selected_video_name, *(video_list))
                b1.destroy()
                sendText.destroy()
                video_menu.pack()
                b1=tkinter.Button(main,text=main_button_text,command=send_button_callback)
                b1.pack()
            if data.startswith("RB:"):
                main_button_text=data.split("RB:")[1]
                b1.configure(text=main_button_text)
            if data.startswith("VI:"):
                video_s.settimeout(None)
                width=int(data.split("VI:")[1].split(",")[0])
                height=int(data.split("VI:")[1].split(",")[1])
                framerate=int(data.split("VI:")[1].split(",")[2])
                start_time=datetime.datetime.now()
                orig_width=width
                orig_height=height
                aspect_ratio=width/height
                display=pygame.display.set_mode((int(width),int(height)),pygame.RESIZABLE)
                threading.Thread(target=track_pygame_events).start()
                pygame.display.flip()
            command_data_length=0
        else:
            data=command_s.recv(17)
            if data.startswith(b"LENGTH"):
                data=data.decode()
                command_data_length=int(data.split("LENGTH:")[1])
    time.sleep(0.2)

def update_screen():
    global width
    global height
    global orig_width
    global orig_height
    global display
    global frame_buffer
    global framerate
    global start_time
    global b1
    global rewind_button
    global ff_button
    global toggle_pause_button
    global video_list
    global all_frames_buffered
    global previous_frames
    global paused
    global frame_updated
    global video_menu
    while True:
        if framerate>0 and display != None and (not paused or frame_updated):
            if len(frame_buffer)>0:
                try:
                    start_time=datetime.datetime.now()
                    display.blit(pygame.transform.scale(pygame.image.frombuffer(frame_buffer[0][1],frame_buffer[0][0],"RGB"),(width,height)),(0,0))
                    pygame.display.flip()
                    if not frame_updated:
                        previous_frames.append(frame_buffer[0])
                        frame_buffer=frame_buffer[1:]
                    else:
                        frame_updated=False
                except Exception as e:
                    pass
            else:
                if all_frames_buffered:
                    pygame.display.quit()
                    display=None
                    width=0
                    height=0
                    framerate=0
                    start_time=None
                    all_frames_buffered=False
                    orig_width=0
                    orig_height=0
                    aspect_ratio=0
                    frame_buffer=[]
                    toggle_pause_button.destroy()
                    ff_button.destroy()
                    media_control_frame.destroy()
                    rewind_button.destroy()
                    video_menu=tkinter.OptionMenu(main, selected_video_name, *(video_list))
                    previous_frames=[]
                    video_menu.pack()
                    b1=tkinter.Button(main,text=main_button_text,command=send_button_callback)
                    b1.pack()
                    serverTextVar.set("Successfully connected to AV server.\nPlease select a video to play.")
                else:
                    send_data(command_s,"E:BUFFERING")
            try:
                time.sleep(1/framerate)
            except ZeroDivisionError:
                time.sleep(0.1)
        else:
            time.sleep(0.1)


def receive_video():
    global video_data_length
    global aspect_ratio
    global width
    global height
    global display
    global video_list
    global selected_video_name
    global frame_buffer
    global framerate
    global orig_width
    global orig_height
    global all_frames_buffered
    while True:
        if video_data_length>0:
            #s_width=round(math.sqrt((orig_width/orig_height)*(video_data_length)/3))
            #s_height=round(math.sqrt((orig_height/orig_width)*(video_data_length)/3))
            s_width=orig_width
            s_height=orig_height
            frame_buffer.append([(s_width,s_height),read_video_frame_from_buffer(video_data_length-const_byte_len+2*sys.getsizeof("")-16)])
            video_data_length=0
        else:
            data=video_s.recv(17)
            if data.startswith(b"LENGTH"):
                data=data.decode()
                video_data_length=int(data.split("LENGTH:")[1])
            elif data.startswith(b"VE"):
                all_frames_buffered=True
        if framerate==0:
            frame_buffer=[]

def format_length(length):
    out_str=""
    for i in range(10-len(str(length))):
        out_str+="0"
    out_str+=str(length)
    return out_str

def send_data(connection,data):
    connection.send("LENGTH:{0}".format(format_length(sys.getsizeof(data))).encode("utf-8"))
    connection.send(data.encode('utf-8'))

def toggle_pause():
    global paused
    paused=not paused

def fast_forward():
    global previous_frames
    global frame_buffer
    global frame_updated
    for frame in frame_buffer[0:int(framerate)*10]:
        previous_frames.append(frame)
    frame_buffer=frame_buffer[int(framerate)*10:]
    frame_updated=True

def rewind():
    global previous_frames
    global frame_buffer
    global frame_updated
    load_frames=previous_frames
    load_frames.reverse()
    for frame in load_frames[:int(framerate)*10]:
        frame_buffer.insert(0,frame)
    previous_frames=previous_frames[0:-1*int(framerate)*10]
    frame_updated=True

def send_button_callback():
    global video_menu
    global toggle_pause_button
    global rewind_button
    global ff_button
    global media_control_frame
    global previous_frames
    global paused
    msg=""
    if main_button_text == "Play":
        msg="VN:"+selected_video_name.get()
    else:
        msg=sendText.get()
    try:
        send_data(command_s,msg)
        if main_button_text == "Play":
            b1.destroy()
            video_menu.destroy()
            media_control_frame=tkinter.Frame(main)
            toggle_pause_button=tkinter.Button(media_control_frame,text="\u23EF",command=toggle_pause)
            rewind_button=tkinter.Button(media_control_frame,text="\u23EA",command=rewind)
            ff_button=tkinter.Button(media_control_frame,text="\u23E9",command=fast_forward)
            toggle_pause_button.pack(side=tkinter.LEFT)
            rewind_button.pack(side=tkinter.LEFT)
            ff_button.pack(side=tkinter.LEFT)
            media_control_frame.pack()
    except ConnectionResetError:
        while True:
            connect(ip)
            time.sleep(5)

def getip():
    connect(ipent.get())

b1=tkinter.Button(main,text="Send",command=send_button_callback)
sendText=tkinter.Entry(main)
serverTextVar = tkinter.StringVar()
selected_video_name = tkinter.StringVar()
receiveText = tkinter.Label(main,textvariable=serverTextVar)
ipinf=tkinter.Label(main,text="Enter server IP")
ipent=tkinter.Entry(main)
ipbut=tkinter.Button(main,text="Enter",command=getip)
ipinf.pack()
ipent.pack()
ipbut.pack()
main.mainloop()
