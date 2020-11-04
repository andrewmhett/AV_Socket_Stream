import socket
import tkinter
import threading
import atexit
import sys
import pygame
import time

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
    try:
        command_s.connect((ip,command_port))
        video_s.connect((ip,video_port))
        server_ip=ip
        ipinf.destroy()
        ipent.destroy()
        ipbut.destroy()
        receiveText.pack()
        sendText.pack()
        b1.pack()
        threading.Thread(target=receive_video).start()
        threading.Thread(target=receive_command).start()
    except Exception as e:
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

def read_video_frame_from_buffer(length):
    data=b""
    counter=0
    while counter<(length-length%2048):
        counter+=2048
        data+=video_s.recv(2048)
    tmp_data=b""
    for i in range(length-sys.getsizeof(data)):
        while tmp_data == b"":
            tmp_data=video_s.recv(1)
        data+=tmp_data
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
    while display != None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                display=None
                send_data(command_s,"VQ")
                toggle_pause_button.destroy()
                ff_button.destroy()
                media_control_frame.destroy()
                rewind_button.destroy()
                video_menu=tkinter.OptionMenu(main, selected_video_name, *(video_list))
                video_menu.pack()
                b1=tkinter.Button(main,text=main_button_text,command=send_button_callback)
                b1.pack()
            if event.type == pygame.VIDEORESIZE:
                width=int(event.w)
                height=int(event.w/aspect_ratio)
                pygame.display.set_mode((width,height),pygame.RESIZABLE)
        time.sleep(.1)

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
    while True:
        if command_data_length>0:
            data=command_s.recv(command_data_length-49).decode()
            print(data)
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
                width=int(data.split("VI:")[1].split(",")[0])
                height=int(data.split("VI:")[1].split(",")[1])
                orig_width=width
                orig_height=height
                aspect_ratio=width/height
                display=pygame.display.set_mode((int(width),int(height)),pygame.RESIZABLE)
                threading.Thread(target=track_pygame_events).start()
                pygame.display.flip()
            if data=="VE":
                pygame.display.quit()
                display=None
                toggle_pause_button.destroy()
                ff_button.destroy()
                media_control_frame.destroy()
                rewind_button.destroy()
                video_menu=tkinter.OptionMenu(main, selected_video_name, *(video_list))
                video_menu.pack()
                b1=tkinter.Button(main,text=main_button_text,command=send_button_callback)
                b1.pack()
            command_data_length=0
        else:
            data=command_s.recv(17)
            if data.startswith(b"LENGTH"):
                data=data.decode()
                command_data_length=int(data.split("LENGTH:")[1])

def update_screen(byte_data):
    global width
    global height
    global orig_width
    global orig_height
    try:
        display.blit(pygame.transform.scale(pygame.image.frombuffer(byte_data,(orig_width,orig_height),"RGB"),(width,height)),(0,0))
        pygame.display.flip()
    except Exception:
        pass

def receive_video():
    global video_data_length
    global aspect_ratio
    global width
    global height
    global display
    global video_list
    global selected_video_name
    while True:
        if video_data_length>0:
            if display != None:
                if pygame.display.get_init():
                    try:
                        data=read_video_frame_from_buffer(video_data_length)
                        threading.Thread(target=update_screen,args=[data,]).start()
                    except pygame.error:
                        pass
            video_data_length=0
        else:
            data=video_s.recv(17)
            if data.startswith(b"LENGTH"):
                data=data.decode()
                video_data_length=int(data.split("LENGTH:")[1])

def format_length(length):
    out_str=""
    for i in range(10-len(str(length))):
        out_str+="0"
    out_str+=str(length)
    return out_str

def send_data(connection,data):
    connection.send("LENGTH:{0}".format(format_length(sys.getsizeof(data))).encode("utf-8"))
    connection.send(data.encode('utf-8'))

def send_button_callback():
    global video_menu
    global toggle_pause_button
    global rewind_button
    global ff_button
    global media_control_frame
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
            toggle_pause_button=tkinter.Button(media_control_frame,text="\u23EF",command=lambda: send_data(command_s,"C:TOGGLE_PAUSE"))
            rewind_button=tkinter.Button(media_control_frame,text="\u23EA",command=lambda: send_data(command_s,"C:REWIND"))
            ff_button=tkinter.Button(media_control_frame,text="\u23E9",command=lambda: send_data(command_s,"C:FAST_FORWARD"))
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
