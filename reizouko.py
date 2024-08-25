# -*- coding: utf-8 -*-
from deepface import DeepFace
import cv2 as cv
import RPi.GPIO as GPIO
import time,os,requests

def send_line(picture,send_age): #line写真付きテキスト通知

    # LineNotify 連携用トークン・キー準備
    line_notify_token = "(情報保護のため開示しておりません。)"
    line_notify_api = "https://notify-api.line.me/api/notify"

    # payload・httpヘッダー設定
    payload = {"message": send_age}
    headers = {"Authorization": "Bearer " + line_notify_token}

    # 送信画像設定
    files = {"imageFile": open(picture,"rb")}  # バイナリファイルオープン

    # 送信
    line_notify = requests.post(line_notify_api, data=payload, headers=headers, files=files)


def send_line_txt(txt): #lineテキスト通知

    # LineNotify 連携用トークン・キー準備
    line_notify_token = "xtKFV7jXTgPM5IxdsMc5nJ3WVOjcOjMEyfp8XhZiNjR"
    line_notify_api = "https://notify-api.line.me/api/notify"

    # payload・httpヘッダー設定
    payload = {"message": txt}
    headers = {"Authorization": "Bearer " + line_notify_token}

    # 送信
    line_notify = requests.post(line_notify_api, data=payload, headers=headers)


def door_check(): #ドアの状態を確認（pigpio）
    door_result = GPIO.input(4)
    return door_result

def door_close(): #閉扉
    if GPIO.input(4) == 0:
        print("閉扉動作を開始")
        while GPIO.input(4) == 0:
            #ドアクローザーの電源ON
            GPIO.output(17, True); GPIO.output(27, False); GPIO.output(22, True)
            time.sleep(0.1)
        print("閉扉動作を完了")
        GPIO.output(17, False); GPIO.output(27, True); GPIO.output(22, True)
        time.sleep(1)
        GPIO.output(17, False); GPIO.output(27, False); GPIO.output(22, False)
    else:
        print("すでに閉扉")


def main():
    global img_no #顔写真保存番号
    global face #認識中に顔を検知した回数
    global face_try #認識の試行回数
    global now_age #JSON形式？の年齢推測結果
    global online #インターネット接続状況
    open_face = 0 #試行中に顔を1回以上検知した回数
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17,GPIO.OUT)
    GPIO.setup(27,GPIO.OUT)
    GPIO.setup(22,GPIO.OUT)
    GPIO.setup(23,GPIO.OUT)
    GPIO.setup(24,GPIO.OUT)
    GPIO.setup(25,GPIO.OUT)
    GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    GPIO.output(25, True)
    time.sleep(0.2)
    GPIO.output(24, True)
    time.sleep(0.2)
    GPIO.output(23, True)
    time.sleep(0.5)
    GPIO.output(25, False)
    time.sleep(0.2)
    GPIO.output(24, False)
    time.sleep(0.2)
    GPIO.output(23, False)
    response = os.system("ping -c 1 8.8.8.8") #googleへpingして応答があればオンラインモード
    if response == 0:
        print("GoogleへのPingに成功。オンラインモードで開始")
        send_line_txt("GoogleへのPingに成功。オンラインモードで開始")
        GPIO.output(25, True)
        time.sleep(1)
        GPIO.output(25, False)
        online = 1
    else:
        print("GoogleへのPingに失敗。オフラインモードで開始")
        GPIO.output(24, True)
        time.sleep(1)
        GPIO.output(24, False)
        online = 0

    while True:

        if GPIO.input(4) == 0:
            print("開扉中のため検出を開始(find face " + str(open_face) +  "times.)")
            face_analysis1()

            if face >= 1: #顔が一個以上あれば
                print("結果：顔は有り")
                face = 0
                open_face += 1
            else:

                if open_face >= 1: #連続した調査の結果，二回目で顔がなくなったなら
                    print("結果：顔が消失")
                    door_close()
                    if online == 1:
                        now_age = str(age("/home/pi/Desktop/face/" + str(img_no) + '.jpg'))
                        start_index = now_age.find('\'age\':') + len('\'age\':') #謎の表形式からageを求める
                        end_index = now_age.find(',', start_index)
                        age_value = int(now_age[start_index:end_index])
                        print(f"推測結果: {age_value}")
                        if age_value >= 37:
                            send_line("/home/pi/Desktop/face/" + str(img_no) + ".jpg","⚠️老人が冷蔵庫を開けたままにしたので閉扉しました⚠️")
                    else:
                        print("(オフライン)")
                    img_no += 1
                    open_face = 0
                else: #顔検知一回目で顔がなかったなら
                    print("結果：顔は無し")
                
        else:
            print("閉扉中")
            open_face = 0
        time.sleep(1)

def face_analysis1(): #カスケード分類器を利用した顔検出
    global img_no
    global face
    global face_try
    face_try = 0
    cap = cv.VideoCapture(0)
    GPIO.output(25, True)

    if not cap.isOpened():
        print("カメラ起動でエラー発生")
        GPIO.output(25, False)
        GPIO.output(23, True)
        time.sleep(5)
        GPIO.output(23, False)
        exit()

    cap.set(cv.CAP_PROP_FRAME_WIDTH, 512)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 384)

    while face_try <= 5:
        ret, frame = cap.read()

        if not ret:
            print("キャプチャでエラーが発生")
            GPIO.output(25, False)
            GPIO.output(23, True)
            time.sleep(5)
            GPIO.output(23, False)
            

        grayimg = cv.cvtColor(frame, cv.COLOR_BGR2GRAY) #負担軽減のため分類は白黒画像で。

        face_cascade = cv.CascadeClassifier(face_cas_path)
        facerect = face_cascade.detectMultiScale(grayimg, scaleFactor=1.2, minNeighbors=5, minSize=(1, 1))

        for rect in facerect:
            cv.rectangle(frame, tuple(rect[0:2]), tuple(rect[0:2]+rect[2:4]), (0, 0, 255), thickness=3)
            if len(facerect) > 0:
               print ("顔を検出")
               face += 1
               cv.imwrite(("/home/pi/Desktop/face/" + str(img_no) + ".jpg"), frame)
               GPIO.output(24, True)
            print("次のように画像を保存：" + str(img_no))
        
        face_try += 1
    
        #if face_try == 5:
        #    cv.imwrite(('C:\\Users\\soma_\\Desktop\\found\\' + str(img_no) + '.jpg'), frame)   これらは試行回数が5のとき強制的にキャプチャ。（デバッグ用）
        print(face_try)
        time.sleep(0.2)
        GPIO.output(24, False)
    GPIO.output(25, False)


def age(img_path): #深層学習を利用した年齢推測（オンライン時のみ）
    global now_age
    print("年齢の推測を開始")
    GPIO.output(25, True)
    time.sleep(0.2)
    GPIO.output(24, True)
    time.sleep(0.2)
    GPIO.output(23, True)
    img = cv.imread(img_path)
    img = cv.cvtColor(img, cv.COLOR_BGR2RGB)  # BGRからRGBに変換
    demography = DeepFace.analyze(img, actions=["age"], enforce_detection=False)
    now_age = demography
    GPIO.output(25, False)
    time.sleep(0.2)
    GPIO.output(24, False)
    time.sleep(0.2)
    GPIO.output(23, False)
    return(demography)

now_age = 0
face_try = 0
face = 0
img_no = 0
online = 0
face_cas_path = "/home/pi/Desktop/haarcascade_frontalface_alt2.xml" #顔の分類器のパスを指定

if __name__ == "__main__":
    try:
        print("AI冷蔵庫V311_起動完了。Ctr+Cでプログラム終了")
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("FINISH")
