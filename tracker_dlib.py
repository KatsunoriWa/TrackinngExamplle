#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=C0103
# Python 2/3 compatibility
from __future__ import print_function
import sys
import os
import time
import numpy as np
import cv2
import dlib

import librect
import libtracker


if __name__ == '__main__':
    import getopt
    optlist, sys.argv[1:] = getopt.getopt(sys.argv[1:], '', ['crop', 'align', 'saveFull'])
    if len(sys.argv) == 1:
        print("""usage:%s  [--crop] (moviefile | uvcID)
--crop: enable crop
--align: enable aligne
--saveFull: save full image
        """ % sys.argv[0])
        print("cv2.__version__", cv2.__version__)
        sys.exit()


    try:
        num = int(sys.argv[1])
        video = cv2.VideoCapture(num)
    except:
        video = cv2.VideoCapture(sys.argv[1])

    if not video.isOpened():
        print("Could not open video")
        sys.exit()

    fullImgDir = "fullImg"
    if not os.path.isdir(fullImgDir):
        os.makedirs(fullImgDir)

    ok, frame = video.read()
    if not ok:
        print('Cannot read video file')
        sys.exit()

    librect.test_overlapRegion()
    librect.test_getIoU()


    #<dlib>
    detector = dlib.get_frontal_face_detector()
    numUpSampling = 0


    dets, scores, idx = detector.run(frame, numUpSampling)
    rects = librect.dets2rects(dets)
    #</dlib>

    print(rects)

    tracker_types = ['BOOSTING', 'MIL', 'KCF', 'TLD', 'MEDIANFLOW', 'GOTURN']
    tracker_type = tracker_types[2]

    trackers = range(len(rects))

    for i, rect in enumerate(rects):
        trackers[i] = libtracker.TrackerWithState(tracker_type)
        ok = trackers[i].init(frame, tuple(rects[i]))

    counter = 0

    interval = 4

    color = {True:(0, 0, 255), False:(255, 0, 0)}
    while True:
        ok, frame = video.read()
        if not ok:
            break

        frameCopy = frame+0

        doDetect = (counter % interval == interval - 1)

        indexes = range(len(trackers))
        indexes.reverse()
        for i in indexes:
            tracker = trackers[i]
            #  追跡する。
            trackOk, bbox = tracker.update(frame)
            if trackOk:            # Tracking success
                p1 = (int(bbox[0]), int(bbox[1]))
                p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                cv2.rectangle(frame, p1, p2, color[doDetect], 2, 1)

                left, top, w, h = bbox
                right, bottom = left+w, top+h
                det = dlib.rectangle(long(left), long(top), long(right), long(bottom))
                stateStr = {True:"detect  frame", False:"no detect  frame"}
                cv2.putText(frame, stateStr[doDetect], (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color[doDetect], 2)
            else:
                del trackers[i]
                print("""del trackers["%d"] """ % i)
                cv2.putText(frame, "Tracking failure detected", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                continue


        if doDetect:
            #<dlib>
            dets, scores, idx = detector.run(frame, numUpSampling)
            faces = dlib.full_object_detections()

            for face in faces:
                alignedImg = dlib.get_face_chip(frameCopy, face, size=320, padding=0.5)
                alignedImg = np.array(alignedImg, dtype=np.uint8)
                cv2.imshow('alignedImg', alignedImg)
                k = cv2.waitKey(1) & 0xff
                if k == ord('q') or k == 27:
                    break

            rects = librect.dets2rects(dets)
            print(rects, scores, idx)
            #</dlib>

            # どれかの検出に重なっているかを調べる。
            # 一番重なりがよいのを見つける。
            # 一番重なりがよいものが、しきい値以上のＩｏＵだったら、追跡の位置を初期化する。
            # 一番の重なりのよいものが一定値未満だったら、新規の追跡を開始する。
            states = [(t.ok, t.bbox) for t in trackers]
            alreadyFounds, asTrack = librect.getBestIoU(rects, states)

            for j, rect in enumerate(rects):# 検出について
                if alreadyFounds[j] > 0.5:
                    # 十分に重なっていて検出結果で追跡を置き換える。
                    print(librect.rect2bbox(rect), "# rect2bbox(rect)")
                    ok = trackers[asTrack[j]].init(frame, librect.rect2bbox(rect))
                    left, top, w, h = rect
                    right, bottom = left+w, top+h
                    det = dlib.rectangle(left, top, right, bottom)
                    [left, right, top, bottom] = [det.left(), det.right(), det.top(), det.bottom()]
                elif alreadyFounds[j] < 0.5 - 0.1:
                    # 対応する追跡がないとして、新規の検出にする。
                    tracker = libtracker.TrackerWithState(tracker_type)
                    ok = tracker.init(frame, librect.rect2bbox(rects[j]))
                    trackers.append(tracker)
                    print("new tracking")
                    print(librect.rect2bbox(rect), "# rect2bbox(rect) new tracking")
                    left, top, w, h = rects[j]
                    right, bottom = left+w, top+h
                    det = dlib.rectangle(left, top, right, bottom)
                else:
                    [left, right, top, bottom] = [det.left(), det.right(), det.top(), det.bottom()]


        cv2.putText(frame, tracker_type + " Tracker", (100, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);
        cv2.putText(frame, "# of Trackers = %d" % len(trackers), (100, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);


        cv2.namedWindow("Tracking q:quit", cv2.WINDOW_NORMAL)
        cv2.imshow("Tracking q:quit", frame)
        counter += 1
        k = cv2.waitKey(1) & 0xff
        if k == ord('q') or k == 27:
            break

    cv2.destroyAllWindows()
    video.release()