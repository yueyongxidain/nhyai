#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main
@author: chineseocr
@mail: chineseocr@hotmail.com
adjust ocr ,ouput char prob
"""

from dnn.ocr import predict  as ocrModel
from dnn.text import detect_lines as textModel
from PIL import Image
import numpy as np
import os
import cv2
from django.conf import settings

def solve(box):
     """
     绕 cx,cy点 w,h 旋转 angle 的坐标
     x = cx-w/2
     y = cy-h/2
     x1-cx = -w/2*cos(angle) +h/2*sin(angle)
     y1 -cy= -w/2*sin(angle) -h/2*cos(angle)

     h(x1-cx) = -wh/2*cos(angle) +hh/2*sin(angle)
     w(y1 -cy)= -ww/2*sin(angle) -hw/2*cos(angle)
     (hh+ww)/2sin(angle) = h(x1-cx)-w(y1 -cy)

     """
     x1,y1,x2,y2,x3,y3,x4,y4= box[:8]
     cx = (x1+x3+x2+x4)/4.0
     cy = (y1+y3+y4+y2)/4.0
     w = (np.sqrt((x2-x1)**2+(y2-y1)**2)+np.sqrt((x3-x4)**2+(y3-y4)**2))/2
     h = (np.sqrt((x2-x3)**2+(y2-y3)**2)+np.sqrt((x1-x4)**2+(y1-y4)**2))/2
     #x = cx-w/2
     #y = cy-h/2
     sinA = (h*(x1-cx)-w*(y1 -cy))*1.0/(h*h+w*w)*2
     angle = np.arcsin(sinA)
     return angle,w,h,cx,cy


def rotate_cut_img(im,box,leftAdjust=0.0,rightAdjust=0.0):
    x1,y1,x2,y2,x3,y3,x4,y4 = box[:8]
    degree,w,h,x_center,y_center = solve(box)
    xmin_ = min(box[0::2])
    xmax_ = max(box[0::2])
    ymin_ = min(box[1::2])
    ymax_ = max(box[1::2])
    x_center = x_center-xmin_
    y_center =y_center-ymin_
    im = im.crop([xmin_,ymin_,xmax_,ymax_])
    degree_ = degree*180.0/np.pi
    xmin = max(1,x_center-w/2-leftAdjust*(w/2))
    ymin =y_center-h/2
    xmax = min(x_center+w/2+rightAdjust*(w/2),im.size[0]-1)
    ymax = y_center+h/2
    newW = xmax-xmin
    newH = ymax-ymin
    tmpImg = im.rotate(degree_,center=(x_center,y_center)).crop([xmin,ymin,xmax,ymax])
    box = {'cx':x_center+xmin_,'cy':y_center+ymin_,'w':newW,'h':newH,'degree':degree_}
    return tmpImg

def draw_boxes(im,boxes):
    for box in boxes:
        x1,y1,x2,y2,x3,y3,x4,y4 = box[:8]
        rectPoints = [[int(x1),int(y1)], [int(x2),int(y2)],[int(x3),int(y3)],[int(x4),int(y4)]]
        # print (rectPoints)

        # BGR定义
        rectColour = (255, 0, 0)
        cv2.line(im, tuple(rectPoints[0]), tuple(rectPoints[1]), rectColour)
        cv2.line(im, tuple(rectPoints[1]), tuple(rectPoints[2]), rectColour)
        cv2.line(im, tuple(rectPoints[2]), tuple(rectPoints[3]), rectColour)
        cv2.line(im, tuple(rectPoints[3]), tuple(rectPoints[0]), rectColour)

    return im

def text_ocr(img,scale,maxScale,TEXT_LINE_SCORE, filePath, fileName):
    try:
        boxes,scores = textModel(img,scale=scale,maxScale=maxScale)
        result = []
        drawBoxes = []
        draw_filename = fileName.split('.')[0] + '_drawed.' + fileName.split('.')[1]
        drawPath = os.path.join(filePath,draw_filename)
        drawUrl = settings.FILE_URL +  settings.MEDIA_URL + 'photos' + '/' + draw_filename
        im= Image.fromarray(img)
        for i,box in enumerate(boxes):
            if scores[i]>TEXT_LINE_SCORE:
                drawBoxes.append(box)
                tmpImg = rotate_cut_img(im,box,leftAdjust=0.01,rightAdjust=0.01)
                # tmpPath = os.path.join(os.getcwd(),"backend","api","handwrite","test", str(i) + '.jpg')
                # tmpImg.save(tmpPath, quality=95)
                text = ocrModel(tmpImg)
                if text['text']!='':
                    text['box'] = [ int(x) for x in box]
                    text['textprob']=round(float(scores[i]),2)
                    result.append(text)
        result = sorted(result,key=lambda x:sum(x['box'][1::2]))

        #draw box in to original image
        if len(drawBoxes) > 0:
            drawImg = draw_boxes(img,drawBoxes)
            # drawPath = os.path.join(os.getcwd(),"backend","api","handwrite","test","draw.jpg")
            cv2.imwrite(drawPath, drawImg)

    except:
        result = [{
            "text": '不支持的文件内容',
            "box": [],
            "drawUrl": ''
        }]
    return result,drawUrl

