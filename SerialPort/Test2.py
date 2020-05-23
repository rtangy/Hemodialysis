import matplotlib.pyplot as plt
import numpy as np


plt.ion()
fig = plt.figure()

xdata = [0]
ydata = [0]

#20个数据的list，用于自动调整坐标轴
AdjustList = []

MaxTime = 100
XFrom = 0
XEnd = 100
YFrom = 0
YEnd = 1
XMoveLen = XEnd/5

# for i in range(300):
#     ydata.append(i%10)
# with recently 20 value,auto adjuet axis value，
def AdjustAxisY(data):
    if len(AdjustList) < 20:
        AdjustList.append(data)
    else:
        global XEnd
        global XFrom
        global YFrom
        global YEnd

        Mindata = min(AdjustList)
        Maxdata = max(AdjustList)
        # 自动调整Y轴的起始与结束的刻度，比之前最大值要大1/5，比最小值要低1/5
        YFrom = Mindata - abs(Mindata/5)
        YEnd = Maxdata + abs(Maxdata/5)
        plt.axis([XFrom, XEnd, YFrom, YEnd])


def AdjustAxisX():
    global XFrom
    global XEnd
    if len(xdata) >= XEnd:
        XEnd = XEnd + XMoveLen
        XFrom = XFrom + XMoveLen
        plt.axis([XFrom, XEnd, YFrom, YEnd])



def DarwPic(XDataTemp,YDataTemp):
    xdata.append(XDataTemp)
    ydata.append(YDataTemp)
    plt.plot(xdata, ydata, label="$data$", color="red", linewidth=1)
    plt.pause(0.1)




#自动绘图加自动调整坐标轴
def AutoDraw(Xdata,Ydata):
    # tempdata = np.random.randint(0, 100)
    DarwPic(Xdata, Ydata)
    AdjustAxisX()
    AdjustAxisY(Ydata)



# 以下是绘制一个折线图，从0,100的随机数

plt.axis([XFrom, XEnd, YFrom, 100])
for i in range(200):
    AutoDraw(i,np.random.randint(0,10))

plt.ioff()
plt.show()

