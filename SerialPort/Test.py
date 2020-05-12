import pyqtgraph as pg
import numpy as np
import array

app = pg.mkQApp()#建立app
win = pg.GraphicsWindow()#建立窗口
win.setWindowTitle(u'pyqtgraph逐点画波形图')
win.resize(800, 500)#小窗口大小

data = array.array('d') #可动态改变数组的大小,double型数组
historyLength = 100#横坐标长度
p = win.addPlot()#把图p加入到窗口中
p.showGrid(x=True, y=True)#把X和Y的表格打开
p.setRange(xRange=[0,historyLength], yRange=[-1.2, 1.2], padding=0)
p.setLabel(axis='left', text='y / V')#靠左
p.setLabel(axis='bottom', text='x / point')
p.setTitle('y = sin(x)')#表格的名字
curve = p.plot()#绘制一个图形
idx = 0
def plotData():
    global idx#内部作用域想改变外部域变量
    tmp = np.sin(np.pi / 50 * idx)
    if len(data)<historyLength:
        data.append(tmp)
    else:
        data[:-1] = data[1:]#前移
        data[-1] = tmp
    curve.setData(data)
    idx += 1

timer = pg.QtCore.QTimer()
timer.timeout.connect(plotData) #定时调用plotData函数
timer.start(50) #多少ms调用一次

app.exec_()
