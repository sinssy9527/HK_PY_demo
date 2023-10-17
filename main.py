# coding=utf-8

import os
import platform
import tkinter
from tkinter import *
from HCNetSDK import *
from PlayCtrl import *
# from time import sleep
import time
from tkinter import simpledialog
from ctypes import create_string_buffer
from tkinter import *
from ctypes import *


#输出窗格
def submit_input():
    global DEV_IP, DEV_PORT, DEV_USER_NAME, DEV_PASSWORD
    def on_submit():
        global DEV_IP, DEV_PORT, DEV_USER_NAME, DEV_PASSWORD
        DEV_IP = create_string_buffer(bytes(e1.get(), 'utf-8'))
        DEV_PORT = int(e2.get())
        DEV_USER_NAME = create_string_buffer(bytes(e3.get(), 'utf-8'))
        DEV_PASSWORD = create_string_buffer(bytes(e4.get(), 'utf-8'))
        input_win.destroy()

# 初始化输入窗口
    input_win = tkinter.Tk()
    ww = 300
    wh = 300
    x = 800
    y = 300
    input_win.geometry("%dx%d+%d+%d" % (ww, wh, x, y))

    e1 = Entry(input_win)
    e2 = Entry(input_win)
    e3 = Entry(input_win)
    e4 = Entry(input_win)

    e1.grid(row=1, column=1)
    e2.grid(row=2, column=1)
    e3.grid(row=3, column=1)
    e4.grid(row=4, column=1)

    Label(input_win, text="请输入设备信息:").grid(row=0,padx=(25,0),pady=10)
    Label(input_win, text="IP地址：").grid(row=1,padx=(25,0),pady=5)
    Label(input_win, text="端口号：").grid(row=2,padx=(25,0),pady=5)
    Label(input_win, text="用户名：").grid(row=3,padx=(25,0),pady=5)
    Label(input_win, text="密码：").grid(row=4,padx=(25,0),pady=5)
    Button(input_win, text='提交',width=30, command=on_submit).grid(row=5,columnspan=2, padx=(40,0),pady=50)

    input_win.mainloop()

WINDOWS_FLAG = True
win = None  # 预览窗口
funcRealDataCallBack_V30 = None  # 实时预览回调函数，需要定义为全局的

PlayCtrl_Port = c_long(-1)  # 播放句柄
Playctrldll = None  # 播放库
FuncDecCB = None   # 播放库解码回调函数，需要定义为全局的



# 获取当前系统环境
def GetPlatform():
    sysstr = platform.system()
    print('' + sysstr)
    if sysstr != "Windows":
        global WINDOWS_FLAG
        WINDOWS_FLAG = False

# 设置SDK初始化依赖库路径
def SetSDKInitCfg():
    # 设置HCNetSDKCom组件库和SSL库加载路径
    # print(os.getcwd())
    if WINDOWS_FLAG:
        strPath = os.getcwd().encode('gbk')
        sdk_ComPath = NET_DVR_LOCAL_SDK_PATH()
        sdk_ComPath.sPath = strPath
        Objdll.NET_DVR_SetSDKInitCfg(2, byref(sdk_ComPath))
        Objdll.NET_DVR_SetSDKInitCfg(3, create_string_buffer(strPath + b'\libcrypto-1_1-x64.dll'))
        Objdll.NET_DVR_SetSDKInitCfg(4, create_string_buffer(strPath + b'\libssl-1_1-x64.dll'))
    else:
        strPath = os.getcwd().encode('utf-8')
        sdk_ComPath = NET_DVR_LOCAL_SDK_PATH()
        sdk_ComPath.sPath = strPath
        Objdll.NET_DVR_SetSDKInitCfg(2, byref(sdk_ComPath))
        Objdll.NET_DVR_SetSDKInitCfg(3, create_string_buffer(strPath + b'/libcrypto.so.1.1'))
        Objdll.NET_DVR_SetSDKInitCfg(4, create_string_buffer(strPath + b'/libssl.so.1.1'))

# 登录设备
def LoginDev(Objdll):
    # 登录注册设备
    device_info = NET_DVR_DEVICEINFO_V30()
    lUserId = Objdll.NET_DVR_Login_V30(DEV_IP, DEV_PORT, DEV_USER_NAME, DEV_PASSWORD, byref(device_info))
    return (lUserId, device_info)

def DecCBFun(nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
    # 解码回调函数
    if pFrameInfo.contents.nType == 3:
        # 解码返回视频YUV数据，将YUV数据转成jpg图片保存到本地
        # 如果有耗时处理，需要将解码数据拷贝到回调函数外面的其他线程里面处理，避免阻塞回调导致解码丢帧
        # sFileName = ('../../pic/test_stamp[%d].jpg'% pFrameInfo.contents.nStamp)
        nWidth = pFrameInfo.contents.nWidth
        nHeight = pFrameInfo.contents.nHeight
        nType = pFrameInfo.contents.nType
        dwFrameNum = pFrameInfo.contents.dwFrameNum
        nStamp = pFrameInfo.contents.nStamp
        # print(nWidth, nHeight, nType, dwFrameNum, nStamp, sFileName)
        # lRet = Playctrldll.PlayM4_ConvertToJpegFile(pBuf, nSize, nWidth, nHeight, nType, c_char_p(sFileName.encode()))
        #
        # if lRet == 0:
        #     print('PlayM4_ConvertToJpegFile fail, error code is:', Playctrldll.PlayM4_GetLastError(nPort))
        # else:
        #     print('PlayM4_ConvertToJpegFile success')

last_time = time.time()  # 上一次收到数据的时间
total_size = 0  # 已经接收到的数据总量
speed = "Speed: 0.00 bytes/sec"


def RealDataCallBack_V30(lPlayHandle, dwDataType, pBuffer, dwBufSize, pUser):
    global last_time
    global total_size
    global speed
    global win
    global cv

    # 计算已经过去的时间(单位：秒)
    elapsed_time = time.time() - last_time
    if elapsed_time > 1.0:  # 每隔一秒更新一次速率
        speed = "Speed: %.2f KB/sec" % (total_size / elapsed_time / 1024)
        win.title("%s" % speed)
        # 重置时间和数据量
        last_time = time.time()
        total_size = 0

    # 累计接收到的数据量
    total_size += dwBufSize
    # 码流回调函数
    if dwDataType == NET_DVR_SYSHEAD:
        # 设置流播放模式
        Playctrldll.PlayM4_SetStreamOpenMode(PlayCtrl_Port, 0)
        # 打开码流，送入40字节系统头数据
        if Playctrldll.PlayM4_OpenStream(PlayCtrl_Port, pBuffer, dwBufSize, 1024*1024):
            # 设置解码回调，可以返回解码后YUV视频数据
            global FuncDecCB
            FuncDecCB = DECCBFUNWIN(DecCBFun)
            Playctrldll.PlayM4_SetDecCallBackExMend(PlayCtrl_Port, FuncDecCB, None, 0, None)
            # 开始解码播放
            if Playctrldll.PlayM4_Play(PlayCtrl_Port, cv.winfo_id()):
                print(u'播放库播放成功')
            else:
                print(u'播放库播放失败')
        else:
            print(u'播放库打开流失败')
    elif dwDataType == NET_DVR_STREAMDATA:
        Playctrldll.PlayM4_InputData(PlayCtrl_Port, pBuffer, dwBufSize)
    else:
        print (u'其他数据,长度:', dwBufSize)

def OpenPreview(Objdll, lUserId, callbackFun):
    '''
    打开预览
    '''
    preview_info = NET_DVR_PREVIEWINFO()
    preview_info.hPlayWnd = 0
    preview_info.lChannel = 1  # 通道号
    preview_info.dwStreamType = 0  # 主码流
    preview_info.dwLinkMode = 0  # TCP
    preview_info.bBlocked = 1  # 阻塞取流

    # 开始预览并且设置回调函数回调获取实时流数据
    lRealPlayHandle = Objdll.NET_DVR_RealPlay_V40(lUserId, byref(preview_info), callbackFun, None)
    return lRealPlayHandle

def InputData(fileMp4, Playctrldll):
    while True:
        pFileData = fileMp4.read(4096)
        if pFileData is None:
            break

        if not Playctrldll.PlayM4_InputData(PlayCtrl_Port, pFileData, len(pFileData)):
            break
'''
-----这个是点击-响应-停止的云台控制函数--------
# 云台控制函数
# def ptz_control(command):
    # 开始云台控制
    lRet = Objdll.NET_DVR_PTZControl(lRealPlayHandle,command, 0)
    if lRet == 0:
        print ('Start ptz control fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
    else:
        print ('Start ptz control success')

    # 转动一秒
    sleep(0.5)

    # 停止云台控制
    lRet = Objdll.NET_DVR_PTZControl(lRealPlayHandle, command, 1)
    if lRet == 0:
        print('Stop ptz control fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
    else:
        print('Stop ptz control success')

'''
def start_ptz_control(command):
    global lRealPlayHandle
    # 开始云台控制
    lRet = Objdll.NET_DVR_PTZControl(lRealPlayHandle,command, 0)
    if lRet == 0:
        print ('Start ptz control fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
    else:
        print ('Start ptz control success')

def stop_ptz_control(command):
    global lRealPlayHandle
    # 停止云台控制
    lRet = Objdll.NET_DVR_PTZControl(lRealPlayHandle, command, 1)
    if lRet == 0:
        print('Stop ptz control fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
    else:
        print('Stop ptz control success')


def ptz_view(ptz_frame):
    # 云台上仰和左转
    ptz_button = Button(ptz_frame, text='↖')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(UP_LEFT))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(UP_LEFT))
    ptz_button.grid(row=0, column=1)

    # 云台上仰
    ptz_button = Button(ptz_frame, text=' ↑ ')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(TILT_UP))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(TILT_UP))
    ptz_button.grid(row=0, column=2)

    # 云台上仰和右转
    ptz_button = Button(ptz_frame, text='↗')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(UP_RIGHT))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(UP_RIGHT))
    ptz_button.grid(row=0, column=3)

    # 云台左转
    ptz_button = Button(ptz_frame, text='←')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(PAN_LEFT))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(PAN_LEFT))
    ptz_button.grid(row=1, column=1)

    # 云台中
    ptz_button = Button(ptz_frame, text='㊣')
    # ptz_button.bind('<Button-1>', lambda e: start_ptz_control(PAN_LEFT))
    # ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(PAN_LEFT))
    ptz_button.grid(row=1, column=2)

    # 云台下俯
    ptz_button = Button(ptz_frame, text='→')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(PAN_RIGHT))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(PAN_RIGHT))
    ptz_button.grid(row=1,  column=3)

    # 云台下俯和左转
    ptz_button = Button(ptz_frame, text='↙')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(DOWN_LEFT))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(DOWN_LEFT))
    ptz_button.grid(row=2, column=1)

    # 云台下俯
    ptz_button = Button(ptz_frame, text=' ↓ ')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(TILT_DOWN))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(TILT_DOWN))
    ptz_button.grid(row=2, column=2)

    # 云台下俯和右转
    ptz_button = Button(ptz_frame, text='↘')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(DOWN_RIGHT))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(DOWN_RIGHT))
    ptz_button.grid(row=2, column=3)

    # 焦距变大(倍率变大)
    ptz_button = Button(ptz_frame, text='变大')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(ZOOM_IN))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(DOWN_RIGHT))
    ptz_button.grid(row=3, column=1)

    # 焦距变小(倍率变小)
    ptz_button = Button(ptz_frame, text='变小')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(ZOOM_OUT))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(ZOOM_OUT))
    ptz_button.grid(row=3, column=2)

    # 焦距变小(倍率变小)
    ptz_button = Button(ptz_frame, text='前调')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(FOCUS_NEAR))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(FOCUS_NEAR))
    ptz_button.grid(row=4, column=1)

    # 焦距变小(倍率变小)
    ptz_button = Button(ptz_frame, text='后调')
    ptz_button.bind('<Button-1>', lambda e: start_ptz_control(FOCUS_FAR))
    ptz_button.bind('<ButtonRelease-1>', lambda e: stop_ptz_control(FOCUS_FAR))
    ptz_button.grid(row=4, column=2)

    # 设置按钮
    # button = tkinter.Button(root, text="设置", command=configure_device)
    # button.pack()
    #
    # root.mainloop()


def main_program():
    global DEV_IP
    global DEV_PORT
    global DEV_USER_NAME
    global DEV_PASSWORD
    global PlayCtrl_Port
    global FuncDecCB
    global cv
    global lRealPlayHandle
    global win
    submit_input()
    # 启用SDK写日志
    if Objdll.NET_DVR_SetLogToFile(2, bytes('../../log/', encoding="utf-8"), True):
        print("Set log file success")
    else:
        print("Set log file fail, error code: ", Objdll.NET_DVR_GetLastError())
    # 获取一个播放句柄

    if not Playctrldll.PlayM4_GetPort(byref(PlayCtrl_Port)):
        print(u'获取播放库句柄失败')
    # 登录判断
    (lUserId, device_info) = LoginDev(Objdll)
    print("登录注册代码：",lUserId)
    if lUserId < 0:
        err = Objdll.NET_DVR_GetLastError()
        print('Login device fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
        # 初始化DLL
        Objdll.NET_DVR_Init()
        # 释放资源
        Objdll.NET_DVR_Cleanup()
        # 登出设备
        Objdll.NET_DVR_Logout(lUserId)
        # 创建错误弹窗提醒
        error_win = tkinter.Tk()
        error_win.resizable(0, 0)
        error_win.title('登录失败')
        ww = 300
        wh = 300
        x = 800
        y = 300
        error_win.geometry("%dx%d+%d+%d" % (ww, wh, x, y))
        Label(error_win, text="登录失败!" ,fg="red").grid(row=0,sticky=NS,padx=(120,0),pady=(70,130))
        print("登录失败")

        def close_window():
            error_win.destroy()
            main_program()

        Button(error_win, text='重新登录', command=close_window).grid(row=1, sticky=NS, padx=(120,0))

        error_win.mainloop()

    else:
        win = tkinter.Tk()
        # 不可以改变大小
        win.resizable(0, 0)

        # 无边框的窗口
        # win.overrideredirect(True)

        sw = win.winfo_screenwidth()
        # 得到屏幕宽度
        sh = win.winfo_screenheight()
        # 得到屏幕高度

        # 窗口宽高
        ww = 908
        wh = 576

        x = (sw - ww) / 2
        y = (sh - wh) / 2
        win.geometry("%dx%d+%d+%d" % (ww, wh, x, y))

        # 创建退出按键
        # b = Button(win, text='退出', command=win.quit)
        # b.pack(side='bottom')


        # 创建一个预览窗口，设置其背景色为白色
        cv = tkinter.Canvas(win, bg='white', width=ww-120, height=wh)
        cv.grid(row=0, column=0)

        # 创建一个 Frame 用于放置云台控制按钮
        ptz_frame = tkinter.Frame(win)
        # 子窗口内容上对齐，并且向左缩进10，向上缩进2
        ptz_frame.grid(row=0, column=1, sticky='n', padx=(10, 0),pady=(10, 0))
        ptz_view(ptz_frame)
        # ip输入窗口
        # submit(ptz_frame)

        #
        #
        # # 登录设备
        # (lUserId, device_info) = LoginDev(Objdll)
        # if lUserId < 0:
        #     err = Objdll.NET_DVR_GetLastError()
        #     print('Login device fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
        #
        #     # 释放资源
        #     Objdll.NET_DVR_Cleanup()
        #
        #     # exit()

        # 定义码流回调函数
        funcRealDataCallBack_V30 = REALDATACALLBACK(RealDataCallBack_V30)
        # 开启预览
        lRealPlayHandle = OpenPreview(Objdll, lUserId, funcRealDataCallBack_V30)
        if lRealPlayHandle < 0:
            print ('Open preview fail, error code is: %d' % Objdll.NET_DVR_GetLastError())
            # 登出设备
            Objdll.NET_DVR_Logout(lUserId)
            # 释放资源
            Objdll.NET_DVR_Cleanup()
            # exit()

        # show Windows
        win.mainloop()

        # 关闭预览
        Objdll.NET_DVR_StopRealPlay(lRealPlayHandle)

        # 停止解码，释放播放库资源
        if PlayCtrl_Port.value > -1:
            Playctrldll.PlayM4_Stop(PlayCtrl_Port)
            Playctrldll.PlayM4_CloseStream(PlayCtrl_Port)
            Playctrldll.PlayM4_FreePort(PlayCtrl_Port)
            PlayCtrl_Port = c_long(-1)
            print("停止解码成功")

        # 登出设备
        Objdll.NET_DVR_Logout(lUserId)

        # 释放资源
        Objdll.NET_DVR_Cleanup()


if __name__ == '__main__':
    global DEV_IP
    global DEV_PORT
    global DEV_USER_NAME
    global DEV_PASSWORD
    # 获取系统平台
    GetPlatform()
    # 加载库,先加载依赖库
    if WINDOWS_FLAG:
        os.chdir(r'./lib/win')
        Objdll = ctypes.CDLL(r'./HCNetSDK.dll')  # 加载网络库
        Playctrldll = ctypes.CDLL(r'./PlayCtrl.dll')  # 加载播放库
    else:
        os.chdir(r'./lib/linux')
        Objdll = cdll.LoadLibrary(r'./libhcnetsdk.so')
        Playctrldll = cdll.LoadLibrary(r'./libPlayCtrl.so')

    SetSDKInitCfg()  # 设置组件库和SSL库加载路径

    # 初始化DLL
    Objdll.NET_DVR_Init()

    main_program()
