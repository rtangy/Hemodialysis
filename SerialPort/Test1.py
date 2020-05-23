import pyqtgraph as pg
import array
import serial
import threading
import numpy as np
from queue import Queue
import time


i = 0
q = Queue(maxsize=0)
def Serial():
    global i;
    global q;
    while(True):
        n = mSerial.inWaiting()
        if(n):
            dat = int.from_bytes(mSerial.readline(1),byteorder='little')  # 格式转换
            if(dat>>7):
                dat =256-dat
                dat =0-dat
            q.put(dat)

def plotData():
    global i;
    if i < historyLength:
        data[i] = q.get()
        i = i+1
    else:
        data[:-1] = data[1:]
        data[i-1] = q.get()
    curve.setData(data)


if __name__ == "__main__":
    app = pg.mkQApp()  # 建立app
    win = pg.GraphicsWindow()  # 建立窗口
    win.setWindowTitle(u'pyqtgraph逐点画波形图')
    win.resize(800, 500)  # 小窗口大小
    data = array.array('i')  # 可动态改变数组的大小,double型数组
    historyLength = 100  # 横坐标长度
    a = 0
    data=np.zeros(historyLength).__array__('d')#把数组长度定下来
    p = win.addPlot()  # 把图p加入到窗口中
    p.showGrid(x=True, y=True)  # 把X和Y的表格打开
    p.setRange(xRange=[0, historyLength], yRange=[-50, 50], padding=0)
    p.setLabel(axis='left', text='y / V')  # 靠左
    p.setLabel(axis='bottom', text='x / point')
    p.setTitle('semg')  # 表格的名字
    curve = p.plot()  # 绘制一个图形
    curve.setData(data)
    portx = 'COM25'
    bps = 19200
    # 串口执行到这已经打开 再用open命令会报错
    mSerial = serial.Serial(portx, int(bps))
    if (mSerial.isOpen()):
        dat = 0xff;
        dat >> 2;
        print("open success")
        # 向端口些数据 字符串必须译码
        mSerial.write("hello".encode())
        mSerial.flushInput()  # 清空缓冲区
    else:
        print("open failed")
        serial.close()  # 关闭端口
    th1 = threading.Thread(target=Serial)
    th1.start()
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(plotData)  # 定时刷新数据显示
    timer.start(1)  # 多少ms调用一次
    app.exec_()
