"""Chinese Text TOP controls with transparent native click targets.

Parameter COMP uses its own UI font and dropped CJK glyphs on this machine.
One explicitly-fonted text texture renders the complete control surface.
"""
panel=view.create(containerCOMP,'controls')
panel.par.x,panel.par.y,panel.par.w,panel.par.h=1000,130,280,440
table=scene.create(tableDAT,'control_labels')
table.clear()
table.appendRow(['x','y','text'])
text=scene.create(textTOP,'control_text')
text.par.specdat=table
text.par.text=''
text.par.resolutionw,text.par.resolutionh=280,440
text.par.font='Microsoft YaHei'
text.par.fontsizex=12
text.par.alignx='left'
text.par.aligny='center'
text.par.bgcolorr,text.par.bgcolorg,text.par.bgcolorb,text.par.bgalpha=.022,.032,.055,1
panel.par.top=text
rows=[('Mode','输入方式'),('Camera','摄像头'),('Mirror','镜像画面'),
      ('Interactionmode','操作模式'),('Rotationsensitivity','旋转灵敏度'),('Resetview','复位视角'),
      ('Sensitivity','移动灵敏度'),('Count','银河粒子'),('Glow','辉光强度'),
      ('Trail','拖尾长度'),('Palette','星系配色'),('Simpose','模拟手势'),
      ('Simscale','模拟缩放'),('Reconnect','重新连接摄像头'),('Reset','重置银河'),
      ('Fullscreen','全屏 / 返回'),('Benchmark','开始 10 分钟测试'),('Stoptest','停止测试记录')]
numeric={'Sensitivity','Glow','Trail','Simscale','Rotationsensitivity'}
pulses={'Reset','Resetview','Reconnect','Fullscreen','Benchmark','Stoptest'}
def target(name,x,y,width,direction):
    button=panel.create(containerCOMP,name+('_minus' if direction<0 else '_plus'))
    button.par.x,button.par.y,button.par.w,button.par.h=x,y,width,23
    button.par.bgalpha=0
    callback=scene.create(panelexecuteDAT,'click_'+button.name)
    callback.par.panels=button
    callback.par.panelvalue='lselect'
    callback.par.offtoon=True
    callback.par.ontooff=False
    callback.par.valuechange=False
    callback.text="def onOffToOn(panelValue):\n    op('runtime').module.ui_action(%r,%d)\n"%(name,direction)

for index,(name,label) in enumerate(rows):
    y=420-index*23
    table.appendRow([12,y,'[ '+label+' ]' if name in pulses else label])
    table.appendRow([162 if name in numeric else 126,y,''])
    if name in numeric:
        table.appendRow([123,y,'−'])
        table.appendRow([254,y,'＋'])
        target(name,110,y-11,40,-1)
        target(name,240,y-11,40,1)
    else:
        target(name,0,y-11,280,1)
table.appendRow([15,12,'点击切换  ·  − / ＋ 调整数值'])
panel.store('row_names',[name for name,label in rows])
